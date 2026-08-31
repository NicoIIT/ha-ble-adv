"""Test Helpers."""

# ruff: noqa: S101
import pytest
import voluptuous as vol
from ble_adv.const import DOMAIN
from ble_adv.helpers import ENC_CMD_PARAMS, get_device_from_id
from homeassistant.core import HomeAssistant

from .conftest import create_base_entry


def test_enc_cmd_params() -> None:
    """Test the generation of ENC_CMD_PARAMS."""
    assert ENC_CMD_PARAMS == {"cmd": 0, "param": None, "arg0": None, "arg1": None, "arg2": None, "arg3": None, "arg4": None}


async def test_action_enc_cmd(hass: HomeAssistant) -> None:
    """Test device action enc_cmd."""
    conf_entry = await create_base_entry(hass, "my_entry", {})
    device = hass.data[DOMAIN][conf_entry.entry_id]
    dev2 = await get_device_from_id(hass, device.device_id)
    assert dev2 == device
    with pytest.raises(vol.Invalid):
        await get_device_from_id(hass, "unknown")
    assert hasattr(device, "config_entry_id")
    delattr(device, "config_entry_id")
    assert not hasattr(device, "config_entry_id")
    dev2 = await get_device_from_id(hass, device.device_id)
    assert dev2 == device
