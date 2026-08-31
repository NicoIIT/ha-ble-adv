"""Provides device triggers."""

from abc import abstractmethod
from typing import Any, cast

import voluptuous as vol
from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.components.homeassistant.triggers import state as state_trigger
from homeassistant.const import (
    CONF_DEVICE,
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_ENTITY_ID,
    CONF_EVENT,
    CONF_EVENT_DATA,
    CONF_PLATFORM,
    CONF_STATE,
    CONF_TRIGGER,
    CONF_TYPE,
    EVENT_STATE_CHANGED,
)
from homeassistant.core import CALLBACK_TYPE, Context, HomeAssistant
from homeassistant.helpers.singleton import singleton
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.trigger import async_validate_trigger_config as async_validate_trigger_config_helper
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, TRIGGER_TYPE_ANY_STATE, TRIGGER_TYPE_EVENT_ENC_CMD
from .device import BleAdvDevice
from .helpers import BYTE_SELECTOR, ENC_CMD_PARAMS, get_device_from_id


class _SubTriggerBase:
    def __init__(self, conf_type: str, schema: dict[Any, Any]) -> None:
        self.conf_type: str = conf_type
        self.base_schema = vol.Schema(schema)
        self.full_schema = DEVICE_TRIGGER_BASE_SCHEMA.extend({vol.Required(CONF_TYPE): conf_type, **schema})

    @abstractmethod
    async def attach_trigger(self, hass: HomeAssistant, config: ConfigType, action: TriggerActionType, trigger_info: TriggerInfo) -> CALLBACK_TYPE:
        """Attach a trigger."""


class _AnyStateTrigger(_SubTriggerBase):
    PARAMS = {state_trigger.CONF_FROM: None, state_trigger.CONF_TO: None}
    SCHEMA = {(vol.Required(x) if v is not None else vol.Optional(x)): vol.Any(str, [str], None) for x, v in PARAMS.items()}

    def __init__(self) -> None:
        super().__init__(TRIGGER_TYPE_ANY_STATE, _AnyStateTrigger.SCHEMA)

    async def attach_trigger(self, hass: HomeAssistant, config: ConfigType, action: TriggerActionType, trigger_info: TriggerInfo) -> CALLBACK_TYPE:
        """Attach a trigger."""
        device: BleAdvDevice = await get_device_from_id(hass, config[CONF_DEVICE_ID])
        state_config = {
            CONF_PLATFORM: CONF_STATE,
            state_trigger.CONF_ENTITY_ID: device.entity_ids,
            state_trigger.CONF_FROM: config.get(state_trigger.CONF_FROM),
            state_trigger.CONF_TO: config.get(state_trigger.CONF_TO),
        }
        state_config = await state_trigger.async_validate_trigger_config(hass, state_config)
        return await state_trigger.async_attach_trigger(hass, state_config, action, trigger_info, platform_type=CONF_DEVICE)


class _EventTrigger(_SubTriggerBase):
    def __init__(self, event_type: str) -> None:
        super().__init__(event_type, {(vol.Required(x) if v is not None else vol.Optional(x)): BYTE_SELECTOR for x, v in ENC_CMD_PARAMS.items()})

    async def attach_trigger(self, hass: HomeAssistant, config: ConfigType, action: TriggerActionType, trigger_info: TriggerInfo) -> CALLBACK_TYPE:
        """Attach a trigger."""
        device = await get_device_from_id(hass, config[CONF_DEVICE_ID])
        event_config = {
            CONF_PLATFORM: CONF_EVENT,
            event_trigger.CONF_EVENT_TYPE: EVENT_STATE_CHANGED,
            CONF_EVENT_DATA: {CONF_ENTITY_ID: device.event_entity_id},
        }

        async def _handle_trigger(run_variables: dict[str, Any], context: Context | None = None) -> None:
            if (
                (new_state := run_variables.get(CONF_TRIGGER, {}).get(CONF_EVENT).data.get("new_state")) is None
                or new_state.attributes.get(event_trigger.CONF_EVENT_TYPE) != self.conf_type
                or any(config.get(x) is not None and new_state.attributes.get(x) != config.get(x) for x in ENC_CMD_PARAMS)
            ):
                return

            if (coro := action(run_variables, context)) is not None:
                await coro

        validated_config = await async_validate_trigger_config_helper(hass, [event_config])
        return await event_trigger.async_attach_trigger(hass, validated_config[0], _handle_trigger, trigger_info)


@singleton(f"{DOMAIN}/device_triggers")
def _get_triggers(_: HomeAssistant) -> dict[str, _SubTriggerBase]:
    triggers = [_AnyStateTrigger(), _EventTrigger(TRIGGER_TYPE_EVENT_ENC_CMD)]
    return {tr.conf_type: tr for tr in triggers}


def _get_trigger(hass: HomeAssistant, conf_type: str) -> _SubTriggerBase:
    if (sub_trig := _get_triggers(hass).get(conf_type)) is not None:
        return sub_trig
    msg = f"Unsupported trigger type '{conf_type}'"
    raise vol.Invalid(msg)


async def async_validate_trigger_config(hass: HomeAssistant, config: ConfigType) -> ConfigType:
    """Validate trigger config dynamically based on CONF_TYPE."""
    return cast("ConfigType", _get_trigger(hass, config[CONF_TYPE]).full_schema(config))


async def async_attach_trigger(hass: HomeAssistant, config: ConfigType, action: TriggerActionType, trigger_info: TriggerInfo) -> CALLBACK_TYPE:
    """Attach a trigger."""
    return await _get_trigger(hass, config[CONF_TYPE]).attach_trigger(hass, config, action, trigger_info)


async def async_get_triggers(hass: HomeAssistant, device_id: str) -> list[dict[str, str]]:
    """List device triggers."""
    return [{CONF_PLATFORM: CONF_DEVICE, CONF_DOMAIN: DOMAIN, CONF_DEVICE_ID: device_id, CONF_TYPE: x} for x in _get_triggers(hass)]


async def async_get_trigger_capabilities(hass: HomeAssistant, config: ConfigType) -> dict[str, Any]:
    """List trigger capabilities."""
    return {"extra_fields": _get_trigger(hass, config[CONF_TYPE]).base_schema}
