"""BLE ADV Adapters."""

import asyncio
import contextlib
import logging
import socket
import struct
from abc import ABC, abstractmethod
from binascii import hexlify
from collections.abc import Awaitable, Callable

from btsocket.btmgmt_protocol import reader as btmgmt_reader

from ..async_socket import AsyncSocketBase, SocketErrorCallback, create_async_socket  # noqa: TID252

_LOGGER = logging.getLogger(__name__)


class AdapterError(Exception):
    """Adapter Exception."""


class BleAdvQueueItem:
    """MultiQueue Item."""

    def __init__(self, key: int, repeat: int, delay: int, interval: int, data: bytes) -> None:
        """Init MultiQueue Item."""
        self.key: int = key
        self.repeat: int = repeat
        self.delay_after: int = delay
        self.interval: int = interval
        self.data: bytes = data


type AdvRecvCallback = Callable[[str, bytes], Awaitable[None]]


class BleAdvAdapter(ABC):
    """Base BLE ADV Adapter including multi Advertising sequencing queues."""

    MAX_ADV_WAIT: float = 3.0

    def __init__(self, name: str) -> None:
        """Init with name."""
        self.name: str = name
        self._on_adv_recv: AdvRecvCallback | None = None
        self._qlen: int = 0
        self._queues_index: dict[str, int] = {}
        self._queues: list[list[BleAdvQueueItem]] = []
        self._locked_tasks: list[asyncio.Task | None] = []
        self._add_event: asyncio.Event = asyncio.Event()
        self._cur_ind: int = -1
        self._lock: asyncio.Lock = asyncio.Lock()
        self._processing: bool = False
        self._dequeue_task: asyncio.Task | None = None
        self._opened: bool = False
        self._advertise_on_going: bool = False

    def _log(self, message: str) -> None:
        _LOGGER.info("[%s] %s.", self.name, message)

    def _log_dbg(self, message: str) -> None:
        _LOGGER.debug("[%s] %s.", self.name, message)

    @property
    def available(self) -> bool:
        """Available."""
        return self._opened

    async def async_init(self) -> None:
        """Async Init."""
        await self.open()
        self._processing = True
        self._dequeue_task = asyncio.create_task(self._dequeue())

    async def drain(self) -> None:
        """Wait for all queued messages to be processed."""
        while any(len(queue) > 0 for queue in self._queues) or self._advertise_on_going or any(task is not None for task in self._locked_tasks):
            await asyncio.sleep(0.1)

    async def async_final(self) -> None:
        """Async Final: clean-up to be ready for another init."""
        async with self._lock:
            self._processing = False
            self._qlen = 0
            self._cur_ind = -1
            self._queues.clear()
            self._queues_index.clear()
            self._locked_tasks.clear()
            self._add_event.set()
        self.close()

    @abstractmethod
    async def open(self) -> None:
        """Try to open the adapter, may throw Exceptions."""

    @abstractmethod
    def close(self) -> None:
        """Close the adapter."""

    @abstractmethod
    async def _start_scan(self) -> None:
        """Start Scan internal."""

    @abstractmethod
    async def _stop_scan(self) -> None:
        """Stop Scan internal."""

    @abstractmethod
    async def _advertise(self, interval: int, data: bytes) -> None:
        """Advertise the msg."""

    @abstractmethod
    async def _handle_error(self, message: str) -> None:
        """Handle irrecoverable error."""

    async def start_scan(self, recv_callback: AdvRecvCallback) -> None:
        """Start Scan."""
        self._on_adv_recv = recv_callback
        await self._start_scan()

    async def stop_scan(self) -> None:
        """Stop Scan."""
        await self._stop_scan()
        self._on_adv_recv = None

    async def enqueue(self, queue_id: str, item: BleAdvQueueItem) -> None:
        """Enqueue an Adv in the queue_id."""
        async with self._lock:
            tq_ind = self._queues_index.get(queue_id, None)
            if tq_ind is None:
                self._queues_index[queue_id] = self._qlen
                self._queues.append([item])
                self._locked_tasks.append(None)
                self._qlen += 1
            else:
                self._queues[tq_ind] = [x for x in self._queues[tq_ind] if x.key != item.key]
                self._queues[tq_ind].append(item)
            self._add_event.set()

    async def _unlock_queue(self, qind: int, delay: int) -> None:
        await asyncio.sleep(delay / 1000.0)
        self._locked_tasks[qind] = None
        self._add_event.set()

    async def _lock_queue_for(self, qind: int, delay: int) -> None:
        if not delay:
            return
        self._locked_tasks[qind] = asyncio.create_task(self._unlock_queue(qind, delay))

    async def _dequeue(self) -> None:
        while self._processing:
            try:
                item = None
                lock_delay = 0
                self._advertise_on_going = False
                await self._add_event.wait()
                async with self._lock:
                    for _ in range(self._qlen):
                        self._cur_ind = (self._cur_ind + 1) % self._qlen
                        if self._locked_tasks[self._cur_ind] is not None:
                            continue
                        tq = self._queues[self._cur_ind]
                        if len(tq) > 0:
                            self._advertise_on_going = True
                            item = tq[0]
                            if item.repeat > 1:
                                tq[0].repeat -= 1
                            else:
                                tq.pop(0)
                                lock_delay = item.delay_after
                            break
                    self._add_event.clear()
                if item is not None:
                    self._log_dbg(f"Advertising {hexlify(item.data, '.').upper()}")
                    await asyncio.wait_for(self._advertise(item.interval, item.data), self.MAX_ADV_WAIT)
                    self._log_dbg(f"End Advertising {hexlify(item.data, '.').upper()}")
                    await self._lock_queue_for(self._cur_ind, lock_delay)
                    self._add_event.set()
            except Exception:
                _LOGGER.exception("BleAdvAdapter - Exception in dequeue")
                await self._handle_error("Exception in Adapter Dequeue")


