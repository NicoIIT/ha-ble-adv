"""Init for async_adapters tests."""

import asyncio

from ble_adv.async_socket import AsyncSocketBase


class _AsyncSocketMock(AsyncSocketBase):
    def __init__(self) -> None:
        super().__init__()
        self.next_read = []
        self.fail_open_nb = 0

    async def _async_open_socket(self, name: str, *args) -> int:  # noqa: ARG002, ANN002
        if self.fail_open_nb > 0:
            self.fail_open_nb -= 1
            raise OSError("Forced Error")
        self.next_read.clear()
        return 1

    async def _async_start_recv(self) -> None:
        await self._setup_recv_loop(self._async_recv)

    async def _async_recv(self) -> tuple[bytes | None, bool]:
        while len(self.next_read) == 0:
            await asyncio.sleep(0.1)
        data = self.next_read.pop(0)
        return data, len(data) > 0

    async def _async_call(self, method: str, *args) -> None:  # noqa: ANN002
        if method in ["bind", "setsockopt"]:
            self._base_call_result(None)
        elif method == "sendall":
            if args[0][:3] == b"\x01\x03\x20":
                # FEATURE Request
                self.next_read.append(bytearray([0x04, 0x0E, 0x00, 0x00, 0x03, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))
            elif args[0][:3] == b"\x01\x0c\x20":
                # SCAN ENABLE / DISABLE
                self.next_read.append(bytearray([0x04, 0x0E, 0x00, 0x00, 0x0C, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))
            elif args[0][:3] == b"\x01\x0b\x20":
                # START PARAMETERS
                self.next_read.append(bytearray([0x04, 0x0E, 0x00, 0x00, 0x0B, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))
            elif args[0][:3] == b"\x01\x06\x20":
                # ADVERTISE PARAMETERS
                self.next_read.append(bytearray([0x04, 0x0E, 0x00, 0x00, 0x06, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))
            elif args[0][:3] == b"\x01\x08\x20":
                # ADVERTISE DATA
                self.next_read.append(bytearray([0x04, 0x0E, 0x00, 0x00, 0x08, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))
            elif args[0][:3] == b"\x01\x0a\x20":
                # ADVERTISE ENABLE / DISABLE
                self.next_read.append(bytearray([0x04, 0x0E, 0x00, 0x00, 0x0A, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))
            elif args[0][:3] == b"\x01\x41\x20":
                # ADVERTISE EXT PARAMETERS
                self.next_read.append(bytearray([0x04, 0x0E, 0x00, 0x00, 0x41, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))
            elif args[0][:3] == b"\x01\x42\x20":
                # ADVERTISE EXT ENABLE / DISABLE
                self.next_read.append(bytearray([0x04, 0x0E, 0x00, 0x00, 0x42, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))
            self._base_call_result(None)

    def _close(self) -> None:
        self.next_read.append(b"")
