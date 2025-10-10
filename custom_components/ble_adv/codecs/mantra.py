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
    BleAdvEntAttr,
    CTLightCmd,
    DeviceCmd,
    Fan6SpeedCmd,
    Fan8SpeedCmd,
    FanCmd,
    FanNSpeedCmd,
    LightCmd,
    Trans,
)
from .models import EncoderMatcher as EncCmd


class MantraEncoder(BleAdvCodec):
    """Mantra encoder."""

    duration: int = 400
    interval: int = 100
    repeat: int = 6
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


class TransRemote(Trans):
    """Specific translator for Remote fixed composed arg0 and arg1."""

    direct = False

    def enc_to_ent(self, enc_cmd: BleAdvEncCmd) -> BleAdvEntAttr:
        """Overload for complex attribute handling."""
        ent_attr = super().enc_to_ent(enc_cmd)
        if ATTR_BR in ent_attr.chg_attrs:
            ent_attr.attrs[ATTR_BR] = max(((enc_cmd.arg0 & 0x0F) - 1) / 10.0, 0.01)
        if ATTR_CT_REV in ent_attr.chg_attrs:
            ent_attr.attrs[ATTR_CT_REV] = ((enc_cmd.arg0 & 0x70) >> 4) / 7.0
        if ATTR_DIR in ent_attr.chg_attrs:
            ent_attr.attrs[ATTR_DIR] = not ((enc_cmd.arg1 >> 6) & 1)
        if ATTR_SPEED in ent_attr.chg_attrs:
            ent_attr.attrs[ATTR_SPEED] = enc_cmd.arg1 & 0x0F
        if ATTR_PRESET in ent_attr.chg_attrs:
            ent_attr.attrs[ATTR_PRESET] = ATTR_PRESET_BREEZE if (enc_cmd.arg1 >> 5) & 1 else ATTR_PRESET_SLEEP if (enc_cmd.arg1 >> 4) & 1 else None
        return ent_attr


TRANS_APP = [
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
    Trans(FanCmd().act(ATTR_PRESET, ATTR_PRESET_BREEZE), EncCmd(0x01).eq("param", 0x0D)),
    Trans(FanCmd().act(ATTR_PRESET, ATTR_PRESET_SLEEP), EncCmd(0x01).eq("param", 0x0E)),
    Trans(FanCmd().act(ATTR_DIR, True), EncCmd(0x01).eq("param", 0x12)),  # Forward
    Trans(FanCmd().act(ATTR_DIR, False), EncCmd(0x01).eq("param", 0x14)),  # Reverse
    Trans(FanNSpeedCmd(0, 31).act(ATTR_SPEED).eq(ATTR_ON, True), EncCmd(0x03).eq("param", 0x01)).copy(ATTR_SPEED, "arg0").no_direct(),
    Trans(Fan8SpeedCmd().act(ATTR_SPEED).eq(ATTR_ON, True), EncCmd(0x03).eq("param", 0x01)).copy(ATTR_SPEED, "arg0", 31.0 / 8.0).no_reverse(),
    Trans(Fan6SpeedCmd().act(ATTR_SPEED).eq(ATTR_ON, True), EncCmd(0x03).eq("param", 0x01)).copy(ATTR_SPEED, "arg0", 31.0 / 6.0).no_reverse(),
    Trans(Fan6SpeedCmd().act(ATTR_SPEED, 2).act(ATTR_DIR, True), EncCmd(0x01).eq("param", 0x0F)).no_direct(),
    Trans(Fan6SpeedCmd().act(ATTR_SPEED, 4).act(ATTR_DIR, True), EncCmd(0x01).eq("param", 0x10)).no_direct(),
    Trans(Fan6SpeedCmd().act(ATTR_SPEED, 6).act(ATTR_DIR, True), EncCmd(0x01).eq("param", 0x11)).no_direct(),
]

TRANS_REMOTE = [
    TransRemote(LightCmd().act(ATTR_ON, False), EncCmd(0x10).eq("param", 0x10)),
    TransRemote(LightCmd().act(ATTR_ON, True), EncCmd(0x10).eq("param", 0x11)),
    TransRemote(LightCmd().act(ATTR_BR), EncCmd(0x10).eq("param", 0x12)),
    TransRemote(LightCmd().act(ATTR_BR), EncCmd(0x10).eq("param", 0x13)),
    TransRemote(LightCmd().act(ATTR_CT_REV), EncCmd(0x10).eq("param", 0x14)),
    TransRemote(LightCmd().act(ATTR_CT_REV), EncCmd(0x10).eq("param", 0x15)),
    TransRemote(FanCmd().act(ATTR_ON, False), EncCmd(0x10).eq("param", 0x20)),
    TransRemote(FanCmd().act(ATTR_ON, True), EncCmd(0x10).eq("param", 0x21)),
    TransRemote(FanCmd().act(ATTR_DIR), EncCmd(0x10).eq("param", 0x24)),
    TransRemote(Fan8SpeedCmd().act(ATTR_SPEED), EncCmd(0x10).eq("param", 0x22)),
    TransRemote(Fan8SpeedCmd().act(ATTR_SPEED), EncCmd(0x10).eq("param", 0x23)),
    TransRemote(Fan8SpeedCmd().act(ATTR_PRESET).act(ATTR_SPEED), EncCmd(0x10).eq("param", 0x25)),
    TransRemote(Fan8SpeedCmd().act(ATTR_PRESET).act(ATTR_SPEED), EncCmd(0x10).eq("param", 0x26)),
]

TRANS = [*TRANS_APP, *TRANS_REMOTE]

CODECS = [
    MantraEncoder().id("mantra_v0").header([0x4E, 0x6F]).prefix([0x72, 0x0E]).ble(0x1A, 0xFF).add_translators(TRANS),
    MantraEncoder().id("mantra_v0", "ios").header([0x4E, 0x6F]).prefix([0x72, 0x0E]).footer([0x04, 0x03, 0x02, 0x01]).ble(0x1A, 0x05).add_translators(TRANS),
]  # fmt: skip
