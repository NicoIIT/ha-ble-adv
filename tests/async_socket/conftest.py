"""Init for async_socket tests."""

# ruff: noqa: S101

import asyncio
import pickle
from collections.abc import Generator
from typing import Self
from unittest import mock

import pytest


class _SocketMock(mock.MagicMock):
    def init(self) -> None:
        self._recv_queue: asyncio.Queue = asyncio.Queue()

    async def sock_recv(self, _: Self, __: int) -> bytes:
        data = await self._recv_queue.get()
        self._recv_queue.task_done()
        return data

    def simulate_recv(self, data: bytes) -> None:
        self._recv_queue.put_nowait(data)

    def close(self) -> None:
        self._recv_queue.put_nowait(b"")


@pytest.fixture
def socket_mock_inst() -> Generator[_SocketMock]:
    """Mock a socket.socket."""
    with mock.patch("socket.socket", new_callable=_SocketMock) as mock_socket:
        mock_inst = mock_socket.return_value
        mock_inst.init()
        with mock.patch.object(asyncio.get_event_loop(), "sock_recv", side_effect=mock_inst.sock_recv):
            yield mock_inst


@pytest.fixture
def btsocket_mock_inst() -> Generator[_SocketMock]:
    """Mock a MGMT btsocket."""

    def btclose(sock: _SocketMock) -> None:
        sock.close()

    with (
        mock.patch("btsocket.btmgmt_socket.open", new_callable=_SocketMock) as mock_socket,
        mock.patch("btsocket.btmgmt_socket.close", side_effect=btclose),
    ):
        mock_inst = mock_socket.return_value
        mock_inst.init()
        with mock.patch.object(asyncio.get_event_loop(), "sock_recv", side_effect=mock_inst.sock_recv):
            yield mock_inst


class _ConMock:
    """Mock a socket pair created by 'open_unix_connection'.

    Act as the tunnel_socket server
    """

    def __init__(self) -> None:
        self.reader = mock.AsyncMock(spec=asyncio.StreamReader)
        self.reader.read.side_effect = self._read
        self.writer = mock.AsyncMock(spec=asyncio.StreamWriter)
        self.writer.write.side_effect = self._write
        self.writer.close.side_effect = self.close
        self._recv_queue: asyncio.Queue = asyncio.Queue()
        self.patched_method = {}

    def open_unix_connection(self, path: str) -> tuple[mock.AsyncMock, mock.AsyncMock]:  # noqa: ARG002
        return self.reader, self.writer

    def close(self) -> None:
        self._recv_queue.put_nowait(b"")

    def _write(self, data: bytes) -> None:
        if len(data) == 2:
            return
        (version, args) = pickle.loads(data)  # noqa: S301
        assert version == 10, "Invalid version"
        method = args[0]
        if method in self.patched_method:
            action, res = self.patched_method[method]
            self.simulate_recv(action, res)
        elif method == "##CREATE":
            self.simulate_recv(0, 1)
        elif method == "##RECV":
            self.simulate_recv(0, None)
        else:
            self.simulate_recv(0, None)

    async def _read(self, _: int) -> bytes:
        data = await self._recv_queue.get()
        self._recv_queue.task_done()
        return data

    def simulate_recv(self, action_code: int, client_data: int | str | None) -> None:
        data = pickle.dumps((action_code, client_data))
        self._recv_queue.put_nowait(len(data).to_bytes(2))
        self._recv_queue.put_nowait(data)


@pytest.fixture
def con_mock() -> Generator[_ConMock]:
    """Fixture unix connection."""
    con_mock = _ConMock()
    with mock.patch("asyncio.open_unix_connection", side_effect=con_mock.open_unix_connection):
        yield con_mock
