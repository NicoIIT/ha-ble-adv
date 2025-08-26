"""BLE ADV Coordinator."""

from __future__ import annotations

import logging
import sys
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any

from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.system_info import async_get_system_info

from .adapters import BleAdvBtHciManager, BleAdvQueueItem
from .codecs.models import BleAdvAdvertisement, BleAdvCodec, BleAdvConfig, BleAdvEntAttr
from .const import DOMAIN
from .esp_adapters import BleAdvEspBtManager

_LOGGER = logging.getLogger(__name__)


class MatchingCallback(ABC):
    """Base MatchingCallback class."""

    @abstractmethod
    async def handle(self, codec_id: str, match_id: str, adapter_id: str, config: BleAdvConfig, ent_attrs: list[BleAdvEntAttr]) -> None:
        """Implement Action."""


class BleAdvCoordinator:
    """Class to manage fetching any BLE ADV data."""

    def __init__(
        self,
        hass: HomeAssistant,
        codecs: dict[str, BleAdvCodec],
        ign_adapters: list[str],
        ign_duration: int,
        ign_cids: list[int],
        ign_macs: list[str],
    ) -> None:
        """Init."""
        self.hass: HomeAssistant = hass
        self.codecs: dict[str, BleAdvCodec] = codecs
        self.ign_cids: set[int] = set(ign_cids)
        self.ign_macs: set[str] = set(ign_macs)
        self.ign_duration: int = ign_duration
        self.ign_adapters = ign_adapters

        self._last_advs: dict[str, dict[bytes, datetime]] = {}
        self._callbacks: dict[str, MatchingCallback] = {}
        self._hci_bt_manager: BleAdvBtHciManager = BleAdvBtHciManager(self.handle_raw_adv, ign_adapters)
        self._esp_bt_manager: BleAdvEspBtManager = BleAdvEspBtManager(self.hass, self.handle_raw_adv, ign_duration, ign_cids, ign_macs)

        self._stop_listening_time: datetime | None = None
        self.listened_raw_advs: list[bytes] = []
        self.listened_decoded_confs: list[tuple[str, str, str, BleAdvConfig]] = []

    async def async_init(self) -> None:
        """Async Init."""
        await self._esp_bt_manager.async_init()
        self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self.on_stop_event)
        if not self._hci_bt_manager.supported_by_host:
            _LOGGER.info(f"Host BT Stack cannot be used as OS {sys.platform} does not support it")
            return
        try:
            await self._hci_bt_manager.async_init()
        except BaseException:
            _LOGGER.exception("Host BT Stack cannot be used")

    async def async_final(self) -> None:
        """Async Final: Clean-up."""
        _LOGGER.info("Cleaning BT Connections.")
        await self._hci_bt_manager.async_final()
        await self._esp_bt_manager.async_final()

    def get_adapter_ids(self) -> list[str]:
        """List bt adapters."""
        return list(self._hci_bt_manager.adapters.keys()) + list(self._esp_bt_manager.adapters.keys())

    def has_available_adapters(self) -> bool:
        """Check if the coordinator has available adapters."""
        return len(self._hci_bt_manager.adapters) > 0 or len(self._esp_bt_manager.adapters) > 0

    async def on_stop_event(self, _: Event) -> None:
        """Act on stop event."""
        await self.async_final()

    def is_listening(self) -> bool:
        """Return if listening."""
        if self._stop_listening_time is not None and datetime.now() > self._stop_listening_time:
            self._stop_listening_time = None
        return self._stop_listening_time is not None

    def start_listening(self, max_duration: float) -> None:
        """Start listening to raw and decoded ADVs."""
        self._stop_listening_time = datetime.now() + timedelta(seconds=max_duration)
        self.listened_raw_advs.clear()
        self.listened_decoded_confs.clear()

    async def register_callback(self, callback_id: str, callback: MatchingCallback) -> None:
        """Register a matching callback by its id."""
        self._callbacks[callback_id] = callback
        _LOGGER.debug(f"Registered callback with id '{callback_id}': {callback}")

    async def unregister_callback(self, callback_id: str) -> None:
        """Unregister a callback by its id."""
        self._callbacks.pop(callback_id)
        _LOGGER.debug(f"Unregistered callback with id '{callback_id}'")

    async def advertise(self, adapter_id: str | None, queue_id: str, qi: BleAdvQueueItem) -> None:
        """Advertise."""
        for last_advs in self._last_advs.values():
            last_advs[bytes(qi.data)] = datetime.now()  # do not re process in case re listen by another adapter
        if adapter_id in self._hci_bt_manager.adapters:
            await self._hci_bt_manager.adapters[adapter_id].enqueue(queue_id, qi)
        elif adapter_id in self._esp_bt_manager.adapters:
            await self._esp_bt_manager.adapters[adapter_id].enqueue(queue_id, qi)
        else:
            _LOGGER.error(f"Cannot process advertising: adapter '{adapter_id}' is not available.")

    async def handle_raw_adv(self, adapter_id: str, orig: str, raw_adv: bytes) -> None:
        """Handle a raw advertising."""
        try:
            # check if the received orig is in the ignored macs
            if orig in self.ign_macs:
                return

            # clean-up last advs for this adapter (keep only the ones received less than self.ign_duration ms ago)
            if adapter_id not in self._last_advs:
                self._last_advs[adapter_id] = {}
            limit_creation = datetime.now() - timedelta(milliseconds=self.ign_duration)
            self._last_advs[adapter_id] = {x: y for x, y in self._last_advs[adapter_id].items() if (y > limit_creation)}

            # check if the full raw one received is a dupe of another one received
            skip = raw_adv in self._last_advs[adapter_id]
            self._last_advs[adapter_id][raw_adv] = datetime.now()
            if skip:
                return

            # Parse the raw data and find the relevant info
            if (adv := BleAdvAdvertisement.FromRaw(raw_adv)) is None:
                await self._on_new_raw_received(adapter_id, orig, raw_adv)
                return

            # Exclude by Company ID
            if int.from_bytes(adv.raw[:2], "little") in self.ign_cids:
                return

            # check if the parsed raw one received is a dupe of another one recently received
            skip = adv.raw in self._last_advs[adapter_id]
            self._last_advs[adapter_id][adv.raw] = datetime.now()
            if skip:
                return

            await self._on_new_raw_received(adapter_id, orig, raw_adv)

            for codec_id, acodec in self.codecs.items():
                enc_cmd, conf = acodec.decode_adv(adv)
                if conf is not None and enc_cmd is not None:
                    await self._on_new_decoded_received(adapter_id, orig, codec_id, acodec.match_id, conf)
                    ent_attrs = acodec.enc_to_ent(enc_cmd)
                    _LOGGER.debug(f"[{adapter_id}][{codec_id}] {conf} / {enc_cmd} / {ent_attrs}")
                    for device_callback in self._callbacks.values():
                        await device_callback.handle(codec_id, acodec.match_id, adapter_id, conf, ent_attrs)

        except Exception:
            _LOGGER.exception(f"[{adapter_id}] Exception handling raw adv message")

    async def _on_new_raw_received(self, adapter_id: str, orig: str, raw_adv: bytes) -> None:
        _LOGGER.debug(f"[{adapter_id}][{orig}] BLE ADV received - RAW - {raw_adv.hex('.').upper()}")
        if self.is_listening():
            self.listened_raw_advs.append(raw_adv)

    async def _on_new_decoded_received(self, adapter_id: str, _: str, codec_id: str, match_id: str, conf: BleAdvConfig) -> None:
        if self.is_listening():
            self.listened_decoded_confs.append((adapter_id, codec_id, match_id, conf))

    def diagnostic_dump(self) -> dict[str, Any]:
        """Dump diagnostc dict."""
        return {
            "hci": self._hci_bt_manager.diagnostic_dump(),
            "esp": self._esp_bt_manager.diagnostic_dump(),
            "codec_ids": list(self.codecs.keys()),
            "ign_adapters": self.ign_adapters,
            "ign_duration": self.ign_duration,
            "ign_cids": list(self.ign_cids),
            "ign_macs": list(self.ign_macs),
        }

    async def full_diagnostic_dump(self) -> dict[str, Any]:
        """Dump Full diagnostic dict including system data."""
        hass_sys_info = await async_get_system_info(self.hass)
        hass_sys_info["run_as_root"] = hass_sys_info["user"] == "root"
        del hass_sys_info["user"]
        entries = {entry_id: self.hass.config_entries.async_get_entry(entry_id) for entry_id in self.hass.data.get(DOMAIN, {})}
        return {"home_assistant": hass_sys_info, "coordinator": self.diagnostic_dump(), "entries": entries}
