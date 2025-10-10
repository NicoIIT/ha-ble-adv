"""Zhi Mei Encoders."""

from binascii import crc_hqx
from typing import ClassVar

from .const import (
    ATTR_BLUE_F,
    ATTR_BR,
    ATTR_CMD,
    ATTR_CMD_BR_DOWN,
    ATTR_CMD_BR_UP,
    ATTR_CMD_CT_DOWN,
    ATTR_CMD_CT_UP,
    ATTR_CMD_PAIR,
    ATTR_CMD_TIMER,
    ATTR_CMD_TOGGLE,
    ATTR_CMD_UNPAIR,
    ATTR_COLD,
    ATTR_CT_REV,
    ATTR_DIR,
    ATTR_GREEN_F,
    ATTR_ON,
    ATTR_OSC,
    ATTR_PRESET,
    ATTR_PRESET_BREEZE,
    ATTR_RED_F,
    ATTR_SPEED,
    ATTR_STEP,
    ATTR_TIME,
    ATTR_WARM,
)
from .models import (
    BleAdvCodec,
    BleAdvConfig,
    BleAdvEncCmd,
    CTLightCmd,
    DeviceCmd,
    Fan3SpeedCmd,
    Fan6SpeedCmd,
    FanCmd,
    LightCmd,
    RGBLightCmd,
    Trans,
)
from .models import EncoderMatcher as EncCmd
from .utils import reverse_all, reverse_byte, whiten


class ZhimeiEncoderV0(BleAdvCodec):
    """Zhi Mei V0 encoder."""

    _len = 9

    def _checksum(self, buffer: bytes) -> int:
        return (sum(buffer) + sum(self._header)) & 0xFF

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
        conf.index = decoded[0]
        conf.tx_count = decoded[1]
        conf.id = int.from_bytes(decoded[2:4], "little")

        enc_cmd = BleAdvEncCmd(decoded[4])
        enc_cmd.arg0 = decoded[5]
        enc_cmd.arg1 = decoded[6]
        enc_cmd.arg2 = decoded[7]

        return enc_cmd, conf

    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytes:
        """Convert an encoder command and a config into a readable buffer."""
        uid = conf.id.to_bytes(2, "little")
        return bytes([conf.index, conf.tx_count, *uid, enc_cmd.cmd, enc_cmd.arg0, enc_cmd.arg1, enc_cmd.arg2])


class ZhimeiEncoderV1(BleAdvCodec):
    """Zhi Mei V1 encoder."""

    _len = 16

    MATRIX: ClassVar[list[int]] = [29, 4, 17, 32, 152, 117, 40, 70, 11, 175, 67, 172, 214, 190, 137, 142]

    def __init__(self) -> None:
        super().__init__()
        self.footer([0x10, 0x11, 0x12, 0x13, 0x14, 0x15])

    def _crc16(self, buffer: bytes) -> int:
        return crc_hqx(buffer, 0)

    def _apply_matrix(self, buffer: bytes, key: int) -> bytes:
        """Apply xor pivot with Encoding Matrix."""
        pivot = self.MATRIX[((buffer[1] >> 4) & 15) ^ (buffer[1] & 15)]
        return bytes([(((x ^ pivot) + self.MATRIX[(key + i) & 0xF]) + 256) % 256 for i, x in enumerate(buffer)])

    def _unapply_matrix(self, buffer: bytes, key: int) -> bytes:
        """Unapply xor pivot with Encoding Matrix."""
        pivot = ((buffer[0] - self.MATRIX[key & 0xF]) & 0xFF) ^ 0xFF
        return bytes([((x - self.MATRIX[(key + i) & 0xF] + 256) % 256) ^ pivot for i, x in enumerate(buffer)])

    def decrypt(self, buffer: bytes) -> bytes | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer."""
        decoded = self._unapply_matrix(buffer[self._header_start_pos :], 6)
        if not self.is_eq(self._crc16(decoded[:-3]), int.from_bytes(decoded[-2:], "little"), "CRC"):
            return None
        decoded = decoded[:-2]
        if decoded[7] != 0xB4:
            decoded = decoded[:9] + self._unapply_matrix(decoded[9:], 10)
        if (
            not self.is_eq(decoded[2], decoded[10], "Dupe 2/10")
            or not self.is_eq(0xFF, decoded[0], "0 not FF")
            or not self.is_eq(0xFF, decoded[9], "9 not FF")
            or not self.is_eq_buf(buffer[: self._header_start_pos], decoded[2 : 2 + self._header_start_pos], "Dupe Pre header")
        ):
            return None
        return decoded

    def encrypt(self, buffer: bytes) -> bytes:
        """Encrypt / whiten a readable buffer."""
        if buffer[7] != 0xB4:
            buffer = buffer[:9] + self._apply_matrix(buffer[9:], 10)
        buffer += self._crc16(buffer[:-1]).to_bytes(2, "little")
        buf_matrix = self._apply_matrix(buffer, 6)
        return buffer[2 : 2 + self._header_start_pos] + buf_matrix

    def convert_to_enc(self, decoded: bytes) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert a readable buffer into an encoder command and a config."""
        conf = BleAdvConfig()
        conf.index = decoded[8]
        conf.tx_count = decoded[2]
        conf.seed = decoded[1]
        conf.id = int.from_bytes(decoded[3:7], "little")

        enc_cmd = BleAdvEncCmd(decoded[7])
        enc_cmd.arg0 = decoded[11]
        enc_cmd.arg1 = decoded[12]
        enc_cmd.arg2 = decoded[13]

        return enc_cmd, conf

    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytes:
        """Convert an encoder command and a config into a readable buffer."""
        uid = (conf.id & 0xFFFF).to_bytes(4, "little")
        return bytes(
            [
                0xFF,
                conf.seed & 0xFF,
                conf.tx_count,
                *uid,
                enc_cmd.cmd,
                conf.index,
                0xFF,
                conf.tx_count,
                enc_cmd.arg0,
                enc_cmd.arg1,
                enc_cmd.arg2,
            ]
        )


