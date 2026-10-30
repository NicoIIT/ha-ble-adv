"""No Name physical remotes."""

from .const import (
    ATTR_CMD,
    ATTR_CMD_BR_DOWN,
    ATTR_CMD_BR_UP,
    ATTR_CMD_CT_DOWN,
    ATTR_CMD_CT_UP,
    ATTR_CMD_TOGGLE,
    ATTR_COLD,
    ATTR_ON,
    ATTR_STEP,
    ATTR_WARM,
)
from .models import (
    BleAdvCodec,
    BleAdvConfig,
    BleAdvEncCmd,
    CTLightCmd,
    LightCmd,
    Trans,
)
from .models import EncoderMatcher as EncCmd


class RemoteEncoder(BleAdvCodec):
    """Phisical Remote encoder."""

    _len = 8

    def _checksum(self, buffer: bytearray) -> int:
        return sum(buffer) & 0xFF

    def decrypt(self, buffer: bytearray) -> bytearray | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer."""
        if not self.is_eq(self._checksum(buffer[:-1]), buffer[-1], "Checksum"):
            return None
        return buffer

    def encrypt(self, buffer: bytearray) -> bytearray:
        """Encrypt / whiten a readable buffer."""
        return buffer + bytearray([self._checksum(buffer)])

    def convert_to_enc(self, decoded: bytearray) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert a readable buffer into an encoder command and a config."""
        conf = BleAdvConfig()
        conf.tx_count = decoded[6]
        conf.id = int.from_bytes(decoded[1:5], "little")

        enc_cmd = BleAdvEncCmd(decoded[5] & 0x3F)
        enc_cmd.arg0 = decoded[0]
        enc_cmd.arg1 = decoded[5] & 0xC0

        return enc_cmd, conf

    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytearray:
        """Convert an encoder command and a config into a readable buffer."""
        uid = conf.id.to_bytes(4, "little")
        return bytearray([enc_cmd.arg0, *uid, enc_cmd.cmd | enc_cmd.arg1, conf.tx_count])


class RemoteXorEncoder(BleAdvCodec):
    """Physical Remote encoder, Service Data UUID 0xF0FF, XOR whitened (seen with WOMO WM9000 lights).

    Unwhitened buffer (17 bytes, XOR 0x31):
        [0]  0x00
        [1]  check: tx ^ cmd ^ id0 ^ id1 ^ id2 ^ 0x30
        [2]  id byte 0
        [3]  0x00
        [4]  tx count (incremented on each press)
        [5]  0x00
        [6]  id byte 1
        [7]  id byte 2
        [8]  0x00
        [9]  cmd
        [10] index
        [11] 0x00
        [12] id byte 3
        [13] check: tx ^ 0x10
        [14] check: copy of [7]
        [15] check: cmd ^ 0x55
        [16] 0x00

    The remote alternates the ON command between 0xB0 (odd tx) and 0xAF (even tx).
    """

    _len = 17
    _tx_max = 256
    XOR_KEY: int = 0x31
    ON_ALT: tuple[int, int] = (0xB0, 0xAF)

    def _check1(self, buffer: bytearray) -> int:
        return buffer[4] ^ buffer[9] ^ buffer[2] ^ buffer[6] ^ buffer[7] ^ 0x30

    def decrypt(self, buffer: bytearray) -> bytearray | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer."""
        data = bytearray(x ^ self.XOR_KEY for x in buffer)
        if (
            any(data[i] != 0 for i in (0, 3, 5, 8, 11, 16))
            or not self.is_eq(self._check1(data), data[1], "Check1")
            or not self.is_eq(data[4] ^ 0x10, data[13], "Check13")
            or not self.is_eq(data[7], data[14], "Check14")
            or not self.is_eq(data[9] ^ 0x55, data[15], "Check15")
        ):
            return None
        return data

    def encrypt(self, buffer: bytearray) -> bytearray:
        """Encrypt / whiten a readable buffer."""
        buffer[1] = self._check1(buffer)
        buffer[13] = buffer[4] ^ 0x10
        buffer[14] = buffer[7]
        buffer[15] = buffer[9] ^ 0x55
        return bytearray(x ^ self.XOR_KEY for x in buffer)

    def convert_to_enc(self, decoded: bytearray) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert a readable buffer into an encoder command and a config."""
        conf = BleAdvConfig()
        conf.id = int.from_bytes(bytes([decoded[2], decoded[6], decoded[7], decoded[12]]), "little")
        conf.index = decoded[10]
        conf.tx_count = decoded[4]
        cmd = self.ON_ALT[0] if decoded[9] == self.ON_ALT[1] else decoded[9]
        return BleAdvEncCmd(cmd), conf

    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytearray:
        """Convert an encoder command and a config into a readable buffer."""
        uid = conf.id.to_bytes(4, "little")
        cmd = enc_cmd.cmd
        if cmd == self.ON_ALT[0] and conf.tx_count % 2 == 0:
            cmd = self.ON_ALT[1]
        return bytearray([0x00, 0x00, uid[0], 0x00, conf.tx_count, 0x00, uid[1], uid[2], 0x00, cmd, conf.index, 0x00, uid[3], 0x00, 0x00, 0x00, 0x00])


TRANS = [
    Trans(LightCmd().act(ATTR_ON, True), EncCmd(0x08)),
    Trans(LightCmd().act(ATTR_ON, False), EncCmd(0x06)),
    Trans(LightCmd(1).act(ATTR_CMD, ATTR_CMD_TOGGLE), EncCmd(0x13)).no_direct(),
    Trans(CTLightCmd().act(ATTR_COLD, 0.1).act(ATTR_WARM, 0.1), EncCmd(0x10)).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_CT_UP), EncCmd(0x02)).copy(ATTR_STEP, "arg0", 10).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_CT_DOWN), EncCmd(0x03)).copy(ATTR_STEP, "arg0", 10).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_BR_UP), EncCmd(0x0A)).copy(ATTR_STEP, "arg0", 10).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_BR_DOWN), EncCmd(0x0B)).copy(ATTR_STEP, "arg0", 10).no_direct(),
    # CCT / brightness Cycle: 0x07
]

TRANS_V5 = [
    Trans(LightCmd().act(ATTR_ON, True), EncCmd(0xB0)),
    Trans(LightCmd().act(ATTR_ON, False), EncCmd(0xA6)),
]

CODECS = [
    RemoteEncoder().id("remote_v4").header([0xF0, 0xFF]).ble(0x1A, 0xFF).add_translators(TRANS),
    RemoteXorEncoder().id("remote_v5").header([0xFF, 0xF0]).ble(0x1A, 0x16).add_translators(TRANS_V5),
]  # fmt: skip
