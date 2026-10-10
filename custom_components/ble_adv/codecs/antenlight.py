"""Antenlight Codec."""

from functools import reduce

from .const import ATTR_ON
from .models import (
    BleAdvCodec,
    BleAdvConfig,
    BleAdvEncCmd,
    LightCmd,
    Trans,
)
from .models import EncoderMatcher as EncCmd


class AntenlightCodec(BleAdvCodec):
    """Antenlight codec.

    Clear buffer (no whitening / encryption) sent as Service Data with UUID 0x0000 (header).

    Decoded buffer (8 bytes):
        [0:2]   id (big endian)
        [2]     group index
        [3]     tx count
        [4]     cmd
        [5:8]   args

    followed on air by a XOR checksum such that the XOR of the full AD structure
    (length 0x0C, type 0x16, UUID, data and checksum) is 0xFF.
    """

    CHECKSUM_SEED: int = 0xE5  # ~(0x0C ^ 0x16): AD length and AD type are part of the XOR

    _len = 9
    _tx_max = 0x100

    def _checksum(self, buffer: bytes | bytearray) -> int:
        return reduce(lambda x, y: x ^ y, buffer, self.CHECKSUM_SEED)

    def decrypt(self, buffer: bytearray) -> bytearray | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer."""
        if not self.is_eq(self._checksum(buffer[:-1]), buffer[-1], "Checksum"):
            return None
        return buffer[:-1]

    def encrypt(self, buffer: bytearray) -> bytearray:
        """Encrypt / whiten a readable buffer."""
        return buffer + bytes([self._checksum(buffer)])

    def convert_to_enc(self, decoded: bytearray) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert a readable buffer into an encoder command and a config."""
        conf = BleAdvConfig()
        conf.id = int.from_bytes(decoded[0:2])
        conf.index = decoded[2]
        conf.tx_count = decoded[3]
        return BleAdvEncCmd(decoded[4], 0, decoded[5], decoded[6], decoded[7]), conf

    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytearray:
        """Convert an encoder command and a config into a readable buffer."""
        args = [enc_cmd.arg0, enc_cmd.arg1, enc_cmd.arg2]
        return bytearray([*conf.id.to_bytes(2), conf.index, conf.tx_count, enc_cmd.cmd, *args])


TRANS = [
    Trans(LightCmd().act(ATTR_ON, True), EncCmd(0x00).eq("arg0", 0x01).eq("arg1", 0x00).eq("arg2", 0x00)),
    Trans(LightCmd().act(ATTR_ON, False), EncCmd(0x00).eq("arg0", 0x00).eq("arg1", 0x00).eq("arg2", 0x00)),
]

CODECS = [
    AntenlightCodec().id("antenlight_v0").header([0x00, 0x00]).ble(0x1A, 0x16).add_translators(TRANS),
]  # fmt: skip
