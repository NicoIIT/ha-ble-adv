"""Device Trigger tests."""

# ruff: noqa: S101
from unittest import mock

import pytest
import voluptuous as vol
from ble_adv import device_trigger
from ble_adv.const import DOMAIN
from homeassistant.core import HomeAssistant

from .conftest import create_base_entry


async def test_list_trigger(hass: HomeAssistant) -> None:
    """Test List Trigger."""
    lst = await device_trigger.async_get_triggers(hass, "toto")
    assert lst == [
        {"device_id": "toto", "domain": "ble_adv", "platform": "device", "type": "any_entity_state"},
        {"device_id": "toto", "domain": "ble_adv", "platform": "device", "type": "enc_cmd"},
    ]


async def test_attach_trigger_any_state(hass: HomeAssistant) -> None:
    """Test attach trigger any_entity_state."""
    conf_entry = await create_base_entry(hass, "my_entry", {})
    device_id = hass.data[DOMAIN][conf_entry.entry_id].device_id
    conf = {"device_id": device_id, "domain": "ble_adv", "platform": "device", "type": "any_entity_state"}
    await device_trigger.async_validate_trigger_config(hass, conf)
    await device_trigger.async_attach_trigger(hass, conf, mock.MagicMock(), mock.MagicMock())
    capa = await device_trigger.async_get_trigger_capabilities(hass, conf)
    assert set(capa["extra_fields"].schema.keys()) == {"from", "to"}
    conf = {"device_id": device_id, "domain": "ble_adv", "platform": "device", "type": "unknown"}
    with pytest.raises(vol.Invalid):
        await device_trigger.async_validate_trigger_config(hass, conf)


async def test_attach_trigger_enc_cmd(hass: HomeAssistant) -> None:
    """Test attach trigger enc_cmd."""
    conf_entry = await create_base_entry(hass, "my_entry", {})
    device_id = hass.data[DOMAIN][conf_entry.entry_id].device_id
    conf = {"device_id": device_id, "domain": "ble_adv", "platform": "device", "type": "enc_cmd", "cmd": 0}
    await device_trigger.async_validate_trigger_config(hass, conf)
    await device_trigger.async_attach_trigger(hass, conf, mock.MagicMock(), mock.MagicMock())
    capa = await device_trigger.async_get_trigger_capabilities(hass, conf)
    assert set(capa["extra_fields"].schema.keys()) == {"cmd", "param", "arg0", "arg1", "arg2", "arg3", "arg4"}
    conf = {"device_id": device_id, "domain": "ble_adv", "platform": "device", "type": "enc_cmd", "cmd": 0, "unknown_param": "toto"}
    with pytest.raises(vol.Invalid):
        await device_trigger.async_validate_trigger_config(hass, conf)
