"""Smart Light (Agarce) codecs."""

from typing import Any, ClassVar

from .const import (
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
    ATTR_ON,
    ATTR_OSC,
    ATTR_PRESET,
    ATTR_PRESET_BREEZE,
    ATTR_SPEED,
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
    Fan6SpeedCmd,
    FanCmd,
    LightCmd,
    Trans,
)
from .models import EncoderMatcher as EncCmd


class AgarceEncoderBase(BleAdvCodec):
    """Common encoder for Agarce (Smart Light)."""

    duration: int = 400
    interval: int = 10
    repeat: int = 60
    _len = 18
    _seed_max = 0xFFF5
    _seed_len = 2

    MATRIX: ClassVar[list[int]] = [0xAA, 0xBB, 0xCC, 0xDD, 0x5A, 0xA5, 0xA5, 0x5A]

    def _crypt(self, buffer: bytearray, seed_bytes: bytearray) -> bytearray:
        """XOR encrypt/decrypt buffer using seed-derived pivot and MATRIX."""
        pivot = [*seed_bytes, *reversed(seed_bytes)]
        return bytearray(x ^ pivot[i % (2 * self._seed_len)] ^ self.MATRIX[i % 8] for i, x in enumerate(buffer))

    def decrypt_base(self, buffer: bytearray, added_sum: int = 0) -> bytearray | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer."""
        if not self.is_eq((sum(buffer[:-1]) + added_sum) & 0xFF, buffer[-1], "Outer Checksum"):
            return None
        decoded = self._crypt(buffer[1 + self._seed_len : -1], buffer[1 : 1 + self._seed_len])
        if not self.is_eq(sum(decoded[:-1]) & 0xFF, decoded[-1], "Inner Checksum"):
            return None
        return bytearray(buffer[: 1 + self._seed_len]) + decoded

    def encrypt_base(self, buffer: bytearray, added_sum: int = 0) -> bytes:
        """Encrypt / whiten a readable buffer."""
        decoded = buffer[1 + self._seed_len :]
        decoded.append(sum(decoded) & 0xFF)
        decoded = bytearray(buffer[: 1 + self._seed_len]) + self._crypt(decoded, buffer[1 : 1 + self._seed_len])
        return bytes([*decoded, (sum(decoded) + added_sum) & 0xFF])


class AgarceEncoder(AgarceEncoderBase):
    """Agarce encoder."""

    def decrypt(self, buffer: bytes) -> bytes | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer."""
        if (decoded := self.decrypt_base(buffer)) is None:
            return None
        is_pair = (decoded[11] & 0xF0) == 0x00
        # Exclude Group Commands, ref https://github.com/NicoIIT/esphome-components/issues/17#issuecomment-2597871821
        if is_pair and (decoded[15] == 0x00):
            return None
        if is_pair:
            decoded[0] |= (decoded[13] & 0x0F) << 4
            decoded[15] = ((decoded[15] & 0x0F) << 4) + decoded[14]
            decoded[14] = 0
            decoded[13] = 0
        else:
            decoded[15] = ((decoded[15] & 0x0F) << 4) + (decoded[11] & 0x0F)
        return bytes(decoded[:-1])

    def encrypt(self, buffer: bytes) -> bytes:
        """Encrypt / whiten a readable buffer."""
        decoded = bytearray(buffer)
        is_pair = decoded[11] == 0x00
        if is_pair:
            decoded[13] = (decoded[0] & 0xF0) >> 4  # arg1
            decoded[14] = decoded[15] & 0x0F  # arg2
            decoded[15] = ((decoded[15] >> 4) & 0x0F) + 0xC0
            decoded[0] = decoded[0] & 0x0F
        else:
            decoded[11] |= decoded[15] & 0x0F
            decoded[15] = (decoded[15] >> 4) & 0x0F
        return self.encrypt_base(decoded)

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
        buf_start = [*conf.seed.to_bytes(2, "little"), conf.tx_count, conf.app_restart_count, 0x00, 0x10, *conf.id.to_bytes(4, "little")]
        return bytes([*buf_start, enc_cmd.cmd, enc_cmd.arg0, enc_cmd.arg1, enc_cmd.arg2, conf.index])


