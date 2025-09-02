"""Config flow tests."""

# ruff: noqa: S101
from unittest import mock

from ble_adv.const import CONF_APPLE_INC_UUIDS, CONF_GOOGLE_LCC_UUIDS
from ble_adv.diagnostics import async_get_config_entry_diagnostics
from homeassistant.core import HomeAssistant


async def test_diagnostics(hass: HomeAssistant) -> None:
    """Test diagnostics."""
    config_entry = mock.AsyncMock()
    config_entry.data = {"conf_data": "data"}
    diag = await async_get_config_entry_diagnostics(hass, config_entry)
    # remove variable info
    diag["coordinator"]["esp"]["logs"].clear()
    diag["coordinator"]["hci"]["supported_by_host"] = True
    assert diag == {
        "coordinator": {
            "esp": {"adapters": {}, "ids": {}, "logs": []},
            "hci": {"adapters": {}, "ids": {}, "logs": [], "supported_by_host": True},
            "ign_adapters": [],
            "ign_duration": 60000,
            "ign_cids": list({*CONF_GOOGLE_LCC_UUIDS, *CONF_APPLE_INC_UUIDS}),
            "ign_macs": [],
            "last_dec_raw": {},
            "last_emitted": {},
            "last_unk_raw": {},
        },
        "entry_data": config_entry.data,
    }