class ZhimeiEncoderV2(BleAdvCodec):
    """Zhi Mei V2 encoder."""

    _len = 13

    def __init__(self) -> None:
        super().__init__()
        self.footer([0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19])

    def _crc16(self, buffer: bytes) -> int:
        pre_cec: int = crc_hqx(reverse_all(buffer), 0xFFFF)
        return 0xFFFF ^ (((reverse_byte(pre_cec & 0xFF) << 8) & 0xFF00) | (reverse_byte(pre_cec >> 8) & 0xFF))

    def decrypt(self, buffer: bytes) -> bytes | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer."""
        decoded = whiten(buffer, 0x48)
        if not self.is_eq(self._crc16(decoded[:-2]), int.from_bytes(decoded[-2:], "little"), "CRC"):
            return None
        return decoded[:-2]

    def encrypt(self, buffer: bytes) -> bytes:
        """Encrypt / whiten a readable buffer."""
        buffer += self._crc16(buffer).to_bytes(2, "little")
        return whiten(buffer, 0x48)

    def convert_to_enc(self, decoded: bytes) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert a readable buffer into an encoder command and a config."""
        pivot = decoded[0] ^ decoded[1] ^ decoded[6] ^ decoded[7]
        decoded = bytes([x ^ pivot for x in decoded])

        conf = BleAdvConfig()
        conf.index = decoded[2]
        conf.tx_count = decoded[6] ^ decoded[0]
        conf.id = int.from_bytes([decoded[5], decoded[0]], "little")

        enc_cmd = BleAdvEncCmd(decoded[4])
        enc_cmd.arg0 = decoded[1]
        enc_cmd.arg1 = decoded[3]
        enc_cmd.arg2 = decoded[7] ^ decoded[1]

        return enc_cmd, conf

    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytes:
        """Convert an encoder command and a config into a readable buffer."""
        uid = (conf.id & 0xFFFF).to_bytes(2, "little")
        decoded = bytes(
            [
                uid[1],
                enc_cmd.arg0,
                conf.index,
                enc_cmd.arg1,
                enc_cmd.cmd,
                uid[0],
                conf.tx_count ^ uid[1],
                enc_cmd.arg0 ^ enc_cmd.arg2,
            ]
        )
        pivot = decoded[0] ^ decoded[1] ^ decoded[6] ^ decoded[7]
        return bytes([x ^ pivot for x in decoded])


TRANS_COMMON = [
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_UNPAIR), EncCmd(0xB0)),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER), EncCmd(0xA5)).split_copy(ATTR_TIME, ["arg0", "arg1"], 1.0 / 60.0, 60),
    Trans(LightCmd().act(ATTR_ON, True), EncCmd(0xB3)),
    Trans(LightCmd().act(ATTR_ON, False), EncCmd(0xB2)),
    Trans(LightCmd(1).act(ATTR_ON, True), EncCmd(0xA6).eq("arg0", 2)),
    Trans(LightCmd(1).act(ATTR_ON, False), EncCmd(0xA6).eq("arg0", 1)),
    Trans(CTLightCmd().act(ATTR_BR), EncCmd(0xB5)).split_copy(ATTR_BR, ["arg2", "arg1"], 1000.0),
    Trans(CTLightCmd().act(ATTR_CT_REV), EncCmd(0xB7)).split_copy(ATTR_CT_REV, ["arg2", "arg1"], 1000.0),
    # Shortcut phone app buttons, only reverse
    Trans(CTLightCmd().eq(ATTR_COLD, 0.1).eq(ATTR_WARM, 0.1), EncCmd(0xA1).eq("arg0", 25).eq("arg1", 25)).no_direct(),  # night mode
    Trans(CTLightCmd().eq(ATTR_COLD, 1).eq(ATTR_WARM, 0), EncCmd(0xA7).eq("arg0", 1)).no_direct(),
    Trans(CTLightCmd().eq(ATTR_COLD, 0).eq(ATTR_WARM, 1), EncCmd(0xA7).eq("arg0", 2)).no_direct(),
    Trans(CTLightCmd().eq(ATTR_COLD, 1).eq(ATTR_WARM, 1), EncCmd(0xA7).eq("arg0", 3)).no_direct(),
    Trans(RGBLightCmd(1).act(ATTR_RED_F).act(ATTR_GREEN_F).act(ATTR_BLUE_F), EncCmd(0xCA))
    .copy(ATTR_RED_F, "arg0", 255)
    .copy(ATTR_GREEN_F, "arg1", 255)
    .copy(ATTR_BLUE_F, "arg2", 255),
]

