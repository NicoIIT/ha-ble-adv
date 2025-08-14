"""BLE ADV Coordinator."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant

from .adapters import AdvRecvCallback, BleAdvAdapter, BleAdvBtManager, BleAdvQueueItem
from .codecs.models import BleAdvAdvertisement, BleAdvCodec, BleAdvConfig, BleAdvEntAttr, as_hex
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ESPHOME_DOMAIN = "esphome"
ESPHOME_BLE_ADV_DISCOVERY_EVENT = f"{ESPHOME_DOMAIN}.{DOMAIN}.discovery"
CONF_ATTR_RAW = "raw"
CONF_ATTR_NAME = "name"
CONF_ATTR_MAC = "mac"
CONF_ATTR_DURATION = "duration"
CONF_ATTR_RECV_EVENT_NAME = "adv_recv_event"
CONF_ATTR_PUBLISH_ADV_SVC = "publish_adv_svc"


class CoordinatorError(Exception):
    """Coordinator Exception."""


class MatchingCallback(ABC):
    """Base MatchingCallback class."""

    @abstractmethod
    async def handle(self, codec_id: str, match_id: str, adapter_id: str, config: BleAdvConfig, ent_attrs: list[BleAdvEntAttr]) -> None:
        """Implement Action."""
        raise CoordinatorError("Not Implemented")


class BleAdvEsphomeAdapter(BleAdvAdapter):
    """ESPHome BT Adapter."""

    def __init__(
        self,
        hass: HomeAssistant,
        conf: dict[str, str],
        on_adv_recv: AdvRecvCallback,
    ) -> None:
        super().__init__(conf[CONF_ATTR_NAME], self._on_error)
        self._conf = conf
        self.hass = hass
        self._on_adv_recv = on_adv_recv

    async def open(self) -> None:
        """Open adapter."""
        self._unreg_listen = self.hass.bus.async_listen(self._conf[CONF_ATTR_RECV_EVENT_NAME], self._on_adv_recv_event)
        self.logger.info(f"ESPHome ble_adv_proxy connected: {self.name}")

    def close(self) -> None:
        """Close the adapter, nothing to do."""
        self._unreg_listen()

    async def _on_error(self, message: str) -> None:
        self.logger.warning(f"Unhandled error: {message}")

    async def _on_adv_recv_event(self, event: Event) -> None:
        """Act on Adv Received event."""
        self.logger.debug(f"ESPHome ADV recv Event: {event.data}")
        await self._on_adv_recv(self.name, bytes.fromhex(event.data[CONF_ATTR_RAW]))

    async def _advertise(self, interval: int, data: bytes) -> None:
        """Advertise the msg."""
        await self.hass.services.async_call(
            ESPHOME_DOMAIN, self._conf[CONF_ATTR_PUBLISH_ADV_SVC], {CONF_ATTR_RAW: data.hex(), CONF_ATTR_DURATION: 3 * interval}
        )
        await asyncio.sleep(0.0028 * interval)


class BleAdvCoordinator:
    """Class to manage fetching any BLE ADV data."""

    def __init__(
        self,
        hass: HomeAssistant,
        codecs: dict[str, BleAdvCodec],
    ) -> None:
        """Init."""
        self.hass: HomeAssistant = hass
        self.codecs: dict[str, BleAdvCodec] = codecs
        self._last_advs: dict[str, dict[bytes, datetime]] = {}
        self._callbacks: dict[str, MatchingCallback] = {}
        self._bt_manager: BleAdvBtManager = BleAdvBtManager(self.handle_raw_adv)
        self._esp_bt_adapters: dict[str, BleAdvAdapter] = {}
        self._cnl_clbck: list[CALLBACK_TYPE] = []

    async def async_init(self) -> None:
        """Async Init."""
        try:
            await self._bt_manager.async_init()
        except BaseException as exc:
            _LOGGER.info(f"Host BT Stack cannot be used: {exc}. If on Linux configure the Bluetooth Host Adapter, else use an ESPHome ble_adv_proxy.")
        self._cnl_clbck.append(self.hass.bus.async_listen(ESPHOME_BLE_ADV_DISCOVERY_EVENT, self.on_discovery_event))
        self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self.on_stop_event)

    async def async_final(self) -> None:
        """Async Final: Clean-up."""
        _LOGGER.info("Cleaning BT Connections.")
        for cancel_callback in self._cnl_clbck:
            cancel_callback()
        for adapter in self._esp_bt_adapters.values():
            await adapter.async_final()
        await self._bt_manager.async_final()

    def get_adapter_ids(self) -> list[str]:
        """List bt adapters."""
        return list(self._bt_manager.adapters.keys()) + list(self._esp_bt_adapters.keys())

    def has_available_adapters(self) -> bool:
        """Check if the coordinator has available adapters."""
        return len(self._bt_manager.adapters) > 0 or len(self._esp_bt_adapters) > 0

    async def on_stop_event(self, _: Event) -> None:
        """Act on stop event."""
        await self.async_final()

    async def on_discovery_event(self, event: Event) -> None:
        """Act on discovery event."""
        _LOGGER.debug(f"Discovery Event: {event.data}")
        adapter_name = event.data[CONF_ATTR_NAME]
        if adapter_name not in self._esp_bt_adapters:
            self._esp_bt_adapters[adapter_name] = BleAdvEsphomeAdapter(self.hass, {**event.data}, self.handle_raw_adv)
            await self._esp_bt_adapters[adapter_name].async_init()

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
        if adapter_id in self._bt_manager.adapters:
            await self._bt_manager.adapters[adapter_id].enqueue(queue_id, qi)
        elif adapter_id in self._esp_bt_adapters:
            await self._esp_bt_adapters[adapter_id].enqueue(queue_id, qi)
        else:
            _LOGGER.error(f"Cannot process advertising: adapter '{adapter_id}' is not available.")

    async def handle_raw_adv(self, adapter_id: str, raw_adv: bytes) -> None:
        """Handle a raw advertising."""
        try:
            # clean-up last advs for this adapter (kept only the ones received less than 10 seconds ago)
            if adapter_id not in self._last_advs:
                self._last_advs[adapter_id] = {}
            limit_creation = datetime.now() - timedelta(seconds=10)

            # check if the full raw one received is a dupe of another one received in the last 10s
            self._last_advs[adapter_id] = {x: y for x, y in self._last_advs[adapter_id].items() if (y > limit_creation)}
            skip = raw_adv in self._last_advs[adapter_id]
            self._last_advs[adapter_id][raw_adv] = datetime.now()
            if skip:
                return

            # Parse the raw data and find the relevant info
            adv = BleAdvAdvertisement.FromRaw(raw_adv)
            if adv is None:
                _LOGGER.debug(f"[{adapter_id}] Not compatible raw data {as_hex(raw_adv)}, ignored")
                return

            # check if the parsed raw one received is a dupe of another one received in the last 10s
            skip = adv.raw in self._last_advs[adapter_id]
            self._last_advs[adapter_id][adv.raw] = datetime.now()
            if skip:
                return

            _LOGGER.debug(f"[{adapter_id}] BLE ADV received - {adv}")
            for codec_id, acodec in self.codecs.items():
                enc_cmd, conf = acodec.decode_adv(adv)
                if conf is not None and enc_cmd is not None:
                    ent_attrs = acodec.enc_to_ent(enc_cmd)
                    _LOGGER.debug(f"[{adapter_id}][{codec_id}] {conf} / {enc_cmd} / {ent_attrs}")
                    for device_callback in self._callbacks.values():
                        await device_callback.handle(codec_id, acodec.match_id, adapter_id, conf, ent_attrs)

        except Exception:
            _LOGGER.exception(f"[{adapter_id}] Exception handling raw adv message")
