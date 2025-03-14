"""BLE ADV Adapters."""

import asyncio
import logging
import socket
import struct
from abc import ABC, abstractmethod
from binascii import hexlify
from collections.abc import Awaitable, Callable

from ..async_socket import AsyncSocketBase, create_async_socket  # noqa: TID252

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

    def __init__(self, name: str) -> None:
        """Init with name."""
        self.name = name
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
        self._opened = False
        self._advertise_on_going = False

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
                    await self._advertise(item.interval, item.data)
                    self._log_dbg(f"End Advertising {hexlify(item.data, '.').upper()}")
                    await self._lock_queue_for(self._cur_ind, lock_delay)
                    self._add_event.set()
            except Exception as exc:
                _LOGGER.warning(f"BleAdvAdapter - Exception in dequeue: {exc}")


SOCK_AF_BLUETOOTH = socket.AF_BLUETOOTH if hasattr(socket, "AF_BLUETOOTH") else 31  # type: ignore[none]
SOCK_BTPROTO_HCI = socket.BTPROTO_HCI if hasattr(socket, "BTPROTO_HCI") else 1  # type: ignore[none]
SOCK_HCI_FILTER = socket.HCI_FILTER if hasattr(socket, "HCI_FILTER") else 2  # type: ignore[none]
SOCK_SOL_HCI = socket.SOL_HCI if hasattr(socket, "SOL_HCI") else 0  # type: ignore[none]


