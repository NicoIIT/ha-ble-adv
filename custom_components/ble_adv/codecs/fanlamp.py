"""Fanlamp Pro Encoders."""

from binascii import crc_hqx
from random import randint
from typing import ClassVar

from Crypto.Cipher import AES

from .const import (
    ATTR_BLUE_F,
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
    ATTR_DIR,
    ATTR_EFFECT,
    ATTR_EFFECT_RGB,
    ATTR_GREEN_F,
    ATTR_ON,
    ATTR_OSC,
    ATTR_PRESET,
    ATTR_PRESET_BREEZE,
    ATTR_PRESET_SLEEP,
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
from .utils import reverse_all, whiten


class FanLampEncoder(BleAdvCodec):
    """Base Fanlamp encoder."""

    def _crc16(self, buffer: bytes, seed: int) -> int:
        """CRC16 CCITT computing."""
        return crc_hqx(buffer, seed)


class FanLampEncoderV1(FanLampEncoder):
    """FanLamp V1 encoder."""

    def __init__(self, arg2: int, arg2_only_on_pair: bool = True, xor1: bool = False, supp_prefix: int = 0, forced_crc2: int = 0) -> None:
        """Init with args."""
        super().__init__()
        self._prefix = bytearray([0xAA, 0x98, 0x43, 0xAF, 0x0B, 0x46, 0x46, 0x46])
        self._len = 24
        if supp_prefix != 0:
            self._prefix.insert(0, supp_prefix)
        self._crc2_seed = self._crc16(self._prefix[1:6], 0xFFFF)
        self._arg2 = arg2
        self._arg2_only_on_pair = arg2_only_on_pair
        self._xor1 = xor1
        self._forced_crc2 = forced_crc2
        self._with_crc2 = (self._forced_crc2 != 0) or (supp_prefix == 0)

    def _crc2(self, buffer: bytes) -> int:
        """Compute CRC 2 as ccitt crc16."""
        return self._forced_crc2 if self._forced_crc2 != 0 else self._crc16(buffer, self._crc2_seed)

    def _get_arg2(self, cmd: int, arg2: int) -> int:
        return arg2 if cmd == 0x22 else self._arg2 if (cmd == 0x28 or (not self._arg2_only_on_pair and cmd not in [0x12, 0x13, 0x1E, 0x1F])) else 0

    def decrypt(self, buffer: bytes) -> bytes | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer."""
        return reverse_all(whiten(buffer, 0x6F))

    def encrypt(self, buffer: bytes) -> bytes:
        """Encrypt / whiten a readable buffer."""
        return whiten(reverse_all(buffer), 0x6F)

    def convert_to_enc(self, decoded: bytes) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert a readable buffer into an encoder command and a config."""
        seed = int.from_bytes(decoded[10:12])
        seed8 = seed & 0xFF
        if (
            not self.is_eq(self._crc16(decoded[:12], seed ^ 0xFFFF), int.from_bytes(decoded[12:14]), "CRC")
            or not self.is_eq(self._get_arg2(decoded[0], decoded[5]), decoded[5], "Arg2")
            or not self.is_eq(seed8 ^ 1 if self._xor1 else seed8, decoded[9], "r2")
            or (self._with_crc2 and not self.is_eq(self._crc2(decoded[:-2]), int.from_bytes(decoded[14:16]), "CRC2"))
        ):
            return None, None

        conf = BleAdvConfig()
        group_index = int.from_bytes(decoded[1:3], "little")
        conf.index = (group_index & 0x0F00) >> 8
        conf.id = (group_index & 0xF0FF) | ((seed8 ^ decoded[8]) << 16)
        conf.tx_count = decoded[6]
        conf.seed = seed

        enc_cmd = BleAdvEncCmd(decoded[0])
        enc_cmd.param = decoded[7]
        if enc_cmd.cmd != 0x28:
            enc_cmd.arg0 = decoded[3]
            enc_cmd.arg1 = decoded[4]
            if enc_cmd.cmd == 0x22:
                enc_cmd.arg2 = decoded[5]
        elif not self.is_eq(conf.id & 0xFF, decoded[3], "Pair Arg0") or not self.is_eq((conf.id >> 8) & 0xF0, decoded[4], "Pair Arg1"):
            return None, None

        return enc_cmd, conf

    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytes:
        """Convert an encoder command and a config into a readable buffer."""
        is_pair_cmd: bool = enc_cmd.cmd == 0x28
        obuf = bytearray()
        obuf.append(enc_cmd.cmd)
        obuf += ((conf.id & 0xF0FF) | ((conf.index & 0x0F) << 8)).to_bytes(2, "little")
        obuf.append(conf.id & 0xFF if is_pair_cmd else enc_cmd.arg0)
        obuf.append((conf.id >> 8) & 0xF0 if is_pair_cmd else enc_cmd.arg1)
        obuf.append(self._get_arg2(enc_cmd.cmd, enc_cmd.arg2))
        obuf.append(conf.tx_count)
        obuf.append(enc_cmd.param)
        seed = conf.seed if conf.seed != 0 else randint(0, 0xFFF5)
        seed8 = seed & 0xFF
        obuf.append(seed8 ^ 1 if self._xor1 else seed8 ^ ((conf.id >> 16) & 0xFF))
        obuf.append(seed8 ^ 1 if self._xor1 else seed8)
        obuf += seed.to_bytes(2)
        obuf += self._crc16(obuf, seed ^ 0xFFFF).to_bytes(2)
        if self._with_crc2:
            obuf += self._crc2(obuf).to_bytes(2)
        else:
            obuf.append(0xAA)
        return obuf


class FanLampEncoderV2(FanLampEncoder):
    """FanLamp V2 encoder."""

    XBOXES: ClassVar[list[int]] = [
        0xB7, 0xFD, 0x93, 0x26, 0x36, 0x3F, 0xF7, 0xCC, 0x34, 0xA5, 0xE5, 0xF1, 0x71, 0xD8, 0x31, 0x15,
        0x04, 0xC7, 0x23, 0xC3, 0x18, 0x96, 0x05, 0x9A, 0x07, 0x12, 0x80, 0xE2, 0xEB, 0x27, 0xB2, 0x75,
        0xD0, 0xEF, 0xAA, 0xFB, 0x43, 0x4D, 0x33, 0x85, 0x45, 0xF9, 0x02, 0x7F, 0x50, 0x3C, 0x9F, 0xA8,
        0x51, 0xA3, 0x40, 0x8F, 0x92, 0x9D, 0x38, 0xF5, 0xBC, 0xB6, 0xDA, 0x21, 0x10, 0xFF, 0xF3, 0xD2,
        0xE0, 0x32, 0x3A, 0x0A, 0x49, 0x06, 0x24, 0x5C, 0xC2, 0xD3, 0xAC, 0x62, 0x91, 0x95, 0xE4, 0x79,
        0xE7, 0xC8, 0x37, 0x6D, 0x8D, 0xD5, 0x4E, 0xA9, 0x6C, 0x56, 0xF4, 0xEA, 0x65, 0x7A, 0xAE, 0x08,
        0xE1, 0xF8, 0x98, 0x11, 0x69, 0xD9, 0x8E, 0x94, 0x9B, 0x1E, 0x87, 0xE9, 0xCE, 0x55, 0x28, 0xDF,
        0x8C, 0xA1, 0x89, 0x0D, 0xBF, 0xE6, 0x42, 0x68, 0x41, 0x99, 0x2D, 0x0F, 0xB0, 0x54, 0xBB, 0x16,
    ]  # fmt: skip

    def __init__(self, device_type: int, with_sign: bool) -> None:
        """Init with args."""
        super().__init__()
        self._len = 24
        self._device_type = device_type
        self._with_sign = with_sign

    def _whiten(self, buffer: bytes, seed: int) -> bytes:
        """Whiten / Unwhiten buffer with seed."""
        obuf = []
        salt = (self._prefix[1] & 0x3) << 5
        for i, val in enumerate(buffer):
            obuf.append((self.XBOXES[((seed + i + 9) & 0x1F) + salt]) ^ seed ^ val)
        return bytes(obuf)

    def _sign(self, buffer: bytes, tx_count: int, seed: int) -> int:
        """Compute uint16 AES ECB sign."""
        key = bytes([seed & 0xFF, (seed >> 8) & 0xFF, tx_count, 0x0D, 0xBF, 0xE6, 0x42, 0x68, 0x41, 0x99, 0x2D, 0x0F, 0xB0, 0x54, 0xBB, 0x16])
        cipher = AES.new(key, AES.MODE_ECB)
        ciphertext = cipher.encrypt(buffer)
        sign = int.from_bytes(ciphertext[0:2], "little")
        return sign if sign != 0 else 0xFFFF

    def decrypt(self, buffer: bytes) -> bytes | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer."""
        seed = int.from_bytes(buffer[-4:-2], "little")
        crc_msg = int.from_bytes(buffer[-2:], "little")
        crc_computed = self._crc16(buffer[:-2], seed ^ 0xFFFF)
        decoded_base = buffer[0:2] + self._whiten(buffer[2:-5], seed & 0xFF)
        sign = int.from_bytes(decoded_base[-2:], "little")
        if (
            not self.is_eq(crc_computed, crc_msg, "CRC")
            or (self._with_sign and not self.is_eq(self._sign(decoded_base[1:17], decoded_base[3], seed), sign, "Sign"))
            or (not self._with_sign and not self.is_eq(0, sign, "NO Sign"))
        ):
            return None
        return decoded_base[:-2] + buffer[-4:-2]  # seed artificially pushed at the end of decoded buffer

    def encrypt(self, decoded: bytes) -> bytes:
        """Encrypt / whiten a readable buffer."""
        seed = int.from_bytes(decoded[-2:], "little")  # seed artificially pushed at the end of decoded buffer
        obuf = bytearray(decoded[:-2])
        obuf += (self._sign(bytes(obuf[1:17]), obuf[3], seed) if self._with_sign else 0).to_bytes(2, "little")
        obuf.append(0)
        obuf = bytearray(obuf[0:2]) + self._whiten(obuf[2:], seed & 0xFF)
        obuf += seed.to_bytes(2, "little")
        obuf += self._crc16(obuf, seed ^ 0xFFFF).to_bytes(2, "little")
        return obuf

    def convert_to_enc(self, decoded: bytes) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert a readable buffer into an encoder command and a config."""
        if not self.is_eq(self._device_type, int.from_bytes(decoded[1:3], "little"), "Device Type"):
            return None, None

        conf = BleAdvConfig()
        conf.seed = int.from_bytes(decoded[-2:], "little")  # seed artificially pushed at the end of decoded buffer
        conf.tx_count = decoded[0]
        conf.id = int.from_bytes(decoded[3:7], "little")
        conf.index = decoded[7]
        enc_cmd = BleAdvEncCmd(decoded[8])
        enc_cmd.param = decoded[10]
        enc_cmd.arg0 = decoded[11]
        enc_cmd.arg1 = decoded[12]
        enc_cmd.arg2 = decoded[13]
        return enc_cmd, conf

    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytes:
        """Convert an encoder command and a config into a readable buffer."""
        dt = self._device_type.to_bytes(2, "little")
        uid = conf.id.to_bytes(4, "little")
        seed = (conf.seed if conf.seed != 0 else randint(1, 0xFFF5)).to_bytes(2, "little")  # seed artificially pushed at the end of decoded buffer
        return bytes([conf.tx_count, *dt, *uid, conf.index, enc_cmd.cmd, 0, enc_cmd.param, enc_cmd.arg0, enc_cmd.arg1, enc_cmd.arg2, *seed])


def _get_fan_translators() -> list[Trans]:
    return [
        Trans(FanCmd().act(ATTR_DIR, True), EncCmd(0x15).eq("arg0", 0)),  # Forward
        Trans(FanCmd().act(ATTR_DIR, False), EncCmd(0x15).eq("arg0", 1)),  # Reverse
        Trans(FanCmd().act(ATTR_OSC, True), EncCmd(0x16).eq("arg0", 1)),
        Trans(FanCmd().act(ATTR_OSC, False), EncCmd(0x16).eq("arg0", 0)),
        Trans(FanCmd().act(ATTR_PRESET, ATTR_PRESET_SLEEP), EncCmd(0x33).eq("arg0", 1)),
        Trans(FanCmd().act(ATTR_PRESET, ATTR_PRESET_BREEZE), EncCmd(0x33).eq("arg0", 2)),
    ]


def _get_device_translators() -> list[Trans]:
    return [
        Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_PAIR), EncCmd(0x28)),
        Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_UNPAIR), EncCmd(0x45)),
        Trans(DeviceCmd().act(ATTR_ON, False), EncCmd(0x6F)).no_direct(),
    ]


