"""Hxlight Codec."""

import colorsys

from .const import (
    ATTR_BLUE,
    ATTR_BR,
    ATTR_CMD,
    ATTR_CMD_BR_DOWN,
    ATTR_CMD_BR_UP,
    ATTR_CMD_CT_DOWN,
    ATTR_CMD_CT_UP,
    ATTR_CMD_PAIR,
    ATTR_CMD_TIMER,
    ATTR_CMD_UNPAIR,
    ATTR_COLD,
    ATTR_CT,
    ATTR_CT_REV,
    ATTR_EFFECT,
    ATTR_EFFECT_NM,
    ATTR_GREEN,
    ATTR_ON,
    ATTR_RED,
    ATTR_STEP,
    ATTR_TIME,
    ATTR_WARM,
)
from .models import (
    BleAdvCodec,
    BleAdvConfig,
    BleAdvEncCmd,
    BleAdvEntAttr,
    CTLightCmd,
    DeviceCmd,
    LightCmd,
    RGBLightCmd,
    Trans,
    TranslatorSet,
)
from .models import EncoderMatcher as EncCmd
from .utils import rev_crc16_ccit, whiten


class LedSpotCodec(BleAdvCodec):
    """Codec for LED Spot App.

    Decoded buffer (12 bytes):
        [0]     0x83 for all commands, mapped to "arg3" - 0x83
        [1:3]   id (big endian)
        [3]     group index, 0 for all
        [4]     param
        [5]     cmd
        [6]     arg0
        [7:11]  hard coded REV_ARGS
        [11]    tx count

    followed on air by the sum of the 12 bytes and a CRC16 CCITT computed on the bit reversed buffer and stored bit reversed.
    """

    WHITEN_SEED: int = 0x59
    CRC_SEED: int = 0xB12B
    REV_ARGS: bytes = bytes([0xFF, 0xF7, 0xFE, 0x01])

    _len = 15
    _tx_max = 0xFE

    def _crc(self, buffer: bytes | bytearray) -> int:
        return rev_crc16_ccit(buffer, self.CRC_SEED, False, False)

    def decrypt(self, buffer: bytearray) -> bytearray | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer."""
        decoded = whiten(buffer, self.WHITEN_SEED)
        if (
            not self.is_eq(self._crc(decoded[:-2]), int.from_bytes(decoded[-2:], "little"), "CRC")
            or not self.is_eq(sum(decoded[:12]) & 0xFF, decoded[12], "Checksum")
            or not self.is_eq(True, decoded[3] > 0, "Group Cmd")
        ):
            return None
        return decoded[:12]

    def encrypt(self, buffer: bytearray) -> bytearray:
        """Encrypt / whiten a readable buffer."""
        buffer = buffer + bytes([sum(buffer) & 0xFF])
        return whiten(buffer + self._crc(buffer).to_bytes(2, "little"), self.WHITEN_SEED)

    def convert_to_enc(self, decoded: bytearray) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert a readable buffer into an encoder command and a config."""
        conf = BleAdvConfig()
        conf.id = int.from_bytes(decoded[1:3])
        conf.index = decoded[3]
        conf.tx_count = decoded[11]
        enc_cmd = BleAdvEncCmd(decoded[5], decoded[4], decoded[6])
        enc_cmd.arg3 = decoded[0] - 0x83
        return enc_cmd, conf

    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytearray:
        """Convert an encoder command and a config into a readable buffer."""
        args = [enc_cmd.param, enc_cmd.cmd, enc_cmd.arg0]
        return bytearray([enc_cmd.arg3 + 0x83, *conf.id.to_bytes(2), conf.index, *args, *self.REV_ARGS, conf.tx_count])


