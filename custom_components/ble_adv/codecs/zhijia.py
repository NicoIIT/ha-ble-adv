"""Zhi Jia Encoders."""

from functools import reduce

from .const import (
    ATTR_BLUE,
    ATTR_BR,
    ATTR_CMD,
    ATTR_CMD_PAIR,
    ATTR_CMD_TIMER,
    ATTR_CMD_UNPAIR,
    ATTR_COLD,
    ATTR_CT,
    ATTR_DIR,
    ATTR_GREEN,
    ATTR_ON,
    ATTR_RED,
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
    Fan3SpeedCmd,
    Fan6SpeedCmd,
    FanCmd,
    LightCmd,
    RGBLightCmd,
    Trans,
)
from .models import EncoderMatcher as EncCmd
from .utils import crc16_le, whiten


class ZhijiaEncoder(BleAdvCodec):
    """Base Zhi Jia encoder."""

    _pivot_index: frozenset[int] = frozenset()
    _pivot_xor = False

    def _crc16(self, buffer: bytes, seed: int) -> int:
        """CRC16 ISO14443AB computing."""
        return crc16_le(buffer, seed, 0x8408, True, True)

    def pivot(self, buffer: bytes | list[int]) -> bytes:
        """Compute and apply a XOR pivot."""
        pivot = reduce(lambda x, y: x ^ y, [x for i, x in enumerate(buffer) if i in self._pivot_index])
        if self._pivot_xor:
            pivot ^= ((pivot & 1) - 1) & 0xFF
        return bytes([x ^ pivot for x in buffer])


class ZhijiaEncoderV0(ZhijiaEncoder):
    """Zhi Jia V0 encoder."""

    _pivot_index: frozenset[int] = frozenset({0, 1, 6, 7})
    _len = 13

    def decrypt(self, buffer: bytes) -> bytes | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer."""
        decoded_base = whiten(whiten(buffer, 0x37), 0x7F)
        if not self.is_eq(int.from_bytes(decoded_base[-2:], "little"), self._crc16(decoded_base[:-2], 0), "CRC"):
            return None
        return decoded_base[:-2]

    def encrypt(self, buffer: bytes) -> bytes:
        """Encrypt / whiten a readable buffer."""
        decoded_base = bytearray(buffer)
        decoded_base += self._crc16(decoded_base, 0).to_bytes(2, "little")
        return whiten(whiten(decoded_base, 0x7F), 0x37)

    def convert_to_enc(self, decoded: bytes) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert a readable buffer into an encoder command and a config."""
        decoded = self.pivot(decoded)

        enc_cmd = BleAdvEncCmd(decoded[4])
        enc_cmd.arg0 = decoded[1]
        enc_cmd.arg1 = decoded[3]
        enc_cmd.arg2 = decoded[1] ^ decoded[7]

        conf = BleAdvConfig()
        conf.id = int.from_bytes([decoded[0], decoded[5]], "little")
        conf.index = decoded[2]
        conf.tx_count = decoded[0] ^ decoded[6]
        return enc_cmd, conf

    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytes:
        """Convert an encoder command and a config into a readable buffer."""
        uuid = int.to_bytes(conf.id, 2, "little")
        oarray = [
            uuid[0],
            enc_cmd.arg0,
            conf.index,
            enc_cmd.arg1,
            enc_cmd.cmd,
            uuid[1],
            uuid[0] ^ conf.tx_count,
            enc_cmd.arg0 ^ enc_cmd.arg2,
        ]
        return self.pivot(oarray)