class AgarceFanTrans(Trans):
    """Argrace specific Fan Translator for complex args handling."""

    def __init__(self) -> None:
        class _AgarceFanEnt(Fan6SpeedCmd):
            def __init__(self) -> None:
                """Init with forced actions."""
                super().__init__()
                self._actions = [ATTR_ON, ATTR_SPEED, ATTR_DIR, ATTR_OSC, ATTR_PRESET]

            def get_supported_features(self) -> tuple[str, int, dict[str, Any]]:
                """Get Features: Force preset."""
                base_type, index, feats = super().get_supported_features()
                return (base_type, index, {**feats, ATTR_PRESET: ATTR_PRESET_BREEZE})

        super().__init__(_AgarceFanEnt(), EncCmd(0x80))

    def ent_to_enc(self, ent_attr: BleAdvEntAttr) -> BleAdvEncCmd:
        """Apply transformations to Encoder Attributes: direct."""
        enc_cmd = super().ent_to_enc(ent_attr)
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
        return enc_cmd

    def enc_to_ent(self, enc_cmd: BleAdvEncCmd) -> BleAdvEntAttr:
        """Apply transformations to Entity Attributes: reverse."""
        ent_attr = super().enc_to_ent(enc_cmd)
        ent_attr.chg_attrs = []
        if enc_cmd.arg2 & 0x01:
            ent_attr.chg_attrs.append(ATTR_SPEED)
        if enc_cmd.arg2 & 0x02:
            ent_attr.chg_attrs.append(ATTR_DIR)
        if enc_cmd.arg2 & 0x04:
            ent_attr.chg_attrs.append(ATTR_PRESET)
        if enc_cmd.arg2 & 0x08:
            ent_attr.chg_attrs.append(ATTR_ON)
        if enc_cmd.arg2 & 0x10:
            ent_attr.chg_attrs.append(ATTR_OSC)
        ent_attr.attrs[ATTR_SPEED] = enc_cmd.arg0 & 0x0F
        ent_attr.attrs[ATTR_ON] = (enc_cmd.arg0 & 0x80) != 0
        ent_attr.attrs[ATTR_DIR] = (enc_cmd.arg0 & 0x10) == 0
        ent_attr.attrs[ATTR_OSC] = enc_cmd.arg1 != 0
        ent_attr.attrs[ATTR_PRESET] = ATTR_PRESET_BREEZE if (enc_cmd.arg0 & 0x20) else None
        return ent_attr


class AgarceRemoteEncoder(AgarceEncoderBase):
    """Agarce Remote encoder/decoder."""

    _len = 22
    _seed_max = 0xFFFFFFFF
    _seed_len = 4

    def decrypt(self, buffer: bytes) -> bytes | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer."""
        return self.decrypt_base(buffer, 0x1A)

    def encrypt(self, buffer: bytes) -> bytes:
        """Encrypt / whiten a readable buffer."""
        return self.encrypt_base(buffer, 0x1A)

    def convert_to_enc(self, decoded: bytes) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert a readable buffer into an encoder command and a config."""
        conf = BleAdvConfig()
        conf.tx_count = decoded[4]
        conf.app_restart_count = decoded[5]
        conf.id = int.from_bytes(decoded[8:14], "little")
        conf.seed = int.from_bytes(decoded[0:4], "little")

        enc_cmd = BleAdvEncCmd(decoded[15])  # command code
        enc_cmd.arg0 = decoded[16]  # rolling code (UNKNOWN)
        enc_cmd.arg1 = decoded[17]  # always 0xFF ?
        enc_cmd.arg2 = decoded[18]  # UNKNOWN2

        return enc_cmd, conf

    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytes:
        """Convert an encoder command and a config into a readable buffer."""
        # The rolling code uses a combination of tx_count and command code and other parameters unknown
        # this is NOT a working implementation but it seems it is not a problem to use this
        rolling_code = (conf.tx_count ^ enc_cmd.cmd) & 0xFF

        return bytes(
            [
                *conf.seed.to_bytes(4, "little"),
                conf.tx_count,
                conf.app_restart_count,
                0x00,
                0x00,
                *conf.id.to_bytes(6, "little"),
                0x00,
                enc_cmd.cmd,
                enc_cmd.arg0 if enc_cmd.arg0 != 0 else rolling_code,
                enc_cmd.arg1 if enc_cmd.arg1 != 0 else 0xFF,
                enc_cmd.arg2,
            ]
        )


