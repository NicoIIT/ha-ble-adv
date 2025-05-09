"""Config flow tests."""

# ruff: noqa: S101
from unittest import mock

from ble_adv.diagnostics import async_get_config_entry_diagnostics
from homeassistant.core import HomeAssistant


async def test_diagnostics(hass: HomeAssistant) -> None:
    """Test diagnostics."""
    config_entry = mock.AsyncMock()
    config_entry.data = {"conf_data": "data"}
    assert await async_get_config_entry_diagnostics(hass, config_entry) == {"entry_data": {"conf_data": "data"}, "adapter_ids": []}
