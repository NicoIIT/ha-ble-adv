"""Test adapters module."""

import asyncio
from unittest import mock

import pytest
from ble_adv.adapters import AdapterError, BleAdvQueueItem, BluetoothHCIAdapter, get_adapter

from . import _AsyncSocketMock


async def test_adapter_factory() -> None:
    """Test Adapter factory."""
    with mock.patch("ble_adv.async_socket.AsyncTunnelSocket", spec=True):
        get_adapter(1)


async def test_adapter() -> None:
    """Test HCI Adapter."""
    mock_sock = _AsyncSocketMock()
    hci_adapter = BluetoothHCIAdapter(1, mock_sock)
    await hci_adapter.async_init()
    assert hci_adapter.available, "HCI Adapter available"  # noqa: S101
    mock_recv_callback = mock.AsyncMock()
    await hci_adapter.start_scan(mock_recv_callback)
    mock_sock.next_read.append(bytearray([0x04, 0x3E, 0x00, 0x02] + [0x10] * 50))
    await asyncio.sleep(0.2)
    mock_recv_callback.assert_called_once_with("hci1", bytearray([0x10] * 0x10))
    await hci_adapter.stop_scan()
    qi1: BleAdvQueueItem = BleAdvQueueItem(20, 1, 500, 20, b"msg01")
    await hci_adapter.enqueue("q1", qi1)
    qi2: BleAdvQueueItem = BleAdvQueueItem(30, 2, 100, 20, b"msg02")
    await hci_adapter.enqueue("q1", qi2)
    await asyncio.sleep(2)
    await hci_adapter.async_final()
    await asyncio.sleep(0.2)


async def test_adapter_ext() -> None:
    """Test HCI Adapter - ADV Extended."""
    mock_sock = _AsyncSocketMock()
    hci_adapter = BluetoothHCIAdapter(1, mock_sock)
    await hci_adapter.async_init()
    hci_adapter._ext_adv = True  # noqa: SLF001
    assert hci_adapter.available, "HCI Adapter available"  # noqa: S101
    mock_recv_callback = mock.AsyncMock()
    await hci_adapter.start_scan(mock_recv_callback)
    mock_sock.next_read.append(bytearray([0x04, 0x3E, 0x00, 0x0D] + [0x10] * 50))
    await asyncio.sleep(0.2)
    mock_recv_callback.assert_called_once_with("hci1", bytearray([0x10] * 0x10))
    await hci_adapter.stop_scan()
    qi1: BleAdvQueueItem = BleAdvQueueItem(20, 1, 500, 20, b"msg01")
    await hci_adapter.enqueue("q1", qi1)
    qi2: BleAdvQueueItem = BleAdvQueueItem(30, 2, 100, 20, b"msg02")
    await hci_adapter.enqueue("q1", qi2)
    await asyncio.sleep(1)
    await hci_adapter.async_final()
    await asyncio.sleep(0.2)


async def test_adapter_recovery() -> None:
    """Test HCI Adapter - Recovery."""
    mock_sock = _AsyncSocketMock()
    hci_adapter = BluetoothHCIAdapter(1, mock_sock)
    await hci_adapter.async_init()
    await hci_adapter.open()  # already opened, no consequences
    assert hci_adapter.available, "HCI Adapter available"  # noqa: S101
    mock_sock.fail_open_nb = 1
    mock_sock._close()  # noqa: SLF001, force closure from remote
    with pytest.raises(AdapterError):
        await hci_adapter.stop_scan()  # immediate call: should fail
    await asyncio.sleep(2)  # wait enough for auto recovery
    await hci_adapter.stop_scan()
    mock_sock.next_read.append(bytearray([0x00]))
    await hci_adapter.async_final()
    await asyncio.sleep(0.2)
