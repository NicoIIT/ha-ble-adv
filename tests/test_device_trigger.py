"""Device Trigger tests."""

# ruff: noqa: S101
from unittest import mock

from ble_adv import device_trigger
from homeassistant.core import HomeAssistant


async def test_list_trigger(hass: HomeAssistant) -> None:
    """Test List Trigger."""
    lst = await device_trigger.async_get_triggers(hass, "toto")
    assert lst == [{"device_id": "toto", "domain": "ble_adv", "platform": "device", "type": "any_entity_state"}]


async def test_attach_trigger(hass: HomeAssistant) -> None:
    """Test attach trigger."""
    conf = {"device_id": "toto", "domain": "ble_adv", "platform": "device", "type": "any_entity_state"}
    await device_trigger.async_attach_trigger(hass, conf, mock.MagicMock(), mock.MagicMock())
