"""Init for HA tests."""

from collections.abc import AsyncGenerator
from typing import Any
from unittest import mock

import pytest
import voluptuous as vol
from ble_adv import async_setup, get_coordinator
from ble_adv.codecs.models import BleAdvEntAttr
from ble_adv.const import CONF_LAST_VERSION, DOMAIN
from ble_adv.coordinator import BleAdvCoordinator
from ble_adv.device import BleAdvEntity
from ble_adv.esp_adapters import (
    CONF_ATTR_DEVICE_ID,
    CONF_ATTR_IGN_DURATION,
    CONF_ATTR_RAW,
    ESPHOME_BLE_ADV_RECV_EVENT,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er


class _Device(mock.AsyncMock):
    unique_id = "device_id"
    available = True
    force_send = False

    add_entity = mock.MagicMock()

    def assert_apply_change(self, ent: BleAdvEntity, chgs: list[str]) -> None:
        self.apply_change.assert_called_once_with(BleAdvEntAttr(chgs, ent.get_attrs(), ent._base_type, ent._index))  # noqa: SLF001
        self.apply_change.reset_mock()

    def assert_no_change(self) -> None:
        self.apply_change.assert_not_called()


class _MockEsphomeConfigEntry(ConfigEntry):
    def __init__(self, bn: str) -> None:
        super().__init__(
            domain="esphome",
            unique_id=f"esp_unique_id_{bn}",
            data={},
            version=1,
            minor_version=0,
            title=bn,
            source="",
            discovery_keys={},  # type: ignore [none]
            options={},
        )
        self.runtime_data = mock.MagicMock()
        self.runtime_data.device_info.name = bn
        self.runtime_data.device_info.mac = "00:00:00:00:00:00"


@pytest.fixture
def device() -> _Device:
    """Fixture device."""
    return _Device()


class MockEspProxy:
    """Mock an ESPHome ble_adv_proxy."""

    def __init__(self, hass: HomeAssistant, name: str) -> None:
        self.hass = hass
        self._name = name
        self._bn = self._name.replace("-", "_")
        self._dev_id = f"{self._bn}_dev_id"
        self._adv_calls = []
        self._setup_calls = []

    def _call_adv(self, call: ServiceCall) -> None:
        self._adv_calls.append(call.data)

    def get_adv_calls(self) -> list[dict[str, Any]]:
        """Get the ADV Calls."""
        calls = self._adv_calls.copy()
        self._adv_calls.clear()
        return calls

    def _call_setup(self, call: ServiceCall) -> None:
        self._setup_calls.append(call.data)

    def get_setup_calls(self) -> list[dict[str, Any]]:
        """Get the SETUP Calls."""
        calls = self._setup_calls.copy()
        self._setup_calls.clear()
        return calls

    async def setup(self) -> None:
        """Set the ble_adv_proxy."""
        # Set the ble_adv_proxy by registering services and entities
        setup_schema = {vol.Required(CONF_ATTR_IGN_DURATION): int}
        adv_schema = {vol.Required(CONF_ATTR_RAW): str}
        self.hass.services.async_register("esphome", f"{self._bn}_setup_svc_v0", self._call_setup, vol.Schema(setup_schema))
        self.hass.services.async_register("esphome", f"{self._bn}_adv_svc_v1", self._call_adv, vol.Schema(adv_schema))
        esp_conf = _MockEsphomeConfigEntry(self._bn)
        await self.hass.config_entries.async_add(esp_conf)
        dr.async_get(self.hass).devices[self._dev_id] = mock.AsyncMock()
        er.async_get(self.hass).async_get_or_create("sensor", self._bn, "ble_adv_proxy_name", device_id=self._dev_id, config_entry=esp_conf)
        await self.set_available(True)

    async def set_available(self, status: bool) -> None:
        """Set the status."""
        state = self._name if status else STATE_UNAVAILABLE
        self.hass.async_add_executor_job(self.hass.states.set, f"sensor.{self._bn}_ble_adv_proxy_name", state)
        await self.hass.async_block_till_done(wait_background_tasks=True)

    async def recv(self, raw: str) -> None:
        """Receive an adv."""
        self.hass.bus.async_fire(ESPHOME_BLE_ADV_RECV_EVENT, {CONF_ATTR_DEVICE_ID: self._dev_id, CONF_ATTR_RAW: raw})


async def create_base_entry(hass: HomeAssistant, entry_id: str | None, data: dict[str, Any], version: int = CONF_LAST_VERSION) -> ConfigEntry:
    """Create a base Entry with default attributes."""
    # for higher HA versions, add parameter: subentries_data=[],
    conf = ConfigEntry(
        domain=DOMAIN,
        unique_id=entry_id,
        data=data,
        version=version,
        minor_version=0,
        title="tl",
        source="",
        discovery_keys={},  # type: ignore [none]
        options={},
    )
    await hass.config_entries.async_add(entry=conf)
    if entry_id is not None:
        hass.data.setdefault(DOMAIN, {})[conf.entry_id] = _Device()
    return conf


@pytest.fixture
async def coord(hass: HomeAssistant) -> AsyncGenerator[BleAdvCoordinator]:
    """Get Basic coordinator with no hci adapter."""
    await async_setup(hass, {DOMAIN: {"ignored_adapters": ["hci"]}})
    coord = await get_coordinator(hass)
    yield coord
    await coord.async_final()
