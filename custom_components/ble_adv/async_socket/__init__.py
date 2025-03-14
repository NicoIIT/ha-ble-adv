"""Async Socket Package."""

import asyncio
import atexit
import os
import pickle
import socket
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Coroutine
from functools import partialmethod
from typing import Any

type SocketRecvCallback = Callable[[bytes], Coroutine]
type SocketCloseCallback = Callable[[], Coroutine]
type SocketWaitRecvCallback = Callable[[], Awaitable[tuple[bytes | None, bool]]]

TUNNEL_SOCKET_FILE_VAR = "TUNNEL_SOCKET_FILE"


class AsyncSocketBase(ABC):
    """Base Async Socket."""

    def __init__(self) -> None:
        self._on_recv: SocketRecvCallback | None = None
        self._on_close: SocketCloseCallback | None = None
        self._ready_recv_event = asyncio.Event()
        self._functional_recv_started: bool = False
        self._recv_task: asyncio.Task | None = None
        self._cmd_event = asyncio.Event()
        self._cmd_exc: BaseException | None = None
        self._cmd_res: bytes | None = None
        self._cmd_lock = asyncio.Lock()

    @abstractmethod
    async def _async_open_socket(self, name: str, *args) -> int:  # noqa: ANN002
        """Open the socket."""

    @abstractmethod
    async def _async_start_recv(self) -> None:
        """Init the socket."""

    async def async_init(self, name: str, read_callback: SocketRecvCallback, close_callback: SocketCloseCallback, *args) -> int:  # noqa: ANN002
        """Async Initialize an async socket: setup the callbacks and create the socket."""
        self._on_recv = read_callback
        self._on_close = close_callback
        return await self._async_open_socket(name, *args)

    async def async_start_recv(self) -> None:
        """Async start listening to the created socket."""
        await self._async_start_recv()
        self._functional_recv_started = True

    async def _setup_recv_loop(self, wait_recv_callback: SocketWaitRecvCallback) -> None:
        """Help function: starts a listening loop."""
        self._ready_recv_event.clear()
        self._recv_task = asyncio.create_task(self._async_base_receive(wait_recv_callback))
        await asyncio.wait_for(self._ready_recv_event.wait(), 1)

    async def _async_base_receive(self, wait_recv_callback: SocketWaitRecvCallback) -> None:
        self._ready_recv_event.set()
        is_listening: bool = True
        while is_listening:
            data, is_listening = await wait_recv_callback()
            if is_listening and self._on_recv and data is not None:
                await self._on_recv(data)
        if self._on_close and self._functional_recv_started:
            self._functional_recv_started = False
            self._on_close_task = asyncio.create_task(self._on_close())

    @abstractmethod
    async def _async_call(self, method: str, *args) -> Any:  # noqa: ANN002, ANN401
        """Call the socket method. MUST call _base_call_result() when finished or _base_call_exception()."""

    def _base_call_result(self, result: Any) -> None:  # noqa: ANN401
        self._cmd_exc = None
        self._cmd_res = result
        self._cmd_event.set()

    def _base_call_exception(self, exception: BaseException) -> None:
        self._cmd_res = None
        self._cmd_exc = exception
        self._cmd_event.set()

    async def _async_call_base(self, method: str, *args) -> Any:  # noqa: ANN002, ANN401
        async with self._cmd_lock:
            self._cmd_event.clear()
            self._cmd_exc = None
            self._cmd_res = None
            await self._async_call(method, *args)
            await asyncio.wait_for(self._cmd_event.wait(), 1)
            if self._cmd_exc is not None:
                raise self._cmd_exc
            return self._cmd_res

    def close(self) -> None:
        """Closure."""
        self._functional_recv_started = False
        self._close()

    @abstractmethod
    def _close(self) -> None:
        """Closure."""

    async_bind = partialmethod(_async_call_base, "bind")
    async_setsockopt = partialmethod(_async_call_base, "setsockopt")
    async_sendall = partialmethod(_async_call_base, "sendall")


class AsyncSocket(AsyncSocketBase):
    """Async Socket standard based on socket.socket."""

    def __init__(self) -> None:
        super().__init__()
        self._socket: socket.socket | None = None

    async def _async_open_socket(self, name: str, *args) -> int:  # noqa: ARG002, ANN002
        self._socket = socket.socket(*args)
        atexit.register(self.close)
        return self._socket.fileno()

    async def _async_start_recv(self) -> None:
        await self._setup_recv_loop(self._async_recv)

    async def _async_recv(self) -> tuple[bytes | None, bool]:
        """Receive Data from socket."""
        if self._socket is None:
            return None, False
        data = await asyncio.get_event_loop().sock_recv(self._socket, 4096)
        return data, len(data) > 0

    def _call_done(self, future: asyncio.Future) -> None:
        if (exc := future.exception()) is not None:
            self._base_call_exception(exc)
        else:
            self._base_call_result(future.result())

    async def _async_call(self, method: str, *args) -> None:  # noqa: ANN002
        future = asyncio.get_event_loop().run_in_executor(None, getattr(self._socket, method), *args)
        future.add_done_callback(self._call_done)

    def _close(self) -> None:
        """Close."""
        if self._socket:
            self._socket.close()
            self._socket = None


class AsyncTunnelSocket(AsyncSocketBase):
    """Async Socket based on tunnel Unix Socket."""

    SOCKET_TUNNEL_FILE = os.environ.get("TUNNEL_SOCKET_FILE", "/tunnel_socket/hci.sock")

    def __init__(self) -> None:
        super().__init__()
        self._unix_reader = None
        self._unix_writer = None

    async def _async_open_socket(self, name: str, *args) -> int:  # noqa: ANN002
        self._unix_reader, self._unix_writer = await asyncio.open_unix_connection(path=self.SOCKET_TUNNEL_FILE)
        await self._setup_recv_loop(self._async_recv)
        return await self._async_call_base("##CREATE", name, *args)

    async def _async_start_recv(self) -> None:
        await self._async_call_base("##RECV", 4096)

    async def _async_recv(self) -> tuple[bytes | None, bool]:
        """Receive Data from socket."""
        if self._unix_reader is None:
            return None, False
        data_len = int.from_bytes(await self._unix_reader.read(2))
        if not data_len:
            return None, False
        data = await self._unix_reader.read(data_len)
        action, recv_data = pickle.loads(data)  # noqa: S301
        if action == 0:
            self._base_call_result(recv_data)
            return None, True
        if action == 1:
            self._base_call_exception(recv_data)
            return None, True
        if action == 10 and self._on_recv:
            return recv_data, True
        return None, True

    async def _async_call(self, method: str, *args) -> None:  # noqa: ANN002
        if self._unix_writer is None:
            return
        data = pickle.dumps((10, [method, *args]))
        self._unix_writer.write(len(data).to_bytes(2))
        self._unix_writer.write(data)
        await self._unix_writer.drain()

    def _close(self) -> None:
        """Closure."""
        if self._unix_writer:
            self._unix_writer.close()
            self._unix_writer = None


def create_async_socket() -> AsyncSocketBase:
    """Return the relevant async socket if the tunneling is properly configured."""
    return AsyncTunnelSocket() if TUNNEL_SOCKET_FILE_VAR in os.environ else AsyncSocket()
