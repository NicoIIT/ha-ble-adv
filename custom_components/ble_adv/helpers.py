"""Provides device triggers."""

from dataclasses import MISSING, fields

import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig, NumberSelectorMode

from .codecs.models import BleAdvEncCmd
from .const import DOMAIN
from .device import BleAdvDevice

BYTE_SELECTOR = NumberSelector(NumberSelectorConfig(min=0, max=255, mode=NumberSelectorMode.BOX))
ENC_CMD_PARAMS = {f.name: (0 if f.default is MISSING else None) for f in fields(BleAdvEncCmd)}


# TO BE REMOVED with HA > 2026.8, use device.config_entry_id only
async def get_device_from_id(hass: HomeAssistant, device_id: str) -> BleAdvDevice:
    """Get BleAdvDevice from its device_id."""
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        msg = f"No device with ID '{device_id}'"
        raise vol.Invalid(msg)
    if hasattr(device, "config_entry_id"):
        entry_id = device.config_entry_id  # type: ignore  # noqa: PGH003
    else:
        entry_id = next(iter(device.config_entries)) if device.config_entries else None
    return hass.data[DOMAIN][entry_id]
