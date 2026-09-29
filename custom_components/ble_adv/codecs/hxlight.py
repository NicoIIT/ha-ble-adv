"""Hxlight Codec."""

from binascii import crc_hqx

from .const import (
    ATTR_BR,
    ATTR_CMD,
    ATTR_CMD_BR_DOWN,
    ATTR_CMD_BR_UP,
    ATTR_COLD,
    ATTR_CT_REV,
    ATTR_EFFECT,
    ATTR_EFFECT_NM,
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
    TranslatorSet,
)
from .models import EncoderMatcher as EncCmd
from .utils import reverse_all, whiten


class HxlightCodec(BleAdvCodec):
    """Hxlight codec.

    Decoded buffer (12 bytes):
        [0]     type: 0x86 for on / off, 0x83 for the other commands
        [1:3]   id (big endian)
        [3]     group index, 0 for all
        [4]     param
        [5]     cmd
        [6]     arg0
        [7:11]  check: [~param, ~cmd, ~arg0, 0x00], other values accepted on decode
                except for color temperature: [100 - arg0, ~cmd, 0x55, 0x55], as sent by the app
        [11]    tx count
    followed on air by the sum of the 12 bytes and a CRC16 CCITT computed on the bit reversed buffer and stored bit reversed.
    """

    WHITEN_SEED: int = 0x59
    CRC_SEED: int = 0xB12B
    TYPES: tuple[int, int] = (0x86, 0x83)

    _len = 15
    _tx_max = 256

    CMD_VALUE: int = 0x65
    PARAM_CT: int = 0x07

    def _crc(self, buffer: bytes | bytearray) -> int:
        return crc_hqx(reverse_all(buffer), self.CRC_SEED)

    def decrypt(self, buffer: bytearray) -> bytearray | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer."""
        decoded = whiten(buffer, self.WHITEN_SEED)
        if not self.is_eq(self._crc(decoded[:-2]), int.from_bytes(reverse_all(decoded[-2:])), "CRC") or not self.is_eq(
            sum(decoded[:12]) & 0xFF, decoded[12], "Checksum"
        ):
            return None
        return decoded[:12]

    def encrypt(self, buffer: bytearray) -> bytearray:
        """Encrypt / whiten a readable buffer."""
        buffer = buffer + bytes([sum(buffer) & 0xFF])
        return whiten(buffer + reverse_all(self._crc(buffer).to_bytes(2)), self.WHITEN_SEED)

    def convert_to_enc(self, decoded: bytearray) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert a readable buffer into an encoder command and a config."""
        if decoded[0] not in self.TYPES:
            return None, None
        conf = BleAdvConfig()
        conf.id = int.from_bytes(decoded[1:3])
        conf.index = decoded[3]
        conf.tx_count = decoded[11]
        return BleAdvEncCmd(decoded[5], decoded[4], decoded[6]), conf

    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytearray:
        """Convert an encoder command and a config into a readable buffer."""
        cmd_type = self.TYPES[0] if enc_cmd.cmd == 0x01 else self.TYPES[1]
        args = [enc_cmd.param, enc_cmd.cmd, enc_cmd.arg0]
        if enc_cmd.cmd == self.CMD_VALUE and enc_cmd.param == self.PARAM_CT:
            check = [100 - enc_cmd.arg0, ~enc_cmd.cmd & 0xFF, 0x55, 0x55]
        else:
            check = [*[~x & 0xFF for x in args], 0x00]
        return bytearray([cmd_type, *conf.id.to_bytes(2), conf.index, *args, *check, conf.tx_count])


TRANS_COMMON = [
    Trans(LightCmd().act(ATTR_ON, False), EncCmd(0x01).eq("arg0", 0x02)),
    Trans(CTLightCmd().act(ATTR_BR), EncCmd(0x65).eq("param", 0x05).min("arg0", 1).max("arg0", 100)).copy(ATTR_BR, "arg0", 100.0),
    Trans(CTLightCmd().act(ATTR_CT_REV), EncCmd(0x65).eq("param", 0x07).max("arg0", 100)).copy(ATTR_CT_REV, "arg0", 100.0),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_BR_UP).eq(ATTR_STEP, 0.1), EncCmd(0x08).eq("arg0", 0x01)).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_BR_DOWN).eq(ATTR_STEP, 0.1), EncCmd(0x08).eq("arg0", 0x02)).no_direct(),
    # Bright, Warm and Comfortable presets, reverse only
    Trans(CTLightCmd().act(ATTR_COLD, 1.0).act(ATTR_WARM, 0.0), EncCmd(0x0E).eq("arg0", 0x01)).no_direct(),
    Trans(CTLightCmd().act(ATTR_COLD, 0.0).act(ATTR_WARM, 1.0), EncCmd(0x0E).eq("arg0", 0x02)).no_direct(),
    Trans(CTLightCmd().act(ATTR_COLD, 0.5).act(ATTR_WARM, 0.5), EncCmd(0x0E).eq("arg0", 0x03)).no_direct(),
]

TRANS = [
    Trans(LightCmd().act(ATTR_ON, True), EncCmd(0x01).eq("arg0", 0x01)),
    # Night Mode: switches the lamp on, 2% brightness, full warm
    Trans(CTLightCmd().act(ATTR_ON, True).act(ATTR_COLD, 0.0).act(ATTR_WARM, 0.02), EncCmd(0x03).eq("arg0", 0x01)).no_direct(),
    *TRANS_COMMON,
]

TRANS_NM_AS_EFFECT = [
    # Night Mode switches the lamp on by itself: do not send ON before it
    Trans(LightCmd().act(ATTR_ON, True).eq(ATTR_EFFECT, None), EncCmd(0x01).eq("arg0", 0x01)).no_reverse(),
    Trans(LightCmd().act(ATTR_ON, True), EncCmd(0x01).eq("arg0", 0x01)).no_direct(),
    Trans(LightCmd().act(ATTR_EFFECT, ATTR_EFFECT_NM), EncCmd(0x03).eq("arg0", 0x01)),
    Trans(LightCmd().act(ATTR_EFFECT).eq(ATTR_EFFECT, None), EncCmd(0x01).eq("arg0", 0x01)).no_reverse(),
    *TRANS_COMMON,
]

HEADER = [0xF0, 0xFF, 0x6D, 0xB6, 0x43, 0x59, 0x3A, 0x60, 0xA7, 0xA1]

CODECS = [
    HxlightCodec().id("hxlight_v0").header(HEADER).footer([0x18]).ble(0x01, 0xFF).add_translators(TRANS).add_translator_set("nm_as_effect", TranslatorSet(TRANS_NM_AS_EFFECT)),
    HxlightCodec().id("hxlight_v0", "nf").header(HEADER).ble(0x01, 0xFF).add_translators(TRANS).add_translator_set("nm_as_effect", TranslatorSet(TRANS_NM_AS_EFFECT)),
]  # fmt: skip
