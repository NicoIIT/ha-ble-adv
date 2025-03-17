"""BLE ADV Coordinator."""

from __future__ import annotations

import logging
import traceback
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from bluetooth_adapters import get_adapters_from_hci
from homeassistant.core import HomeAssistant

from .adapters import BleAdvAdapter, get_adapter
from .codecs.models import BleAdvAdvertisement, BleAdvCodec, BleAdvConfig, BleAdvEntAttr, as_hex

_LOGGER = logging.getLogger(__name__)


class CoordinatorError(Exception):
    """Coordinator Exception."""


class MatchingCallback(ABC):
    """Base MatchingCallback class."""

    @abstractmethod
    async def handle(self, codec_id: str, adapter_id: str, config: BleAdvConfig, ent_attrs: list[BleAdvEntAttr]) -> None:
        """Implement Action."""
        raise CoordinatorError("Not Implemented")


class BleAdvCoordinator:
    """Class to manage fetching any BLE ADV data."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        codecs: dict[str, BleAdvCodec],
    ) -> None:
        """Init."""
        self.hass: HomeAssistant = hass
        self.logger: logging.Logger = logger
        self.codecs: dict[str, BleAdvCodec] = codecs
        self.adapters: dict[str, BleAdvAdapter] = {}
        self._last_advs: dict[bytes, datetime] = {}
        self._callbacks: dict[str, MatchingCallback] = {}

    async def async_init(self) -> None:
        """Async Init."""
        bt_adapters: list[int] = list(get_adapters_from_hci().keys())
        _LOGGER.debug(f"BT Adapters from hci: {bt_adapters}")
        if not bt_adapters:
            bt_adapters = list(range(3))
        for adapter_id in bt_adapters:
            try:
                adapter = get_adapter(adapter_id)
                await adapter.async_init()
                self.adapters[adapter.name] = adapter
            except Exception as exc:
                _LOGGER.info(f"Failed to init adapter {adapter.name}:{type(exc)}:{exc}, ignoring it")
                adapter.close()

    async def async_final(self) -> None:
        """Async Final: Clean-up."""
        for adapter in self.adapters.values():
            await adapter.async_final()

    def get_adapter(self, adapter_id: str) -> BleAdvAdapter:
        """Get the adapter."""
        return self.adapters[adapter_id]

    def has_available_adapters(self) -> bool:
        """Check if the coordinator has available adapters."""
        return any(adapter.available for adapter in self.adapters.values())

    async def register_callback(self, callback_id: str, callback: MatchingCallback) -> None:
        """Register a matching callback by its id."""
        if len(self._callbacks) == 0:
            for adapter in self.adapters.values():
                await adapter.start_scan(self.handle_raw_adv)
            self.logger.info("Adapters registered")

        self._callbacks[callback_id] = callback
        self.logger.info(f"Registered callback with id '{callback_id}': {callback}")

    async def unregister_callback(self, callback_id: str) -> None:
        """Unregister a callback by its id."""
        self._callbacks.pop(callback_id)
        self.logger.info(f"Unregistered callback with id '{callback_id}'")
        if len(self._callbacks) == 0:
            for adapter in self.adapters.values():
                await adapter.stop_scan()
            self.logger.info("Adapters unregistered")

    async def handle_raw_adv(self, adapter_id: str, raw_adv: bytes) -> None:
        """Handle a raw advertising."""
        try:
            # clean-up last advs and check for dupe
            limit_creation = datetime.now() - timedelta(seconds=35)
            self._last_advs = {x: y for x, y in self._last_advs.items() if (y > limit_creation)}
            if raw_adv in self._last_advs:
                return
            self._last_advs[raw_adv] = datetime.now()

            # Parse the raw data and find the relevant info
            adv = BleAdvAdvertisement.FromRaw(raw_adv)
            if adv is None:
                _LOGGER.debug(f"Not compatible raw data {as_hex(raw_adv)}, ignored")
                return

            # also add the decoded data to the ignore list
            if adv.raw in self._last_advs:
                return
            self._last_advs[adv.raw] = datetime.now()

            _LOGGER.debug(f"BLE ADV received - {adv}")
            for codec_id, acodec in self.codecs.items():
                enc_cmd, conf = acodec.decode_adv(adv)
                if conf is not None and enc_cmd is not None:
                    ent_attrs = acodec.enc_to_ent(enc_cmd)
                    if False:
                        # DEBUG MODE: Log and Test re encoding
                        _LOGGER.info(f"[{codec_id}] enc: {enc_cmd} / config: {conf}")
                        enc_cmds = []
                        for ent_attr in ent_attrs:
                            _LOGGER.debug(f"[{codec_id} COMP] ent: {ent_attr}")
                            enc_cmds += acodec.ent_to_enc(ent_attr)
                        if len(enc_cmds) > 1:
                            _LOGGER.error(f"[{codec_id} COMP] more than one enc_cmd generated at re-encode")
                        elif len(enc_cmds) == 0:
                            _LOGGER.error(f"[{codec_id} COMP] no enc_cmd generated at re-encode")
                        elif enc_cmds[0] != enc_cmd:
                            _LOGGER.error(f"[{codec_id} COMP] diff - recv: {enc_cmd} / reenc - {enc_cmds[0]}")
                        else:
                            _LOGGER.info("[{codec_id} COMP] OK")

                    for device_callback in self._callbacks.values():
                        await device_callback.handle(codec_id, adapter_id, conf, ent_attrs)

        except Exception:
            _LOGGER.error(traceback.format_exc())


# ruff: noqa: ERA001

# from __future__ import annotations

# import asyncio
# import logging
# import traceback
# import re

# from datetime import datetime, timedelta
# from time import clock_gettime

# from habluetooth import BluetoothScanningMode
# from homeassistant.components import bluetooth
# from homeassistant.core import HomeAssistant, callback
# from homeassistant.components.bluetooth.models import BluetoothChange, BluetoothServiceInfoBleak

# from homeassistant.components.bluetooth.api import _get_manager
# from bluetooth_adapters import get_dbus_managed_objects

# from .codecs.models import MatchingDeviceCallback, BleAdvAdvertisement, BleAdvEncCmd, BleAdvConfig, as_hex
# # NOOOOOOOOOOO from .device import BleAdvDevice

# _LOGGER = logging.getLogger(__name__)

# UUID_REGEX = re.compile("0000([0-9a-fA-F]{4})-0000-1000-8000-00805f9b34fb")
# UUID_GEN = "0000{:02x}{:02x}-0000-1000-8000-00805f9b34fb"

# class BleAdvCoordinator:

#     """Class to manage fetching any BLE ADV data."""

#     def __init__(
#         self,
#         hass: HomeAssistant,
#         logger: logging.Logger,
#         codecs,
#     ) -> None:
#         """Initialize"""
#         self.hass = hass
#         self.logger = logger
#         self.codecs = codecs
#         self._last_advs = []
#         self._last_adv_03 = {}
#         self._bluetooth_rem_callback = None
#         self._callbacks: dict[MatchingDeviceCallback] = {}
#         self._ready = False

#     async def register_callback(self, id, callback: MatchingDeviceCallback) -> None:
#         if len(self._callbacks) == 0:
#             self._bluetooth_rem_callback = bluetooth.api.async_register_callback(
#                     self.hass,
#                     self._handle_bluetooth_event,
#                     None,
#                     BluetoothScanningMode.PASSIVE,
#             )
#             self.logger.info(f"Bluetooth callback registered")
#             #await asyncio.sleep(0.2) # ignore the initial elements sent by HA bluetooth and that are not live
#             self._ready = True

#         self._callbacks[id] = callback
#         self.logger.info(f"Registered callback with id '{id}': {callback}")

#     async def unregister_callback(self, id) -> None:
#         self._callbacks.pop(id)
#         self.logger.info(f"Unregistered callback with id '{id}'")
#         if len(self._callbacks) == 0 and self._bluetooth_rem_callback is not None:
#             self.logger.info(f"Bluetooth callback unregistered")
#             self._ready = False
#             self._bluetooth_rem_callback()
#             self._bluetooth_rem_callback = None

#     @callback
#     def _handle_bluetooth_event(
#         self,
#         service_info: BluetoothServiceInfoBleak,
#         change: BluetoothChange,
#     ) -> None:
#         """Handle a bluetooth event."""
#         # if too far in the past, ignore
#         if service_info.time < (clock_gettime(6) - 0.1):
#             _LOGGER.info(f"Ignored")
#             return

#         # clean-up last advs
#         limit_creation = datetime.now() - timedelta(seconds=35)
#         self._last_advs = [ x for x in self._last_advs if (x._created > limit_creation) ]
#         self._last_adv_03 = { x:y for x,y in self._last_adv_03.items() if (y[2] > limit_creation) }

#         # convert the newly received one
#         raw_data = bytes()
#         ble_type = None
#         for k,v in service_info.manufacturer_data.items():
#             raw_data += k.to_bytes(2, 'little')
#             raw_data += v
#             ble_type = 0xFF
#         if ble_type is None:
#             for k, v in service_info.service_data.items():
#                 if match := UUID_REGEX.fullmatch(k):
#                     raw_data += int(match.group(1), 16).to_bytes(2, 'little')
#                     raw_data += v
#                     ble_type = 0x16
#         if ble_type is None:
#             for uuid in service_info.service_uuids:
#                 if match := UUID_REGEX.fullmatch(uuid):
#                     raw_data += int(match.group(1), 16).to_bytes(2, 'little')
#                     ble_type = 0x03
#         if not ble_type:
#             return

#         # WORKAROUND for (stupid? BLE Apps using BLE ADV in non standard way...) non compatible behaviour
#         # The HA framework and BlueZ aggregates the UUIDs previously received for an address
#         # with the ones newly received, resulting in a "message" unreadable for us
#         # We keep the previously received UUIDs for this address and we rebuild the message with only the new parts
#         # And the common part a the beginning of the message (that are not re added as considered duplicate...)
#         # BUT if some other part of the message is common in between the previous and the new, we will NOT be able to identify them...
#         if ble_type == 0x03:
#             # find if this one starts as the previous 0x03 adv for the same address
#             prev_raw, adv_len, created_time = self._last_adv_03.get(service_info.address, (None,None,None))
#             if prev_raw and raw_data.startswith(prev_raw) and prev_raw != raw_data:
#                 # _LOGGER.info(f"exists - prev: {as_hex(prev_raw)}, len: {adv_len}")
#                 new_data = raw_data[len(prev_raw):]
#                 new_data = prev_raw[:adv_len - len(new_data)] + new_data
#                 # _LOGGER.info(f"new: {as_hex(new_data)}, len: {len(new_data)}")
#                 self._last_adv_03[service_info.address] = (raw_data, adv_len, datetime.now())
#                 raw_data = new_data
#             else:
#                 # _LOGGER.info(f"new: {as_hex(raw_data)}, len: {len(raw_data)}")
#                 self._last_adv_03[service_info.address] = (raw_data, len(raw_data), datetime.now())
#         # End of WORKAROUND

#         adv = BleAdvAdvertisement(ble_type, raw_data)

#         # check if not dupe and launch async callback
#         if not adv in self._last_advs:
#             self._last_advs.append(adv)
#             asyncio.run_coroutine_threadsafe(self._async_handle_bluetooth_event(adv), self.hass.loop)

#     async def _async_handle_bluetooth_event(self, adv: BleAdvAdvertisement) -> None:
#         _LOGGER.info(f"BLE ADV received - {adv}")
#         try:
#             for id, acodec in self.codecs.items():
#                 enc_cmd, conf = acodec.decode_adv(adv)
#                 if conf != None:
#                     _LOGGER.info(f"[{id}] enc: {enc_cmd} / config: {conf}")
#                     for device_callback in self._callbacks.values():
#                         if device_callback.matches(id, conf):
#                             await device_callback.callback(id, conf, enc_cmd)

#         except Exception:
#             _LOGGER.error(traceback.format_exc())

#     async def async_send_command(self,  codec_id: str, conf: BleAdvConfig, enc_cmd: BleAdvEncCmd):
#         _LOGGER.info(f"Sending command: '{enc_cmd}' to '{codec_id}'")
#         try:
#             acodec = self.codecs.get(codec_id)
#             adv: BleAdvAdvertisement = acodec.encode_adv(enc_cmd, conf)
#             _LOGGER.info(f"Gen ADV: {adv}")
#             if adv._ble_type == 0x03:
#                 uuids = [ UUID_GEN.format(adv._raw[i+1], adv._raw[i]) for i in range(0, len(adv._raw), 2) ]
#                 _LOGGER.info(uuids)

#         except Exception:
#             _LOGGER.error(traceback.format_exc())

#         manager = _get_manager(self.hass)
#         # adapters = await manager.async_get_bluetooth_adapters()
#         # _LOGGER.info(adapters)
#         dbuses = await get_dbus_managed_objects()
#         adv_ifaces = [ key for key, val in dbuses.items() if 'org.bluez.LEAdvertisingManager1' in val]
#         _LOGGER.info(f"{adv_ifaces} support advertising")
