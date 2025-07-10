"""Mantra Lighting Application."""

from .const import (
    ATTR_BR,
    ATTR_CMD,
    ATTR_CMD_TIMER,
    ATTR_COLD,
    ATTR_CT_REV,
    ATTR_DIR,
    ATTR_ON,
    ATTR_PRESET,
    ATTR_PRESET_BREEZE,
    ATTR_PRESET_SLEEP,
    ATTR_SPEED,
    ATTR_TIME,
    ATTR_WARM,
)
from .models import (
    BleAdvCodec,
    BleAdvConfig,
    BleAdvEncCmd,
    CTLightCmd,
    DeviceCmd,
    Fan6SpeedCmd,
    FanCmd,
    LightCmd,
    Trans,
)
from .models import EncoderMatcher as EncCmd


class MantraEncoder(BleAdvCodec):
    """Mantra encoder."""

    _len: int = 18
    _tx_max: int = 0x0FFF
    _family = bytes([0x12, 0x34, 0x56, 0x78])

    def _whiten16(self, buffer: bytes, seed: int, param: int = 4777, xorer: int = 73) -> bytearray:
        obuf = bytearray()
        r = seed
        for val in buffer:
            b = 0
            for j in range(8):
                high_bit = 0x8000 & r
                r = (r << 1) & 0xFFFF
                if high_bit != 0:
                    r ^= param
                    b |= 1 << (7 - j)
                if r == 0:
                    r = 1061
            obuf.append(val ^ xorer ^ b)
        return obuf

    def decrypt(self, buffer: bytes) -> bytes | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer."""
        obuf = bytearray(buffer[:5])
        obuf += self._whiten16(buffer[5:], int.from_bytes(buffer[2:4]))
        return obuf

    def encrypt(self, buffer: bytes) -> bytes:
        """Encrypt / whiten a readable buffer."""
        obuf = bytearray(buffer[:5])
        obuf += self._whiten16(buffer[5:], int.from_bytes(buffer[2:4]))
        return obuf

    def convert_to_enc(self, decoded: bytes) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert a readable buffer into an encoder command and a config."""
        if not self.is_eq(0x06, decoded[2], "2 as 0x06") or not self.is_eq_buf(self._family, decoded[4:8], "Family"):
            return None, None

        conf = BleAdvConfig()
        conf.tx_count = int.from_bytes(decoded[0:2])
        conf.index = (conf.tx_count & 0xF000) >> 12
        conf.tx_count = conf.tx_count & 0x0FFF
        conf.id = int.from_bytes(decoded[8:10])

        enc_cmd = BleAdvEncCmd(decoded[3])
        enc_cmd.param = decoded[10]
        enc_cmd.arg0 = decoded[11]
        enc_cmd.arg1 = decoded[12]
        enc_cmd.arg2 = decoded[13]
        enc_cmd.arg3 = decoded[14]
        enc_cmd.arg4 = decoded[15]

        return enc_cmd, conf

    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytes:
        """Convert an encoder command and a config into a readable buffer."""
        count = (conf.tx_count + (conf.index << 12)).to_bytes(2)
        uid = conf.id.to_bytes(2)
        return bytes(
            [*count, 0x06, enc_cmd.cmd, *self._family, *uid, enc_cmd.param, enc_cmd.arg0, enc_cmd.arg1, enc_cmd.arg2, enc_cmd.arg3, enc_cmd.arg4]
        )


TRANS = [
    Trans(DeviceCmd().act(ATTR_ON, False), EncCmd(0x01).eq("param", 0x02)).no_direct(),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER).eq(ATTR_TIME, 60), EncCmd(0x01).eq("param", 0x09)),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER).eq(ATTR_TIME, 120), EncCmd(0x01).eq("param", 0x0A)),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER).eq(ATTR_TIME, 240), EncCmd(0x01).eq("param", 0x0B)),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER).eq(ATTR_TIME, 480), EncCmd(0x01).eq("param", 0x0C)),
    Trans(LightCmd().act(ATTR_ON, True), EncCmd(0x01).eq("param", 0x05)),
    Trans(LightCmd().act(ATTR_ON, False), EncCmd(0x01).eq("param", 0x06)),
    Trans(CTLightCmd().act(ATTR_COLD).act(ATTR_WARM), EncCmd(0x02))
    .copy(ATTR_WARM, "param", 255)
    .copy(ATTR_COLD, "arg0", 255)
    .copy(ATTR_BR, "arg1", 7)
    .copy(ATTR_CT_REV, "arg2", 6)
    .copy(ATTR_BR, "arg3", 255)
    .copy(ATTR_CT_REV, "arg4", 255),
    Trans(FanCmd().act(ATTR_ON, True), EncCmd(0x01).eq("param", 0x07)),
    Trans(FanCmd().act(ATTR_ON, False), EncCmd(0x01).eq("param", 0x08)),
    Trans(FanCmd().act(ATTR_PRESET, ATTR_PRESET_BREEZE), EncCmd(0x01).eq("param", 0x0D)),  # TENTATIVE
    Trans(FanCmd().act(ATTR_PRESET, ATTR_PRESET_SLEEP), EncCmd(0x01).eq("param", 0x0E)),
    Trans(FanCmd().act(ATTR_DIR, True), EncCmd(0x01).eq("param", 0x12)),  # Forward
    Trans(FanCmd().act(ATTR_DIR, False), EncCmd(0x01).eq("param", 0x14)),  # Reverse
    # // Trans(FanCmd().act(ATTR_DIR, True), EncCmd(0x01).eq("param", 0x11)).no_reverse(),  # Forward with speed full
    Trans(Fan6SpeedCmd().act(ATTR_SPEED).eq(ATTR_ON, True), EncCmd(0x03).eq("param", 0x01)).copy(ATTR_SPEED, "arg0", 31.0 / 6.0),
    Trans(Fan6SpeedCmd().act(ATTR_SPEED, 2).act(ATTR_DIR, True), EncCmd(0x01).eq("param", 0x0F)).no_direct(),
    Trans(Fan6SpeedCmd().act(ATTR_SPEED, 4).act(ATTR_DIR, True), EncCmd(0x01).eq("param", 0x10)).no_direct(),
    Trans(Fan6SpeedCmd().act(ATTR_SPEED, 6).act(ATTR_DIR, True), EncCmd(0x01).eq("param", 0x11)).no_direct(),
]

CODECS = [
    MantraEncoder().id("mantra_v0").header([0x4E, 0x6F]).prefix([0x72, 0x0E]).ble(0x1A, 0xFF).add_translators(TRANS),
]  # fmt: skip
