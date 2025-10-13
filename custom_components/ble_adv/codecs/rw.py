"""RW.Light."""

from binascii import crc_hqx
from random import randint
from typing import Self

from .const import (
    ATTR_BLUE,
    ATTR_BR,
    ATTR_CMD,
    ATTR_CMD_PAIR,
    ATTR_CMD_TIMER,
    ATTR_CMD_UNPAIR,
    ATTR_CT_REV,
    ATTR_EFFECT,
    ATTR_EFFECT_RGB,
    ATTR_GREEN,
    ATTR_ON,
    ATTR_RED,
    ATTR_SPEED,
    ATTR_TIME,
)
from .models import (
    BleAdvCodec,
    BleAdvConfig,
    BleAdvEncCmd,
    BleAdvEntAttr,
    CTLightCmd,
    DeviceCmd,
    Fan100SpeedCmd,
    FanCmd,
    LightCmd,
    RGBLightCmd,
    Trans,
)
from .models import EncoderMatcher as EncCmd
from .utils import reverse_all, whiten


class RwEncoder(BleAdvCodec):
    """RW encoder."""

    _len = 18

    def _crc16(self, buffer: bytes) -> int:
        """CRC16 CCITT computing."""
        # // 0x696B = crc_hqx(bytes([0x52, 0x9C, 0x54, 0x6E, 0x55]), 0xFFFF))
        return crc_hqx(buffer, 0x696B)

    def common_header(self) -> Self:
        """Set common header."""
        return self.header([0xDD, 0xB2, 0xDA, 0x6C, 0x9F, 0x01, 0x7A, 0x34])

    def decrypt(self, buffer: bytes) -> bytes | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer."""
        decoded = reverse_all(whiten(buffer, 0x69))
        if (
            not self.is_eq(0x4C, decoded[8], "8 is 0x4C")
            or not self.is_eq(0xFF, decoded[9], "9 is 0xFF")
            or not self.is_eq(0x00, decoded[10], "10 is 0x00")
            or not self.is_eq(0x01, decoded[12], "12 is 0x01")
            or not self.is_eq(0x02, decoded[14], "14 is 0x02")
            or not self.is_eq(int.from_bytes(decoded[-2:]), self._crc16(decoded[:-2]), "CRC")
        ):
            return None

        pivot = decoded[11] ^ decoded[13] ^ decoded[15]
        return bytes(
            [
                decoded[0] ^ pivot,
                decoded[1] ^ pivot,
                decoded[2] ^ pivot ^ decoded[1],
                decoded[3] ^ pivot ^ decoded[1],
                decoded[4] ^ pivot ^ decoded[1],
                decoded[5] ^ pivot ^ decoded[2],
                decoded[6] ^ pivot ^ decoded[2],
                decoded[7] ^ pivot ^ decoded[2],
                decoded[11] ^ pivot ^ decoded[5],
                decoded[13] ^ pivot ^ decoded[5],
                pivot,
            ]
        )

    def encrypt(self, buffer: bytes) -> bytes:
        """Encrypt / whiten a readable buffer."""
        b12 = buffer[1] ^ buffer[2]
        encoded = bytes(
            [
                buffer[0] ^ buffer[10],
                buffer[1] ^ buffer[10],
                buffer[2] ^ buffer[1],
                buffer[3] ^ buffer[1],
                buffer[4] ^ buffer[1],
                buffer[5] ^ b12 ^ buffer[10],
                buffer[6] ^ b12 ^ buffer[10],
                buffer[7] ^ b12 ^ buffer[10],
                0x4C,
                0xFF,
                0x00,
                buffer[8] ^ b12,
                0x01,
                buffer[9] ^ b12,
                0x02,
                buffer[8] ^ buffer[9] ^ buffer[10],
            ]
        )
        encoded += self._crc16(encoded).to_bytes(2)
        return whiten(reverse_all(encoded), 0x69)

    def convert_to_enc(self, decoded: bytes) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert a readable buffer into an encoder command and a config."""
        conf = BleAdvConfig()
        conf.id = int.from_bytes(decoded[2:6], "little")
        conf.index = decoded[6]
        conf.tx_count = decoded[1]
        conf.seed = decoded[10]

        enc_cmd = BleAdvEncCmd(decoded[0])
        enc_cmd.arg0 = decoded[7]
        enc_cmd.arg1 = decoded[8]
        enc_cmd.arg2 = decoded[9]

        return enc_cmd, conf

    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytes:
        """Convert an encoder command and a config into a readable buffer."""
        seed = conf.seed if conf.seed != 0 else randint(1, 0xF5)
        uid = conf.id.to_bytes(4, "little")
        return bytes([enc_cmd.cmd, conf.tx_count, *uid, conf.index, enc_cmd.arg0, enc_cmd.arg1, enc_cmd.arg2, seed])


