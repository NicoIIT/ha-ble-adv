"""Provides device triggers."""

import voluptuous as vol
from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import state as state_trigger
from homeassistant.const import CONF_DEVICE, CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_STATE, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

TRIGGER_TYPE_ANY_STATE = "any_entity_state"
CONF_TYPES = [TRIGGER_TYPE_ANY_STATE]

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(CONF_TYPES),
        vol.Optional(state_trigger.CONF_FROM): vol.Any(str, [str], None),
        vol.Optional(state_trigger.CONF_TO): vol.Any(str, [str], None),
    }
)


async def async_attach_trigger(hass: HomeAssistant, config: ConfigType, action: TriggerActionType, trigger_info: TriggerInfo) -> CALLBACK_TYPE:
    """Listen for device's entities state changes."""
    entities = er.async_entries_for_device(er.async_get(hass), config[CONF_DEVICE_ID])
    state_config = {
        CONF_PLATFORM: CONF_STATE,
        state_trigger.CONF_ENTITY_ID: [x.entity_id for x in entities],
        state_trigger.CONF_FROM: config.get(state_trigger.CONF_FROM),
        state_trigger.CONF_TO: config.get(state_trigger.CONF_TO),
    }

    state_config = await state_trigger.async_validate_trigger_config(hass, state_config)
    return await state_trigger.async_attach_trigger(hass, state_config, action, trigger_info, platform_type=CONF_DEVICE)


async def async_get_triggers(_: HomeAssistant, device_id: str) -> list[dict[str, str]]:
    """List device triggers."""
    return [{CONF_PLATFORM: CONF_DEVICE, CONF_DOMAIN: DOMAIN, CONF_DEVICE_ID: device_id, CONF_TYPE: x} for x in CONF_TYPES]
