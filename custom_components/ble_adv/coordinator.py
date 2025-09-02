"""BLE ADV Coordinator."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.system_info import async_get_system_info

from .adapters import BleAdvBtHciManager, BleAdvQueueItem
from .codecs.models import BleAdvAdvertisement, BleAdvCodec, BleAdvConfig, BleAdvEncCmd, BleAdvEntAttr
from .const import CONF_ADAPTER_ID, CONF_DEVICE_QUEUE, CONF_DURATION, CONF_INTERVAL, CONF_RAW, CONF_REPEAT, DOMAIN
from .esp_adapters import BleAdvEspBtManager

_LOGGER = logging.getLogger(__name__)


class BleAdvBaseDevice:
    """Base Ble Adv Device."""

    def __init__(
        self,
        coordinator: BleAdvCoordinator,
        unique_id: str,
        codec_id: str,
        adapter_ids: list[str],
        repeat: int,
        interval: int,
        duration: int,
        config: BleAdvConfig,
    ) -> None:
        self.coordinator: BleAdvCoordinator = coordinator
        self.unique_id: str = unique_id
        self.adapter_ids: set[str] = set(adapter_ids)
        self.codec_id: str = codec_id
        self.codec: BleAdvCodec = coordinator.codecs[codec_id]
        self.config: BleAdvConfig = config
        self.repeat: int = repeat
        self.interval: int = interval
        self.duration: int = duration

        self.in_use_codec_ids: set[str] = set()
        self._listeners: list[tuple[str, BleAdvConfig]] = []
        self.add_listener(codec_id, config)

    @property
    def available(self) -> bool:
        """Return True if the device is available: if one of the adapters is available."""
        return any(adapter_id in self.coordinator.get_adapter_ids() for adapter_id in self.adapter_ids)

    def add_listener(self, codec_id: str, config: BleAdvConfig) -> None:
        """Add a listener to this device."""
        self.in_use_codec_ids.add(codec_id)
        self._listeners.append((self.coordinator.codecs[codec_id].match_id, config))

    def match(self, match_id: str, adapter_id: str, config: BleAdvConfig) -> bool:
        """Match a given adapter / config."""
        return adapter_id in self.adapter_ids and any(
            (match_id == x) and (config.id == y.id) and (config.index == y.index) for x, y in self._listeners
        )

    async def async_on_command(self, ent_attrs: list[BleAdvEntAttr]) -> None:
        """Call on matching command received."""

    async def apply_cmd(self, enc_cmd: BleAdvEncCmd) -> None:
        """Apply command."""
        advs: list[BleAdvAdvertisement] = self.codec.encode_advs(enc_cmd, self.config)
        qi = BleAdvQueueItem(enc_cmd.cmd, self.repeat, self.duration, self.interval, [x.to_raw() for x in advs], self.codec.ign_duration)
        for adapter_id in self.adapter_ids:
            await self.coordinator.advertise(adapter_id, self.unique_id, qi)

    async def advertise(self, ent_attr: BleAdvEntAttr) -> None:
        """Encode and Advertise a message."""
        enc_cmds = self.codec.ent_to_enc(ent_attr)
        for enc_cmd in enc_cmds:
            await self.apply_cmd(enc_cmd)


@dataclass
class BleAdvRecvItem:
    """Received Adv and its related info."""

    del_time: datetime
    match_id: str
    pub_devices: set[str]
    conf: BleAdvConfig
    ent_attrs: list[BleAdvEntAttr]


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

        self._raw_last_advs: dict[bytes, datetime] = {}
        self._emit_last_advs: dict[bytes, datetime] = {}
        self._dec_last_advs: dict[bytes, BleAdvRecvItem] = {}

        self._devices: list[BleAdvBaseDevice] = []
        self._in_use_codecs: set[str] = set()

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

    def _recompute_in_use_codecs(self) -> None:
        match_ids = {self.codecs[codec_id].match_id for x in self._devices for codec_id in x.in_use_codec_ids}
        self._in_use_codecs = {x.codec_id for x in self.codecs.values() if x.match_id in match_ids}

    def add_device(self, device: BleAdvBaseDevice) -> None:
        """Register a device."""
        self._devices.append(device)
        self._recompute_in_use_codecs()
        self._raw_last_advs.clear()
        _LOGGER.debug(f"Registered device '{device.unique_id}'")

    def remove_device(self, device: BleAdvBaseDevice) -> None:
        """Unregister a device."""
        self._devices = [x for x in self._devices if x.unique_id != device.unique_id]
        self._recompute_in_use_codecs()
        self._dec_last_advs.clear()
        _LOGGER.debug(f"Unregistered device '{device.unique_id}'")

    async def advertise(self, adapter_id: str | None, queue_id: str, qi: BleAdvQueueItem) -> None:
        """Advertise."""
        # Ignore the future emitted advs while they are being emitted by potentially other adapters
        for raw_adv in qi.data:
            self._emit_last_advs[bytes(raw_adv)] = datetime.now() + timedelta(milliseconds=qi.ign_duration)
        if adapter_id in self._hci_bt_manager.adapters:
            await self._hci_bt_manager.adapters[adapter_id].enqueue(queue_id, qi)
        elif adapter_id in self._esp_bt_manager.adapters:
            await self._esp_bt_manager.adapters[adapter_id].enqueue(queue_id, qi)
        else:
            _LOGGER.error(f"Cannot process advertising: adapter '{adapter_id}' is not available.")

    async def inject_raw(self, dt: dict[str, Any]) -> dict[str, str]:
        """Injects a raw advertisement."""
        if dt[CONF_ADAPTER_ID] not in self.get_adapter_ids():
            return {CONF_ADAPTER_ID: f"Should be in {self.get_adapter_ids()}"}
        try:
            raw = bytes.fromhex(dt[CONF_RAW].replace(".", ""))
        except ValueError:
            return {CONF_RAW: "Cannot convert to bytes"}
        ign_duration = 4 * dt[CONF_REPEAT] * dt[CONF_INTERVAL]
        qi: BleAdvQueueItem = BleAdvQueueItem(None, 3 * dt[CONF_REPEAT], dt[CONF_DURATION], dt[CONF_INTERVAL], [raw], ign_duration)
        await self.advertise(dt[CONF_ADAPTER_ID], dt[CONF_DEVICE_QUEUE], qi)
        return {}

    async def decode_raw(self, raw_adv_str: str) -> list[str]:
        """Decode a Raw ADV."""
        try:
            raw_adv = bytes.fromhex(raw_adv_str.replace(".", ""))
        except ValueError:
            return ["Cannot convert to bytes"]
        adv = BleAdvAdvertisement.FromRaw(raw_adv)
        for codec_id, acodec in self.codecs.items():
            enc_cmd, conf = acodec.decode_adv(adv)
            if conf is not None and enc_cmd is not None:
                ent_attrs = acodec.enc_to_ent(enc_cmd)
                return [codec_id, raw_adv.hex(".").upper(), repr(enc_cmd), repr(conf), " / ".join([repr(x) for x in ent_attrs])]
        return ["Could not be decoded by any known codec"]

    async def _publish_to_devices(self, adapter_id: str, recv: BleAdvRecvItem) -> None:
        # Publish to any device that matches, if not already done
        for device in self._devices:
            if device.unique_id not in recv.pub_devices and device.match(recv.match_id, adapter_id, recv.conf):
                await device.async_on_command(recv.ent_attrs)
                recv.pub_devices.add(device.unique_id)

    def _handle_listening(self, adapter_id: str, _: str, raw_adv: bytes) -> None:
        if raw_adv not in self.listened_raw_advs:
            self.listened_raw_advs.append(raw_adv)
        for codec_id, acodec in self.codecs.items():
            enc_cmd, conf = acodec.decode_adv(BleAdvAdvertisement.FromRaw(raw_adv))
            if conf is not None:
                data = (adapter_id, codec_id, acodec.match_id, conf)
                if data not in self.listened_decoded_confs:
                    self.listened_decoded_confs.append(data)

    async def handle_raw_adv(self, adapter_id: str, orig: str, raw_adv: bytes) -> None:
        """Handle a raw advertising."""
        try:
            # check if the received orig is in the ignored macs, or if too short to be considered
            if orig in self.ign_macs or len(raw_adv) < 8:
                return

            # Parse the raw data and find the relevant info ble_type and raw
            adv = BleAdvAdvertisement.FromRaw(raw_adv)

            # Exclude by Company ID
            if int.from_bytes(adv.raw[:2], "little") in self.ign_cids:
                return

            # Clean-up last raw / emitted / decoded advs based on expiry date
            now = datetime.now()
            self._raw_last_advs = {x: y for x, y in self._raw_last_advs.items() if (y > now)}
            self._emit_last_advs = {x: y for x, y in self._emit_last_advs.items() if (y > now)}
            self._dec_last_advs = {x: y for x, y in self._dec_last_advs.items() if (y.del_time > now)}

            # Check if already present in last emitted advs: ignore
            if raw_adv in self._emit_last_advs:
                return

            # Check if already present in last raw advs: extend exclusion duration
            if raw_adv in self._raw_last_advs:
                self._raw_last_advs[raw_adv] = now + timedelta(milliseconds=self.ign_duration)
                return

            if self.is_listening():
                self._handle_listening(adapter_id, orig, raw_adv)

            # Check if already present in last decoded advs: re check another matching device with different adapter
            if adv.raw in self._dec_last_advs:
                await self._publish_to_devices(adapter_id, self._dec_last_advs[adv.raw])
                return

            # Try to decode Adv with in used codecs only
            recv = None
            for codec_id in self._in_use_codecs:
                acodec = self.codecs[codec_id]
                enc_cmd, conf = acodec.decode_adv(adv)
                if conf is not None and enc_cmd is not None:
                    ent_attrs = acodec.enc_to_ent(enc_cmd)
                    recv = BleAdvRecvItem(now + timedelta(milliseconds=acodec.ign_duration), acodec.match_id, set(), conf, ent_attrs)
                    _LOGGER.debug(f"[{codec_id}] {conf} / {enc_cmd} / {ent_attrs}")
                    await self._publish_to_devices(adapter_id, recv)
                    if acodec.multi_advs:
                        for reenc_adv in acodec.encode_advs(enc_cmd, conf):
                            self._dec_last_advs[reenc_adv.raw] = recv
                    else:
                        self._dec_last_advs[adv.raw] = recv

            # Not decoded by in_used codecs: consider raw and ignored during the next standard ign_duration
            if not recv:
                self._raw_last_advs[raw_adv] = now + timedelta(milliseconds=self.ign_duration)

        except Exception:
            _LOGGER.exception(f"[{adapter_id}] Exception handling raw adv message")

    def diagnostic_dump(self) -> dict[str, Any]:
        """Dump diagnostc dict."""
        return {
            "hci": self._hci_bt_manager.diagnostic_dump(),
            "esp": self._esp_bt_manager.diagnostic_dump(),
            "ign_adapters": self.ign_adapters,
            "ign_duration": self.ign_duration,
            "ign_cids": list(self.ign_cids),
            "ign_macs": list(self.ign_macs),
            "last_emitted": {x.hex().upper(): y for x, y in self._emit_last_advs.items()},
            "last_unk_raw": {x.hex().upper(): y for x, y in self._raw_last_advs.items()},
            "last_dec_raw": {x.hex().upper(): y for x, y in self._dec_last_advs.items()},
        }

    async def full_diagnostic_dump(self) -> dict[str, Any]:
        """Dump Full diagnostic dict including system data."""
        hass_sys_info = await async_get_system_info(self.hass)
        hass_sys_info["run_as_root"] = hass_sys_info["user"] == "root"
        del hass_sys_info["user"]
        entries = {entry_id: self.hass.config_entries.async_get_entry(entry_id) for entry_id in self.hass.data.get(DOMAIN, {})}
        return {"home_assistant": hass_sys_info, "coordinator": self.diagnostic_dump(), "entries": entries}
