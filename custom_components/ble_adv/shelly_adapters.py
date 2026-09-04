"""BLE ADV Shelly Adapters."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from typing import Any

from aioshelly.ble.const import BLE_SCAN_RESULT_EVENT
from aioshelly.ble.parser import parse_ble_scan_result_event
from aioshelly.rpc_device import RpcDevice, RpcUpdateType, bluetooth_mac_from_primary_mac
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry, format_mac

from .adapters import (
    AdapterEventCallback,
    AdvRecvCallback,
    BleAdvAdapter,
    BleAdvAdapterAdvItem,
    BleAdvBtManager,
)

SHELLY_DOMAIN = "shelly"

INCOMPATIBLE_SHELLY_MODELS = (
    "SHWT-1",  # Shelly Flood (Battery)
    "SHHT-1",  # Shelly H&T Gen1 (Battery)
    "SHSEN-1",  # Shelly Sense (Battery)
    "SHBTN-1",  # Shelly Button 1 (Battery)
    "SHBTN-2",  # Shelly Button 2 (Battery)
    "SHMOS-01",  # Shelly Motion 1 (Battery)
    "SHMOS-02",  # Shelly Motion 2 (Battery)
    "SHBLU",  # Complete Shelly BLU lineup (Battery, pure Bluetooth protocol)
    "SHEM",  # Shelly EM (Gen1 - No Bluetooth hardware)
    "SHEM-3",  # Shelly 3EM (Gen1 - No Bluetooth hardware)
    "SHSW",  # Legacy Gen1 relays (Shelly 1, 1PM, 2.5, etc. - No Bluetooth hardware)
    "SHPLG",  # Legacy Gen1 plugs (Shelly Plug / Plug S - No Bluetooth hardware)
    "SHUNI",  # Shelly Uni Gen1 (No Bluetooth hardware)
)


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
        await self.rpc_device.call_rpc("BLE.AdvertiseOnce", {"adv_data": clean_data.hex()})
        await asyncio.sleep(0.0009 * item.repeat * item.interval)


class BleAdvShellyBtManager(BleAdvBtManager):
    """Class to manage Shelly Adapters directly from raw HA events with filtering."""

    WAIT_REDISCOVER: float = 1.0

    def __init__(self, hass: HomeAssistant, adv_recv_callback: AdvRecvCallback, adapter_event_callback: AdapterEventCallback) -> None:
        super().__init__(adapter_event_callback)
        self.hass: HomeAssistant = hass
        self.handle_raw_adv: AdvRecvCallback = adv_recv_callback
        self._cnl_callback: dict[str, CALLBACK_TYPE] = {}

    async def async_init(self) -> None:
        """Async Init: Discovery and optimized registration to the HA event bus."""
        await self._discover_existing()

        # Listen to device registry updates and trigger a re-evaluation of the device entry to dynamically add or remove adapters
        @callback
        def _reg_fil(event_data: Mapping[str, Any]) -> bool:
            return event_data.get("action") == "create"

        async def _on_dr_upd(event: Event) -> None:
            device_id = event.data.get("device_id")
            if device_id is not None and (device_entry := dr.async_get(self.hass).async_get(device_id)) is not None:
                if any(k == SHELLY_DOMAIN for k, v in device_entry.identifiers):
                    await self._create_adapter(device_entry)

        self._cnl_callback["dr_upd"] = self.hass.bus.async_listen(event_type="device_registry_updated", listener=_on_dr_upd, event_filter=_reg_fil)

    async def async_final(self) -> None:
        """Async Final: Complete cleanup."""
        for cancel_callback in self._cnl_callback.values():
            cancel_callback()
        self._cnl_callback.clear()
        await self._clean()

    async def _discover_existing(self) -> None:
        """Scan the registry using config entries to fetch only Shelly devices."""
        dev_reg = dr.async_get(self.hass)

        # Look up all active config entries managed by the official shelly integration
        for entry in self.hass.config_entries.async_entries(SHELLY_DOMAIN):
            # Fetch only the devices matching this specific configuration entry wrapper
            for device_entry in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
                await self._create_adapter(device_entry)

    async def _create_adapter(self, device_entry: DeviceEntry) -> None:
        """Create a new adapter instance for the given device_id."""
        adapter_name = f"{device_entry.name}" if device_entry.name else f"shelly_{device_entry.id[:6]}"
        if adapter_name in self.adapters:
            return

        if device_entry.disabled_by is not None:
            self._add_diag(f"Discarded '{adapter_name}': disabled", logging.INFO)
            return

        if device_entry.model is not None and device_entry.model.upper().startswith(INCOMPATIBLE_SHELLY_MODELS):
            self._add_diag(f"Discarded '{adapter_name}': incompatible hardware model: {device_entry.model}", logging.INFO)
            return

        if (conf_id := device_entry.config_entry_id) is None:
            self._add_diag(f"Discarded '{adapter_name}': no entry", logging.INFO)
            return

        entry = self.hass.config_entries.async_get_entry(conf_id)
        if not (
            entry
            and entry.unique_id
            and entry.state is ConfigEntryState.LOADED
            and hasattr(entry, "runtime_data")
            and hasattr(entry.runtime_data, "rpc")
            and hasattr(entry.runtime_data.rpc, "device")
        ):
            self._add_diag(f"Discarded '{adapter_name}': Incompatible device data", logging.INFO)
            return

        rpc_device: RpcDevice = entry.runtime_data.rpc.device
        bt_mac = format_mac(bluetooth_mac_from_primary_mac(entry.unique_id)).upper()

        @callback
        def _on_aioshelly_update(device: RpcDevice, update_type: RpcUpdateType) -> None:
            if update_type is RpcUpdateType.EVENT:
                if (event := device.event) is not None and event.get("event") == BLE_SCAN_RESULT_EVENT:
                    for address, _, raw in parse_ble_scan_result_event(event.get("data", [])):
                        self.hass.async_create_task(self.handle_raw_adv(adapter_name, address, raw))
                return

            exists_already = adapter_name in self.adapters
            if not device.connected and exists_already:
                self.hass.async_create_task(self._remove_adapter(adapter_name))
            elif device.connected and not exists_already:
                adapter_instance = BleAdvShellyAdapter(self, adapter_name, bt_mac, rpc_device)
                self.hass.async_create_task(self._add_adapter(adapter_name, device_entry.id, adapter_instance))

        rpc_device.subscribe_updates(_on_aioshelly_update)

        # create the adapter only if connected, otherwise wait for the status update event to trigger the creation
        if rpc_device.connected:
            adapter = BleAdvShellyAdapter(self, adapter_name, bt_mac, rpc_device)
            await self._add_adapter(adapter_name, device_entry.id, adapter)
            return

    async def reset_adapter(self, adapter_name: str, reason: str) -> None:
        """Reset the designated adapter instance and trigger a fresh discovery loop."""
        self._add_diag(f"Resetting Shelly adapter '{adapter_name}' - {reason}")
        await self._remove_adapter(adapter_name)
        await asyncio.sleep(self.WAIT_REDISCOVER)
        await self._discover_existing()
