"""Test adapters module."""

# ruff: noqa: ANN001, SLF001, S101, D103
import asyncio
from unittest import mock

import pytest
from ble_adv.adapters import AdapterError, BleAdvQueueItem, BluetoothHCIAdapter, get_adapter

from .conftest import _AsyncSocketMock


async def test_adapter_factory() -> None:
    """Test Adapter factory."""
    with mock.patch("ble_adv.async_socket.AsyncTunnelSocket", spec=True):
        get_adapter(1)


START_SCAN = ("op_call", 0x0C, b"\x01\x00")
SCAN_PARAM = ("op_call", 0x0B, b"\x00\x10\x00\x10\x00\x00\x00")
STOP_SCAN = ("op_call", 0x0C, b"\x00\x00")


def adv_msg(interval: int, data: bytes) -> list[tuple[str, int, bytes]]:
    inter = interval.to_bytes(2, "little")
    return [
        ("op_call", 0x0A, b"\x00"),  # DISABLE ADV
        ("op_call", 0x06, inter + inter + b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x07\x00"),  # SET ADV PARAM
        ("op_call", 0x08, len(data).to_bytes(1) + data),  # SET ADV DATA
        ("op_call", 0x0A, b"\x01"),  # ENABLE ADV
        ("op_call", 0x0A, b"\x00"),  # DISABLE ADV
        ("op_call", 0x08, b"\x00"),  # RESET ADV DATA
    ]


OPEN_CALLS = [
    ("bind", ((1,),)),
    ("setsockopt", (0, 2, b"\x10\x00\x00\x00\x00@\x00\x00\x00\x00\x00@\x00\x00\x00\x00")),
    ("op_call", 0x03, b""),  # GET FEATURES
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


START_EXT_SCAN = ("op_call", 0x42, b"\x01\x00\x00\x00\x00\x00")
SCAN_EXT_PARAM = ("op_call", 0x41, b"\x00\x00\x01\x00\x10\x00\x10\x00")
STOP_EXT_SCAN = ("op_call", 0x42, b"\x00\x00\x00\x00\x00\x00")


async def test_adapter_ext(hci_adapter: BluetoothHCIAdapter, mock_socket: _AsyncSocketMock) -> None:
    assert mock_socket.get_calls() == OPEN_CALLS
    hci_adapter._ext_adv = True
    assert hci_adapter.available, "HCI Adapter available"
    mock_recv_callback = mock.AsyncMock()
    await hci_adapter.start_scan(mock_recv_callback)
    assert mock_socket.get_calls() == [STOP_EXT_SCAN, SCAN_EXT_PARAM, START_EXT_SCAN]
    mock_socket.simulate_recv(bytearray([0x04, 0x3E, 0x00, 0x0D] + [0x10] * 50))
    await asyncio.sleep(0.1)
    mock_recv_callback.assert_called_once_with("hci1", bytearray([0x10] * 0x10))
    await hci_adapter.stop_scan()
    assert mock_socket.get_calls() == [STOP_EXT_SCAN]
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
