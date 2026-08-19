"""Switch Entity tests."""

from unittest import mock

from ble_adv.switch import async_setup_entry
from homeassistant.core import HomeAssistant

from .conftest import create_base_entry


async def test_setup(hass: HomeAssistant) -> None:
    """Test async_setup_entry."""
    ent = await create_base_entry(hass, "ent_id", {})
    add_ent_mock = mock.MagicMock()
    await async_setup_entry(hass, ent, add_ent_mock)
    add_ent_mock.assert_called_once()
