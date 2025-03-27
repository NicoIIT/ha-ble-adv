"""Test async_socket module."""

# ruff: noqa: S101
import asyncio
import os
from unittest import mock

import pytest
from ble_adv.async_socket import TUNNEL_SOCKET_FILE_VAR, AsyncSocket, AsyncTunnelSocket, create_async_socket

from .conftest import _ConMock, _SocketMock


async def test_socket(socket_mock_inst: _SocketMock) -> None:
    """Test AsyncSocket."""
    sock = AsyncSocket()
    mock_recv_callback = mock.AsyncMock()
    mock_close_callback = mock.AsyncMock()
    await sock._async_recv()  # noqa: SLF001
    await sock.async_init("test", mock_recv_callback, mock_close_callback, False, "", "", "")
    socket_mock_inst.bind.assert_not_called()
    await sock.async_bind((1,))
    socket_mock_inst.bind.assert_called_once_with((1,))
    socket_mock_inst.bind.side_effect = OSError("Cannot Connect")
    with pytest.raises(OSError):
        await sock.async_bind((1,))
    socket_mock_inst.setsockopt.assert_not_called()
    await sock.async_setsockopt(1, 2, 3)
    socket_mock_inst.setsockopt.assert_called_once_with(1, 2, 3)
    await sock.async_start_recv()
    mock_recv_callback.assert_not_called()
    socket_mock_inst.simulate_recv(b"recv data")
    await asyncio.sleep(0.1)
    mock_recv_callback.assert_called_with(b"recv data")
    sock.close()
    await asyncio.sleep(0.1)
    mock_close_callback.assert_not_called()


async def test_socket_remote_close(socket_mock_inst: _SocketMock) -> None:
    """Test AsyncSocket."""
    sock = AsyncSocket()
    mock_recv_callback = mock.AsyncMock()
    mock_close_callback = mock.AsyncMock()

    async def rem_close_callback() -> None:
        await mock_close_callback()

    await sock.async_init("test", mock_recv_callback, rem_close_callback, False, "", "", "")
    socket_mock_inst.close()  # simulate socket remote close
    await asyncio.sleep(0.1)
    mock_close_callback.assert_not_called()  # close before start_recv: no remote_close
    socket_mock_inst.init()  # clean pending messages in simulated socket
    await sock.async_init("test", mock_recv_callback, rem_close_callback, False, "", "", "")
    await sock.async_start_recv()
    await asyncio.sleep(0.1)
    socket_mock_inst.close()  # simulate socket remote close
    await asyncio.sleep(0.1)
    mock_close_callback.assert_called()  # close after start_recv: remote_close called
    mock_close_callback.reset_mock()
    sock.close()
    await asyncio.sleep(0.1)
    mock_close_callback.assert_not_called()  # close by standard close: remote_close not called


async def test_btsocket(btsocket_mock_inst: _SocketMock) -> None:
    """Test AsyncSocket."""
    sock = AsyncSocket()
    mock_recv_callback = mock.AsyncMock()
    mock_close_callback = mock.AsyncMock()
    await sock._async_recv()  # noqa: SLF001
    await sock.async_init("test", mock_recv_callback, mock_close_callback, True)
    await sock.async_start_recv()
    mock_recv_callback.assert_not_called()
    btsocket_mock_inst.simulate_recv(b"recv data")
    await asyncio.sleep(0.1)
    mock_recv_callback.assert_called_with(b"recv data")
    sock.close()
    await asyncio.sleep(0.1)
    mock_close_callback.assert_not_called()


async def test_tunnel_socket(con_mock: _ConMock) -> None:
    """Test AsyncTunnelSocket."""
    sock = AsyncTunnelSocket()
    mock_recv_callback = mock.AsyncMock()
    mock_close_callback = mock.AsyncMock()
    await sock._async_recv()  # noqa: SLF001
    await sock._async_call("nm")  # noqa: SLF001
    await sock.async_init("test", mock_recv_callback, mock_close_callback, False, "", "", "")
    con_mock.simulate_recv(100, "invalid action")
    con_mock.patched_method["bind"] = (1, OSError("Connection Error"))
    with pytest.raises(OSError):
        await sock.async_bind((1,))
    con_mock.patched_method.clear()
    await sock.async_bind((1,))
    await sock.async_setsockopt(1, 2, 3)
    await sock.async_start_recv()
    mock_recv_callback.assert_not_called()
    con_mock.simulate_recv(10, "recv data")
    await asyncio.sleep(0.1)
    mock_recv_callback.assert_called_with("recv data")
    sock.close()
    await asyncio.sleep(0.1)
    mock_close_callback.assert_not_called()


async def test_tunnel_socket_remote_close(con_mock: _ConMock) -> None:
    """Test AsyncSocket."""
    sock = AsyncTunnelSocket()
    mock_recv_callback = mock.AsyncMock()
    mock_close_callback = mock.AsyncMock()

    async def rem_close_callback() -> None:
        await mock_close_callback()

    await sock.async_init("test", mock_recv_callback, rem_close_callback, False, "", "", "")
    con_mock.close()  # simulate socket remote close
    await asyncio.sleep(0.1)
    mock_close_callback.assert_not_called()  # close before start_recv: no remote_close
    await sock.async_init("test", mock_recv_callback, rem_close_callback, False, "", "", "")
    await sock.async_start_recv()
    await asyncio.sleep(0.1)
    con_mock.close()  # simulate socket remote close
    await asyncio.sleep(0.1)
    mock_close_callback.assert_called()  # close after start_recv: remote_close called
    mock_close_callback.reset_mock()
    sock.close()
    await asyncio.sleep(0.1)
    mock_close_callback.assert_not_called()  # close by standard close: remote_close not called


def test_create_async_socket() -> None:
    """Test AsyncSocket factory."""
    with mock.patch.dict(os.environ, {}, clear=True):
        assert isinstance(create_async_socket(), AsyncSocket)
    with mock.patch.dict(os.environ, {TUNNEL_SOCKET_FILE_VAR: "whatever"}):
        assert isinstance(create_async_socket(), AsyncTunnelSocket)
