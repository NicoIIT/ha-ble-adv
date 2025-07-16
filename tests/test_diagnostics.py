"""Config flow tests."""

# ruff: noqa: S101
from unittest import mock

from ble_adv.codecs import get_codecs
from ble_adv.const import CONF_APPLE_INC_UUIDS, CONF_GOOGLE_LCC_UUIDS
from ble_adv.diagnostics import async_get_config_entry_diagnostics
from homeassistant.core import HomeAssistant


async def test_diagnostics(hass: HomeAssistant) -> None:
    """Test diagnostics."""
    config_entry = mock.AsyncMock()
    config_entry.data = {"conf_data": "data"}
    assert await async_get_config_entry_diagnostics(hass, config_entry) == {
        "coordinator": {
            "adapter_ids": [],
            "codec_ids": list(get_codecs().keys()),
            "ign_adapters": [],
            "ign_duration": 20000,
            "ign_cids": list({*CONF_GOOGLE_LCC_UUIDS, *CONF_APPLE_INC_UUIDS}),
            "ign_macs": [],
        },
        "entry_data": {"conf_data": "data"},
    }