class ZhijiaEncoderV1(ZhijiaEncoder):
    """Zhi Jia V1 encoder."""

    _pivot_index: frozenset[int] = frozenset({2, 4, 9, 12, 13, 15})
    _len = 23
    _pivot_xor = True

    def __init__(self, mac: list[int]) -> None:
        super().__init__()
        self._mac: bytes = bytearray(mac)

    def decrypt(self, buffer: bytes) -> bytes | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer."""
        decoded_base = whiten(buffer, 0x37)
        if not self.is_eq(int.from_bytes(decoded_base[-2:], "little"), self._crc16(decoded_base[:-2], 0), "CRC"):
            return None
        return decoded_base[:-2]

    def encrypt(self, buffer: bytes) -> bytes:
        """Encrypt / whiten a readable buffer."""
        decoded_base = bytearray(buffer)
        decoded_base += self._crc16(decoded_base, 0).to_bytes(2, "little")
        return whiten(decoded_base, 0x37)

    def common_convert_to_enc(self, decoded: bytes) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert common part to encoder command and config."""
        addr = bytes([decoded[7], decoded[10], decoded[13] ^ decoded[4]])
        if not self.is_eq_buf(self._mac, addr, "Mac"):
            return None, None

        conf = BleAdvConfig()
        conf.id = int.from_bytes([decoded[2], decoded[12] ^ decoded[2], decoded[15] ^ decoded[9]], "little")
        conf.index = decoded[6]
        conf.tx_count = decoded[4]

        enc_cmd = BleAdvEncCmd(decoded[9])
        enc_cmd.arg0 = decoded[0]
        enc_cmd.arg1 = decoded[3]
        enc_cmd.arg2 = decoded[5]

        return enc_cmd, conf

    def common_convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> list[int]:
        """Convert common part for an encoder command and a config into a readable buffer."""
        uuid = int.to_bytes(conf.id, 3, "little")

        key = enc_cmd.cmd ^ enc_cmd.arg0 ^ enc_cmd.arg1 ^ enc_cmd.arg2
        key ^= uuid[0] ^ uuid[1] ^ uuid[2] ^ conf.tx_count ^ conf.index ^ self._mac[0] ^ self._mac[1] ^ self._mac[2]

        return [
            enc_cmd.arg0,
            key,
            uuid[0],
            enc_cmd.arg1,
            conf.tx_count,
            enc_cmd.arg2,
            conf.index,
            self._mac[0],
            0x00,
            enc_cmd.cmd,
            self._mac[1],
            0x00,
            uuid[1] ^ uuid[0],
            self._mac[2] ^ conf.tx_count,
            0x00,
            uuid[2] ^ enc_cmd.cmd,
            0x00,
        ]

    def convert_to_enc(self, decoded: bytes) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert a readable buffer into an encoder command and a config."""
        decoded = self.pivot(decoded)
        enc_cmd, conf = self.common_convert_to_enc(decoded)
        if (
            enc_cmd is None
            or conf is None
            or not self.is_eq(0x00, decoded[8], "8 as 0x00")
            or not self.is_eq(0x00, decoded[11], "11 as 0x00")
            or not self.is_eq(decoded[7], decoded[14], "Dupe 7/14")
        ):
            return None, None
        return enc_cmd, conf

    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytes:
        """Convert an encoder command and a config into a readable buffer."""
        oarray = self.common_convert_from_enc(enc_cmd, conf)
        oarray[14] = oarray[7]
        return self.pivot(oarray)


class ZhijiaEncoderV2(ZhijiaEncoderV1):
    """Zhi Jia V2 encoder."""

    _pivot_index: frozenset[int] = frozenset({3, 7, 11, 12, 13, 15})
    _len = 24
    _pivot_xor = True

    def decrypt(self, buffer: bytes) -> bytes | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer."""
        buf1 = whiten(buffer, 0x6F)
        buf2 = whiten(buf1[:-2], 0xD3) + buf1[-2:]
        if not self.is_eq_buf(bytes([0x00] * 7), buf2[-7:], "Zero padding"):
            return None
        return buf2[:-7]

    def encrypt(self, buffer: bytes) -> bytes:
        """Encrypt / whiten a readable buffer."""
        buf1 = buffer + bytes([0x00] * 7)
        return whiten(whiten(buf1[:-2], 0xD3) + buf1[-2:], 0x6F)

    def convert_to_enc(self, decoded: bytes) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert a readable buffer into an encoder command and a config."""
        decoded = self.pivot(decoded)
        enc_cmd, conf = self.common_convert_to_enc(decoded)
        if (
            enc_cmd is None
            or conf is None
            or not self.is_eq(decoded[2] ^ decoded[3] ^ decoded[4] ^ decoded[7], decoded[8], "decoded 8")
            or not self.is_eq(0x00, decoded[11], "11 as 0x00")
            or not self.is_eq(decoded[2] ^ decoded[3] ^ decoded[4] ^ decoded[9], decoded[14], "decoded 14")
        ):
            return None, None
        return enc_cmd, conf

    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytes:
        """Convert an encoder command and a config into a readable buffer."""
        oarray = self.common_convert_from_enc(enc_cmd, conf)
        oarray[1] ^= oarray[9]
        oarray[8] = oarray[2] ^ oarray[3] ^ oarray[4] ^ oarray[7]
        oarray[14] = oarray[2] ^ oarray[3] ^ oarray[4] ^ oarray[9]
        return bytearray(self.pivot(oarray))


class ZhijiaEncoderRemote(ZhijiaEncoderV1):
    """Zhi Jia Remote encoder."""

    _len = 17

    def decrypt(self, buffer: bytes) -> bytes | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer."""
        return buffer

    def encrypt(self, buffer: bytes) -> bytes:
        """Encrypt / whiten a readable buffer."""
        return buffer

    def convert_to_enc(self, decoded: bytes) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert a readable buffer into an encoder command and a config."""
        decoded = bytes([x ^ decoded[5] for x in decoded])
        enc_cmd, conf = self.common_convert_to_enc(decoded)
        if (
            enc_cmd is None
            or conf is None
            or not self.is_eq(0x01, decoded[8], "8 as 0x01")
            or not self.is_eq(0x02, decoded[11], "11 as 0x02")
            or not self.is_eq(decoded[2], decoded[14], "decoded 14")
        ):
            return None, None

        return enc_cmd, conf

    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytes:
        """Convert an encoder command and a config into a readable buffer."""
        oarray = self.common_convert_from_enc(enc_cmd, conf)
        oarray[1] ^= 0x04
        oarray[8] = 0x01
        oarray[11] = 0x02
        oarray[14] = oarray[2]
        oarray[16] = 0x06
        pivot = 0xC9  # NOT SURE AT ALL OF THIS

        return bytearray(bytes(x ^ pivot ^ 0x06 for x in oarray))


TRANS_V0 = [
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_PAIR), EncCmd(0xB4)),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_UNPAIR), EncCmd(0xB0)),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER).eq(ATTR_TIME, 60), EncCmd(0xD4)),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER).eq(ATTR_TIME, 120), EncCmd(0xD5)),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER).eq(ATTR_TIME, 240), EncCmd(0xD6)),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER).eq(ATTR_TIME, 480), EncCmd(0xD7)),
    Trans(LightCmd().act(ATTR_ON, True), EncCmd(0xB3)),
    Trans(LightCmd().act(ATTR_ON, False), EncCmd(0xB2)),
    Trans(CTLightCmd().act(ATTR_BR), EncCmd(0xB5)).split_copy(ATTR_BR, ["arg2", "arg1"], 1000.0),
    Trans(CTLightCmd().act(ATTR_CT), EncCmd(0xB7)).split_copy(ATTR_CT, ["arg2", "arg1"], 1000.0),
    Trans(LightCmd(1).act(ATTR_ON, True), EncCmd(0xA6).eq("arg0", 1)),
    Trans(LightCmd(1).act(ATTR_ON, False), EncCmd(0xA6).eq("arg0", 2)),
    Trans(FanCmd().act(ATTR_DIR, True), EncCmd(0xD9)),  # Forward
    Trans(FanCmd().act(ATTR_DIR, False), EncCmd(0xDA)),  # Reverse
    Trans(FanCmd().act(ATTR_ON, False), EncCmd(0xD8)),
    # Fan speed_count 3, direct and reverse
    Trans(Fan3SpeedCmd().act(ATTR_ON, True).eq(ATTR_SPEED, 1), EncCmd(0xD2)),
    Trans(Fan3SpeedCmd().act(ATTR_ON, True).eq(ATTR_SPEED, 2), EncCmd(0xD1)),
    Trans(Fan3SpeedCmd().act(ATTR_ON, True).eq(ATTR_SPEED, 3), EncCmd(0xD0)),
    # Fan speed_count 6, direct only
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED).min(ATTR_SPEED, 1).max(ATTR_SPEED, 2), EncCmd(0xD2)).no_reverse(),
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED).min(ATTR_SPEED, 3).max(ATTR_SPEED, 4), EncCmd(0xD1)).no_reverse(),
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED).min(ATTR_SPEED, 5).max(ATTR_SPEED, 6), EncCmd(0xD0)).no_reverse(),
    # Physical remote and phone app shortcut buttons, reverse only
    Trans(CTLightCmd().eq(ATTR_COLD, 0.1).eq(ATTR_WARM, 0.1), EncCmd(0xA1).eq("arg0", 25).eq("arg1", 25)).no_direct(),  # night mode
    Trans(CTLightCmd().eq(ATTR_COLD, 1).eq(ATTR_WARM, 0), EncCmd(0xA2).eq("arg0", 255).eq("arg1", 0)).no_direct(),
    Trans(CTLightCmd().eq(ATTR_COLD, 0).eq(ATTR_WARM, 1), EncCmd(0xA3).eq("arg0", 0).eq("arg1", 255)).no_direct(),
    Trans(CTLightCmd().eq(ATTR_COLD, 1).eq(ATTR_WARM, 1), EncCmd(0xA4).eq("arg0", 255).eq("arg1", 255)).no_direct(),
    Trans(CTLightCmd().eq(ATTR_COLD, 1).eq(ATTR_WARM, 0), EncCmd(0xA7).eq("arg0", 1)).no_direct(),
    Trans(CTLightCmd().eq(ATTR_COLD, 0).eq(ATTR_WARM, 1), EncCmd(0xA7).eq("arg0", 2)).no_direct(),
    Trans(CTLightCmd().eq(ATTR_COLD, 1).eq(ATTR_WARM, 1), EncCmd(0xA7).eq("arg0", 3)).no_direct(),
]

TRANS_COMMON_V1_V2 = [
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_PAIR), EncCmd(0xA2)),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_UNPAIR), EncCmd(0xA3)),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER), EncCmd(0xD9)).copy(ATTR_TIME, "arg0", 1.0 / 60.0),
    Trans(LightCmd().act(ATTR_ON, True), EncCmd(0xA5)),
    Trans(LightCmd().act(ATTR_ON, False), EncCmd(0xA6)),
    Trans(LightCmd(1).act(ATTR_ON, True), EncCmd(0xAF)),
    Trans(LightCmd(1).act(ATTR_ON, False), EncCmd(0xB0)),
    Trans(FanCmd().act(ATTR_DIR, True), EncCmd(0xDB)),  # Forward
    Trans(FanCmd().act(ATTR_DIR, False), EncCmd(0xDA)),  # Reverse
    Trans(FanCmd().act(ATTR_ON, False), EncCmd(0xD7)),
    # Fan speed_count 3, direct and reverse
    Trans(Fan3SpeedCmd().act(ATTR_ON, True).eq(ATTR_SPEED, 1), EncCmd(0xD6)),
    Trans(Fan3SpeedCmd().act(ATTR_ON, True).eq(ATTR_SPEED, 2), EncCmd(0xD5)),
    Trans(Fan3SpeedCmd().act(ATTR_ON, True).eq(ATTR_SPEED, 3), EncCmd(0xD4)),
    # Fan speed_count 6, direct only
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED).min(ATTR_SPEED, 1).max(ATTR_SPEED, 2), EncCmd(0xD6)).no_reverse(),
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED).min(ATTR_SPEED, 3).max(ATTR_SPEED, 4), EncCmd(0xD5)).no_reverse(),
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED).min(ATTR_SPEED, 5).max(ATTR_SPEED, 6), EncCmd(0xD4)).no_reverse(),
    # Physical remote and phone app shortcut buttons, reverse only
    Trans(CTLightCmd().eq(ATTR_COLD, 0.1).eq(ATTR_WARM, 0.1), EncCmd(0xA7).eq("arg0", 25).eq("arg1", 25)).no_direct(),  # night mode
    Trans(CTLightCmd().eq(ATTR_COLD, 1).eq(ATTR_WARM, 0), EncCmd(0xA8).eq("arg0", 250).eq("arg1", 0)).no_direct(),
    Trans(CTLightCmd().eq(ATTR_COLD, 0).eq(ATTR_WARM, 1), EncCmd(0xA8).eq("arg0", 0).eq("arg1", 250)).no_direct(),
    Trans(CTLightCmd().eq(ATTR_COLD, 1).eq(ATTR_WARM, 1), EncCmd(0xA8).eq("arg0", 250).eq("arg1", 250)).no_direct(),
]

TRANS_V1 = [
    *TRANS_COMMON_V1_V2,
    Trans(CTLightCmd().act(ATTR_BR), EncCmd(0xAD)).copy(ATTR_BR, "arg0", 250),
    Trans(CTLightCmd().act(ATTR_CT), EncCmd(0xAE)).copy(ATTR_CT, "arg0", 250),
]

TRANS_V2 = [
    *TRANS_COMMON_V1_V2,
    Trans(CTLightCmd().act(ATTR_BR), EncCmd(0xAD)).copy(ATTR_BR, "arg0", 250),
    Trans(CTLightCmd().act(ATTR_CT), EncCmd(0xAE)).copy(ATTR_CT, "arg0", 250),
    Trans(RGBLightCmd().act(ATTR_BR), EncCmd(0xC8)).copy(ATTR_BR, "arg0", 250),
    Trans(RGBLightCmd().act(ATTR_RED).act(ATTR_GREEN).act(ATTR_BLUE), EncCmd(0xCA))
    .copy(ATTR_RED, "arg0", 250)
    .copy(ATTR_GREEN, "arg1", 250)
    .copy(ATTR_BLUE, "arg2", 250),
]


TRANS_V2_FL = [
    *TRANS_COMMON_V1_V2,
    Trans(CTLightCmd().act(ATTR_COLD).act(ATTR_WARM), EncCmd(0xA8)).copy(ATTR_COLD, "arg0", 250).copy(ATTR_WARM, "arg1", 250),
    Trans(RGBLightCmd().act(ATTR_BR), EncCmd(0xC8)).copy(ATTR_BR, "arg0", 250),
    Trans(RGBLightCmd().act(ATTR_RED).act(ATTR_GREEN).act(ATTR_BLUE), EncCmd(0xCA))
    .copy(ATTR_RED, "arg0", 250)
    .copy(ATTR_GREEN, "arg1", 250)
    .copy(ATTR_BLUE, "arg2", 250),
    # req from app, only reverse, replaced by CT.LIGHT_CWW_COLD_WARM on direct to get ride of flickering
    Trans(CTLightCmd().act(ATTR_BR), EncCmd(0xAD)).copy(ATTR_BR, "arg0", 250).no_direct(),
    Trans(CTLightCmd().act(ATTR_CT), EncCmd(0xAE)).copy(ATTR_CT, "arg0", 250).no_direct(),
]

TRANS_VR1 = [
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_PAIR), EncCmd(0xA2)),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_UNPAIR), EncCmd(0xA3)),
    Trans(LightCmd().act(ATTR_ON, True), EncCmd(0xA5)),
    Trans(LightCmd().act(ATTR_ON, False), EncCmd(0xA6)),
    Trans(CTLightCmd().act(ATTR_COLD).act(ATTR_WARM), EncCmd(0xA8)).copy(ATTR_COLD, "arg0", 250).copy(ATTR_WARM, "arg1", 250),
    #  Missing: AF / A7 / A9 / AC / AB / AA
]

CODECS = [
    # Zhi Jia standard Android App
    ZhijiaEncoderV0().id("zhijia_v0").header([0xF9, 0x08, 0x49]).prefix([0x08, 0x80, 0x98]).ble(0x1A, 0xFF).add_translators(TRANS_V0),
    ZhijiaEncoderV1([0x19, 0x01, 0x10]).id("zhijia_v1").header([0xF9, 0x08, 0x49]).prefix([0x55, 0x08, 0x80, 0x98]).ble(0x1A, 0xFF).add_translators(TRANS_V1),
    ZhijiaEncoderV2([0x19, 0x01, 0x10]).id("zhijia_v2").header([0x22, 0x9D]).ble(0x1A, 0xFF).add_translators(TRANS_V2),
    ZhijiaEncoderV2([0x19, 0x01, 0x10]).id("zhijia_v2_fl").header([0x22, 0x9D]).ble(0x1A, 0xFF).add_translators(TRANS_V2_FL),
    # Zhi Guang standard Android App
    ZhijiaEncoderV0().id("zhiguang_v0").header([0xF9, 0x08, 0x49]).prefix([0x33, 0xAA, 0x55]).ble(0x1A, 0xFF).add_translators(TRANS_V0),
    ZhijiaEncoderV1([0x20, 0x03, 0x05]).id("zhiguang_v1").header([0xF9, 0x08, 0x49]).prefix([0xA0, 0xC0, 0x04, 0x04]).ble(0x1A, 0xFF).add_translators(TRANS_V1),
    ZhijiaEncoderV2([0x20, 0x03, 0x05]).id("zhiguang_v2").header([0x22, 0x9D]).ble(0x1A, 0xFF).add_translators(TRANS_V2),
    # Zhi Jia Remote
    ZhijiaEncoderRemote([0x20, 0x03, 0x05]).id("zhijia_vr1").header([0xF0, 0xFF]).ble(0x1A, 0xFF).add_translators(TRANS_VR1),
]  # fmt: skip

# ruff: noqa: ERA001
# "zhijia": {
#     "variants": {
#         "v2_fl": {  # to resolve flickering issues
#             "class": "ZhijiaEncoderV2",
#             "translator": "default_translator_zjv2fl",
#             "args": [[0x19, 0x01, 0x10]],
#             "max_forced_id": 0xFFFFFF,
#             "ble_param": [0x1A, 0xFF],
#             "header": [0x22, 0x9D],
#         },
#     },
