"""Smart Elfin App."""

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
    ATTR_PRESET_SLEEP,
    ATTR_SPEED,
    ATTR_STEP,
    ATTR_TIME,
    ATTR_WARM,
)
from .fanlamp import TRANS_FANLAMP_VR2, FanLampEncoderV2
from .models import (
    BleAdvCodec,
    BleAdvConfig,
    BleAdvEncCmd,
    CTLightCmd,
    DeviceCmd,
    Fan6SpeedCmd,
    FanCmd,
    LightCmd,
    Trans,
)
from .models import EncoderMatcher as EncCmd


class SmartElfinEncoder(BleAdvCodec):
    """Smart Elfin encoder."""

    _len = 12
    _tx_max: int = 0xFE
    _tx_step: int = 2
    second_type: int = 0x16
    second_raw: bytes = bytes([0x00] * 8)

    def decrypt(self, buffer: bytes) -> bytes | None:
        """Decrypt / unwhiten an incoming raw buffer into a readable buffer."""
        return buffer

    def encrypt(self, buffer: bytes) -> bytes:
        """Encrypt / whiten a readable buffer."""
        return buffer

    def convert_to_enc(self, decoded: bytes) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        """Convert a readable buffer into an encoder command and a config."""
        conf = BleAdvConfig()
        conf.id = int.from_bytes(decoded[0:3], "little")
        conf.tx_count = decoded[3]
        conf.codec_params = [list(decoded[4:8])]

        enc_cmd = BleAdvEncCmd(decoded[9])
        enc_cmd.param = decoded[8]
        enc_cmd.arg0 = decoded[10]
        enc_cmd.arg1 = decoded[11]

        return enc_cmd, conf

    def convert_from_enc(self, enc_cmd: BleAdvEncCmd, conf: BleAdvConfig) -> bytes:
        """Convert an encoder command and a config into a readable buffer."""
        uid = conf.id.to_bytes(3, "little")
        return bytes([*uid, conf.tx_count, *(conf.codec_params[0]), enc_cmd.param, enc_cmd.cmd, enc_cmd.arg0, enc_cmd.arg1])


