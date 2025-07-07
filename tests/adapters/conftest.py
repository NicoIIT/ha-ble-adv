"""Fixtures for async_socket module."""
# ruff: noqa: D103

import asyncio
from collections.abc import AsyncGenerator
from unittest import mock

import pytest
from ble_adv.adapters import BleAdvAdapter, BleAdvBtManager, BluetoothHCIAdapter
from ble_adv.async_socket import AsyncSocketBase


class _AsyncSocketMock(AsyncSocketBase):
    fail_open_nb: int = 0

    def __init__(self) -> None:
        super().__init__()
        self._recv_queue: asyncio.Queue = asyncio.Queue()
        self.hci_adv_not_allowed: bool = False
        self.hci_ext_adv: bool = False
        self._calls = []

    async def _async_open_socket(self, _: str, *__) -> int:  # noqa: ANN002
        if _AsyncSocketMock.fail_open_nb > 0:
            _AsyncSocketMock.fail_open_nb -= 1
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
                if data == b"\x01\x08 \n\tforce_rto":
                    return
                ret_code = 0x0C if self.hci_adv_not_allowed and data[1] in [0x06, 0x08, 0x0A] else 0x00
                self._calls.append(("op_call", data[1], data[4:]))
                if data[1] == 0x03 and self.hci_ext_adv:
                    features = (1 << 12).to_bytes(8, "little")
                    self.simulate_recv(bytearray([0x04, 0x0E, 0x00, 0x00, data[1], 0x20, ret_code, *features]))
                else:
                    self.simulate_recv(bytearray([0x04, 0x0E, 0x00, 0x00, data[1], 0x20, ret_code, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))
                self._base_call_result(None)
                return
            self._calls.append(("mgmt", data[0], data))
            if data == b"\x03\x00\xff\xff\x00\x00":  # get controller index list
                self.simulate_recv(b"\x01\x00\xff\xff\x07\x00\x03\x00\x00\x01\x00\x00\x00")
                self._base_call_result(None)
                return
            if data == b"\x04\x00\x00\x00\x00\x00":  # get controller info
                self.simulate_recv(b"\x01\x00\x00\x00\x1b\x01\x04\x00\x00\xbfg7 EH\x08\x02\x00\xff\xfe\x01\x00\xc1\n\x00\x00\x0c\x01")
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
async def bt_manager() -> AsyncGenerator[BleAdvBtManager]:
    mocks: list[_AsyncSocketMock] = []

    def create_mock_socket() -> _AsyncSocketMock:
        amock = _AsyncSocketMock()
        mocks.append(amock)
        return amock

    with mock.patch("ble_adv.adapters.create_async_socket", side_effect=create_mock_socket):
        btmgt = BleAdvBtManager(mock.AsyncMock())
        BleAdvAdapter.MAX_ADV_WAIT = 0.2
        BluetoothHCIAdapter.CMD_RTO = 0.1
        BleAdvBtManager.MGMT_CMD_RTO = 0.1
        await btmgt.async_init()
        yield btmgt
        await btmgt.async_final()
        for amock in mocks:
            await amock.wait_for_closure()