def _get_light_translators(param_attr: str, cold_attr: str, warm_attr: str) -> list[Trans]:
    return [
        Trans(LightCmd().act(ATTR_ON, True), EncCmd(0x10)),
        Trans(LightCmd().act(ATTR_ON, False), EncCmd(0x11)),
        Trans(LightCmd(1).act(ATTR_ON, True), EncCmd(0x12)),
        Trans(LightCmd(1).act(ATTR_ON, False), EncCmd(0x13)),
        Trans(CTLightCmd().act(ATTR_COLD).act(ATTR_WARM), EncCmd(0x21).eq(param_attr, 0))
        .copy(ATTR_COLD, cold_attr, 255)
        .copy(ATTR_WARM, warm_attr, 255),
        Trans(LightCmd().act(ATTR_CMD, ATTR_CMD_TOGGLE), EncCmd(0x09)).no_direct(),
        Trans(CTLightCmd().act(ATTR_COLD, 0.1).act(ATTR_WARM, 0.1), EncCmd(0x23)).no_direct(),  # night mode
        Trans(CTLightCmd().act(ATTR_COLD).act(ATTR_WARM), EncCmd(0x21).eq(param_attr, 0x40))
        .copy(ATTR_COLD, cold_attr, 255)
        .copy(ATTR_WARM, warm_attr, 255)
        .no_direct(),
        Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_CT_UP).eq(ATTR_STEP, 0.1), EncCmd(0x21).eq(param_attr, 0x18)).no_direct(),
        Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_CT_DOWN).eq(ATTR_STEP, 0.1), EncCmd(0x21).eq(param_attr, 0x24)).no_direct(),
        Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_BR_UP).eq(ATTR_STEP, 0.1), EncCmd(0x21).eq(param_attr, 0x14)).no_direct(),
        Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_BR_DOWN).eq(ATTR_STEP, 0.1), EncCmd(0x21).eq(param_attr, 0x28)).no_direct(),
    ]