class HxlightCodec(LedSpotCodec):
    """Hxlight codec.

    Decoded buffer (12 bytes), same as Parent except [0] and [7:11]:
        [0]     type: 0x86 for on / off and Timer, 0x84 for RGB Light, 0x83 for the other commands
                mapped to "arg3" - 0x83
        [7:11]  [~param, ~cmd, ~arg0, 0x00], except for:
                    color temperature: [arg1, ~cmd, 0x55, 0x55]
                    RGB: [~param, ~cmd, 0x55, 0x55]
                    Timer: [arg1, arg2, 0x55, 0x55] (No Direct)
    """

    def convert_to_enc(self, decoded: bytearray) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert a readable buffer into an encoder command and a config."""
        enc_cmd, conf = super().convert_to_enc(decoded)
        if enc_cmd is None or conf is None:
            return None, None
        enc_cmd.arg1 = 0 if decoded[7] == (~enc_cmd.param & 0xFF) else decoded[7]
        enc_cmd.arg2 = 0 if decoded[8] == (~enc_cmd.cmd & 0xFF) else decoded[8]
        return enc_cmd, conf

    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytearray:
        """Convert an encoder command and a config into a readable buffer."""
        buffer = super().convert_from_enc(enc_cmd, conf)
        if enc_cmd.cmd == 0x65 and enc_cmd.param == 0x07:
            buffer[7:11] = [enc_cmd.arg1, ~enc_cmd.cmd & 0xFF, 0x55, 0x55]
        elif enc_cmd.arg3 == 0x01:
            buffer[7:11] = [~enc_cmd.param & 0xFF, ~enc_cmd.cmd & 0xFF, 0x55, 0x55]
        else:
            buffer[7:11] = [~enc_cmd.param & 0xFF, ~enc_cmd.cmd & 0xFF, ~enc_cmd.arg0 & 0xFF, 0x00]
        return buffer


class TransRGB(Trans):
    """Translator for RGB commands into unique HUE in arg0 with Blue at 0/255."""

    def ent_to_enc(self, ent_attr: BleAdvEntAttr) -> BleAdvEncCmd:
        """Translate an entity attribute into an encoder command."""
        enc_cmd = super().ent_to_enc(ent_attr)
        hue, _, _ = colorsys.rgb_to_hsv(ent_attr.attrs[ATTR_RED], ent_attr.attrs[ATTR_GREEN], ent_attr.attrs[ATTR_BLUE])
        enc_cmd.arg0 = round(((2 / 3 - hue) % 1.0) * 255)
        return enc_cmd

    def enc_to_ent(self, enc_cmd: BleAdvEncCmd) -> BleAdvEntAttr:
        """Translate an encoder command into an entity attribute."""
        ent_attr = super().enc_to_ent(enc_cmd)
        hue = (2 / 3 - enc_cmd.arg0 / 255.0) % 1.0
        ent_attr.attrs[ATTR_RED], ent_attr.attrs[ATTR_GREEN], ent_attr.attrs[ATTR_BLUE] = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
        return ent_attr


TRANS_LS = [
    Trans(LightCmd().act(ATTR_ON, True), EncCmd(0x01).eq("arg0", 0x01)),
    Trans(LightCmd().act(ATTR_ON, False), EncCmd(0x01).eq("arg0", 0x02)),
    Trans(CTLightCmd().act(ATTR_BR), EncCmd(0x64).eq("param", 0x05)).copy(ATTR_BR, "arg0", 100.0),
    Trans(CTLightCmd().act(ATTR_CT_REV), EncCmd(0x64).eq("param", 0x07)).copy(ATTR_CT_REV, "arg0", 100.0),  # NOT IN APP, MAY WORK...
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_BR_UP).eq(ATTR_STEP, 0.1), EncCmd(0x08).eq("arg0", 0x01)).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_BR_DOWN).eq(ATTR_STEP, 0.1), EncCmd(0x08).eq("arg0", 0x02)).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_CT_UP).eq(ATTR_STEP, 0.1), EncCmd(0x0A).eq("arg0", 0x01)).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_CT_DOWN).eq(ATTR_STEP, 0.1), EncCmd(0x0A).eq("arg0", 0x02)).no_direct(),
]

TRANS_HL_COMMON = [
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_PAIR), EncCmd(0x02).eq("arg0", 0x01)),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_UNPAIR), EncCmd(0x02).eq("arg0", 0x02)),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER).eq(ATTR_TIME, 0), EncCmd(0x02).eq("param", 0x09).eq("arg3", 0x03)).no_direct(),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER), EncCmd(0x01).eq("param", 0x09).eq("arg3", 0x03))
    .split_copy(ATTR_TIME, ["arg1", "arg2"], 1.0 / 60.0, 60)
    .no_direct(),
    Trans(LightCmd().act(ATTR_ON, False), EncCmd(0x01).eq("arg0", 0x02).eq("arg3", 0x03)),
    Trans(CTLightCmd().act(ATTR_BR), EncCmd(0x65).eq("param", 0x05).eq("arg3", 0x00)).copy(ATTR_BR, "arg0", 100.0),
    Trans(CTLightCmd().act(ATTR_CT_REV), EncCmd(0x65).eq("param", 0x07).max("arg0", 100))
    .copy(ATTR_CT_REV, "arg0", 100.0)
    .copy(ATTR_CT, "arg1", 100.0),
    # Bright, Warm and Comfortable presets, reverse only
    Trans(CTLightCmd().act(ATTR_COLD, 1.0).act(ATTR_WARM, 0.0), EncCmd(0x0E).eq("arg0", 0x01)).no_direct(),
    Trans(CTLightCmd().act(ATTR_COLD, 0.0).act(ATTR_WARM, 1.0), EncCmd(0x0E).eq("arg0", 0x02)).no_direct(),
    Trans(CTLightCmd().act(ATTR_COLD, 0.5).act(ATTR_WARM, 0.5), EncCmd(0x0E).eq("arg0", 0x03)).no_direct(),
    # RGB commands, second light???
    TransRGB(RGBLightCmd(1).act(ATTR_RED).act(ATTR_GREEN).act(ATTR_BLUE), EncCmd(0x16).eq("arg3", 0x01)),
    Trans(RGBLightCmd(1).act(ATTR_BR), EncCmd(0x65).eq("param", 0x05).eq("arg3", 0x01)).copy(ATTR_BR, "arg0", 100.0),
]

TRANS_HL = [
    Trans(LightCmd().act(ATTR_ON, True), EncCmd(0x01).eq("arg0", 0x01).eq("arg3", 0x03)),
    # Night Mode: switches the lamp on, 2% brightness, full warm
    Trans(CTLightCmd().act(ATTR_ON, True).act(ATTR_COLD, 0.0).act(ATTR_WARM, 0.02), EncCmd(0x03).eq("arg0", 0x01)).no_direct(),
    *TRANS_HL_COMMON,
]

TRANS_HL_NM_AS_EFFECT = [
    # Night Mode switches the lamp on by itself: do not send ON before it
    Trans(LightCmd().act(ATTR_ON, True).eq(ATTR_EFFECT, None), EncCmd(0x01).eq("arg0", 0x01).eq("arg3", 0x03)).no_reverse(),
    Trans(LightCmd().act(ATTR_ON, True), EncCmd(0x01).eq("arg0", 0x01).eq("arg3", 0x03)).no_direct(),
    Trans(LightCmd().act(ATTR_EFFECT, ATTR_EFFECT_NM), EncCmd(0x03).eq("arg0", 0x01)),
    Trans(LightCmd().act(ATTR_EFFECT).eq(ATTR_EFFECT, None), EncCmd(0x01).eq("arg0", 0x01).eq("arg3", 0x03)).no_reverse(),
    *TRANS_HL_COMMON,
]

HEADER = [0xF0, 0xFF, 0x6D, 0xB6, 0x43, 0x59, 0x3A, 0x60, 0xA7, 0xA1]

CODECS = [
    HxlightCodec().id("hxlight_v0").header(HEADER).footer([0x18]).ble(0x01, 0xFF).add_translators(TRANS_HL).add_translator_set("nm_as_effect", TranslatorSet(TRANS_HL_NM_AS_EFFECT)),
    LedSpotCodec().id("ledspot_v0").header(HEADER).ble(0x01, 0xFF).add_translators(TRANS_LS)
]  # fmt: skip
