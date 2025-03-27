"""Test adapters module."""

# ruff: noqa: ANN001, SLF001, S101, D103
import asyncio
from unittest import mock

import pytest
from ble_adv.adapters import AdapterError, BleAdvQueueItem, BluetoothHCIAdapter

from .conftest import _AsyncSocketMock, _BtManagerMock

START_SCAN = ("op_call", 0x0C, b"\x01\x00")
SCAN_PARAM = ("op_call", 0x0B, b"\x00\x10\x00\x10\x00\x00\x00")
STOP_SCAN = ("op_call", 0x0C, b"\x00\x00")


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


OPEN_CALLS = [
    ("bind", ((1,),)),
    ("setsockopt", (0, 2, b"\x10\x00\x00\x00\x00@\x00\x00\x00\x00\x00@\x00\x00\x00\x00")),
]


async def test_adapter(hci_adapter: BluetoothHCIAdapter, mock_socket: _AsyncSocketMock) -> None:
    assert mock_socket.get_calls() == OPEN_CALLS
    assert hci_adapter.available, "HCI Adapter available"
    mock_recv_callback = mock.AsyncMock()
    await hci_adapter.start_scan(mock_recv_callback)
    assert mock_socket.get_calls() == [STOP_SCAN, SCAN_PARAM, START_SCAN]
    mock_socket.simulate_recv(bytearray([0x00]))  # invalid message, ignored
    await asyncio.sleep(0.1)
    mock_recv_callback.assert_not_called()
    mock_socket.simulate_recv(bytearray([0x04, 0x3E, 0x00, 0x02] + [0x10] * 50))
    await asyncio.sleep(0.1)
    mock_recv_callback.assert_called_once_with("hci1", bytearray([0x10] * 0x10))
    await hci_adapter.stop_scan()
    assert mock_socket.get_calls() == [STOP_SCAN]
    await hci_adapter.enqueue("q1", BleAdvQueueItem(20, 1, 150, 20, b"msg01"))
    await hci_adapter.enqueue("q1", BleAdvQueueItem(30, 2, 100, 20, b"msg02"))
    await hci_adapter.drain()
    assert mock_socket.get_calls() == [*adv_msg(20, b"msg01"), *adv_msg(20, b"msg02"), *adv_msg(20, b"msg02")]


async def test_adapter_recovery(hci_adapter: BluetoothHCIAdapter, mock_socket: _AsyncSocketMock) -> None:
    await hci_adapter.open()  # already opened, no consequences
    assert hci_adapter.available, "HCI Adapter available"
    assert mock_socket.get_calls() == OPEN_CALLS
    mock_socket.fail_open_nb = 1
    mock_socket._close()  # simulate closure from remote
    with pytest.raises(AdapterError):
        await hci_adapter.stop_scan()  # immediate call: should fail
    assert mock_socket.get_calls() == [STOP_SCAN]
    await hci_adapter.enqueue("q1", BleAdvQueueItem(20, 1, 100, 20, b"msg01"))
    await hci_adapter.drain()
    assert mock_socket.get_calls() == []
    while not hci_adapter.available:
        await asyncio.sleep(0.1)
    assert mock_socket.get_calls() == OPEN_CALLS
    await hci_adapter.stop_scan()
    assert mock_socket.get_calls() == [STOP_SCAN]


MGMT_OPEN_CALLS = [
    ("mgmt", 3, b"\x03\x00\xff\xff\x00\x00"),
    ("mgmt", 4, b"\x04\x00\x00\x00\x00\x00"),
]


async def test_btmanager(bt_manager: _BtManagerMock) -> None:
    assert bt_manager.get_sock_mock().get_calls() == MGMT_OPEN_CALLS
    bt_manager.get_sock_mock()._close()  # simulate closure from remote
    await asyncio.sleep(1.2)  # wait for reconnection
    assert bt_manager.get_sock_mock().get_calls() == MGMT_OPEN_CALLS
    bt_manager.get_sock_mock().simulate_recv(b"\x06\x00\x00\x00")  # simulate change on adapters
    await asyncio.sleep(0.2)  # wait for final / init
    assert bt_manager.get_sock_mock().get_calls() == MGMT_OPEN_CALLS
