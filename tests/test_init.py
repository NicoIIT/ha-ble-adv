"""ble_adv component init tests."""

# ruff: noqa: S101
from unittest import mock

from ble_adv import async_migrate_entry, async_setup, async_setup_entry, async_unload_entry, get_coordinator
from ble_adv.const import (
    CONF_ADAPTER_ID,
    CONF_ADAPTER_IDS,
    CONF_CODEC_ID,
    CONF_DURATION,
    CONF_FANS,
    CONF_FORCE_SEND,
    CONF_FORCED_ID,
    CONF_INDEX,
    CONF_INTERVAL,
    CONF_LIGHTS,
    CONF_RAW,
    CONF_REFRESH_DIR_ON_START,
    CONF_REFRESH_ON_START,
    CONF_REFRESH_OSC_ON_START,
    CONF_REMOTE,
    CONF_REPEAT,
    CONF_REPEATS,
    CONF_TECHNICAL,
    CONF_USE_DIR,
    DOMAIN,
)
from homeassistant.const import CONF_DEVICE, CONF_NAME
from homeassistant.core import HomeAssistant

from .conftest import create_base_entry


async def test_setup(hass: HomeAssistant) -> None:
    """Test component setup."""
    await async_setup(hass, {})


BASE_DEVICE_CONF = {CONF_CODEC_ID: "fanlamp_pro_v1", CONF_FORCED_ID: 0x1010, CONF_INDEX: 0}
BASE_TECH_CONF = {CONF_REPEAT: 1, CONF_INTERVAL: 20, CONF_DURATION: 100}
BASE_REMOTE_CONF = {CONF_CODEC_ID: "fanlamp_pro_v1", CONF_FORCED_ID: 0x2020, CONF_INDEX: 0}

BASE_CONF_V0 = {
    CONF_DEVICE: {CONF_ADAPTER_ID: "adapter_id", **BASE_DEVICE_CONF},
    CONF_TECHNICAL: BASE_TECH_CONF,
    CONF_FANS: [{}, {}, {}],
    CONF_LIGHTS: [{}, {}, {}],
}

BASE_CONF_V2 = {
    CONF_DEVICE: BASE_DEVICE_CONF,
    CONF_TECHNICAL: {CONF_ADAPTER_ID: "adapter_id", **BASE_TECH_CONF},
    CONF_FANS: [{}, {}, {}],
    CONF_LIGHTS: [{}, {}, {}],
}

BASE_CONF = {
    CONF_DEVICE: BASE_DEVICE_CONF,
    CONF_TECHNICAL: {CONF_REPEATS: 3, CONF_ADAPTER_IDS: ["adapter_id"], CONF_FORCE_SEND: False, **BASE_TECH_CONF},
    CONF_FANS: [{}, {}, {}],
    CONF_LIGHTS: [{}, {}, {}],
}

BASE_CONF_W_REMOTE = {**BASE_CONF, CONF_REMOTE: BASE_REMOTE_CONF}


async def test_setup_entry(hass: HomeAssistant) -> None:
    """Test entry with latest config."""
    entry = await create_base_entry(hass, "idlast", BASE_CONF_W_REMOTE)
    hass.config_entries.async_forward_entry_setups = mock.AsyncMock()
    await async_setup(hass, {DOMAIN: {"ignored_adapters": ["hci"]}})
    await async_setup_entry(hass, entry)
    assert entry.entry_id in hass.data[DOMAIN]
    coord = await get_coordinator(hass)
    coord.inject_raw = mock.AsyncMock(return_value={"test": "error"})
    await hass.services.async_call(DOMAIN, "inject_raw", {CONF_ADAPTER_ID: "a", CONF_RAW: "r"})
    coord.inject_raw.assert_awaited_once_with(
        {"adapter_id": "a", "raw": "r", "device_queue": "device", "interval": 20.0, "repeat": 3.0, "duration": 800.0}
    )
    await async_unload_entry(hass, entry)
    assert entry.entry_id not in hass.data[DOMAIN]


async def test_setup_entry_no_id(hass: HomeAssistant) -> None:
    """Test entry with latest config but no unique_id."""
    entry = await create_base_entry(hass, None, {}, 4)
    await async_setup_entry(hass, entry)
    assert entry.entry_id not in hass.data.get(DOMAIN, [])


