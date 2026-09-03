"""Shelly Adapters tests."""

# ruff: noqa: S101
import binascii
from unittest import mock

from ble_adv.adapters import BleAdvQueueItem
from ble_adv.coordinator import BleAdvCoordinator
from ble_adv.shelly_adapters import BleAdvShellyBtManager
from homeassistant.core import HomeAssistant

from .conftest import MockShellyDevice


async def test_shelly_bt_manager(hass: HomeAssistant, coord: BleAdvCoordinator) -> None:  # noqa: ARG001
    """Test Shelly BT Manager."""
    moc_recv = mock.AsyncMock()
    moc_adapt = mock.AsyncMock()
    man = BleAdvShellyBtManager(hass, moc_recv, moc_adapt)
    man.WAIT_REDISCOVER = 0
    t1 = MockShellyDevice(hass, "shelly-test1", "01")
    await t1.setup()  # Adding device before init
    assert list(man.adapters.keys()) == []
    await man.async_init()
    assert list(man.adapters.keys()) == ["shelly-test1"]
    moc_adapt.assert_awaited_once_with("shelly-test1", True)
    moc_adapt.reset_mock()
    await t1.set_available(False)
    assert list(man.adapters.keys()) == []
    moc_adapt.assert_awaited_once_with("shelly-test1", False)
    moc_adapt.reset_mock()
    await t1.set_available(True)
    assert list(man.adapters.keys()) == ["shelly-test1"]
    msg = b"msg01"
    await t1.recv([1, "AA:BB:CC:DD:EE:FF", -50, binascii.b2a_base64(msg).decode("ascii"), ""])
    moc_recv.assert_awaited_once_with("shelly-test1", "AA:BB:CC:DD:EE:FF", msg)
    moc_recv.reset_mock()
    await t1.recv([2, [["AA:BB:CC:DD:EE:FF", -50, binascii.b2a_base64(msg).decode("ascii"), ""]]])
    moc_recv.assert_awaited_once_with("shelly-test1", "AA:BB:CC:DD:EE:FF", msg)
    moc_recv.reset_mock()
    t2 = MockShellyDevice(hass, "shelly-test2", "02")
    await t2.setup()  # Adding device after init
    assert list(man.adapters.keys()) == ["shelly-test1", "shelly-test2"]
    await man.reset_adapter("shelly-test2", "test")
    assert list(man.adapters.keys()) == ["shelly-test1", "shelly-test2"]
    await man.async_final()


async def test_shelly_adapter(hass: HomeAssistant, coord: BleAdvCoordinator) -> None:  # noqa: ARG001
    """Test Shelly Adapter."""
    moc_recv = mock.AsyncMock()
    moc_adapt = mock.AsyncMock()
    man = BleAdvShellyBtManager(hass, moc_recv, moc_adapt)
    man.WAIT_REDISCOVER = 0
    t1 = MockShellyDevice(hass, "shelly-test1", "01")
    await t1.setup()
    await man.async_init()
    man_adapter = man.adapters["shelly-test1"]
    assert man_adapter.mac == "01:00:00:00:00:02"
    msg = b"msg01"
    await man_adapter.enqueue("q1", BleAdvQueueItem(20, 1, 150, 60, [msg], 2))
    await man_adapter.drain()
    t1.rpc_device.call_rpc.assert_awaited_once_with("BLE.AdvertiseOnce", {"adv_data": msg.hex()})
    t1.rpc_device.call_rpc.reset_mock()
    msg_with_ad = bytes([0x02, 0x01, 0x06]) + msg
    await man_adapter.enqueue("q1", BleAdvQueueItem(20, 1, 150, 60, [msg_with_ad], 2))
    await man_adapter.drain()
    t1.rpc_device.call_rpc.assert_awaited_once_with("BLE.AdvertiseOnce", {"adv_data": msg.hex()})
    t1.rpc_device.call_rpc.reset_mock()
    await man.async_final()