SOCK_AF_BLUETOOTH = socket.AF_BLUETOOTH if hasattr(socket, "AF_BLUETOOTH") else 31  # type: ignore[none]
SOCK_BTPROTO_HCI = socket.BTPROTO_HCI if hasattr(socket, "BTPROTO_HCI") else 1  # type: ignore[none]
SOCK_HCI_FILTER = socket.HCI_FILTER if hasattr(socket, "HCI_FILTER") else 2  # type: ignore[none]
SOCK_SOL_HCI = socket.SOL_HCI if hasattr(socket, "SOL_HCI") else 0  # type: ignore[none]


class BluetoothHCIAdapter(BleAdvAdapter):
    """BLE ADV direct HCI Adapter."""

    CMD_RTO: float = 1.0

    HCI_SUCCESS = 0x00
    HCI_COMMAND_PKT = 0x01
    HCI_EVENT_PKT = 0x04

    EVT_CMD_COMPLETE = 0x0E
    EVT_LE_META_EVENT = 0x3E

    EVT_LE_ADVERTISING_REPORT = 0x02
    EVT_LE_EXTENDED_ADVERTISING_REPORT = 0x0D

    OGF_LE_CTL = 0x08
    OCF_LE_SET_ADVERTISING_PARAMETERS = 0x06
    OCF_LE_SET_ADVERTISING_DATA = 0x08
    OCF_LE_SET_ADVERTISE_ENABLE = 0x0A
    OCF_LE_SET_SCAN_PARAMETERS = 0x0B
    OCF_LE_SET_SCAN_ENABLE = 0x0C
    ADV_FILTER = struct.pack(
        "<LLLHxx",
        1 << HCI_EVENT_PKT,
        1 << EVT_CMD_COMPLETE,
        1 << (EVT_LE_META_EVENT - 0x20),
        0,
    )

    def __init__(
        self,
        name: str,
        device_id: int,
        async_socket: AsyncSocketBase,
        on_error: SocketErrorCallback,
    ) -> None:
        """Create Adapter."""
        super().__init__(name)
        self.device_id: int = device_id
        self._async_socket: AsyncSocketBase = async_socket
        self._on_error: SocketErrorCallback = on_error
        self._cmd_event: asyncio.Event = asyncio.Event()
        self._on_going_cmd: int | None = None
        self._adv_lock: asyncio.Lock = asyncio.Lock()
        self._cmd_lock: asyncio.Lock = asyncio.Lock()

    async def open(self) -> None:
        """Open the adapters. Can throw exception if invalid."""
        if self._opened:
            return
        fileno = await self._async_socket.async_init(
            self.name,
            self._recv,
            self._on_error,
            False,
            SOCK_AF_BLUETOOTH,
            socket.SOCK_RAW,
            SOCK_BTPROTO_HCI,
        )
        await self._async_socket.async_bind((self.device_id,))
        await self._async_socket.async_setsockopt(SOCK_SOL_HCI, SOCK_HCI_FILTER, self.ADV_FILTER)
        await self._async_socket.async_start_recv()
        self._opened = True
        self._log(f"Connected - fileno: {fileno}")

    def close(self) -> None:
        """Close Adapter."""
        self._opened = False
        self._async_socket.close()

    async def _handle_error(self, message: str) -> None:
        """Handle irrecoverable error."""
        await self._on_error(message)

    async def _recv(self, data: bytes) -> None:
        if data[0] != self.HCI_EVENT_PKT:
            return
        if (data[1] == self.EVT_LE_META_EVENT) and self._on_adv_recv is not None:
            if data[3] == self.EVT_LE_ADVERTISING_REPORT:
                await self._on_adv_recv(self.name, data[14 : 14 + data[13]])
            if data[3] == self.EVT_LE_EXTENDED_ADVERTISING_REPORT:
                await self._on_adv_recv(self.name, data[29 : 29 + data[28]])
        elif (data[1] == self.EVT_CMD_COMPLETE) and (int.from_bytes(data[4:6], "little") == self._on_going_cmd):
            self._ret_code = data[6]
            self._ret_data = data[7:]
            self._cmd_event.set()

    async def _send_hci_cmd(self, cmd_type: int, cmd_data: bytes = bytearray()) -> tuple[int, bytes | None]:
        if not self._opened:
            raise AdapterError("Adapter not available")
        data_len = len(cmd_data)
        op_code = cmd_type + (self.OGF_LE_CTL << 10)  # OCF on 10 bits, OGF on 6 bits
        cmd = struct.pack(f"<BHB{data_len}B", self.HCI_COMMAND_PKT, op_code, data_len, *cmd_data)
        async with self._cmd_lock:
            self._cmd_event.clear()
            self._on_going_cmd = op_code
            self._ret_code = 0
            self._ret_data = None
            await self._async_socket.async_sendall(cmd)
            await asyncio.wait_for(self._cmd_event.wait(), self.CMD_RTO)
            return self._ret_code, self._ret_data

    async def _set_scan_parameters(self, scan_type: int = 0x00, interval: int = 0x10, window: int = 0x10) -> None:
        cmd = bytearray([scan_type]) + interval.to_bytes(2, "little") + window.to_bytes(2, "little")
        await self._send_hci_cmd(self.OCF_LE_SET_SCAN_PARAMETERS, cmd + bytearray([0x00, 0x00]))

    async def _set_scan_enable(self, *, enabled: bool = True) -> None:
        await self._send_hci_cmd(self.OCF_LE_SET_SCAN_ENABLE, bytearray([0x01 if enabled else 0x00, 0x00]))

    async def _set_advertise_enable(self, *, enabled: bool = True) -> None:
        await self._send_hci_cmd(self.OCF_LE_SET_ADVERTISE_ENABLE, bytearray([0x01 if enabled else 0x00]))

    async def _set_advertising_parameter(self, min_interval: int = 0xA0, max_interval: int = 0xA0) -> None:
        params = bytearray()
        params += min_interval.to_bytes(2, "little")
        params += max_interval.to_bytes(2, "little")
        params += bytes([0, 0, 0, 0, 0, 0, 0, 0, 0, 0x07, 0])
        await self._send_hci_cmd(self.OCF_LE_SET_ADVERTISING_PARAMETERS, params)

    async def _set_advertising_data(self, data: bytes) -> None:
        # btmon will give error 'invalid packet size' if data not of len 31, but the command is successful.
        await self._send_hci_cmd(self.OCF_LE_SET_ADVERTISING_DATA, bytearray([len(data), *data]))

    async def _advertise(self, interval: int, data: bytes) -> None:
        """Advertise the 'data' for the given interval."""
        int_as_hex = int(interval * 1.6)
        async with self._adv_lock:
            await self._set_advertise_enable(enabled=False)
            await self._set_advertising_parameter(int_as_hex, int_as_hex)
            await self._set_advertising_data(data)
            await self._set_advertise_enable()
            await asyncio.sleep(0.0028 * interval)
            await self._set_advertise_enable(enabled=False)
            # set a fake adv, just in case it would be re enabled
            await self._set_advertising_data(bytes([0x03, 0xFF, 0x00, 0x00]))

    async def _start_scan(self) -> None:
        await self._set_scan_enable(enabled=False)
        await self._set_scan_parameters()
        await self._set_scan_enable()

    async def _stop_scan(self) -> None:
        await self._set_scan_enable(enabled=False)