def _get_rgb_translators() -> list[Trans]:
    return [
        Trans(RGBLightCmd(1).act(ATTR_RED_F).act(ATTR_GREEN_F).act(ATTR_BLUE_F), EncCmd(0x22))
        .copy(ATTR_RED_F, "arg0", 255)
        .copy(ATTR_GREEN_F, "arg1", 255)
        .copy(ATTR_BLUE_F, "arg2", 255),
        Trans(RGBLightCmd(1).act(ATTR_CMD, ATTR_CMD_BR_UP).eq(ATTR_STEP, 0.1), EncCmd(0x22).eq("arg0", 0x14)).no_direct(),  # NOT TESTED
        Trans(RGBLightCmd(1).act(ATTR_CMD, ATTR_CMD_BR_DOWN).eq(ATTR_STEP, 0.1), EncCmd(0x22).eq("arg0", 0x28)).no_direct(),  # NOT TESTED
        Trans(RGBLightCmd(1).act(ATTR_EFFECT, ATTR_EFFECT_RGB), EncCmd(0x1E)),
        Trans(RGBLightCmd(1).act(ATTR_EFFECT).eq(ATTR_EFFECT, None), EncCmd(0x1F)),
    ]


TRANS_FANLAMP_V1 = [
    *_get_light_translators("param", "arg0", "arg1"),
    *_get_rgb_translators(),
    Trans(FanCmd().act(ATTR_ON, False), EncCmd(0x31).eq("arg1", 0).eq("arg0", 0)),
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED), EncCmd(0x32).eq("arg1", 6).min("arg0", 1)).copy(ATTR_SPEED, "arg0"),
    Trans(Fan3SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED), EncCmd(0x31).eq("arg1", 0).min("arg0", 1)).copy(ATTR_SPEED, "arg0"),
    *_get_fan_translators(),
    *_get_device_translators(),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER), EncCmd(0x51)).split_copy(ATTR_TIME, ["arg0"], 1.0 / 60.0, 256),
]

