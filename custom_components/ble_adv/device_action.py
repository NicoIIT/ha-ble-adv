"""Provides device actions for BleAdvDevice."""

from abc import abstractmethod
from typing import Any, cast

import voluptuous as vol
from homeassistant.const import (
    CONF_DEVICE,
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_PLATFORM,
    CONF_TYPE,
)
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.singleton import singleton
from homeassistant.helpers.typing import ConfigType, TemplateVarsType

from .codecs.models import BleAdvEncCmd
from .const import DOMAIN, TRIGGER_TYPE_EVENT_ENC_CMD
from .device import BleAdvDevice
from .helpers import BYTE_SELECTOR, ENC_CMD_PARAMS, get_device_from_id

DEVICE_ACTION_BASE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PLATFORM): CONF_DEVICE,
        vol.Required(CONF_DOMAIN): cv.string,
        vol.Required(CONF_DEVICE_ID): cv.string,
    }
)


class _SubActionBase:
    def __init__(self, conf_type: str, schema: dict[Any, Any]) -> None:
        self.conf_type: str = conf_type
        self.base_schema = vol.Schema(schema)
        self.full_schema = DEVICE_ACTION_BASE_SCHEMA.extend({vol.Required(CONF_TYPE): conf_type, **schema})

    @abstractmethod
    async def async_call_action(self, hass: HomeAssistant, config: ConfigType, variables: TemplateVarsType, context: Context | None = None) -> None:
        """Execute the action."""


class _CommandAction(_SubActionBase):
    def __init__(self, event_type: str) -> None:
        super().__init__(event_type, {(vol.Required(x) if v is not None else vol.Optional(x)): BYTE_SELECTOR for x, v in ENC_CMD_PARAMS.items()})

    async def async_call_action(self, hass: HomeAssistant, config: ConfigType, _: TemplateVarsType, __: Context | None = None) -> None:
        """Execute the action by sending the command to the device."""
        device: BleAdvDevice = await get_device_from_id(hass, config[CONF_DEVICE_ID])
        enc_cmd = BleAdvEncCmd(**{x: int(config.get(x, 0)) for x in ENC_CMD_PARAMS if config.get(x) is not None})
        await device.apply_cmd(enc_cmd)


@singleton(f"{DOMAIN}/device_actions")
def _get_actions(_: HomeAssistant) -> dict[str, _SubActionBase]:
    actions = [_CommandAction(TRIGGER_TYPE_EVENT_ENC_CMD)]
    return {act.conf_type: act for act in actions}


def _get_action(hass: HomeAssistant, conf_type: str) -> _SubActionBase:
    if (sub_act := _get_actions(hass).get(conf_type)) is not None:
        return sub_act
    msg = f"Unsupported action type '{conf_type}'"
    raise vol.Invalid(msg)


async def async_validate_action_config(hass: HomeAssistant, config: ConfigType) -> ConfigType:
    """Validate action config dynamically based on CONF_TYPE."""
    return cast("ConfigType", _get_action(hass, config[CONF_TYPE]).full_schema(config))


async def async_call_action_from_config(hass: HomeAssistant, config: ConfigType, variables: TemplateVarsType, context: Context | None = None) -> None:
    """Execute a device action from a configuration block."""
    await _get_action(hass, config[CONF_TYPE]).async_call_action(hass, config, variables, context)


async def async_get_actions(hass: HomeAssistant, device_id: str) -> list[dict[str, str]]:
    """List device actions."""
    return [{CONF_PLATFORM: CONF_DEVICE, CONF_DOMAIN: DOMAIN, CONF_DEVICE_ID: device_id, CONF_TYPE: x} for x in _get_actions(hass)]


async def async_get_action_capabilities(hass: HomeAssistant, config: ConfigType) -> dict[str, Any]:
    """List action capabilities."""
    return {"extra_fields": _get_action(hass, config[CONF_TYPE]).base_schema}