async def test_migrate_v1_no_adapter(hass: HomeAssistant) -> None:
    """Test migration from config v1."""
    conf = await create_base_entry(hass, "idv10", BASE_CONF_V0, 1)
    await async_migrate_entry(hass, conf)
    assert conf.data[CONF_TECHNICAL][CONF_ADAPTER_IDS] == ["adapter_id"]


async def test_migrate_v1_one_adapter(hass: HomeAssistant) -> None:
    """Test migration from config v1."""
    conf = await create_base_entry(hass, "idv11", BASE_CONF_V0, 1)
    coordinator = await get_coordinator(hass)
    coordinator.get_adapter_ids = mock.MagicMock(return_value=["new_id"])
    await async_migrate_entry(hass, conf)
    assert conf.data[CONF_TECHNICAL][CONF_ADAPTER_IDS] == ["new_id"]


async def test_migrate_v1_two_adapter(hass: HomeAssistant) -> None:
    """Test migration from config v1."""
    conf = await create_base_entry(hass, "idv12", BASE_CONF_V0, 1)
    coordinator = await get_coordinator(hass)
    coordinator.get_adapter_ids = mock.MagicMock(return_value=["new_id2", "other_id"])
    await async_migrate_entry(hass, conf)
    assert conf.data[CONF_TECHNICAL][CONF_ADAPTER_IDS] == ["new_id2", "other_id"]


async def test_migrate_v2(hass: HomeAssistant) -> None:
    """Test migration from config v2."""
    conf_wrong_adapt = BASE_CONF_V2.copy()
    conf_wrong_adapt[CONF_DEVICE][CONF_ADAPTER_ID] = "prev_adapter_id"
    conf_wrong_adapt[CONF_DEVICE][CONF_NAME] = "name"
    conf = await create_base_entry(hass, "idv2", conf_wrong_adapt, 1)
    await async_migrate_entry(hass, conf)
    assert conf.data[CONF_TECHNICAL][CONF_ADAPTER_IDS] == ["prev_adapter_id"]
    assert CONF_NAME not in conf.data[CONF_DEVICE]


async def test_migrate_v3(hass: HomeAssistant) -> None:
    """Test migration from config v3."""
    conf_wrong_adapt = BASE_CONF_W_REMOTE.copy()
    conf_wrong_adapt[CONF_REMOTE][CONF_ADAPTER_ID] = "prev_adapter_id"
    conf = await create_base_entry(hass, "idv31", conf_wrong_adapt, 1)
    await async_migrate_entry(hass, conf)
    assert CONF_ADAPTER_ID not in conf.data[CONF_REMOTE]


async def test_migrate_v3_entities(hass: HomeAssistant) -> None:
    """Test migration from config v3 for FAN / LIGHT entities."""
    conf_ent = BASE_CONF_W_REMOTE.copy()
    conf_ent[CONF_FANS] = [{CONF_REFRESH_ON_START: True, CONF_USE_DIR: True}, {CONF_REFRESH_ON_START: False}]
    conf_ent[CONF_LIGHTS] = [{}]
    conf = await create_base_entry(hass, "idv32", conf_ent, 1)
    await async_migrate_entry(hass, conf)
    assert conf.data[CONF_FANS] == [
        {CONF_REFRESH_DIR_ON_START: True, CONF_REFRESH_OSC_ON_START: False, CONF_USE_DIR: True},
        {CONF_REFRESH_DIR_ON_START: False, CONF_REFRESH_OSC_ON_START: False},
        {},
    ]
    assert conf.data[CONF_LIGHTS] == [{}, {}, {}]


async def test_migrate_v4(hass: HomeAssistant) -> None:
    """Test migration from config v4."""
    conf = await create_base_entry(hass, "idv41", BASE_CONF, 4)
    await async_migrate_entry(hass, conf)
    assert CONF_ADAPTER_ID not in conf.data[CONF_TECHNICAL]
    assert conf.data[CONF_TECHNICAL][CONF_ADAPTER_IDS] == ["adapter_id"]


async def test_default_ign_cids(hass: HomeAssistant) -> None:
    """Test that Company IDs ignored by default are not used by codecs."""
    coord = await get_coordinator(hass)
    used_cids = [int.from_bytes(codec._header[:2], "little") for codec in coord.codecs.values()]  # noqa: SLF001
    common_cids = [cid for cid in used_cids if cid in coord.ign_cids]
    assert common_cids == []
