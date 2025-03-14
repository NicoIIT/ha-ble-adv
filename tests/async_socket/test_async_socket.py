"""Test async_socket module."""

# ruff: noqa: S101
import asyncio
import os
from unittest import mock

import pytest
from ble_adv.async_socket import TUNNEL_SOCKET_FILE_VAR, AsyncSocket, AsyncTunnelSocket, create_async_socket

from . import _ConMock, _SocketMock


async def test_socket_sock() -> None:
    """Base instance and init of socket."""
    sock = AsyncSocket()
    sock_mock = _SocketMock()
    with (
        mock.patch("socket.socket", spec=True) as mock_socket,
        mock.patch.object(asyncio.get_event_loop(), "sock_recv") as sock_recv_mock,
    ):
        mock_inst = mock_socket.return_value
        sock_recv_mock.side_effect = sock_mock.read
        mock_inst.close.side_effect = sock_mock.close
        mock_recv_callback = mock.AsyncMock()
        mock_close_callback = mock.AsyncMock()
        await sock.async_init("test", mock_recv_callback, mock_close_callback, "", "", "")
        mock_inst.bind.assert_not_called()
        await sock.async_bind((1,))
        mock_inst.bind.assert_called_once_with((1,))
        mock_inst.bind.side_effect = OSError("Cannot Connect")
        with pytest.raises(OSError):
            await sock.async_bind((1,))
        mock_inst.setsockopt.assert_not_called()
        await sock.async_setsockopt(1, 2, 3)
        mock_inst.setsockopt.assert_called_once_with(1, 2, 3)
        await sock.async_start_recv()
        sock_mock.next_read.append("recv data")
        await asyncio.sleep(0.2)
        mock_recv_callback.assert_called_with("recv data")
        sock.close()
        await asyncio.sleep(0.2)
        mock_close_callback.assert_not_called()


async def test_tunnel_socket() -> None:
    """Test standard AsyncTunnelSocket."""
    con_mock = _ConMock()

    with mock.patch("asyncio.open_unix_connection", side_effect=con_mock.open_unix_connection):
        sock = AsyncTunnelSocket()
        mock_recv_callback = mock.AsyncMock()
        mock_close_callback = mock.AsyncMock()
        await sock._async_recv()  # noqa: SLF001
        await sock._async_call("nm")  # noqa: SLF001
        await sock.async_init("test", mock_recv_callback, mock_close_callback, "", "", "")
        con_mock.add_read(100, "invalid action")
        con_mock.patched_method["bind"] = (1, OSError("Connection Error"))
        with pytest.raises(OSError):
            await sock.async_bind((1,))
        con_mock.patched_method.clear()
        await sock.async_bind((1,))
        await sock.async_setsockopt(1, 2, 3)
        await sock.async_start_recv()
        con_mock.add_read(10, "recv data")
        await asyncio.sleep(0.2)
        mock_recv_callback.assert_called_with("recv data")
        sock.close()
        await asyncio.sleep(0.2)
        mock_close_callback.assert_not_called()


def test_create_async_socket() -> None:
    """Test AsyncSocket factory."""
    with mock.patch.dict(os.environ, {}, clear=True):
        assert isinstance(create_async_socket(), AsyncSocket)
    with mock.patch.dict(os.environ, {TUNNEL_SOCKET_FILE_VAR: "whatever"}):
        assert isinstance(create_async_socket(), AsyncTunnelSocket)