TRANS_V1 = [
    *TRANS_COMMON,
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_PAIR), EncCmd(0xB4).eq("arg0", 0xAA).eq("arg1", 0x66).eq("arg2", 0x55)),
]

TRANS_V2 = [
    *TRANS_COMMON,
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_PAIR), EncCmd(0xB4)),
]

TRANS_FAN_COMMON = [
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_PAIR), EncCmd(0xB4).eq("arg0", 0xAA).eq("arg1", 0x66).eq("arg2", 0x55)),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_UNPAIR), EncCmd(0xB0)),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER), EncCmd(0xD4)).split_copy(ATTR_TIME, ["arg0"], 1.0 / 3600.0),
    Trans(DeviceCmd().act(ATTR_ON, True), EncCmd(0xB3)),
    Trans(DeviceCmd().act(ATTR_ON, False), EncCmd(0xB2)),
    Trans(LightCmd().act(ATTR_ON, True), EncCmd(0xA6).eq("arg0", 2)),
    Trans(LightCmd().act(ATTR_ON, False), EncCmd(0xA6).eq("arg0", 1)),
    Trans(CTLightCmd().act(ATTR_BR), EncCmd(0xB5).eq("arg0", 0)).split_copy(ATTR_BR, ["arg2", "arg1"], 1000.0),
    Trans(CTLightCmd().act(ATTR_CT_REV), EncCmd(0xB7).eq("arg0", 0)).split_copy(ATTR_CT_REV, ["arg2", "arg1"], 1000.0),
    Trans(FanCmd().act(ATTR_DIR, True), EncCmd(0xD9)),  # Forward
    Trans(FanCmd().act(ATTR_DIR, False), EncCmd(0xDA)),  # Reverse
    Trans(FanCmd().act(ATTR_OSC, True), EncCmd(0xDE).eq("arg0", 1)),
    Trans(FanCmd().act(ATTR_OSC, False), EncCmd(0xDE).eq("arg0", 2)),
    Trans(FanCmd().act(ATTR_ON, False), EncCmd(0xD1)),
    Trans(FanCmd().act(ATTR_PRESET, ATTR_PRESET_BREEZE), EncCmd(0xDB)),
    # Fan speed_count 6, direct and reverse
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED), EncCmd(0xD3)).copy(ATTR_SPEED, "arg0"),
    # Fan speed_count 3, direct only
    Trans(Fan3SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED), EncCmd(0xD3)).copy(ATTR_SPEED, "arg0", 2.0).no_reverse(),
    # Shortcut phone app buttons, only reverse
    Trans(CTLightCmd().eq(ATTR_COLD, 0.1).eq(ATTR_WARM, 0.1), EncCmd(0xA1).eq("arg0", 25).eq("arg1", 25)).no_direct(),  # night mode
    Trans(CTLightCmd().eq(ATTR_COLD, 1).eq(ATTR_WARM, 0), EncCmd(0xA7).eq("arg0", 1)).no_direct(),
    Trans(CTLightCmd().eq(ATTR_COLD, 0).eq(ATTR_WARM, 1), EncCmd(0xA7).eq("arg0", 2)).no_direct(),
    Trans(CTLightCmd().eq(ATTR_COLD, 1).eq(ATTR_WARM, 1), EncCmd(0xA7).eq("arg0", 3)).no_direct(),
    # Standard Remote buttons, only reverse
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_BR_UP).eq(ATTR_STEP, 0.166), EncCmd(0xB5).eq("arg0", 1)).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_BR_DOWN).eq(ATTR_STEP, 0.166), EncCmd(0xB5).eq("arg0", 2)).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_CT_UP).eq(ATTR_STEP, 0.166), EncCmd(0xB7).eq("arg0", 2)).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_CT_DOWN).eq(ATTR_STEP, 0.166), EncCmd(0xB7).eq("arg0", 1)).no_direct(),
]