class BluetoothHCIAdapter(BleAdvAdapter):
    """BLE ADV direct HCI Adapter."""

    HCI_SUCCESS = 0x00
    HCI_COMMAND_PKT = 0x01
    HCI_EVENT_PKT = 0x04

    EVT_CMD_COMPLETE = 0x0E
    EVT_LE_META_EVENT = 0x3E

    EVT_LE_ADVERTISING_REPORT = 0x02
    EVT_LE_EXTENDED_ADVERTISING_REPORT = 0x0D

    OGF_LE_CTL = 0x08
    OCF_LE_READ_LOCAL_SUPPORTED_FEATURES = 0x03
    OCF_LE_SET_ADVERTISING_PARAMETERS = 0x06
    OCF_LE_SET_ADVERTISING_DATA = 0x08
    OCF_LE_SET_ADVERTISE_ENABLE = 0x0A
    OCF_LE_SET_SCAN_PARAMETERS = 0x0B
    OCF_LE_SET_SCAN_ENABLE = 0x0C
    OCF_LE_SET_EXTENDED_SCAN_PARAMETERS = 0x41
    OCF_LE_SET_EXTENDED_SCAN_ENABLE = 0x42

    ADV_FILTER = struct.pack(
        "<LLLHxx",
        1 << HCI_EVENT_PKT,
        1 << EVT_CMD_COMPLETE,
        1 << (EVT_LE_META_EVENT - 0x20),
        0,
    )

    def __init__(
        self,
        device_id: int,
        async_socket: AsyncSocketBase,
    ) -> None:
        """Create Adapter."""
        super().__init__(f"hci{device_id}")
        self.device_id = device_id
        self._async_socket = async_socket
        self._ext_adv = None
        self._cmd_event = asyncio.Event()
        self._on_going_cmd = None
        self._adv_lock = asyncio.Lock()
        self._cmd_lock = asyncio.Lock()

    async def open(self) -> None:
        """Open the adapters. Can throw exception if invalid."""
        if self._opened:
            return
        fileno = await self._async_socket.async_init(
            self.name,
            self._recv,
            self._remote_close,
            SOCK_AF_BLUETOOTH,
            socket.SOCK_RAW | socket.SOCK_NONBLOCK,
            SOCK_BTPROTO_HCI,
        )
        await self._async_socket.async_bind((self.device_id,))
        await self._async_socket.async_setsockopt(SOCK_SOL_HCI, SOCK_HCI_FILTER, self.ADV_FILTER)
        await self._async_socket.async_start_recv()
        self._opened = True
        ret_code, data = await self._send_hci_cmd(self.OCF_LE_READ_LOCAL_SUPPORTED_FEATURES)
        if ret_code == self.HCI_SUCCESS and data is not None:
            features = int.from_bytes(data)
            self._ext_adv = features & (1 << 12)
        self._log(f"Connected - fileno: {fileno}")

    def close(self) -> None:
        """Close Adapter."""
        self._opened = False
        self._async_socket.close()

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

    async def _remote_close(self) -> None:
        self._log("Connection closed by peer, reconnecting ..")
        self._opened = False
        nb_attempt = 0
        while True:
            await asyncio.sleep(1)
            nb_attempt += 1
            try:
                await self.open()
                break
            except Exception as exc:
                self._log_dbg(f"Reconnect failed ({nb_attempt}): {exc}, retrying..")
                self.close()

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
            try:
                await asyncio.wait_for(self._cmd_event.wait(), 1)
            except TimeoutError as err:
                ctx = f"Timeout sending command {op_code}"
                raise AdapterError(ctx) from err
            return self._ret_code, self._ret_data

    async def _set_scan_parameters(self, scan_type: int = 0x00, interval: int = 0x10, window: int = 0x10) -> None:
        cmd = bytearray([scan_type]) + interval.to_bytes(2, "little") + window.to_bytes(2, "little")
        addr = 0x00
        filter_ = 0x00
        phys = 0x01
        if self._ext_adv:
            await self._send_hci_cmd(
                self.OCF_LE_SET_EXTENDED_SCAN_PARAMETERS,
                bytearray([addr, filter_, phys]) + cmd,
            )
        else:
            await self._send_hci_cmd(self.OCF_LE_SET_SCAN_PARAMETERS, cmd + bytearray([addr, filter_]))

    async def _set_scan_enable(self, *, enabled: bool = True, filter_duplicates: bool = False) -> None:
        cmd = bytearray([0x01 if enabled else 0x00, 0x01 if filter_duplicates else 0x00])
        if self._ext_adv:
            await self._send_hci_cmd(self.OCF_LE_SET_EXTENDED_SCAN_ENABLE, cmd + bytearray([0, 0, 0, 0]))
        else:
            await self._send_hci_cmd(self.OCF_LE_SET_SCAN_ENABLE, cmd)

    async def _set_advertise_enable(self, *, enabled: bool = True) -> None:
        await self._send_hci_cmd(self.OCF_LE_SET_ADVERTISE_ENABLE, bytearray([0x01 if enabled else 0x00]))

    async def _set_advertising_parameter(self, min_interval: int = 0xA0, max_interval: int = 0xA0) -> None:
        params = bytearray()
        params += min_interval.to_bytes(2, "little")
        params += max_interval.to_bytes(2, "little")
        params += bytes([0, 0, 0, 0, 0, 0, 0, 0, 0, 0x07, 0])
        await self._send_hci_cmd(self.OCF_LE_SET_ADVERTISING_PARAMETERS, params)

    async def _set_advertising_data(self, data: bytes | None) -> None:
        await self._send_hci_cmd(
            self.OCF_LE_SET_ADVERTISING_DATA,
            bytearray([len(data), *data]) if data is not None else bytearray([0]),
        )

    async def _advertise(self, interval: int, data: bytes) -> None:
        """Advertise the 'data' for the given interval."""
        async with self._adv_lock:
            await self._set_advertise_enable(enabled=False)
            await self._set_advertising_parameter(int(interval), int(interval))
            await self._set_advertising_data(data)
            await self._set_advertise_enable()
            await asyncio.sleep(0.0028 * interval)
            await self._set_advertise_enable(enabled=False)
            await self._set_advertising_data(None)

    async def _start_scan(self) -> None:
        await self._set_scan_enable(enabled=False)
        await self._set_scan_parameters()
        await self._set_scan_enable()

    async def _stop_scan(self) -> None:
        await self._set_scan_enable(enabled=False)


def get_adapter(device_id: int) -> BleAdvAdapter:
    """Get the Adapter corresponding to the device_id and the potential tunneling config."""
    return BluetoothHCIAdapter(device_id, create_async_socket())