TRANS_FANLAMP_V2 = [
    *_get_light_translators("arg0", "arg1", "arg2"),
    *_get_rgb_translators(),
    Trans(Fan6SpeedCmd().act(ATTR_ON, False), EncCmd(0x31).eq("arg0", 0x20).eq("arg1", 0)),
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED), EncCmd(0x31).eq("arg0", 0x20).min("arg1", 1)).copy(ATTR_SPEED, "arg1"),
    Trans(Fan3SpeedCmd().act(ATTR_ON, False), EncCmd(0x31).eq("arg0", 0).eq("arg1", 0)),
    Trans(Fan3SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED), EncCmd(0x31).eq("arg0", 0).min("arg1", 1)).copy(ATTR_SPEED, "arg1"),
    *_get_fan_translators(),
    *_get_device_translators(),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER), EncCmd(0x41)).split_copy(ATTR_TIME, ["arg0", "arg1"], 1.0 / 60.0, 256),
]

CODECS = [
    # FanLamp Pro android App
    FanLampEncoderV1(0x83, False).id("fanlamp_pro_v1").header([0x77, 0xF8]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V1),
    FanLampEncoderV2(0x0400, False).id("fanlamp_pro_v2").header([0xF0, 0x08]).prefix([0x10, 0x80, 0x00]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V2),
    FanLampEncoderV2(0x0400, True).id("fanlamp_pro_v3", None).header([0xF0, 0x08]).prefix([0x20, 0x80, 0x00]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V2),
    FanLampEncoderV2(0x0400, True).id("fanlamp_pro_v3", "s1").header([0xF0, 0x08]).prefix([0x20, 0x81, 0x00]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V2),
    FanLampEncoderV2(0x0400, True).id("fanlamp_pro_v3", "s2").header([0xF0, 0x08]).prefix([0x20, 0x82, 0x00]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V2),
    FanLampEncoderV2(0x0400, True).id("fanlamp_pro_v3", "s3").header([0xF0, 0x08]).prefix([0x20, 0x83, 0x00]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V2),
    # FanLamp Pro IOS App
    FanLampEncoderV2(0x0400, True).id("fanlamp_pro_vi3", None).header([0xF0, 0x08]).prefix([0x30, 0x80, 0x00]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V2),
    FanLampEncoderV2(0x0400, True).id("fanlamp_pro_vi3", "s1").header([0xF0, 0x08]).prefix([0x30, 0x81, 0x00]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V2),
    FanLampEncoderV2(0x0400, True).id("fanlamp_pro_vi3", "s2").header([0xF0, 0x08]).prefix([0x30, 0x82, 0x00]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V2),
    FanLampEncoderV2(0x0400, True).id("fanlamp_pro_vi3", "s3").header([0xF0, 0x08]).prefix([0x30, 0x83, 0x00]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V2),
    # LampSmart Pro android App
    FanLampEncoderV1(0x81, True).id("lampsmart_pro_v1").header([0x77, 0xF8]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V1),
    FanLampEncoderV2(0x0100, False).id("lampsmart_pro_v2").header([0xF0, 0x08]).prefix([0x10, 0x80, 0x00]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V2),
    FanLampEncoderV2(0x0100, True).id("lampsmart_pro_v3", None).header([0xF0, 0x08]).prefix([0x30, 0x80, 0x00]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V2),
    FanLampEncoderV2(0x0100, True).id("lampsmart_pro_v3", "s1").header([0xF0, 0x08]).prefix([0x30, 0x81, 0x00]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V2),
    FanLampEncoderV2(0x0100, True).id("lampsmart_pro_v3", "s2").header([0xF0, 0x08]).prefix([0x30, 0x82, 0x00]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V2),
    FanLampEncoderV2(0x0100, True).id("lampsmart_pro_v3", "s3").header([0xF0, 0x08]).prefix([0x30, 0x83, 0x00]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V2),
    # LampSmart Pro IOS App
    FanLampEncoderV1(0x81, True, False, 0x55).id("lampsmart_pro_vi1").header([0xF9, 0x08]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V1),
    FanLampEncoderV2(0x0100, True).id("lampsmart_pro_vi3", None).header([0xF0, 0x08]).prefix([0x21, 0x80, 0x00]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V2),
    FanLampEncoderV2(0x0100, True).id("lampsmart_pro_vi3", "s1").header([0xF0, 0x08]).prefix([0x21, 0x81, 0x00]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V2),
    FanLampEncoderV2(0x0100, True).id("lampsmart_pro_vi3", "s2").header([0xF0, 0x08]).prefix([0x21, 0x82, 0x00]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V2),
    FanLampEncoderV2(0x0100, True).id("lampsmart_pro_vi3", "s3").header([0xF0, 0x08]).prefix([0x21, 0x83, 0x00]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V2),
    # FanLamp remotes
    FanLampEncoderV1(0x83, False, True, 0x00, 0x9372).id("remote_v1").header([0x56, 0x55, 0x18, 0x87, 0x52]).ble(0x00, 0xFF).add_translators(TRANS_FANLAMP_V1),
    FanLampEncoderV2(0x0400, False).id("remote_v2").header([0xF0, 0x08]).prefix([0x10, 0x00, 0x56]).ble(0x02, 0x16).add_translators(TRANS_FANLAMP_V2),
    FanLampEncoderV2(0x0100, False).id("remote_v21").header([0xF0, 0x08]).prefix([0x10, 0x00, 0x56]).ble(0x02, 0x16).add_translators(TRANS_FANLAMP_V2),
    FanLampEncoderV2(0x0400, True).id("remote_v3").header([0xF0, 0x08]).prefix([0x10, 0x00, 0x56]).ble(0x02, 0x16).add_translators(TRANS_FANLAMP_V2),
    FanLampEncoderV2(0x0100, True).id("remote_v31").header([0xF0, 0x08]).prefix([0x10, 0x00, 0x56]).ble(0x02, 0x16).add_translators(TRANS_FANLAMP_V2),
    # Legacy variants from no known apps, initially present in ESPHome component. Still used by some remotes
    FanLampEncoderV1(0x81, True, True, 0x55).id("other_v1b").header([0xF9, 0x08]).ble(0x02, 0x16).add_translators(TRANS_FANLAMP_V1),
    FanLampEncoderV1(0x81, True, True).id("other_v1a").header([0x77, 0xF8]).ble(0x02, 0x03).add_translators(TRANS_FANLAMP_V1),
    FanLampEncoderV2(0x0100, False).id("other_v2").header([0xF0, 0x08]).prefix([0x10, 0x80, 0x00]).ble(0x19, 0x16).add_translators(TRANS_FANLAMP_V2),
    FanLampEncoderV2(0x0100, True).id("other_v3").header([0xF0, 0x08]).prefix([0x10, 0x80, 0x00]).ble(0x19, 0x16).add_translators(TRANS_FANLAMP_V2),
]  # fmt: skip
