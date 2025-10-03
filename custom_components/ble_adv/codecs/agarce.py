"""Smart Light (Agarce) codecs."""

from random import randint
from typing import Any, ClassVar

from .const import (
    ATTR_BR,
    ATTR_CMD,
    ATTR_CMD_PAIR,
    ATTR_CMD_UNPAIR,
    ATTR_CT_REV,
    ATTR_DIR,
    ATTR_ON,
    ATTR_OSC,
    ATTR_PRESET,
    ATTR_PRESET_BREEZE,
    ATTR_SPEED,
    ATTR_SUB_TYPE,
    FAN_TYPE,
    FAN_TYPE_6SPEED,
)
from .models import (
    BleAdvCodec,
    BleAdvConfig,
    BleAdvEncCmd,
    BleAdvEntAttr,
    CTLightCmd,
    DeviceCmd,
    LightCmd,
    Trans,
)
from .models import EncoderMatcher as EncCmd


class AgarceEncoder(BleAdvCodec):
    """Agarce encoder."""

    duration: int = 400
    interval: int = 10
    repeat: int = 60
    _len = 18

    MATRIX: ClassVar[list[int]] = [0xAA, 0xBB, 0xCC, 0xDD, 0x5A, 0xA5, 0xA5, 0x5A]

    def _crypt(self, buffer: bytes, seed: int) -> bytearray:
        pivot0 = seed & 0xFF
        pivot1 = seed >> 8
        return bytearray([x ^ self.MATRIX[i % 8] ^ (pivot0 if (((i + 1) / 2 % 2) < 1) else pivot1) for i, x in enumerate(buffer)])

    def ent_to_enc(self, ent_attr: BleAdvEntAttr) -> list[BleAdvEncCmd]:
        """Convert Entity Attributes to list of Encoder Attributes, OVERRIDEN."""
        if ent_attr.base_type == FAN_TYPE and ent_attr.index == 0:
            enc_cmd = BleAdvEncCmd(0x80)
            enc_cmd.arg0 = 0x80 if ent_attr.attrs[ATTR_ON] else 0x00
            enc_cmd.arg0 |= ent_attr.attrs[ATTR_SPEED]
            enc_cmd.arg0 |= 0x00 if ent_attr.attrs[ATTR_DIR] else 0x10
            enc_cmd.arg0 |= 0x20 if ent_attr.attrs[ATTR_PRESET] == ATTR_PRESET_BREEZE else 0x00
            enc_cmd.arg1 = int(ent_attr.attrs[ATTR_OSC])
            enc_cmd.arg2 = 0x01 if ATTR_SPEED in ent_attr.chg_attrs else 0x00
            enc_cmd.arg2 |= 0x02 if ATTR_DIR in ent_attr.chg_attrs else 0x00
            enc_cmd.arg2 |= 0x04 if ATTR_PRESET in ent_attr.chg_attrs else 0x00
            enc_cmd.arg2 |= 0x08 if ATTR_ON in ent_attr.chg_attrs else 0x00
            enc_cmd.arg2 |= 0x10 if ATTR_OSC in ent_attr.chg_attrs else 0x00
            return [enc_cmd]
        return super().ent_to_enc(ent_attr)

    def enc_to_ent(self, enc_cmd: BleAdvEncCmd) -> list[BleAdvEntAttr]:
        """Convert Encoder Attributes to list of Entity Attributes, OVERRIDEN."""
        if enc_cmd.cmd == 0x80:
            attr_chg = []
            if enc_cmd.arg2 & 0x01:
                attr_chg.append(ATTR_SPEED)
            if enc_cmd.arg2 & 0x02:
                attr_chg.append(ATTR_DIR)
            if enc_cmd.arg2 & 0x04:
                attr_chg.append(ATTR_PRESET)
            if enc_cmd.arg2 & 0x08:
                attr_chg.append(ATTR_ON)
            if enc_cmd.arg2 & 0x10:
                attr_chg.append(ATTR_OSC)
            attrs = {
                ATTR_SUB_TYPE: FAN_TYPE_6SPEED,
                ATTR_SPEED: enc_cmd.arg0 & 0x0F,
                ATTR_ON: (enc_cmd.arg0 & 0x80) != 0,
                ATTR_DIR: (enc_cmd.arg0 & 0x10) == 0,
                ATTR_OSC: enc_cmd.arg1 != 0,
                ATTR_PRESET: ATTR_PRESET_BREEZE if (enc_cmd.arg0 & 0x20) else None,
            }
            return [BleAdvEntAttr(attr_chg, attrs, FAN_TYPE, 0)]
        return super().enc_to_ent(enc_cmd)

    def decrypt(self, buffer: bytes) -> bytes | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer."""
        if not self.is_eq(sum(buffer[:-1]) & 0xFF, buffer[-1], "Checksum2"):
            return None
        decoded = self._crypt(buffer[3:-1], int.from_bytes(buffer[1:3], "little"))
        if not self.is_eq(sum(decoded[:-1]) & 0xFF, decoded[-1], "Checksum"):
            return None
        is_pair = (decoded[8] & 0xF0) == 0x00
        # Exclude Group Commands, ref https://github.com/NicoIIT/esphome-components/issues/17#issuecomment-2597871821
        if is_pair and (decoded[12] == 0x00):
            return None
        prefix = buffer[0]
        if is_pair:
            prefix |= (decoded[10] & 0x0F) << 4
            decoded[12] = ((decoded[12] & 0x0F) << 4) + decoded[11]
            decoded[11] = 0
            decoded[10] = 0
        else:
            decoded[12] = ((decoded[12] & 0x0F) << 4) + (decoded[8] & 0x0F)
        return bytes([prefix, buffer[1], buffer[2], *decoded[:-1]])

    def encrypt(self, buffer: bytes) -> bytes:
        """Encrypt / whiten a readable buffer."""
        decoded = bytearray(buffer[3:])
        is_pair = decoded[8] == 0x00
        prefix = buffer[0]
        if is_pair:
            decoded[10] = (prefix & 0xF0) >> 4  # arg1
            decoded[11] = decoded[12] & 0x0F  # arg2
            decoded[12] = ((decoded[12] >> 4) & 0x0F) + 0xC0
            prefix = prefix & 0x0F
        else:
            decoded[8] |= decoded[12] & 0x0F
            decoded[12] = (decoded[12] >> 4) & 0x0F
        decoded.append(sum(decoded) & 0xFF)
        decoded = bytearray([prefix, buffer[1], buffer[2]]) + self._crypt(decoded, int.from_bytes(buffer[1:3], "little"))
        return bytes([*decoded, sum(decoded) & 0xFF])

    def convert_to_enc(self, decoded: bytes) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert a readable buffer into an encoder command and a config."""
        enc_cmd = BleAdvEncCmd(decoded[10] & 0xF0)
        enc_cmd.arg0 = decoded[11]
        enc_cmd.arg1 = decoded[12]
        enc_cmd.arg2 = decoded[13]

        conf = BleAdvConfig()
        conf.tx_count = decoded[2]
        conf.app_restart_count = decoded[3]
        # decoded[4:5] => rem_seq;  // 0x1000 / 0x5000 ?
        conf.id = int.from_bytes(decoded[6:10], "little")
        conf.index = decoded[14]
        conf.seed = int.from_bytes(decoded[0:2], "little")
        return enc_cmd, conf

    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytes:
        """Convert an encoder command and a config into a readable buffer."""
        uid = conf.id.to_bytes(4, "little")
        seed = (conf.seed if conf.seed != 0 else randint(1, 0xFFF5)).to_bytes(2, "little")
        return seed + bytes(
            [
                conf.tx_count,
                conf.app_restart_count,
                0x00,
                0x10,
                *uid,
                enc_cmd.cmd,
                enc_cmd.arg0,
                enc_cmd.arg1,
                enc_cmd.arg2,
                conf.index,
            ]
        )

    def get_supported_features(self, base_type: str) -> list[dict[str, set[Any]]]:
        """Get the featues supported by the translators."""
        if base_type == FAN_TYPE:
            return [
                {
                    ATTR_SUB_TYPE: {FAN_TYPE_6SPEED},
                    ATTR_PRESET: {ATTR_PRESET_BREEZE},
                    ATTR_SPEED: set(range(6)),
                    ATTR_ON: {True, False},
                    ATTR_DIR: {True, False},
                    ATTR_OSC: {True, False},
                }
            ]
        return super().get_supported_features(base_type)


