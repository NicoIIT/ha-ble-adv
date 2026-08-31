"""Provides device triggers."""

from dataclasses import MISSING, fields

import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig, NumberSelectorMode, ObjectSelectorField

from .codecs.models import BleAdvEncCmd
from .const import DOMAIN
from .device import BleAdvDevice

BYTE_SELECTOR = NumberSelector(NumberSelectorConfig(min=0, max=255, mode=NumberSelectorMode.BOX))
ENC_CMD_PARAMS = {f.name: (0 if f.default is MISSING else None) for f in fields(BleAdvEncCmd)}
ENC_CMD_SELECTOR = {f.name: ObjectSelectorField(selector=BYTE_SELECTOR, required=f.default is MISSING) for f in fields(BleAdvEncCmd)}


async def get_device_from_id(hass: HomeAssistant, device_id: str) -> BleAdvDevice:
    """Get BleAdvDevice from its device_id."""
    device_entry = dr.async_get(hass).async_get(device_id)
    if device_entry is not None and (device := hass.data[DOMAIN].get(device_entry.config_entry_id)) is not None:
        return device
    msg = f"No '{DOMAIN}' device with ID '{device_id}'"
    raise vol.Invalid(msg)
