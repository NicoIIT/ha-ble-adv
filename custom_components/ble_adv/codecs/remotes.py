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

    def _checksum(self, buffer: bytes) -> int:
        return sum(buffer) & 0xFF

    def decrypt(self, buffer: bytes) -> bytes | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer."""
        if not self.is_eq(self._checksum(buffer[:-1]), buffer[-1], "Checksum"):
            return None
        return buffer

    def encrypt(self, buffer: bytes) -> bytes:
        """Encrypt / whiten a readable buffer."""
        return buffer + bytes([self._checksum(buffer)])

    def convert_to_enc(self, decoded: bytes) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert a readable buffer into an encoder command and a config."""
        conf = BleAdvConfig()
        conf.tx_count = decoded[6]
        conf.id = int.from_bytes(decoded[1:5], "little")

        enc_cmd = BleAdvEncCmd(decoded[5] & 0x3F)
        enc_cmd.arg0 = decoded[0]
        enc_cmd.arg1 = decoded[5] & 0xC0

        return enc_cmd, conf

    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytes:
        """Convert an encoder command and a config into a readable buffer."""
        uid = conf.id.to_bytes(4, "little")
        return bytes([enc_cmd.arg0, *uid, enc_cmd.cmd | enc_cmd.arg1, conf.tx_count])


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

CODECS = [
    RemoteEncoder().id("remote_v4").header([0xF0, 0xFF]).ble(0x1A, 0xFF).add_translators(TRANS),
]  # fmt: skip