class TransRGB(Trans):
    """Specific Translator for complex RGB args handling."""

    def enc_to_ent(self, enc_cmd: BleAdvEncCmd) -> BleAdvEntAttr:
        """Overload for complex attribute handling."""
        ent_attr = super().enc_to_ent(enc_cmd)
        ent_attr.attrs[ATTR_RED] = (enc_cmd.arg0 & 0x0F) / 15.0
        ent_attr.attrs[ATTR_GREEN] = ((enc_cmd.arg0 & 0xF0) >> 4) / 15.0
        ent_attr.attrs[ATTR_BLUE] = (enc_cmd.arg1 & 0x0F) / 15.0
        return ent_attr

    def ent_to_enc(self, ent_attr: BleAdvEntAttr) -> BleAdvEncCmd:
        """Overload for complex attribute handling."""
        enc_cmd = super().ent_to_enc(ent_attr)
        enc_cmd.arg0 = int(15.0 * ent_attr.attrs[ATTR_RED]) & 0x0F | (int(15.0 * ent_attr.attrs[ATTR_GREEN]) << 4)
        enc_cmd.arg1 = int(15.0 * ent_attr.attrs[ATTR_BLUE])
        return enc_cmd


def _trans_rgb(index: int) -> list[Trans]:
    return [
        Trans(RGBLightCmd(index).act(ATTR_ON, True), EncCmd(0x31)),
        Trans(RGBLightCmd(index).act(ATTR_ON, False), EncCmd(0x32)),
        Trans(RGBLightCmd(index).act(ATTR_EFFECT, ATTR_EFFECT_RGB), EncCmd(0x3F)),
        Trans(RGBLightCmd(index).act(ATTR_EFFECT).eq(ATTR_EFFECT, None), EncCmd(0x3C)),
        Trans(RGBLightCmd(index).act(ATTR_EFFECT, "Strobe"), EncCmd(0x3D)),
        Trans(RGBLightCmd(index).act(ATTR_EFFECT, "Fade"), EncCmd(0x3B)),
        Trans(RGBLightCmd(index).act(ATTR_EFFECT, "Smooth"), EncCmd(0x43)),
        TransRGB(RGBLightCmd(index).act(ATTR_BR).act(ATTR_RED).act(ATTR_GREEN).act(ATTR_BLUE), EncCmd(0x48)).copy(ATTR_BR, "arg2", 100.0),
    ]


TRANS_FAN = [
    Trans(FanCmd().act(ATTR_ON, False), EncCmd(0x61).eq("arg1", 0)),
    Trans(FanCmd().act(ATTR_ON, True), EncCmd(0x61).eq("arg1", 1)),
    Trans(Fan100SpeedCmd().act(ATTR_SPEED, 1), EncCmd(0x62).eq("arg1", 0)),
    Trans(Fan100SpeedCmd().act(ATTR_SPEED), EncCmd(0x62).min("arg1", 1)).copy(ATTR_SPEED, "arg1"),
]

TRANS_DEVICE = [
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_PAIR), EncCmd(0x76)),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_UNPAIR), EncCmd(0x78)),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER), EncCmd(0x63)).copy(ATTR_TIME, "arg1"),
]

TRANS_CWW = [
    Trans(LightCmd().act(ATTR_ON, True), EncCmd(0x01)),
    Trans(LightCmd().act(ATTR_ON, False), EncCmd(0x02)),
    Trans(CTLightCmd().act(ATTR_BR), EncCmd(0x0B)).copy(ATTR_BR, "arg0", 100.0),
    Trans(CTLightCmd().act(ATTR_CT_REV), EncCmd(0x0C)).copy(ATTR_CT_REV, "arg0", 100.0),
    Trans(CTLightCmd().act(ATTR_EFFECT, "Reading"), EncCmd(0x08)),
    Trans(CTLightCmd().act(ATTR_EFFECT, "Theater"), EncCmd(0x07)),
    Trans(CTLightCmd().act(ATTR_EFFECT, "Party"), EncCmd(0x09)),
    Trans(CTLightCmd().act(ATTR_EFFECT, "Night Light"), EncCmd(0x0A)),
]

# TRANS_MIX corresponds to interface types MIX / WT / RGB WT / FAN
TRANS_MIX = [
    *TRANS_DEVICE,
    *TRANS_CWW,
    *_trans_rgb(1),
    Trans(LightCmd(2).act(ATTR_ON, True), EncCmd(0x10)),
    Trans(LightCmd(2).act(ATTR_ON, False), EncCmd(0x11)),
    *TRANS_FAN,
]

CODECS = [
    RwEncoder().id("rwlight_mix").common_header().ble(0x1A, 0xFF).add_translators(TRANS_MIX),
    RwEncoder().id("rwlight_mix", "ios").common_header().ble(0x1A, 0x03).add_translators(TRANS_MIX),
]  # fmt: skip
