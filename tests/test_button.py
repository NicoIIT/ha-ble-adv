"""Button Entity tests."""

from unittest import mock

from ble_adv.button import async_setup_entry
from ble_adv.device import BleAdvRepairButton
from homeassistant.core import HomeAssistant

from .conftest import create_base_entry


async def test_setup(hass: HomeAssistant) -> None:
    """Test async_setup_entry."""
    ent = await create_base_entry(hass, "ent_id", {})
    add_ent_mock = mock.MagicMock()
    await async_setup_entry(hass, ent, add_ent_mock)
    add_ent_mock.assert_called_once()
    button = add_ent_mock.call_args.args[0][0]
    assert isinstance(button, BleAdvRepairButton)


async def test_press_repairs_with_the_device(hass: HomeAssistant) -> None:
    """Pressing the button re-pairs the device it belongs to."""
    ent = await create_base_entry(hass, "ent_id", {})
    add_ent_mock = mock.MagicMock()
    await async_setup_entry(hass, ent, add_ent_mock)
    button = add_ent_mock.call_args.args[0][0]
    await button.async_press()
    ent.runtime_data.async_repair.assert_awaited_once()
