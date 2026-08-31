"""Device Action tests."""

# ruff: noqa: S101
from unittest import mock

import pytest
import voluptuous as vol
from ble_adv import device_action
from ble_adv.const import DOMAIN
from homeassistant.core import HomeAssistant

from .conftest import create_base_entry


async def test_list_action(hass: HomeAssistant) -> None:
    """Test List Action."""
    lst = await device_action.async_get_actions(hass, "toto")
    assert lst == [{"device_id": "toto", "domain": "ble_adv", "platform": "device", "type": "enc_cmd"}]


async def test_action_enc_cmd(hass: HomeAssistant) -> None:
    """Test device action enc_cmd."""
    conf_entry = await create_base_entry(hass, "my_entry", {})
    device_id = hass.data[DOMAIN][conf_entry.entry_id].device_id
    conf = {"device_id": device_id, "domain": "ble_adv", "platform": "device", "type": "enc_cmd", "cmd": 0}
    await device_action.async_validate_action_config(hass, conf)
    await device_action.async_call_action_from_config(hass, conf, mock.MagicMock(), mock.MagicMock())
    capa = await device_action.async_get_action_capabilities(hass, conf)
    assert set(capa["extra_fields"].schema.keys()) == {"cmd", "param", "arg0", "arg1", "arg2", "arg3", "arg4"}
    conf = {"device_id": device_id, "domain": "ble_adv", "platform": "device", "type": "enc_cmd", "cmd": 0, "unknown_param": "toto"}
    with pytest.raises(vol.Invalid):
        await device_action.async_validate_action_config(hass, conf)
