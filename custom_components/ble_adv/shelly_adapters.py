"""BLE ADV Shelly Adapters."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Mapping
from typing import Any

from aioshelly.ble.const import BLE_SCAN_RESULT_EVENT
from aioshelly.ble.parser import parse_ble_scan_result_event
from aioshelly.rpc_device import RpcDevice, RpcUpdateType, bluetooth_mac_from_primary_mac
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import format_mac

from .adapters import (
    AdapterEventCallback,
    AdvRecvCallback,
    BleAdvAdapter,
    BleAdvAdapterAdvItem,
    BleAdvBtManager,
)

SHELLY_DOMAIN = "shelly"
RPC_BLE_ADVERT_METHOD = "BLE.AdvertiseOnce"


class BleAdvShellyAdapter(BleAdvAdapter):
    """Shelly BT Adapter leveraging the native aioshelly RPC connection inside HA."""

    def __init__(self, manager: BleAdvShellyBtManager, adapter_name: str, mac: str, rpc_device: RpcDevice) -> None:
        super().__init__(adapter_name, mac, self._on_error, 1000)
        self.manager: BleAdvShellyBtManager = manager
        self.rpc_device: RpcDevice = rpc_device

    async def open(self) -> None:
        """Open the adapter using the shared WebSocket tunnel."""
        self._opened = True
        self._add_diag("Connected via Home Assistant RPC tunnel", logging.INFO)

    def close(self) -> None:
        """Close the adapter."""
        self._opened = False
        self._add_diag("Disconnected", logging.INFO)

    async def _on_error(self, message: str) -> None:
        await self.manager.reset_adapter(self.name, f"Unhandled error: {message}")

    async def _advertise(self, item: BleAdvAdapterAdvItem) -> None:
        """Broadcast the cleaned BLE frame using HA's native aioshelly RPC client."""
        # Strip standard BLE 'Flags' structure (type 0x01) if present at the start, as Shelly firmware auto-prepends it
        clean_data = item.data[item.data[0] + 1 :] if item.data[1] == 0x01 else item.data
        await self.rpc_device.call_rpc(RPC_BLE_ADVERT_METHOD, {"adv_data": clean_data.hex()})
        await asyncio.sleep(0.0009 * item.repeat * item.interval)


type RpcListenerCallback = Callable[[RpcDevice, RpcUpdateType], None]