def lb(buf: bytes) -> int:
    """Help convert from little indian byte."""
    return int.from_bytes(buf, "little")


class BleAdvBtManager:
    """Manage the bluetooth Adapters using MGMT api.

    Bluez mgmt-api: https://web.git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/mgmt-api.txt
    """

    MGMT_CMD_RTO: float = 3.0

    def __init__(self, adv_recv_callback: AdvRecvCallback) -> None:
        self._mgmt_sock: AsyncSocketBase = create_async_socket()
        self._hci_adapters: dict[str, BleAdvAdapter] = {}
        self._hci_adapter_ids: dict[str, int] = {}
        self._hci_adapter_names: dict[int, str] = {}
        self._mgmt_cmd_event = asyncio.Event()
        self._og_mgmt_cmd = None
        self._og_mgmt_dev_id = None
        self._mgmt_cmd_lock = asyncio.Lock()
        self._adv_lock = asyncio.Lock()
        self._mgmt_opened = False
        self._adv_recv: AdvRecvCallback = adv_recv_callback
        self._reconnecting: bool = False

    @property
    def adapters(self) -> dict[str, BleAdvAdapter]:
        """Get hci adapters dict."""
        return self._hci_adapters

    async def async_init(self) -> None:
        """Init the handler: init the MGMT Socket and the discovered adapters."""
        fileno = await self._mgmt_sock.async_init("mgmt", self._mgmt_recv, self._mgmt_close, True)
        await self._mgmt_sock.async_start_recv()
        _LOGGER.debug(f"MGMT Connected - fileno: {fileno}")
        self._mgmt_opened = True
        # Controller Index List
        _, index_resp = await self.send_mgmt_cmd(0xFFFF, 0x03, b"")
        nb = lb(index_resp[0:2])
        _LOGGER.debug(f"MGMT Nb Adapters: {nb}")
        for i in range(nb):
            dev_id = lb(index_resp[2 * (i + 1) : 2 * (i + 2)])
            _, info_resp = await self.send_mgmt_cmd(dev_id, 0x04, b"")
            btaddr = ":".join([f"{x:02X}" for x in reversed(info_resp[0:6])])
            _LOGGER.debug(f"MGMT Adapter hci{dev_id} btaddr: {btaddr}")
            name = f"hci/{btaddr}"
            self._hci_adapter_ids[name] = dev_id
            self._hci_adapter_names[dev_id] = name
            self._hci_adapters[name] = BluetoothHCIAdapter(name, dev_id, create_async_socket(), self._hci_adapter_error)
            await self._hci_adapters[name].async_init()
            await self._hci_adapters[name].start_scan(self._adv_recv)

    async def async_final(self) -> None:
        """Finalize: Stop Discovery and clean adapters."""
        self._mgmt_opened = False
        for adapter in self._hci_adapters.values():
            await adapter.async_final()
        self._mgmt_sock.close()
        self._hci_adapters.clear()
        self._hci_adapter_ids.clear()
        self._hci_adapter_names.clear()

    async def _mgmt_recv(self, data: bytes) -> None:
        # //_LOGGER.debug(f"mgmt recv: {data}")
        cmd_type = lb(data[0:2])
        dev_id = lb(data[2:4])
        if cmd_type == 0x0001 and dev_id == self._og_mgmt_dev_id and lb(data[6:8]) == self._og_cmd:
            # Command Complete on relevant controller and relevant pending command
            self._ret_code = data[8]
            self._ret_data = data[9:]
            self._mgmt_cmd_event.set()
        elif cmd_type in [0x12, 0x13]:
            # discovery events, ignore
            pass
        elif cmd_type in [0x03, 0x04, 0x05, 0x06]:
            # Adapter changes: trigger refresh
            _LOGGER.debug(f"Event triggering refresh: 0x{cmd_type:04X}")
            self._launch_refresh()
        else:
            with contextlib.suppress(Exception):
                _LOGGER.debug(f"Unhandled Event: {btmgmt_reader(data)}")

    async def _hci_adapter_error(self, message: str) -> None:
        _LOGGER.debug(f"HCI Adapter error: {message}, resetting")
        self._launch_refresh()

    async def _mgmt_close(self, message: str) -> None:
        _LOGGER.debug(f"MGMT Error: {message}, resetting ..")
        self._launch_refresh()

    def _launch_refresh(self) -> None:
        if self._reconnecting:
            return
        self._reconnecting = True
        self._reset_task = asyncio.create_task(self._acquire_connection())

    async def _acquire_connection(self) -> None:
        """Securely acquire connection."""
        await self.async_final()
        nb_attempt = 0
        while self._reconnecting:
            nb_attempt += 1
            try:
                await self.async_init()
                self._reconnecting = False
            except Exception as exc:
                _LOGGER.debug(f"Reconnect failed ({nb_attempt}): {exc}, retrying..")
                await self.async_final()
                await asyncio.sleep(1)

    async def send_mgmt_cmd(self, device_id: int, cmd_type: int, cmd_data: bytes = bytearray()) -> tuple[int, bytes]:
        """Send a MGMT command."""
        if not self._mgmt_opened or self._mgmt_sock is None:
            raise AdapterError("Adapter not available")
        data_len = len(cmd_data)
        cmd = struct.pack(f"<HHH{data_len}B", cmd_type, device_id, data_len, *cmd_data)
        # //_LOGGER.debug(f"mgmt cmd: {cmd}")
        async with self._mgmt_cmd_lock:
            self._mgmt_cmd_event.clear()
            self._og_cmd = cmd_type
            self._og_mgmt_dev_id = device_id
            self._ret_code = 0
            self._ret_data = b""
            await self._mgmt_sock.async_sendall(cmd)
            await asyncio.wait_for(self._mgmt_cmd_event.wait(), self.MGMT_CMD_RTO)
            return self._ret_code, self._ret_data
