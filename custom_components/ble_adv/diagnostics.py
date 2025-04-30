"ble_adv Diagnostics."

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import get_coordinator


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    coordinator = await get_coordinator(hass)
    return {
        "entry_data": {**entry.data},
        "adapter_ids": coordinator.get_adapter_ids(),
    }