TRANS = [
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_PAIR), EncCmd(0xFB).eq("arg0", 0x01).eq("arg1", 0x03)),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_UNPAIR), EncCmd(0xFD).eq("arg0", 0x01).eq("arg1", 0x00)),
    Trans(DeviceCmd().act(ATTR_ON, False), EncCmd(0x01).eq("param", 0x00).eq("arg0", 0x01).eq("arg1", 0x00)).no_direct(),
    Trans(DeviceCmd().act(ATTR_ON, True), EncCmd(0x01).eq("param", 0x00).eq("arg0", 0x01).eq("arg1", 0x01)).no_direct(),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER).eq(ATTR_TIME, 7200), EncCmd(0x09).eq("arg0", 0x02).eq("arg1", 0x00)).no_direct(),
    Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER).eq(ATTR_TIME, 14400), EncCmd(0x09).eq("arg0", 0x02).eq("arg1", 0x01)).no_direct(),
    Trans(LightCmd().act(ATTR_ON, True), EncCmd(0x03).eq("param", 0x0F).eq("arg0", 0x01).eq("arg1", 0x01)),
    Trans(LightCmd().act(ATTR_ON, False), EncCmd(0x03).eq("param", 0x0F).eq("arg0", 0x01).eq("arg1", 0x00)),
    Trans(LightCmd().act(ATTR_ON, ATTR_CMD_TOGGLE), EncCmd(0x03).eq("param", 0x0F).eq("arg0", 0x01).eq("arg1", 0x02)),
    Trans(LightCmd(1).act(ATTR_ON, True), EncCmd(0x06).eq("param", 0x0F).eq("arg0", 0x01).eq("arg1", 0x01)),  # NOT CONFIRMED
    Trans(LightCmd(1).act(ATTR_ON, False), EncCmd(0x06).eq("param", 0x0F).eq("arg0", 0x01).eq("arg1", 0x00)),  # NOT CONFIRMED
    Trans(CTLightCmd().act(ATTR_COLD, 0.1).act(ATTR_WARM, 0.1), EncCmd(0x13).eq("arg0", 0x02).eq("arg1", 5)).no_direct(),
    Trans(CTLightCmd().act(ATTR_COLD, 0.0).act(ATTR_WARM, 1.0), EncCmd(0x13).eq("arg0", 0x02).eq("arg1", 100)).no_direct(),
    Trans(CTLightCmd().act(ATTR_COLD, 1.0).act(ATTR_WARM, 0.0), EncCmd(0x13).eq("arg0", 0x02).eq("arg1", 0)).no_direct(),
    Trans(CTLightCmd().act(ATTR_BR), EncCmd(0x0E).eq("arg0", 0x01)).copy(ATTR_BR, "arg1", 100.0),
    Trans(CTLightCmd().act(ATTR_CT_REV), EncCmd(0x0F).eq("arg0", 0x01)).copy(ATTR_CT_REV, "arg1", 100.0),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_BR_UP).eq(ATTR_STEP, 0.1), EncCmd(0x0C).eq("arg0", 0x01).eq("arg1", 0x01)).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_BR_DOWN).eq(ATTR_STEP, 0.1), EncCmd(0x0C).eq("arg0", 0x01).eq("arg1", 0x02)).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_CT_DOWN).eq(ATTR_STEP, 0.1), EncCmd(0x0D).eq("arg0", 0x01).eq("arg1", 0x01)).no_direct(),
    Trans(CTLightCmd().act(ATTR_CMD, ATTR_CMD_CT_UP).eq(ATTR_STEP, 0.1), EncCmd(0x0D).eq("arg0", 0x01).eq("arg1", 0x02)).no_direct(),
    Trans(FanCmd().act(ATTR_DIR, True), EncCmd(0x04).eq("param", 0x0F).eq("arg0", 0x01).eq("arg1", 0x01)),  # Forward
    Trans(FanCmd().act(ATTR_DIR, False), EncCmd(0x04).eq("param", 0x0F).eq("arg0", 0x01).eq("arg1", 0x02)),  # Reverse
    Trans(FanCmd().act(ATTR_DIR, ATTR_CMD_TOGGLE).act(ATTR_ON, True), EncCmd(0x04).eq("param", 0x0F).eq("arg0", 0x01).eq("arg1", 0x03)).no_direct(),
    Trans(FanCmd().act(ATTR_OSC, True), EncCmd(0x05).eq("param", 0x0F).eq("arg0", 0x01).eq("arg1", 0x01)),
    Trans(FanCmd().act(ATTR_OSC, False), EncCmd(0x05).eq("param", 0x0F).eq("arg0", 0x01).eq("arg1", 0x00)),
    Trans(FanCmd().act(ATTR_OSC, ATTR_CMD_TOGGLE), EncCmd(0x05).eq("param", 0x0F).eq("arg0", 0x01).eq("arg1", 0x02)).no_direct(),
    Trans(FanCmd().act(ATTR_PRESET).eq(ATTR_PRESET, None), EncCmd(0x01).eq("param", 0x0F).eq("arg0", 0x01).eq("arg1", 0x00)).no_direct(),
    Trans(FanCmd().act(ATTR_PRESET, ATTR_PRESET_BREEZE), EncCmd(0x01).eq("param", 0x0F).eq("arg0", 0x01).eq("arg1", 0x01)),
    Trans(FanCmd().act(ATTR_PRESET, ATTR_PRESET_SLEEP), EncCmd(0x01).eq("param", 0x0F).eq("arg0", 0x01).eq("arg1", 0x02)),
    Trans(Fan6SpeedCmd().act(ATTR_ON, False), EncCmd(0x02).eq("arg0", 0x01).eq("arg1", 0x00)),
    Trans(Fan6SpeedCmd().act(ATTR_ON, True).act(ATTR_SPEED), EncCmd(0x02).eq("arg0", 0x01).min("arg1", 10)).copy(ATTR_SPEED, "arg1", 10),
]

CODECS = [
    SmartElfinEncoder().id("smartelfin_v0").header([0x57, 0x46, 0x54, 0x58]).ble(0x02, 0x07).add_translators(TRANS),
    FanLampEncoderV2(0x0000).id("smartelfin_fl_vr0").ble(0x1A, 0x03).add_translators(TRANS_FANLAMP_VR2),
]  # fmt: skip
