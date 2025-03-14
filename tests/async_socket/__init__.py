"""Init for async_socket tests."""

# ruff: noqa: S101

import asyncio
import pickle
from unittest import mock


class _SocketMock:
    def __init__(self) -> None:
        self.next_read = []

    async def read(self, sock: mock.Mock, leng: int) -> bytes:  # noqa: ARG002
        while len(self.next_read) == 0:
            await asyncio.sleep(0.1)
        return self.next_read.pop(0)

    def close(self) -> None:
        self.next_read.append(b"")


class _ConMock:
    """Mock a socket pair created by 'open_unix_connection'.

    Act as the tunnel_socket server
    """

    def __init__(self) -> None:
        self.reader = mock.AsyncMock(spec=asyncio.StreamReader)
        self.reader.read.side_effect = self._read
        self.writer = mock.AsyncMock(spec=asyncio.StreamWriter)
        self.writer.write.side_effect = self._write
        self.writer.close.side_effect = self._close
        self.next_read: bytes = bytearray()
        self._close_req = False
        self.patched_method = {}

    def open_unix_connection(self, path: str) -> tuple[mock.AsyncMock, mock.AsyncMock]:  # noqa: ARG002
        return self.reader, self.writer

    def _close(self) -> None:
        self._close_req = True

    def _write(self, data: bytes) -> None:
        if len(data) == 2:
            return
        (version, args) = pickle.loads(data)  # noqa: S301
        assert version == 10, "Invalid version"
        method = args[0]
        if method in self.patched_method:
            action, res = self.patched_method[method]
            self.add_read(action, res)
        elif method == "##CREATE":
            self.add_read(0, 1)
        elif method == "##RECV":
            self.add_read(0, None)
        else:
            self.add_read(0, None)

    async def _read(self, leng: int) -> bytes:
        while len(self.next_read) == 0 and not self._close_req:
            await asyncio.sleep(0.1)

        if self._close_req:
            return b""

        if len(self.next_read) > leng:
            data = self.next_read[:leng]
            self.next_read = self.next_read[leng:]
        else:
            data = self.next_read
            self.next_read = bytearray()
        return data

    def add_read(self, action_code: int, client_data: int | str | None) -> None:
        data = pickle.dumps((action_code, client_data))
        self.next_read += len(data).to_bytes(2)
        self.next_read += data
