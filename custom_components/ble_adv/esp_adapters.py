"""BLE ADV ESPHome Adapters."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event

from .adapters import AdvRecvCallback, BleAdvAdapter
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ESPHOME_DOMAIN = "esphome"
ESPHOME_BLE_ADV_DISCOVERY_EVENT = f"{ESPHOME_DOMAIN}.{DOMAIN}.discovery"
ESPHOME_BLE_ADV_RECV_EVENT = f"{ESPHOME_DOMAIN}.{DOMAIN}.raw_adv"
CONF_ADV_SVCS = ["adv_svc_v1", "adv_svc"]
CONF_SETUP_SVCS = ["setup_svc_v0"]
CONF_ATTR_RAW = "raw"
CONF_ATTR_DURATION = "duration"
CONF_ATTR_REPEAT = "repeat"
CONF_ATTR_DEVICE_ID = "device_id"
CONF_ATTR_IGN_ADVS = "ignored_advs"
CONF_ATTR_IGN_CIDS = "ignored_cids"
CONF_ATTR_IGN_MACS = "ignored_macs"
CONF_ATTR_IGN_DURATION = "ignored_duration"
CONF_ATTR_ORIGIN = "orig"

CONF_ATTR_NAME = "name"
CONF_ATTR_MAC = "mac"
CONF_ATTR_RECV_EVENT_NAME = "adv_recv_event"
CONF_ATTR_PUBLISH_ADV_SVC = "publish_adv_svc"


class BleAdvEsphomeAdapter(BleAdvAdapter):
    """ESPHome BT Adapter with discovery based on Event - LEGACY."""

    def __init__(self, manager: BleAdvEspBtManager, conf: dict[str, str]) -> None:
        super().__init__(conf[CONF_ATTR_NAME], self._on_error, 100)
        self._conf = conf
        self.manager: BleAdvEspBtManager = manager

    async def open(self) -> None:
        """Open adapter."""
        self.logger.info("Connected")

    def close(self) -> None:
        """Close the adapter, nothing to do."""
        self.logger.info("Disconnected")

    async def _on_error(self, message: str) -> None:
        self.logger.warning(f"Unhandled error: {message}. Removing adapter")
        await self.manager.remove_adapter(self.name)

    async def _advertise(self, interval: int, repeat: int, data: bytes) -> None:
        """Advertise the msg."""
        await self.manager.hass.services.async_call(
            ESPHOME_DOMAIN, self._conf[CONF_ATTR_PUBLISH_ADV_SVC], {CONF_ATTR_RAW: data.hex(), CONF_ATTR_DURATION: repeat * interval}
        )
        await asyncio.sleep(0.0009 * repeat * interval)


class BleAdvEsphomeService:
    """ESPHome Dynamic Service.

    Chooses the best available service to call.
    Filters the supported attributes.
    Fill default values for unsupported attributes.
    """

    def __init__(self, hass: HomeAssistant, device_name: str, svcs: list[str]) -> None:
        self.hass: HomeAssistant = hass
        esp_svcs: list[str] = [f"{device_name}_{svc}" for svc in svcs]
        all_svcs = self.hass.services.async_services_for_domain(ESPHOME_DOMAIN)
        for esp_svc in esp_svcs:
            if esp_svc in all_svcs:
                self._svc_name = esp_svc
                break
        self._svc_attrs: dict[str, Any] = {attr: self._def_attr_val(val) for attr, val in all_svcs[self._svc_name].schema.schema.items()}  # type: ignore NONE

    def _def_attr_val(self, attr_type: Any) -> Any:  # noqa: ANN401
        return [] if isinstance(attr_type, list) else "" if attr_type == cv.string else False if attr_type == cv.boolean else 0

    async def call(self, attrs: dict[str, Any]) -> None:
        """Call the service with the given attributes, filtered with the effectively available attributes and default values for others."""
        attrs = {attr: attrs.get(attr, def_val) for attr, def_val in self._svc_attrs.items()}
        await self.hass.services.async_call(ESPHOME_DOMAIN, self._svc_name, attrs)


class BleAdvEsphomeAdapterV2(BleAdvAdapter):
    """ESPHome BT Adapter with discovery based on text_sensor name entity."""

    def __init__(self, manager: BleAdvEspBtManager, adapter_name: str, device_name: str) -> None:
        super().__init__(adapter_name, self._on_error, 100)
        self.manager: BleAdvEspBtManager = manager
        self._adv_svc_: BleAdvEsphomeService = BleAdvEsphomeService(manager.hass, device_name, CONF_ADV_SVCS)
        self._setup_svc_: BleAdvEsphomeService = BleAdvEsphomeService(manager.hass, device_name, CONF_SETUP_SVCS)

    async def open(self) -> None:
        """Open adapter."""
        call_params = {
            CONF_ATTR_IGN_DURATION: self.manager.ign_duration,
            CONF_ATTR_IGN_CIDS: self.manager.ign_cids,
            CONF_ATTR_IGN_MACS: self.manager.ign_macs,
        }
        await self._setup_svc_.call(call_params)
        self.logger.info("Connected")

    def close(self) -> None:
        """Close the adapter, nothing to do."""
        self.logger.info("Disconnected")

    async def _on_error(self, message: str) -> None:
        self.logger.warning(f"Unhandled error: {message}. Removing adapter")
        await self.manager.remove_adapter(self.name)

    async def _advertise(self, interval: int, repeat: int, data: bytes) -> None:
        """Advertise the msg."""
        params = {
            CONF_ATTR_RAW: data.hex(),
            CONF_ATTR_DURATION: interval,
            CONF_ATTR_REPEAT: repeat,
            CONF_ATTR_IGN_DURATION: int(1.5 * interval * repeat),
            CONF_ATTR_IGN_ADVS: [data.hex()],
        }
        await self._adv_svc_.call(params)
        await asyncio.sleep(0.0009 * repeat * interval)


class BleAdvEspBtManager:
    """Class to manage ESPHome BLE ADV Proxies Bluetooth Adapters."""

    PROXY_NAME_PATTERN: re.Pattern = re.compile(r"sensor.(\w+)_ble_adv_proxy_name")

    def __init__(self, hass: HomeAssistant, adv_recv_callback: AdvRecvCallback, ign_duration: int, ign_cids: list[int], ign_macs: list[str]) -> None:
        """Init."""
        self.hass: HomeAssistant = hass
        self.handle_raw_adv = adv_recv_callback
        self.ign_duration: int = ign_duration
        self.ign_cids: list[int] = ign_cids
        self.ign_macs: list[str] = ign_macs
        self.adapters: dict[str, BleAdvAdapter] = {}
        self._device_to_name: dict[str, str] = {}
        self._cnl_clbck: list[CALLBACK_TYPE] = []

    async def async_init(self) -> None:
        """Async Init."""
        ent_reg = er.async_get(self.hass)
        proxy_name_ids = [ent.entity_id for ent in ent_reg.entities.values() if self.PROXY_NAME_PATTERN.match(ent.entity_id) is not None]
        _LOGGER.debug(f"BLE ADV Name Entities: {proxy_name_ids}")
        for entity_id in proxy_name_ids:
            if (adapter_name := self._get_name_from_state(self.hass.states.get(entity_id))) is not None:
                await self._create_adapter(adapter_name, entity_id)

        self._cnl_clbck.append(async_track_state_change_event(self.hass, proxy_name_ids, self._async_name_state_changed_listener))
        self._cnl_clbck.append(self.hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, self._proxy_created, event_filter=self._proxy_filter))
        self._cnl_clbck.append(self.hass.bus.async_listen(ESPHOME_BLE_ADV_DISCOVERY_EVENT, self._on_discovery_event))
        self._cnl_clbck.append(self.hass.bus.async_listen(ESPHOME_BLE_ADV_RECV_EVENT, self._on_adv_recv_event))

    async def async_final(self) -> None:
        """Async Final: Clean-up."""
        for cancel_callback in self._cnl_clbck:
            cancel_callback()
        self._cnl_clbck.clear()
        for adapter in self.adapters.values():
            await adapter.async_final()
        self.adapters.clear()

    def _get_name_from_state(self, name_state: State | None) -> str | None:
        if name_state is None or name_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None
        return name_state.state

    async def _create_adapter(self, adapter_name: str, entity_id: str) -> None:
        if adapter_name in self.adapters:
            return
        device_name = dv.group(1) if (dv := self.PROXY_NAME_PATTERN.match(entity_id)) is not None else adapter_name.replace("-", "_")
        if (ent := er.async_get(self.hass).async_get(entity_id)) is not None and (dev_id := ent.device_id) is not None:
            self._device_to_name[dev_id] = adapter_name

        self.adapters[adapter_name] = BleAdvEsphomeAdapterV2(self, adapter_name, device_name)
        await self.adapters[adapter_name].async_init()

    async def remove_adapter(self, adapter_name: str) -> None:
        """Remove an adapter."""
        if (adapter := self.adapters.pop(adapter_name, None)) is not None:
            await adapter.async_final()
            self._device_to_name = {k: v for k, v in self._device_to_name.items() if v != adapter_name}

    async def _async_name_state_changed_listener(self, event: Event[EventStateChangedData]) -> None:
        _LOGGER.debug(f"Name State Event: {event.data}")
        if (adapter_name := self._get_name_from_state(event.data["new_state"])) is not None:
            await self._create_adapter(adapter_name, event.data["entity_id"])
        elif (adapter_name := self._get_name_from_state(event.data["old_state"])) is not None:
            await self.remove_adapter(adapter_name)

    @callback
    def _proxy_filter(self, event_data: er.EventEntityRegistryUpdatedData) -> bool:
        return event_data["action"] == "create" and self.PROXY_NAME_PATTERN.match(event_data["entity_id"]) is not None

    async def _proxy_created(self, event: Event[er.EventEntityRegistryUpdatedData]) -> None:
        _LOGGER.debug(f"Registry Event: {event.data['entity_id']} {event.data['action']}")
        self._cnl_clbck.append(async_track_state_change_event(self.hass, [event.data["entity_id"]], self._async_name_state_changed_listener))

    async def _on_discovery_event(self, event: Event) -> None:
        # //_LOGGER.debug(f"Discovery Event: {event.data}")
        adapter_name = event.data[CONF_ATTR_NAME]
        if adapter_name not in self.adapters:
            _LOGGER.warning("ESPHome ble_adv_proxy LEGACY discovery by Event, please upgrade your proxy to latest version.")
            self._device_to_name[event.data[CONF_ATTR_DEVICE_ID]] = adapter_name
            self.adapters[adapter_name] = BleAdvEsphomeAdapter(self, {**event.data})
            await self.adapters[adapter_name].async_init()

    async def _on_adv_recv_event(self, event: Event) -> None:
        # //_LOGGER.debug(f"ESPHome ADV recv Event: {event.data}")
        await self.handle_raw_adv(
            self._device_to_name.get(event.data.get(CONF_ATTR_DEVICE_ID, ""), "no_adapter"),
            event.data.get(CONF_ATTR_ORIGIN, ""),
            bytes.fromhex(event.data[CONF_ATTR_RAW]),
        )
