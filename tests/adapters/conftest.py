"""Fixtures for async_socket module."""
# ruff: noqa: ANN001, SLF001, S101, D103

import asyncio
from collections.abc import AsyncGenerator

import pytest
from ble_adv.adapters import BluetoothHCIAdapter
from ble_adv.async_socket import AsyncSocketBase


class _AsyncSocketMock(AsyncSocketBase):
    def __init__(self) -> None:
        super().__init__()
        self._recv_queue: asyncio.Queue = asyncio.Queue()
        self.fail_open_nb = 0
        self._calls = []

    async def _async_open_socket(self, name: str, *args) -> int:  # noqa: ARG002, ANN002
        if self.fail_open_nb > 0:
            self.fail_open_nb -= 1
            raise OSError("Forced Error")
        self._recv_queue = asyncio.Queue()
        return 1

    async def _async_start_recv(self) -> None:
        await self._setup_recv_loop(self._async_recv)

    async def _async_recv(self) -> tuple[bytes | None, bool]:
        data = await self._recv_queue.get()
        self._recv_queue.task_done()
        return data, len(data) > 0

    async def _async_call(self, method: str, *args) -> None:  # noqa: ANN002
        if method == "sendall":
            data = args[0]
            if data[0] == 0x01 and data[2] == 0x20:
                self._calls.append(("op_call", data[1], data[4:]))
                self.simulate_recv(bytearray([0x04, 0x0E, 0x00, 0x00, data[1], 0x20, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))
                self._base_call_result(None)
                return
        self._calls.append((method, args))
        self._base_call_result(None)

    def _close(self) -> None:
        self.simulate_recv(b"")

    def get_calls(self) -> list[tuple[str, int | str | None]]:
        calls = self._calls.copy()
        self._calls.clear()
        return calls

    async def wait_for_closure(self) -> None:
        while self._recv_task is not None and not self._recv_task.done():
            await asyncio.sleep(0.1)

    def simulate_recv(self, data: bytes) -> None:
        self._recv_queue.put_nowait(data)


@pytest.fixture
async def mock_socket() -> AsyncGenerator[_AsyncSocketMock]:
    sock = _AsyncSocketMock()
    yield sock
    await sock.wait_for_closure()


@pytest.fixture
async def hci_adapter(mock_socket: _AsyncSocketMock) -> AsyncGenerator[BluetoothHCIAdapter]:
    hci_adapter = BluetoothHCIAdapter(1, mock_socket)
    await hci_adapter.async_init()
    yield hci_adapter
    await hci_adapter.drain()
    await hci_adapter.async_final()