class BleAdvShellyBtManager(BleAdvBtManager):
    """Class to manage Shelly Adapters directly from raw HA events with filtering."""

    WAIT_REDISCOVER: float = 1.0
    CONF_SHELLY: str = "shelly"

    def __init__(
        self, hass: HomeAssistant, adv_recv_callback: AdvRecvCallback, adapter_event_callback: AdapterEventCallback, ign_adapters: list[str]
    ) -> None:
        super().__init__(self.CONF_SHELLY, adv_recv_callback, adapter_event_callback, ign_adapters)
        self.hass: HomeAssistant = hass
        self._cnl_callback: dict[str, CALLBACK_TYPE] = {}
        self._rpc_prev_listeners: dict[str, RpcListenerCallback | None] = {}

    async def async_init(self) -> None:
        """Async Init: Discovery and optimized registration to the HA event bus."""
        await self._discover_existing()

        # Listen to device registry for creation of "shelly" devices, as it is not possible to listen for ConfigEntry directly
        @callback
        def _reg_fil(event_data: Mapping[str, Any]) -> bool:
            return event_data.get("action") == "create"

        async def _on_dr_upd(event: Event[dr.EventDeviceRegistryUpdatedData]) -> None:
            if (
                (device_id := event.data.get("device_id")) is not None
                and (device_entry := dr.async_get(self.hass).async_get(device_id)) is not None
                and any(k == SHELLY_DOMAIN for k, v in device_entry.identifiers)
                and (entry := self.hass.config_entries.async_get_entry(device_entry.config_entry_id)) is not None
            ):
                await self._handle_new_entry(entry)

        self._cnl_callback["dr_upd"] = self.hass.bus.async_listen(dr.EVENT_DEVICE_REGISTRY_UPDATED, _on_dr_upd, _reg_fil)

    async def async_final(self) -> None:
        """Async Final: Complete cleanup."""
        for cancel_callback in self._cnl_callback.values():
            cancel_callback()
        self._cnl_callback.clear()
        for conf_id, prev_listener in self._rpc_prev_listeners.items():
            if (entry := self.hass.config_entries.async_get_entry(conf_id)) is not None and entry.state is ConfigEntryState.LOADED:
                try:
                    entry.runtime_data.rpc.device._update_listener = prev_listener  # noqa: SLF001
                except Exception as err:
                    self._add_diag(f"Failed to restore listener on entry {entry.title}: {err}")
        self._rpc_prev_listeners.clear()
        await self._clean()

    async def _discover_existing(self) -> None:
        """Scan the registry using config entries to fetch only Shelly devices."""
        for entry in self.hass.config_entries.async_entries(SHELLY_DOMAIN, include_disabled=True):
            await self._handle_new_entry(entry)

    async def _handle_new_entry(self, entry: ConfigEntry) -> None:
        """Assess and monitor the Shelly ConfigEntry."""
        # we do not do anything if the entry is already monitored
        if entry.entry_id in self._cnl_callback:
            return

        adapter_name = entry.title

        # listen to any load / unload events on this config entry
        @callback
        def _on_entry_state_change() -> None:
            if entry.state == ConfigEntryState.UNLOAD_IN_PROGRESS:
                # Entry is being unloaded / disabled: remove the adapter
                self._add_diag(f"Unloading entry {entry.entry_id}")
                if adapter_name in self.adapters:
                    self.hass.async_create_task(self._remove_adapter(adapter_name))
                # As best effort remove the custom rpc_device listener
                # as the rpc_device is destroyed with the entry runtime_data also destroyed when unloaded
                self._rpc_prev_listeners.pop(entry.entry_id, None)
            elif entry.state == ConfigEntryState.LOADED:
                # Entry finished loading
                self._add_diag(f"Loading entry {entry.entry_id}")
                self.hass.async_create_task(self._handle_loaded_entry(entry))

        self._cnl_callback[entry.entry_id] = entry.async_on_state_change(_on_entry_state_change)

        # Delegate the follow up when entry is loaded if not already the case
        if entry.state is not ConfigEntryState.LOADED:
            self._add_diag(f"Pending '{adapter_name}' entry loaded", logging.DEBUG)
            return

        await self._handle_loaded_entry(entry)

    async def _handle_loaded_entry(self, entry: ConfigEntry) -> None:
        """Handle a LOADED Shelly entry."""
        adapter_name = entry.title

        if not (
            hasattr(entry, "runtime_data")
            and hasattr(entry.runtime_data, "rpc")
            and hasattr(entry.runtime_data.rpc, "device")
            and isinstance(entry.runtime_data.rpc.device, RpcDevice)
        ):
            self._add_diag(f"Discarded '{adapter_name}': Incompatible device - not supporting RPC", logging.INFO)
            return

        # Listen to BLE Scan / connection / disconnection Events
        rpc_device: RpcDevice = entry.runtime_data.rpc.device
        if entry.entry_id not in self._rpc_prev_listeners:
            # we need to replace the listener with our own to intercept BLE events / connection / disconnection events
            self._rpc_prev_listeners[entry.entry_id] = rpc_device._update_listener  # noqa: SLF001

            @callback
            def _on_aioshelly_update(rpc_device_in: RpcDevice, update_type: RpcUpdateType) -> None:
                # if we are called here, it means we already replaced the rpc_device listener with our own
                try:
                    if update_type is RpcUpdateType.EVENT:
                        if (event := rpc_device_in.event) is not None and event.get("event") == BLE_SCAN_RESULT_EVENT:
                            for address, _, raw in parse_ble_scan_result_event(event.get("data", [])):
                                self.hass.async_create_task(self._adv_recv(adapter_name, address, raw))
                    elif update_type is RpcUpdateType.DISCONNECTED:
                        # on disconnection, remove the adapter instance
                        if adapter_name in self.adapters:
                            self.hass.async_create_task(self._remove_adapter(adapter_name))
                    elif update_type is RpcUpdateType.INITIALIZED:
                        # on reconnection, create the adapter instance
                        if adapter_name not in self.adapters:
                            self.hass.async_create_task(self._create_adapter(adapter_name, rpc_device_in, entry.entry_id))
                except Exception as err:
                    self._add_diag(f"Exception in shelly update: {err}")

                # call the previous listener if it exists
                if (prev_listener := self._rpc_prev_listeners.get(entry.entry_id)) is not None:
                    prev_listener(rpc_device_in, update_type)

            rpc_device._update_listener = _on_aioshelly_update  # noqa: SLF001
            self._add_diag(f"callback added for entry {entry.entry_id} / {entry.title}")

        # if rpc_device not already initialized, wait for the INITIALIZED event to trigger the creation
        if not rpc_device.initialized:
            self._add_diag(f"Pending '{adapter_name}' rpc_device initialized", logging.DEBUG)
            return

        await self._create_adapter(adapter_name, rpc_device, entry.entry_id)

    async def _create_adapter(self, adapter_name: str, rpc_device: RpcDevice, conf_id: str) -> None:
        """Validate an initialized device (RPC_BLE_ADVERT_METHOD available and BLE activated) and create the adapter instance."""
        if not rpc_device.config.get("ble", {}).get("enable", False):
            self._add_diag(f"Discarded '{adapter_name}': BLE not activated", logging.INFO)
            return

        methods_list = await rpc_device.methods_list()
        if RPC_BLE_ADVERT_METHOD not in methods_list:
            self._add_diag(f"Discarded '{adapter_name}': {RPC_BLE_ADVERT_METHOD} not available, please upgrade to firmware 2.0.0", logging.INFO)
            return

        bt_mac = format_mac(bluetooth_mac_from_primary_mac(rpc_device.shelly["mac"])).upper()

        adapter = BleAdvShellyAdapter(self, adapter_name, bt_mac, rpc_device)
        await self._add_adapter(adapter_name, conf_id, adapter)

    async def reset_adapter(self, adapter_name: str, msg: str) -> None:
        """Reset the designated adapter instance and trigger a fresh discovery loop."""
        self._add_diag(f"No reset for Shelly adapter '{adapter_name}', let Shelly handle this - {msg}.", logging.WARNING)
