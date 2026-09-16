"""BLE ADV Shelly Adapters."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine, Mapping
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr

from .adapters import (
    AdapterEventCallback,
    AdvRecvCallback,
    BleAdvAdapter,
    BleAdvAdapterAdvItem,
    BleAdvBtManager,
)

SHELLY_DOMAIN = "shelly"
RPC_BLE_ADVERT_METHOD = "BLE.AdvertiseOnce"


type ConnectedCallback = Callable[[], bool]
type OnConnectionStateChange = Callable[[bool], Coroutine[None, None, None]]
type AdvertiseRpcCallback = Callable[[str, dict[str, Any]], Coroutine[None, None, dict[str, Any]]]


class BleAdvShellyAdapter(BleAdvAdapter):
    """Shelly BT Adapter leveraging the native aioshelly RPC connection inside HA."""

    def __init__(self, manager: BleAdvShellyBtManager, adapter_name: str, mac: str, advertise_rpc_clbk: AdvertiseRpcCallback) -> None:
        super().__init__(adapter_name, mac, self._on_error, 1000)
        self.manager: BleAdvShellyBtManager = manager
        self._advertise_rpc_clbk: AdvertiseRpcCallback = advertise_rpc_clbk

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
        await self._advertise_rpc_clbk(RPC_BLE_ADVERT_METHOD, {"adv_data": clean_data.hex()})
        await asyncio.sleep(0.0009 * item.repeat * item.interval)


class _MonitoredDevice:
    WAIT_MONITOR: float = 1.0

    def __init__(self, hass: HomeAssistant, connected_callback: ConnectedCallback, state_chg_clbk: OnConnectionStateChange) -> None:
        self._connected_callback = connected_callback
        self._state_chg_callback = state_chg_clbk
        self.connected: bool = self._connected_callback()
        self._mon_task: asyncio.Task = hass.async_create_task(self._monitor())

    async def _monitor(self) -> None:
        try:
            while True:
                new_connected = self._connected_callback()
                if new_connected != self.connected:
                    self.connected = new_connected
                    await self._state_chg_callback(new_connected)
                await asyncio.sleep(_MonitoredDevice.WAIT_MONITOR)
        except asyncio.CancelledError:
            pass

    def stop(self) -> None:
        self._mon_task.cancel()


class BleAdvShellyBtManager(BleAdvBtManager):
    """Class to manage Shelly Adapters directly from raw HA events with filtering."""

    NAME: str = "shl"

    def __init__(
        self, hass: HomeAssistant, adv_recv_callback: AdvRecvCallback, adapter_event_callback: AdapterEventCallback, ign_adapters: list[str]
    ) -> None:
        super().__init__(BleAdvShellyBtManager.NAME, adv_recv_callback, adapter_event_callback, ign_adapters)
        self.hass: HomeAssistant = hass
        self._mon_devices: dict[str, _MonitoredDevice] = {}
        self._cnl_callback: dict[str, CALLBACK_TYPE] = {}
        self._cnl_scan_callback: dict[str, CALLBACK_TYPE] = {}

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
        for mon_dev in self._mon_devices.values():
            mon_dev.stop()
        self._mon_devices.clear()
        for cancel_callback in self._cnl_scan_callback.values():
            cancel_callback()
        self._cnl_scan_callback.clear()
        for cancel_callback in self._cnl_callback.values():
            cancel_callback()
        self._cnl_callback.clear()
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

        adapter_name = self._full_adapter_name(entry.title)

        # check if the adapter is ignored per configuration
        if self._ignored_adapter(adapter_name):
            self._add_diag(f"Ignored '{adapter_name}' per configuration.", logging.INFO)
            return

        # listen to any load / unload events on this config entry
        @callback
        def _on_entry_state_change() -> None:
            if entry.state == ConfigEntryState.UNLOAD_IN_PROGRESS:
                # Entry is being unloaded / disabled: remove the adapter
                self._add_diag(f"Unloading entry {entry.entry_id}")
                if adapter_name in self.adapters:
                    self.hass.async_create_task(self._remove_adapter(adapter_name))
                if (mon_dev := self._mon_devices.pop(entry.entry_id, None)) is not None:
                    mon_dev.stop()
                self._cnl_scan_callback.pop(entry.entry_id, None)
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
        # We import here to avoid useless dependency on Shelly Component / aioshelly if the user do not have any Shelly Integration
        from aioshelly.ble.const import BLE_SCAN_RESULT_EVENT, BLE_SCRIPT_NAME  # noqa: PLC0415
        from aioshelly.ble.parser import parse_ble_scan_result_event  # noqa: PLC0415
        from homeassistant.components.shelly.coordinator import ShellyRpcCoordinator  # noqa: PLC0415

        adapter_name = self._full_adapter_name(entry.title)

        if not (hasattr(entry, "runtime_data") and hasattr(entry.runtime_data, "rpc") and isinstance(entry.runtime_data.rpc, ShellyRpcCoordinator)):
            self._add_diag(f"Discarded '{adapter_name}': Incompatible device - not supporting RPC", logging.INFO)
            return

        if entry.entry_id in self._mon_devices:
            return

        # The Shelly device is a valid RPC Device: monitor and re asses it on connection / deconnection
        rpc_coord: ShellyRpcCoordinator = entry.runtime_data.rpc

        @callback
        async def _validate_and_create_adapter() -> None:
            # Check Shelly device Capacities
            methods_list = await rpc_coord.device.methods_list()
            if RPC_BLE_ADVERT_METHOD not in methods_list:
                self._add_diag(f"Discarded '{adapter_name}': {RPC_BLE_ADVERT_METHOD} not available, please upgrade to firmware 2.0.0", logging.INFO)
                return

            scripts_list = await rpc_coord.device.script_list()
            if not any(script.get("name") == BLE_SCRIPT_NAME and script.get("running") for script in scripts_list):
                check_url = "check https://www.home-assistant.io/integrations/shelly/ to set Scanner Mode as 'Passive' or 'Auto'"
                self._add_diag(f"Discarded '{adapter_name}': {BLE_SCRIPT_NAME} not present or running, {check_url}.", logging.INFO)
                return

            # Listen to BLE Scan events
            def _async_on_event(event: dict[str, Any]) -> None:
                try:
                    if event.get("event") == BLE_SCAN_RESULT_EVENT:
                        for address, _, raw in parse_ble_scan_result_event(event.get("data", [])):
                            self.hass.async_create_task(self._adv_recv(adapter_name, address, raw))
                except Exception as err:
                    self._add_diag(f"Error handling event {event}: {err}")
                    return

            if entry.entry_id not in self._cnl_scan_callback:
                self._add_diag(f"Subscribe to Scan: {adapter_name}")
                self._cnl_scan_callback[entry.entry_id] = rpc_coord.async_subscribe_events(_async_on_event)

            adapter = BleAdvShellyAdapter(self, adapter_name, rpc_coord.bluetooth_source, rpc_coord.device.call_rpc)
            await self._add_adapter(adapter_name, entry.entry_id, adapter)

        @callback
        async def _conn_state_changed(connected: bool) -> None:
            if connected:
                self._add_diag(f"Evaluating '{adapter_name}' on connection")
                await _validate_and_create_adapter()
            else:
                self._add_diag(f"Removing '{adapter_name}' on disconnection")
                await self._remove_adapter(adapter_name)

        @callback
        def _is_connected() -> bool:
            return rpc_coord.connected

        self._mon_devices[entry.entry_id] = _MonitoredDevice(self.hass, _is_connected, _conn_state_changed)

        if not rpc_coord.connected:
            self._add_diag(f"Pending '{adapter_name}': Not connected - will assess later", logging.INFO)
            return

        await _validate_and_create_adapter()

    async def reset_adapter(self, adapter_name: str, msg: str) -> None:
        """Reset the designated adapter instance and trigger a fresh discovery loop."""
        self._add_diag(f"No reset for Shelly adapter '{adapter_name}', let Shelly handle this - {msg}.", logging.WARNING)