TRANS_REMOTE = [
    Trans(DeviceCmd().act(ATTR_ON, False), EncCmd(0x10)).no_direct(),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER).eq(ATTR_TIME, 60 * 60), EncCmd(0x12)).no_direct(),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER).eq(ATTR_TIME, 2 * 60 * 60), EncCmd(0x14)).no_direct(),
    Trans(LightCmd().act(ATTR_ON, ATTR_CMD_TOGGLE), EncCmd(0x04)).no_direct(),
    Trans(LightCmd().act(ATTR_ON, True), EncCmd(0x04)).no_reverse(),
    Trans(LightCmd().act(ATTR_ON, False), EncCmd(0x04)).no_reverse(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_CT_UP).eq(ATTR_STEP, 0.166), EncCmd(0x0B)).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_CT_DOWN).eq(ATTR_STEP, 0.166), EncCmd(0x09)).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_BR_UP).eq(ATTR_STEP, 0.166), EncCmd(0x13)).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_BR_DOWN).eq(ATTR_STEP, 0.166), EncCmd(0x0C)).no_direct(),
    Trans(CTLightCmd().eq(ATTR_COLD, 0.1).eq(ATTR_WARM, 0.1), EncCmd(0x07)).no_direct(),  # night mode (toogle?)
    Trans(FanCmd().act(ATTR_DIR, ATTR_CMD_TOGGLE), EncCmd(0x02)).no_direct(),
    Trans(FanCmd().act(ATTR_DIR, True), EncCmd(0x02)).no_reverse(),
    Trans(FanCmd().act(ATTR_DIR, False), EncCmd(0x02)).no_reverse(),
    Trans(FanCmd().act(ATTR_PRESET, ATTR_PRESET_BREEZE), EncCmd(0x11)),  # Breeze mode
    Trans(Fan6SpeedCmd().act(ATTR_ON, False), EncCmd(0x0E)),
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED, 1), EncCmd(0x03)),
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED, 2), EncCmd(0x05)),
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED, 3), EncCmd(0x08)),
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED, 4), EncCmd(0x0A)),
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED, 5), EncCmd(0x0D)),
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED, 6), EncCmd(0x0F)),
]

TRANS_FAN_V1 = [
    *TRANS_FAN_COMMON,
    Trans(RGBLightCmd(1).act(ATTR_RED_F).act(ATTR_GREEN_F).act(ATTR_BLUE_F), EncCmd(0xCA))
    .copy(ATTR_RED_F, "arg0", 255)
    .copy(ATTR_GREEN_F, "arg1", 255)
    .copy(ATTR_BLUE_F, "arg2", 255),
]

CODECS = [
    # Zhi Mei standard Android App
    ZhimeiEncoderV0().id("zhimei_fan_v0").header([0x55]).ble(0x19, 0x03).add_translators(TRANS_FAN_COMMON).add_rev_only_trans(TRANS_REMOTE),
    ZhimeiEncoderV1().id("zhimei_fan_v1").header([0x48, 0x46, 0x4B, 0x4A]).ble(0x1A, 0x03).add_translators(TRANS_FAN_V1).add_rev_only_trans(TRANS_REMOTE),
    ZhimeiEncoderV1().id("zhimei_v1").header([0x48, 0x46, 0x4B, 0x4A]).ble(0x1A, 0x03).add_translators(TRANS_V1),
    ZhimeiEncoderV2().id("zhimei_v2").header([0xF9, 0x08, 0x49]).ble(0x1A, 0x03).prefix([0x33, 0xAA, 0x55]).add_translators(TRANS_V2),
    # Zhi Mei Remotes
    ZhimeiEncoderV0().fid("zhimei_fan_vr0", "zhimei_fan_v0").header([0x55]).ble(0, 0).add_translators(TRANS_REMOTE),
    ZhimeiEncoderV1().fid("zhimei_fan_vr1", "zhimei_fan_v1").header([0x48, 0x46, 0x4B, 0x4A], 3).ble(0x1A, 0xFF).add_translators(TRANS_REMOTE),
    ZhimeiEncoderV1().fid("zhimei_fan_v1b", "zhimei_fan_v1").header([0x00, 0x00, 0x00, 0x48, 0x46, 0x4B, 0x4A]).ble(0x1A, 0xFF).add_translators(TRANS_FAN_V1),
    ZhimeiEncoderV1().fid("zhimei_v1b", "zhimei_v1").header([0x58, 0x55, 0x18, 0x48, 0x46, 0x4B, 0x4A]).ble(0x1A, 0xFF).add_translators(TRANS_V1),
]  # fmt: skip