TRANS = [
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_PAIR), EncCmd(0x00).eq("arg0", 1)),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_UNPAIR), EncCmd(0x00).eq("arg0", 0)),
    Trans(DeviceCmd().act(ATTR_ON, False), EncCmd(0x70).max("arg0", 1)).no_direct(),
    Trans(DeviceCmd().act(ATTR_ON, True), EncCmd(0x70).min("arg0", 2)).no_direct(),
    Trans(LightCmd().act(ATTR_ON, True), EncCmd(0x10).eq("arg0", 1)).copy(ATTR_CT_REV, "arg1", 100).copy(ATTR_BR, "arg2", 100),
    Trans(LightCmd().act(ATTR_ON, False), EncCmd(0x10).eq("arg0", 0)).copy(ATTR_CT_REV, "arg1", 100).copy(ATTR_BR, "arg2", 100),
    Trans(CTLightCmd().act(ATTR_CT_REV).act(ATTR_BR), EncCmd(0x20)).copy(ATTR_CT_REV, "arg0", 100).copy(ATTR_BR, "arg1", 100),
    AgarceFanTrans(),
]

TRANS_REMOTE = [
    # Light commands
    Trans(LightCmd().act(ATTR_ON, True), EncCmd(0x11)).no_reverse(),  # Toggle acts as Turn On
    Trans(LightCmd().act(ATTR_ON, False), EncCmd(0x11)).no_reverse(),  # Toggle acts as Turn Off
    Trans(LightCmd().act(ATTR_CMD, ATTR_CMD_TOGGLE), EncCmd(0x11)).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_BR_UP).eq(ATTR_STEP, 0.1), EncCmd(0x03)).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_BR_DOWN).eq(ATTR_STEP, 0.1), EncCmd(0x04)).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_CT_DOWN).eq(ATTR_STEP, 0.1), EncCmd(0x05)).no_direct(),  # K+ = colder = CT down
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_CT_UP).eq(ATTR_STEP, 0.1), EncCmd(0x06)).no_direct(),  # K- = warmer = CT up
    Trans(CTLightCmd().act(ATTR_COLD, 1.0).act(ATTR_WARM, 1.0), EncCmd(0x09)),  # K button: full warm+cold
    Trans(CTLightCmd().act(ATTR_ON, True).act(ATTR_COLD, 0.1).act(ATTR_WARM, 0.1), EncCmd(0x07)),  # Night light
    # Device commands
    Trans(DeviceCmd().act(ATTR_ON, False), EncCmd(0x4E)).no_direct(),  # All off
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER).eq(ATTR_TIME, 7200), EncCmd(0x4A)).no_direct(),  # 2H Timer
    # Fan speed commands (fan speed 1-6, codes 0x3C-0x41)
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED, 1.0), EncCmd(0x3C)),
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED, 2.0), EncCmd(0x3D)),
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED, 3.0), EncCmd(0x3E)),
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED, 4.0), EncCmd(0x3F)),
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED, 5.0), EncCmd(0x40)),
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED, 6.0), EncCmd(0x41)),
    # Fan control commands
    Trans(FanCmd().act(ATTR_ON, False), EncCmd(0x42)),  # Fan off
    Trans(FanCmd().act(ATTR_DIR, True), EncCmd(0x47)),  # Forward
    Trans(FanCmd().act(ATTR_DIR, False), EncCmd(0x48)),  # Reverse
    Trans(FanCmd().act(ATTR_PRESET, ATTR_PRESET_BREEZE), EncCmd(0x45)),  # Breeze
    Trans(FanCmd().act(ATTR_OSC, True), EncCmd(0x52)),  # Oscillation
]


CODECS = [
    AgarceEncoder().id("agarce_v3").header([0xF9, 0x09]).prefix([0x83]).ble(0x19, 0xFF).add_translators(TRANS),
    AgarceEncoder().id("agarce_v4").header([0xF9, 0x09]).prefix([0x84]).ble(0x19, 0xFF).add_translators(TRANS),
    AgarceRemoteEncoder().id("agarce_vr3").header([0xF9, 0x09]).prefix([0x03]).ble(0x00, 0xFF).add_translators(TRANS_REMOTE),
    AgarceRemoteEncoder().id("agarce_vr4").header([0xF9, 0x09]).prefix([0x04]).ble(0x00, 0xFF).add_translators(TRANS_REMOTE),
]
