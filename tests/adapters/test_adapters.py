"""Test adapters module."""

# ruff: noqa: SLF001, S101, D103
import asyncio
from unittest import mock

import pytest
from ble_adv.adapters import AdapterError, BleAdvBtManager, BleAdvQueueItem, BluetoothHCIAdapter

from .conftest import _AsyncSocketMock


def adv_msg(interval: int, data: bytes) -> list[tuple[str, int, bytes]]:
    inter = int(interval * 1.6).to_bytes(2, "little")
    return [
        ("op_call", 0x0A, b"\x00"),  # DISABLE ADV
        ("op_call", 0x06, inter + inter + b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x07\x00"),  # SET ADV PARAM
        ("op_call", 0x08, len(data).to_bytes(1) + data),  # SET ADV DATA
        ("op_call", 0x0A, b"\x01"),  # ENABLE ADV
        ("op_call", 0x0A, b"\x00"),  # DISABLE ADV
        ("op_call", 0x08, b"\x04\x03\xff\x00\x00"),  # RESET ADV DATA
    ]


def adv_ext_msg(interval: int, data: bytes) -> list[tuple[str, int, bytes]]:
    inter = int(interval * 1.6).to_bytes(2, "little")
    return [
        ("op_call", 0x39, b"\x00\x01\x01\x00\x00\x00"),  # DISABLE ADV EXT
        ("op_call", 0x36, b"\x01\x10\x00" + inter + b"\x00" + inter + b"\x00\x07\x00\x00\x00\x00\x00\x00\x00\x00\x00\x7f\x01\x00\x01\x00\x00"),
        ("op_call", 0x37, b"\x01\x03\x01" + len(data).to_bytes(1) + data),  # SET ADV DATA EXT
        ("op_call", 0x39, b"\x01\x01\x01\x00\x00\x00"),  # ENABLE ADV EXT
        ("op_call", 0x39, b"\x00\x01\x01\x00\x00\x00"),  # DISABLE ADV EXT
        ("op_call", 0x37, b"\x01\x03\x01\x04\x03\xff\x00\x00"),  # RESET ADV DATA  EXT
    ]


def adv_mgmt_msg(data: bytes) -> list[mock._Call]:
    return [
        mock.call(0, 0x3E, b"\x01\x00\x00\x00\x00\x00\x00\x00\x00" + len(data).to_bytes(2, "little") + data),
        mock.call(0, 0x3F, b"\x01"),
    ]


INIT_CALLS = [
    ("bind", ((0,),)),
    ("setsockopt", (0, 2, b"\x10\x00\x00\x00\x00@\x00\x00\x00\x00\x00@\x00\x00\x00\x00")),
    ("op_call", 0x03, b""),  # LE Features
    ("op_call", 0x0A, b"\x01"),  # Test ADV Enabled
    ("op_call", 0x0A, b"\x00"),  # Test ADV Disabled
    ("op_call", 0x0C, b"\x00\x00"),  # Disable Scan
    ("op_call", 0x0B, b"\x00\x10\x00\x10\x00\x00\x00"),  # Scan Parameters
    ("op_call", 0x0C, b"\x01\x00"),  # Enable Scan
]

HCI_NAME = "hci/48:45:20:37:67:BF"

DEVICE_MAC_STR = "AA:BB:CC:DD:EE:FF"
DEVICE_MAC_INT = list(reversed(bytes.fromhex(DEVICE_MAC_STR.replace(":", ""))))


async def test_split_queue() -> None:
    qi = BleAdvQueueItem(0, 10, 0, 10, b"qi")
    qi.split_repeat(60)
    assert qi.repeat == 2
    assert qi.adapter_repeat == 6
    qi = BleAdvQueueItem(0, 10, 0, 10, b"qi")
    qi.split_repeat(150)
    assert qi.repeat == 1
    assert qi.adapter_repeat == 10
    qi = BleAdvQueueItem(0, 10, 0, 10, b"qi")
    qi.split_repeat(5)
    assert qi.repeat == 10
    assert qi.adapter_repeat == 1


async def test_adapter(mock_socket: _AsyncSocketMock) -> None:
    hci_adapter = BluetoothHCIAdapter("hci0", 0, mock.AsyncMock(), mock.AsyncMock(), mock.AsyncMock())
    hci_adapter._async_socket = mock_socket
    BluetoothHCIAdapter.CMD_RTO = 0.1
    await hci_adapter.async_init()
    assert mock_socket.get_calls() == INIT_CALLS
    assert hci_adapter.available, "HCI Adapter available"
    await hci_adapter.open()  # already opened, ignored
    assert mock_socket.get_calls() == []
    mock_socket.simulate_recv(bytearray([0x00]))  # invalid message, ignored
    await asyncio.sleep(0.1)
    hci_adapter._on_adv_recv.assert_not_called()
    mock_socket.simulate_recv(bytearray([0x04, 0x3E, 0x00, 0x02, 0x01, 0x03, 0x01] + DEVICE_MAC_INT + [0x10] * 50))
    await asyncio.sleep(0.1)
    hci_adapter._on_adv_recv.assert_called_once_with("hci0", DEVICE_MAC_STR, bytearray([0x10] * 0x10))
    hci_adapter._on_adv_recv.reset_mock()
    mock_socket.simulate_recv(bytearray([0x04, 0x3E, 0x00, 0x0D, 0x01, 0x03, 0x00, 0x01] + DEVICE_MAC_INT + [0x10] * 50))
    await asyncio.sleep(0.1)
    hci_adapter._on_adv_recv.assert_called_once_with("hci0", DEVICE_MAC_STR, bytearray([0x10] * 0x10))
    await hci_adapter.enqueue("q1", BleAdvQueueItem(20, 1, 150, 60, b"msg01"))
    await hci_adapter.enqueue("q1", BleAdvQueueItem(30, 2, 100, 60, b"msg02"))
    await hci_adapter.drain()
    assert mock_socket.get_calls() == [*adv_msg(60, b"msg01"), *adv_msg(60, b"msg02"), *adv_msg(60, b"msg02")]
    await hci_adapter.async_final()
    with pytest.raises(AdapterError):
        await hci_adapter._advertise(20, 3, b"")


INIT_CALLS_EXT_ADV = [
    ("bind", ((0,),)),
    ("setsockopt", (0, 2, b"\x10\x00\x00\x00\x00@\x00\x00\x00\x00\x00@\x00\x00\x00\x00")),
    ("op_call", 0x03, b""),  # LE Features
    ("op_call", 0x0C, b"\x00\x00"),  # Disable Scan
    ("op_call", 0x0B, b"\x00\x10\x00\x10\x00\x00\x00"),  # Scan Parameters
    ("op_call", 0x0C, b"\x01\x00"),  # Enable Scan
]


async def test_adapter_ext_adv(mock_socket: _AsyncSocketMock) -> None:
    hci_adapter = BluetoothHCIAdapter("hci0", 0, mock.AsyncMock(), mock.AsyncMock(), mock.AsyncMock())
    hci_adapter._async_socket = mock_socket
    hci_adapter._async_socket.hci_ext_adv = True
    BluetoothHCIAdapter.CMD_RTO = 0.1
    await hci_adapter.async_init()
    assert mock_socket.get_calls() == INIT_CALLS_EXT_ADV
    assert hci_adapter.available, "HCI Adapter available"
    await hci_adapter.enqueue("q1", BleAdvQueueItem(20, 1, 150, 60, b"msg01"))
    await hci_adapter.enqueue("q1", BleAdvQueueItem(30, 2, 100, 60, b"msg02"))
    await hci_adapter.drain()
    assert mock_socket.get_calls() == [*adv_ext_msg(60, b"msg01"), *adv_ext_msg(60, b"msg02"), *adv_ext_msg(60, b"msg02")]
    await hci_adapter.async_final()


async def test_adapter_mgmt_adv(mock_socket: _AsyncSocketMock) -> None:
    mock_mgmt_cmd = mock.AsyncMock()
    hci_adapter_adv_mgmt = BluetoothHCIAdapter("hci0", 0, mock_mgmt_cmd, mock.AsyncMock(), mock.AsyncMock())
    hci_adapter_adv_mgmt._async_socket = mock_socket
    hci_adapter_adv_mgmt._async_socket.hci_adv_not_allowed = True
    BluetoothHCIAdapter.CMD_RTO = 0.1
    await hci_adapter_adv_mgmt.async_init()
    assert mock_socket.get_calls() == INIT_CALLS
    assert hci_adapter_adv_mgmt.available, "HCI Adapter available"
    await hci_adapter_adv_mgmt.open()  # already opened, ignored
    assert mock_socket.get_calls() == []
    await hci_adapter_adv_mgmt.enqueue("q1", BleAdvQueueItem(20, 1, 150, 60, b"msg01"))
    await hci_adapter_adv_mgmt.enqueue("q1", BleAdvQueueItem(30, 2, 100, 60, b"msg02"))
    await hci_adapter_adv_mgmt.drain()
    mock_mgmt_cmd.assert_has_calls([*adv_mgmt_msg(b"msg01"), *adv_mgmt_msg(b"msg02"), *adv_mgmt_msg(b"msg02")])
    await hci_adapter_adv_mgmt.async_final()


MGMT_OPEN_CALLS = [
    ("mgmt", 3, b"\x03\x00\xff\xff\x00\x00"),
    ("mgmt", 4, b"\x04\x00\x00\x00\x00\x00"),
]


async def test_btmanager(bt_manager: BleAdvBtManager) -> None:
    assert bt_manager._mgmt_sock.get_calls() == MGMT_OPEN_CALLS  # type: ignore[none]
    assert bt_manager.adapters[HCI_NAME]._async_socket.get_calls() == INIT_CALLS  # type: ignore[none]
    bt_manager._mgmt_sock.simulate_recv(b"\x12\x00\x00\x00")  # type: ignore[none]
    bt_manager._mgmt_sock.simulate_recv(b"\x14\x00\x00\x00")  # type: ignore[none]


async def test_btmanager_error(bt_manager: BleAdvBtManager) -> None:
    assert bt_manager._mgmt_sock.get_calls() == MGMT_OPEN_CALLS  # type: ignore[none]
    assert bt_manager.adapters[HCI_NAME]._async_socket.get_calls() == INIT_CALLS  # type: ignore[none]
    with pytest.raises(TimeoutError):
        await bt_manager.send_mgmt_cmd(0, 0x14, b"")
    await bt_manager.async_final()
    with pytest.raises(AdapterError):
        await bt_manager.send_mgmt_cmd(0, 0x12, b"")


async def test_btmanager_mgmt_close(bt_manager: BleAdvBtManager) -> None:
    assert bt_manager._mgmt_sock.get_calls() == MGMT_OPEN_CALLS  # type: ignore[none]
    assert bt_manager.adapters[HCI_NAME]._async_socket.get_calls() == INIT_CALLS  # type: ignore[none]
    _AsyncSocketMock.fail_open_nb = 1  # type: ignore[none]
    bt_manager._mgmt_sock._close()  # simulate MGMT closure from remote # type: ignore[none]
    await asyncio.sleep(0.2)  # wait for first reconnection (forced failed)
    assert bt_manager._mgmt_sock is None
    await asyncio.sleep(1.0)  # wait for second reconnection
    assert bt_manager._mgmt_sock.get_calls() == MGMT_OPEN_CALLS  # type: ignore[none]


async def test_btmanager_hci_adapter_close(bt_manager: BleAdvBtManager) -> None:
    assert bt_manager._mgmt_sock.get_calls() == MGMT_OPEN_CALLS  # type: ignore[none]
    assert bt_manager.adapters[HCI_NAME]._async_socket.get_calls() == INIT_CALLS  # type: ignore[none]
    bt_manager.adapters[HCI_NAME]._async_socket._close()  # simulate HCI Adapter closure from remote # type: ignore[none]
    await asyncio.sleep(0.2)  # wait for reconnection
    assert bt_manager._mgmt_sock.get_calls() == MGMT_OPEN_CALLS  # type: ignore[none]


async def test_btmanager_hci_and_mgmt_close(bt_manager: BleAdvBtManager) -> None:
    assert bt_manager._mgmt_sock.get_calls() == MGMT_OPEN_CALLS  # type: ignore[none]
    assert bt_manager.adapters[HCI_NAME]._async_socket.get_calls() == INIT_CALLS  # type: ignore[none]
    bt_manager._mgmt_sock._close()  # simulate MGMT closure from remote # type: ignore[none]
    bt_manager.adapters[HCI_NAME]._async_socket._close()  # simulate HCI Adapter closure from remote # type: ignore[none]
    await asyncio.sleep(0.2)  # wait for reconnection
    assert bt_manager._mgmt_sock.get_calls() == MGMT_OPEN_CALLS  # type: ignore[none]
    assert bt_manager.adapters[HCI_NAME]._async_socket.get_calls() == INIT_CALLS  # type: ignore[none]


async def test_btmanager_mgmt_adapter_change(bt_manager: BleAdvBtManager) -> None:
    assert bt_manager._mgmt_sock.get_calls() == MGMT_OPEN_CALLS  # type: ignore[none]
    assert bt_manager.adapters[HCI_NAME]._async_socket.get_calls() == INIT_CALLS  # type: ignore[none]
    bt_manager._mgmt_sock.simulate_recv(b"\x06\x00\x00\x00")  # simulate change on adapters # type: ignore[none]
    await asyncio.sleep(0.2)  # wait for final / init
    assert bt_manager._mgmt_sock.get_calls() == MGMT_OPEN_CALLS  # type: ignore[none]
    assert bt_manager.adapters[HCI_NAME]._async_socket.get_calls() == INIT_CALLS  # type: ignore[none]


async def test_btmanager_hci_error(bt_manager: BleAdvBtManager) -> None:
    assert bt_manager._mgmt_sock.get_calls() == MGMT_OPEN_CALLS  # type: ignore[none]
    assert bt_manager.adapters[HCI_NAME]._async_socket.get_calls() == INIT_CALLS  # type: ignore[none]
    # simulate rto by adapter on advertising
    await bt_manager.adapters[HCI_NAME].enqueue("q1", BleAdvQueueItem(30, 2, 100, 20, b"force_rto"))
    await asyncio.sleep(0.3)  # wait for final / init
    assert bt_manager._mgmt_sock.get_calls() == MGMT_OPEN_CALLS  # type: ignore[none]
    assert bt_manager.adapters[HCI_NAME]._async_socket.get_calls() == INIT_CALLS  # type: ignore[none]


async def test_ignored_hci() -> None:
    bt_manager = BleAdvBtManager(mock.AsyncMock(), ["hci"])
    await bt_manager.async_init()
    assert bt_manager._disabled
