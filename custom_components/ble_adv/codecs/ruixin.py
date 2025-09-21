"""RuiXin App."""

from random import randint
from typing import ClassVar

from .const import (
    ATTR_BR,
    ATTR_CMD,
    ATTR_CMD_BR_DOWN,
    ATTR_CMD_BR_UP,
    ATTR_CMD_CT_DOWN,
    ATTR_CMD_CT_UP,
    ATTR_CMD_PAIR,
    ATTR_CMD_TOGGLE,
    ATTR_CT,
    ATTR_DIR,
    ATTR_ON,
    ATTR_SPEED,
    ATTR_STEP,
)
from .models import (
    BleAdvCodec,
    BleAdvConfig,
    BleAdvEncCmd,
    CTLightCmd,
    DeviceCmd,
    Fan100SpeedCmd,
    FanCmd,
    LightCmd,
    Trans,
)
from .models import EncoderMatcher as EncCmd


class RuiXinEncoder(BleAdvCodec):
    """RuiXin encoder."""

    _len = 16
    PADDING: ClassVar[bytes] = bytes([0x00] * 6)

    def _checksum(self, buffer: bytes) -> int:
        return sum(buffer) & 0xFF

    def decrypt(self, buffer: bytes) -> bytes | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer."""
        buffer = buffer[:2] + bytes([((x - buffer[0] - i) + 256) % 256 for i, x in enumerate(buffer[2:16])])
        if not self.is_eq(self._checksum(buffer[2:15]), buffer[15], "Checksum"):
            return None
        return buffer[:10]

    def encrypt(self, buffer: bytes) -> bytes:
        """Encrypt / whiten a readable buffer."""
        buffer = bytearray(buffer + self.PADDING)
        buffer[15] = self._checksum(buffer[2:15])
        return buffer[:2] + bytes([((x + buffer[0] + i) + 256) % 256 for i, x in enumerate(buffer[2:16])]) + buffer[16:]

    def convert_to_enc(self, decoded: bytes) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert a readable buffer into an encoder command and a config."""
        conf = BleAdvConfig()
        conf.seed = decoded[0]
        conf.tx_count = decoded[1]
        conf.id = int.from_bytes(decoded[2:6], "little")

        enc_cmd = BleAdvEncCmd(decoded[6])
        enc_cmd.arg0 = decoded[7]
        enc_cmd.arg1 = decoded[8]
        enc_cmd.arg2 = decoded[9]

        return enc_cmd, conf

    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytes:
        """Convert an encoder command and a config into a readable buffer."""
        seed = conf.seed if conf.seed != 0 else randint(1, 0xF5)
        uid = conf.id.to_bytes(4, "little")
        return bytes([seed, conf.tx_count, *uid, enc_cmd.cmd, enc_cmd.arg0, enc_cmd.arg1, enc_cmd.arg2])


class RuiXinRemoteEncoder(RuiXinEncoder):
    """RuiXin Remote encoder."""

    _len = 19
    PADDING: ClassVar[bytes] = bytes([0x07, 0x08, 0x09, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15])


TRANS = [
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_PAIR), EncCmd(0xAA)),
    Trans(DeviceCmd().act(ATTR_ON, False), EncCmd(0x11)).no_direct(),
    Trans(LightCmd().act(ATTR_ON, True), EncCmd(0x01)),
    Trans(LightCmd().act(ATTR_ON, False), EncCmd(0x02)),
    Trans(LightCmd().act(ATTR_CMD, ATTR_CMD_TOGGLE), EncCmd(0x21)).no_direct(),
    Trans(CTLightCmd().act(ATTR_BR), EncCmd(0x0C)).copy(ATTR_BR, "arg0", 250),
    Trans(CTLightCmd().act(ATTR_CT), EncCmd(0x0D)).copy(ATTR_CT, "arg0", 250),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_BR_UP).act(ATTR_STEP, 1.0 / 12), EncCmd(0x25)).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_BR_DOWN).act(ATTR_STEP, 1.0 / 12), EncCmd(0x26)).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_CT_UP).act(ATTR_STEP, 1.0 / 12), EncCmd(0x27)).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_CT_DOWN).act(ATTR_STEP, 1.0 / 12), EncCmd(0x28)).no_direct(),
    Trans(CTLightCmd().act(ATTR_BR, 1.0).act(ATTR_CT, 0.0), EncCmd(0x07)).no_direct(),
    Trans(CTLightCmd().act(ATTR_BR, 0.5).act(ATTR_CT, 0.5), EncCmd(0x08)).no_direct(),
    Trans(CTLightCmd().act(ATTR_BR, 1.0).act(ATTR_CT, 1.0), EncCmd(0x09)).no_direct(),
    Trans(FanCmd().act(ATTR_ON, True), EncCmd(0x03)).no_direct(),
    Trans(FanCmd().act(ATTR_ON, False), EncCmd(0x04)),
    Trans(FanCmd().act(ATTR_DIR, False), EncCmd(0x05)),  # Reverse
    Trans(FanCmd().act(ATTR_DIR, True), EncCmd(0x06)),  # Forward
    Trans(Fan100SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED), EncCmd(0x10)).copy(ATTR_SPEED, "arg0"),
]

CODECS = [
    RuiXinEncoder().id("ruixin_v0").header([0xFF, 0xFF, 0x01, 0x02, 0x03, 0x04, 0x69, 0x72, 0x36, 0x0E]).ble(0x00, 0xFF).add_translators(TRANS),
    RuiXinRemoteEncoder().id("ruixin_v0", "r1").header([0x00, 0x00, 0x00, 0x52, 0x58, 0x4B, 0x69, 0x72, 0x36, 0x0E]).ble(0x00, 0xFF).add_translators(TRANS),
]  # fmt: skip
