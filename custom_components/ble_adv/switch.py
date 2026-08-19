"""Switch Handling."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SILENT_SWITCH_TYPE
from .device import BleAdvDevice, BleAdvSwitch


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Entry setup."""
    device: BleAdvDevice = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BleAdvSwitch(device, SILENT_SWITCH_TYPE)], True)
