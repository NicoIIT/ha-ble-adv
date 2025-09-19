"""Esp-adapters tests."""

# ruff: noqa: S101
from unittest import mock

from ble_adv.esp_adapters import BleAdvEspBtManager
from homeassistant.core import HomeAssistant

from tests.conftest import MockEspProxy


async def test_esp_bt_manager(hass: HomeAssistant) -> None:
    """Test ESP BT Manager."""
    moc_recv = mock.AsyncMock()
    moc_adapt = mock.AsyncMock()
    man = BleAdvEspBtManager(hass, moc_recv, moc_adapt, 10000, [], [])
    man.WAIT_REDISCOVER = 0
    t1 = MockEspProxy(hass, "esp-test1")
    await t1.setup()  # Adding proxy before init
    assert list(man.adapters.keys()) == []
    await man.async_init()
    assert list(man.adapters.keys()) == ["esp-test1"]
    moc_adapt.assert_awaited_once_with("esp-test1", True)
    moc_adapt.reset_mock()
    await t1.set_available(False)
    assert list(man.adapters.keys()) == []
    moc_adapt.assert_awaited_once_with("esp-test1", False)
    moc_adapt.reset_mock()
    await t1.set_available(True)
    assert list(man.adapters.keys()) == ["esp-test1"]
    t2 = MockEspProxy(hass, "esp-test2")
    await t2.setup()  # Adding proxy after init
    assert list(man.adapters.keys()) == ["esp-test1", "esp-test2"]
    t3 = MockEspProxy(hass, "esp-test3", True)
    await t3.setup()  # Adding proxy by dicovery event - LEGACY
    assert list(man.adapters.keys()) == ["esp-test1", "esp-test2", "esp-test3"]
    await man.reset_adapter("esp-test2", "test")
    assert list(man.adapters.keys()) == ["esp-test1", "esp-test3", "esp-test2"]
    await man.reset_adapter("esp-test3", "test")
    assert list(man.adapters.keys()) == ["esp-test1", "esp-test2"]
    await man.async_final()
