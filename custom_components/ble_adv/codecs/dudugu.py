"""Dudugu Codec."""

from __future__ import annotations

from binascii import crc_hqx
from typing import ClassVar

from .const import (
    ATTR_CMD,
    ATTR_CMD_TIMER,
    ATTR_DIR,
    ATTR_ON,
    ATTR_PRESET,
    ATTR_PRESET_BREEZE,
    ATTR_SPEED,
    ATTR_TIME,
)
from .models import (
    BleAdvCodec,
    BleAdvConfig,
    BleAdvEncCmd,
    DeviceCmd,
    Fan6SpeedCmd,
    FanCmd,
    Trans,
)
from .models import EncoderMatcher as EncCmd
from .utils import whiten


class DuduguCodec(BleAdvCodec):
    """Dudugu codec."""

    KEY: ClassVar[bytes] = bytes([0x99, 0x6B, 0x75, 0x96])
    WHITEN_SEED: int = 0x53

    _len = 24
    _seed_max = 0xFE

    def _crc(self, buffer: bytes | bytearray, seed: int) -> int:
        crc = crc_hqx(buffer, 0xFF00 | ((~seed) & 0xFF))
        key = int.from_bytes(self.KEY, "little")
        return (crc + (key >> 16) + (key & 0xFFFF)) & 0xFFFF

    def decrypt(self, buffer: bytearray) -> bytearray | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer."""
        data = bytearray(whiten(buffer, self.WHITEN_SEED))
        data[:-3] = bytes(value ^ data[-3] for value in data[:-3])
        if not self.is_eq(int.from_bytes(data[-2:], "little"), self._crc(data[:-2], data[-3]), "crc"):
            return None
        data[5:-3] = bytes(value ^ self.KEY[i & 3] for i, value in enumerate(data[5:-3]))
        return data[:-2]

    def encrypt(self, buffer: bytearray) -> bytearray:
        """Encrypt / whiten a readable buffer."""
        buffer[5:-1] = bytes(value ^ self.KEY[i & 3] for i, value in enumerate(buffer[5:-1]))
        crc = self._crc(buffer, buffer[-1]).to_bytes(2, "little")
        buffer[:-1] = bytes(value ^ buffer[-1] for value in buffer[:-1])
        return bytearray(whiten(buffer + crc, self.WHITEN_SEED))

    def convert_to_enc(self, decoded: bytearray) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert a readable buffer into an encoder command and a config."""
        conf = BleAdvConfig()
        conf.id = int.from_bytes(decoded[0:4], "little")
        conf.index = int.from_bytes(decoded[4:6], "little")
        conf.tx_count = decoded[7]
        conf.seed = decoded[20]

        enc_cmd = BleAdvEncCmd(decoded[8])
        enc_cmd.arg0 = decoded[11]
        enc_cmd.arg1 = decoded[12]
        enc_cmd.arg2 = decoded[13]

        return enc_cmd, conf

    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytearray:
        """Convert an encoder command and a config into a readable buffer."""
        uid = conf.id.to_bytes(4, "little")
        index = conf.index.to_bytes(2, "little")
        args = [enc_cmd.arg0, enc_cmd.arg1, enc_cmd.arg2]
        return bytearray([*uid, *index, 0x10, conf.tx_count, enc_cmd.cmd, 0x00, 0x00, *args, 0x00, 0x00, 0x00, 0x00, 0x00, 0x93, conf.seed])


TRANSLATORS = [
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER), EncCmd(0x41)).split_copy(ATTR_TIME, ["arg0", "arg1"], 1.0 / 60.0).no_direct(),
    Trans(FanCmd().act(ATTR_DIR, True), EncCmd(0x15).eq("arg0", 1)),  # Forward
    Trans(FanCmd().act(ATTR_DIR, False), EncCmd(0x15).eq("arg0", 0)),  # Reverse
    Trans(FanCmd().act(ATTR_PRESET, ATTR_PRESET_BREEZE), EncCmd(0x33).eq("arg0", 2)),
    Trans(FanCmd().act(ATTR_PRESET).eq(ATTR_PRESET, None), EncCmd(0x33).eq("arg0", 0)),
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED), EncCmd(0x31).eq("arg0", 0x20).min("arg1", 1)).copy(ATTR_SPEED, "arg1"),
    Trans(Fan6SpeedCmd().act(ATTR_ON, False), EncCmd(0x31).eq("arg0", 0x20).eq("arg1", 0)),
]

CODECS = [
    DuduguCodec().id("dudugu_v0").header([0xF8, 0xF2]).ble(0x02, 0x03).prefix([0x90]).add_translators(TRANSLATORS),
]
