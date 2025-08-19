"""LE Light."""

from typing import ClassVar

from .const import (
    ATTR_BLUE_F,
    ATTR_BR,
    ATTR_CMD,
    ATTR_CMD_TIMER,
    ATTR_CT,
    ATTR_CT_REV,
    ATTR_DIR,
    ATTR_GREEN_F,
    ATTR_ON,
    ATTR_RED_F,
    ATTR_SPEED,
    ATTR_TIME,
)
from .models import (
    BleAdvCodec,
    BleAdvConfig,
    BleAdvEncCmd,
    CTLightCmd,
    DeviceCmd,
    Fan3SpeedCmd,
    FanCmd,
    LightCmd,
    RGBLightCmd,
    Trans,
)
from .models import EncoderMatcher as EncCmd


class LeEncoder(BleAdvCodec):
    """LE encoder."""

    _len = 21
    XBOXES: ClassVar[list[int]] = [0xCB, 0x6A, 0x95, 0x8D, 0xB6, 0x7B, 0x35, 0x5A, 0x6E, 0x49, 0x5C, 0x85, 0x37, 0x3C, 0xA6, 0x88]

    def _checksum(self, buffer: bytes) -> int:
        return ((sum(buffer) + 1) & 0xFF) ^ 0xFF

    def encode(self, buffer: bytes, salt: int) -> bytes:
        """Encode by xor and salt."""
        xora = self.XBOXES[salt & 15]
        return bytearray([x ^ xora for x in buffer])

    def decrypt(self, buffer: bytes) -> bytes | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer."""
        data_len = buffer[0]
        zero_len = self._len - data_len - 1
        if (
            zero_len < 0
            or not self.is_eq(0x01, buffer[1], "1 is 1")
            or not self.is_eq_buf(bytes([0x00] * zero_len), buffer[-zero_len:], "Zero at end")
        ):
            return None
        decoded_base = buffer[2:6] + self.encode(buffer[6 : data_len + 1], buffer[2])

        if not self.is_eq(0xFE, decoded_base[4], "4 is FE") or not self.is_eq(self._checksum(decoded_base[:-1]), decoded_base[-1], "Checksum"):
            return None
        return decoded_base[:-1]

    def encrypt(self, buffer: bytes) -> bytes:
        """Encrypt / whiten a readable buffer."""
        data = [len(buffer) + 2, 0x01, *buffer, self._checksum(buffer)]
        zero_buf = [0x00] * (self._len - len(data))
        return bytes([*data[:6], *self.encode(bytes(data[6:]), data[2]), *zero_buf])

    def convert_to_enc(self, decoded: bytes) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert a readable buffer into an encoder command and a config."""
        conf = BleAdvConfig()
        conf.id = int.from_bytes(decoded[:4], "little")
        conf.index = decoded[5]
        conf.tx_count = decoded[6]

        enc_cmd = BleAdvEncCmd(decoded[7])
        enc_cmd.param = decoded[8]  # nb of args
        enc_cmd.arg0 = 0 if enc_cmd.param < 1 else decoded[9]
        enc_cmd.arg1 = 0 if enc_cmd.param < 2 else decoded[10]
        enc_cmd.arg2 = 0 if enc_cmd.param < 3 else decoded[11]

        return enc_cmd, conf

    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytes:
        """Convert an encoder command and a config into a readable buffer."""
        uid = conf.id.to_bytes(4, "little")
        args = [enc_cmd.param, enc_cmd.arg0, enc_cmd.arg1, enc_cmd.arg2]
        return bytes([*uid, 0xFE, conf.index, conf.tx_count, enc_cmd.cmd, *args[: enc_cmd.param + 1]])


TRANS = [
    Trans(FanCmd().act(ATTR_ON, False), EncCmd(0x21).eq("param", 1).eq("arg0", 0)),
    Trans(Fan3SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED, 1), EncCmd(0x21).eq("param", 1).eq("arg0", 1)),
    Trans(Fan3SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED, 2), EncCmd(0x21).eq("param", 1).eq("arg0", 2)),
    Trans(Fan3SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED, 3), EncCmd(0x21).eq("param", 1).eq("arg0", 3)),
    Trans(Fan3SpeedCmd().act(ATTR_DIR, True), EncCmd(0x21).eq("param", 1).eq("arg0", 128)),
    Trans(Fan3SpeedCmd().act(ATTR_DIR, False), EncCmd(0x21).eq("param", 1).eq("arg0", 129)),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER), EncCmd(0x22).eq("param", 3).eq("arg0", 0))
    .no_direct()
    .copy(ATTR_TIME, "arg1", 7.0 / 1800.0)
    .copy(ATTR_TIME, "arg2", 8.0 / 1800.0),
    Trans(LightCmd().act(ATTR_ON, True), EncCmd(0x00).eq("param", 1).eq("arg0", 1)),
    Trans(LightCmd().act(ATTR_ON, False), EncCmd(0x01).eq("param", 1).eq("arg0", 1)),
    Trans(CTLightCmd().act(ATTR_BR), EncCmd(0x08).eq("param", 2)).split_copy(ATTR_BR, ["arg1", "arg0"], 1000.0, 256),
    Trans(CTLightCmd().act(ATTR_CT).max(ATTR_CT, 0.5), EncCmd(0x0D).eq("param", 2).eq("arg0", 128)).copy(ATTR_CT, "arg1", 256.0),
    Trans(CTLightCmd().act(ATTR_CT_REV).max(ATTR_CT_REV, 0.4999999999), EncCmd(0x0D).eq("param", 2).eq("arg1", 128).max("arg0", 127)).copy(
        ATTR_CT_REV, "arg0", 256.0
    ),
    Trans(CTLightCmd().act(ATTR_BR, 0.1).act(ATTR_CT, 0.1), EncCmd(0x12).eq("param", 2).eq("arg0", 0).eq("arg1", 5)).no_direct(),
    Trans(RGBLightCmd(1).act(ATTR_RED_F).act(ATTR_GREEN_F).act(ATTR_BLUE_F), EncCmd(0x16).eq("param", 3))
    .copy(ATTR_RED_F, "arg0", 255)
    .copy(ATTR_GREEN_F, "arg1", 255)
    .copy(ATTR_BLUE_F, "arg2", 255),
]

CODECS = [
    LeEncoder().id("lelight").header([0xFF, 0xFF, 0xFF, 0xFF]).ble(0x1A, 0xFF).add_translators(TRANS),
]  # fmt: skip