TRANS = [
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_PAIR), EncCmd(0x00).eq("arg0", 1)),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_UNPAIR), EncCmd(0x00).eq("arg0", 0)),
    Trans(DeviceCmd().act(ATTR_ON, False), EncCmd(0x70).max("arg0", 1)).no_direct(),
    Trans(DeviceCmd().act(ATTR_ON, True), EncCmd(0x70).min("arg0", 2)).no_direct(),
    Trans(LightCmd().act(ATTR_ON, True), EncCmd(0x10).eq("arg0", 1)).copy(ATTR_CT_REV, "arg1", 100).copy(ATTR_BR, "arg2", 100),
    Trans(LightCmd().act(ATTR_ON, False), EncCmd(0x10).eq("arg0", 0)).copy(ATTR_CT_REV, "arg1", 100).copy(ATTR_BR, "arg2", 100),
    Trans(CTLightCmd().act(ATTR_CT_REV).act(ATTR_BR), EncCmd(0x20)).copy(ATTR_CT_REV, "arg0", 100).copy(ATTR_BR, "arg1", 100),
]


CODECS = [
    AgarceEncoder().id("agarce_v3").header([0xF9, 0x09]).prefix([0x83]).ble(0x19, 0xFF).add_translators(TRANS),
    AgarceEncoder().id("agarce_v4").header([0xF9, 0x09]).prefix([0x84]).ble(0x19, 0xFF).add_translators(TRANS),
]
