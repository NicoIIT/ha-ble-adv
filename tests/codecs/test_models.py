"""Models Unit Tests."""

# ruff: noqa: S101
from copy import copy

from ble_adv.codecs.const import (
    ATTR_BLUE,
    ATTR_BLUE_F,
    ATTR_BR,
    ATTR_CMD,
    ATTR_CMD_PAIR,
    ATTR_CMD_TIMER,
    ATTR_COLD,
    ATTR_CT,
    ATTR_DIR,
    ATTR_GREEN,
    ATTR_GREEN_F,
    ATTR_ON,
    ATTR_OSC,
    ATTR_PRESET,
    ATTR_PRESET_BREEZE,
    ATTR_PRESET_SLEEP,
    ATTR_RED,
    ATTR_RED_F,
    ATTR_SPEED,
    ATTR_SUB_TYPE,
    ATTR_TIME,
    ATTR_WARM,
    DEVICE_TYPE,
    FAN_TYPE,
    FAN_TYPE_3SPEED,
    FAN_TYPE_6SPEED,
    LIGHT_TYPE,
    LIGHT_TYPE_CWW,
    LIGHT_TYPE_ONOFF,
    LIGHT_TYPE_RGB,
)
from ble_adv.codecs.models import (
    BleAdvAdvertisement,
    BleAdvCodec,
    BleAdvConfig,
    BleAdvEncCmd,
    BleAdvEntAttr,
    CTLightCmd,
    DeviceCmd,
    EncoderMatcher,
    EntityMatcher,
    Fan3SpeedCmd,
    Fan6SpeedCmd,
    FanCmd,
    LightCmd,
    RGBLightCmd,
    Trans,
    as_hex,
)

from . import _from_dotted

EncCmd = EncoderMatcher


def test_adv() -> None:
    """Test BleAAdvdvertisement."""
    raw_msg = "F0.08.10.80.33.BC.2E.B0.49.EA.58.76.C0.1D.99.5E.9C.D6.B8.0E.6E.14.2B.A5.30.A9"
    raw_with_ble = "1B.16." + raw_msg
    adv_str = _from_dotted("02.01.19." + raw_with_ble)
    adv = BleAdvAdvertisement.FromRaw(adv_str)
    assert adv is not None, "Adv is not None"
    assert as_hex(adv.raw) == raw_msg
    assert adv.ble_type == 0x16
    assert adv.to_raw() == _from_dotted(raw_with_ble)
    assert repr(adv) == "Type: 0x16, raw: " + raw_msg
    assert adv == BleAdvAdvertisement(0x16, _from_dotted(raw_msg))
    adv.ad_flag = 0x19
    adv = BleAdvAdvertisement.FromRaw(_from_dotted(raw_msg))
    assert adv is None


def test_enc_cmd() -> None:
    """Test BleAdvEncCmd."""
    enc_cmd = BleAdvEncCmd(0x10)
    enc_cmd.param = 0x11
    enc_cmd.arg0 = 0x12
    enc_cmd.arg1 = 0x13
    enc_cmd.arg2 = 0x14
    assert repr(enc_cmd) == "cmd: 0x10, param: 0x11, args: [18,19,20]"


def test_ent_attr() -> None:
    """Test BleAdvEntAttr."""
    attrs = {ATTR_ON: True, ATTR_SPEED: 6, ATTR_DIR: True, ATTR_OSC: False}
    ent_attr = BleAdvEntAttr([ATTR_ON, ATTR_SPEED], attrs, FAN_TYPE, 0)
    assert repr(ent_attr) == "fan_0: ['on', 'speed'] / {'on': True, 'speed': 6, 'dir': True, 'osc': False}"
    assert ent_attr.attrs == attrs
    assert ent_attr.id == (FAN_TYPE, 0)
    assert ent_attr.get_attr_as_float(ATTR_SPEED) == 6.0


def test_config() -> None:
    """Test BleAdvConfig."""
    conf = BleAdvConfig(12, 1)
    conf.seed = 0x12
    conf.tx_count = 2
    assert repr(conf) == "id: 0x0000000C, index: 1, tx: 2, seed: 0x0012"


def test_entity_matcher() -> None:
    """Test EntityMatcher."""
    matcher = EntityMatcher(LIGHT_TYPE, 0, LIGHT_TYPE_CWW, False)
    matcher.min(ATTR_CT, 0.5)
    matcher.max(ATTR_BR, 0.5)
    assert repr(matcher) == "light_0 / []"
    matcher.act(ATTR_ON, True)
    assert repr(matcher) == "light_0 / ['on']"
    assert matcher.create() == BleAdvEntAttr([ATTR_ON], {ATTR_ON: True}, LIGHT_TYPE, 0)
    assert matcher.get_supported_features() == (LIGHT_TYPE, 0, {ATTR_ON: True, ATTR_SUB_TYPE: LIGHT_TYPE_CWW})
    assert matcher.matches(BleAdvEntAttr([ATTR_ON], {ATTR_ON: True, ATTR_CT: 0.8, ATTR_BR: 0.2}, LIGHT_TYPE, 0))
    assert not matcher.matches(BleAdvEntAttr([ATTR_ON], {ATTR_ON: True, ATTR_CT: 0.2, ATTR_BR: 0.2}, LIGHT_TYPE, 0))
    assert not matcher.matches(BleAdvEntAttr([ATTR_ON], {ATTR_ON: True, ATTR_CT: 0.8, ATTR_BR: 0.2}, LIGHT_TYPE, 1))
    assert not matcher.matches(BleAdvEntAttr([ATTR_CT], {ATTR_ON: True, ATTR_CT: 0.8, ATTR_BR: 0.2}, LIGHT_TYPE, 0))


ent_fan3 = BleAdvEntAttr([ATTR_ON], {ATTR_SUB_TYPE: FAN_TYPE_3SPEED, ATTR_ON: True, ATTR_SPEED: 3, ATTR_DIR: True, ATTR_OSC: False}, FAN_TYPE, 0)
ent_fan6 = BleAdvEntAttr([ATTR_ON], {ATTR_SUB_TYPE: FAN_TYPE_6SPEED, ATTR_ON: True, ATTR_SPEED: 6, ATTR_DIR: True, ATTR_OSC: False}, FAN_TYPE, 0)
ent_light_binary = BleAdvEntAttr([ATTR_ON], {ATTR_SUB_TYPE: LIGHT_TYPE_ONOFF, ATTR_ON: True}, LIGHT_TYPE, 0)
ent_light_cww = BleAdvEntAttr([ATTR_ON], {ATTR_SUB_TYPE: LIGHT_TYPE_CWW, ATTR_ON: True, ATTR_CT: 1.0, ATTR_BR: 1.0}, LIGHT_TYPE, 0)
ent_light_rgb = BleAdvEntAttr(
    [ATTR_ON], {ATTR_SUB_TYPE: LIGHT_TYPE_RGB, ATTR_ON: True, ATTR_RED: 1.0, ATTR_GREEN: 1.0, ATTR_BLUE: 1.0}, LIGHT_TYPE, 0
)
ent_device = BleAdvEntAttr([ATTR_CMD], {ATTR_CMD: ATTR_CMD_PAIR}, DEVICE_TYPE, 0)


def test_fan_entity_matchers() -> None:
    """Test the Fan EntityMatcher."""
    assert FanCmd().act(ATTR_ON, True).matches(ent_fan3)
    assert FanCmd().act(ATTR_ON, True).matches(ent_fan6)
    assert not FanCmd(1).act(ATTR_ON, True).matches(ent_fan3)
    assert Fan3SpeedCmd().act(ATTR_ON, True).matches(ent_fan3)
    assert Fan6SpeedCmd().act(ATTR_ON, True).matches(ent_fan6)
    assert not Fan3SpeedCmd().act(ATTR_ON, True).matches(ent_fan6)
    assert not Fan6SpeedCmd().act(ATTR_ON, True).matches(ent_fan3)
    assert not FanCmd().act(ATTR_ON, True).matches(ent_light_binary)


def test_light_entity_matchers() -> None:
    """Test the Light EntityMatcher."""
    assert not LightCmd().act(ATTR_ON, True).matches(ent_fan3)
    assert not LightCmd(1).act(ATTR_ON, True).matches(ent_light_binary)
    assert LightCmd().act(ATTR_ON, True).matches(ent_light_binary)
    assert LightCmd().act(ATTR_ON, True).matches(ent_light_cww)
    assert LightCmd().act(ATTR_ON, True).matches(ent_light_rgb)
    assert not RGBLightCmd().act(ATTR_ON, True).matches(ent_light_binary)
    assert not RGBLightCmd().act(ATTR_ON, True).matches(ent_light_cww)
    assert LightCmd().act(ATTR_ON, True).matches(ent_light_rgb)
    assert not CTLightCmd().act(ATTR_ON, True).matches(ent_light_binary)
    assert CTLightCmd().act(ATTR_ON, True).matches(ent_light_cww)
    assert not CTLightCmd().act(ATTR_ON, True).matches(ent_light_rgb)


def test_device_entity_matchers() -> None:
    """Test the Device EntityMatcher."""
    assert not DeviceCmd().act(ATTR_CMD, ATTR_CMD_PAIR).matches(ent_fan3)
    assert DeviceCmd().act(ATTR_CMD, ATTR_CMD_PAIR).matches(ent_device)


def test_encoder_matcher() -> None:
    """Test EncderMatcher."""
    matcher = EncoderMatcher(0x10)
    assert matcher.create() == BleAdvEncCmd(0x10)
    assert not matcher.matches(BleAdvEncCmd(0x20))
    enc_cmd = BleAdvEncCmd(0x10)
    enc_cmd.param = 1
    matcher.eq("param", 0)
    assert not matcher.matches(enc_cmd)
    matcher.eq("param", 1)
    assert matcher.matches(enc_cmd)
    assert matcher.create() == enc_cmd


def test_trans() -> None:
    """Test Trans."""
    tr = Trans(LightCmd().act(ATTR_ON, True), EncCmd(0x10)).copy(ATTR_BR, "arg0", 255.0)
    tr_nr = copy(tr).no_reverse()
    tr_nd = copy(tr).no_direct()
    assert repr(tr) == "light_0 / ['on'] / cmd: 0x10 / [('br', 'arg0', 255.0)]"
    assert tr.matches_enc(BleAdvEncCmd(0x10))
    assert tr_nd.matches_enc(BleAdvEncCmd(0x10))
    assert not tr_nr.matches_enc(BleAdvEncCmd(0x10))
    assert not tr.matches_enc(BleAdvEncCmd(0x11))
    assert tr.matches_ent(ent_light_binary)
    assert not tr_nd.matches_ent(ent_light_binary)
    assert tr_nr.matches_ent(ent_light_binary)
    assert not tr.matches_ent(ent_fan3)
    enc_cmd = BleAdvEncCmd(0x10)
    enc_cmd.arg0 = 255
    assert tr.ent_to_enc(ent_light_cww) == enc_cmd
    assert tr.enc_to_ent(enc_cmd) == BleAdvEntAttr([ATTR_ON], {ATTR_ON: True, ATTR_BR: 1.0}, LIGHT_TYPE, 0)


def test_trans_sv() -> None:
    """Test Trans Split Value Option."""

    def enc_cmd(a: int, b: int, c: int) -> BleAdvEncCmd:
        enc_cmd = BleAdvEncCmd(0x51)
        enc_cmd.arg0 = a
        enc_cmd.arg1 = b
        enc_cmd.arg2 = c
        return enc_cmd

    def ent_attr(time: int) -> BleAdvEntAttr:
        return BleAdvEntAttr([ATTR_CMD], {ATTR_CMD: ATTR_CMD_TIMER, ATTR_TIME: time}, DEVICE_TYPE, 0)

    tr = Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER), EncCmd(0x51)).split_copy(ATTR_TIME, ["arg0"], 1.0, 256)
    tr_all = Trans(DeviceCmd().act(ATTR_CMD, ATTR_CMD_TIMER), EncCmd(0x51)).split_copy(ATTR_TIME, ["arg0", "arg1", "arg2"], 2, 256)
    assert tr.ent_to_enc(ent_attr(50)) == enc_cmd(50, 0, 0)
    assert tr.enc_to_ent(enc_cmd(50, 0, 0)) == ent_attr(50)
    assert tr.ent_to_enc(ent_attr(500)) == enc_cmd(244, 0, 0)  ### Hum... may need to be changed...
    assert tr_all.ent_to_enc(ent_attr(50)) == enc_cmd(100, 0, 0)
    assert tr_all.enc_to_ent(enc_cmd(100, 0, 0)) == ent_attr(50)
    assert tr_all.ent_to_enc(ent_attr(72 + 256 * (12 + 256 * 52))) == enc_cmd(2 * 72, 2 * 12, 2 * 52)
    assert tr_all.enc_to_ent(enc_cmd(2 * 72, 2 * 12, 2 * 52)) == ent_attr(72 + 256 * (12 + 256 * 52))


class _TestCodec(BleAdvCodec):
    def __init__(self) -> None:
        super().__init__()
        self._debug_mode = True
        self._len = 4

    def decrypt(self, buffer: bytes) -> bytes | None:
        return buffer

    def encrypt(self, decoded: bytes) -> bytes:
        return decoded

    def convert_to_enc(self, _: bytes) -> tuple[BleAdvEncCmd | None, BleAdvConfig | None]:
        return BleAdvEncCmd(0x10), BleAdvConfig()

    def convert_from_enc(self, _: BleAdvEncCmd, __: BleAdvConfig) -> bytes:
        return b"test"


def test_codec() -> None:
    """Test BleAdvCodec."""
    codec = _TestCodec().id("test_codec").ble(0x19, 0x16).header([0x55, 0x56])
    codec.add_translators(
        [
            Trans(LightCmd(1).act(ATTR_ON, True), EncCmd(0x12)),
            Trans(LightCmd(1).act(ATTR_ON, False), EncCmd(0x13)),
            Trans(FanCmd().act(ATTR_PRESET, ATTR_PRESET_BREEZE), EncCmd(0x33).eq("arg0", 2)),
            Trans(FanCmd().act(ATTR_PRESET, ATTR_PRESET_SLEEP), EncCmd(0x33).eq("arg0", 1)),
        ]
    )
    assert codec.codec_id == "test_codec"
    assert codec._ble_type == 0x16  # noqa: SLF001
    assert codec._header == bytearray([0x55, 0x56])  # noqa: SLF001
    assert codec.get_supported_features(LIGHT_TYPE) == [{}, {ATTR_ON: {False, True}, ATTR_SUB_TYPE: {LIGHT_TYPE_ONOFF}}]
    assert codec.get_supported_features(FAN_TYPE) == [{ATTR_PRESET: {ATTR_PRESET_BREEZE, ATTR_PRESET_SLEEP}}]
    codec.add_translators(
        [
            Trans(LightCmd().act(ATTR_ON, True), EncCmd(0x10)),
            Trans(LightCmd().act(ATTR_ON, False), EncCmd(0x11)),
        ]
    )
    assert codec.get_supported_features(LIGHT_TYPE) == [
        {ATTR_ON: {False, True}, ATTR_SUB_TYPE: {LIGHT_TYPE_ONOFF}},
        {ATTR_ON: {False, True}, ATTR_SUB_TYPE: {LIGHT_TYPE_ONOFF}},
    ]
    codec.add_translators(
        [
            Trans(CTLightCmd().act(ATTR_COLD).act(ATTR_WARM), EncCmd(0x21).eq("param", 0)).copy(ATTR_COLD, "arg0", 255).copy(ATTR_WARM, "arg1", 255),
            Trans(RGBLightCmd().act(ATTR_RED_F).act(ATTR_GREEN_F).act(ATTR_BLUE_F), EncCmd(0x22))
            .copy(ATTR_RED_F, "arg0", 255)
            .copy(ATTR_GREEN_F, "arg1", 255)
            .copy(ATTR_BLUE_F, "arg2", 255),
        ]
    )
    assert codec.get_supported_features(LIGHT_TYPE) == [
        {ATTR_ON: {False, True}, ATTR_SUB_TYPE: {LIGHT_TYPE_ONOFF, LIGHT_TYPE_CWW, LIGHT_TYPE_RGB}},
        {ATTR_ON: {False, True}, ATTR_SUB_TYPE: {LIGHT_TYPE_ONOFF}},
    ]
    assert repr(codec.encode_adv(BleAdvEncCmd(0x10), BleAdvConfig())) == "Type: 0x16, raw: 55.56.74.65.73.74"
    assert codec.decode_adv(BleAdvAdvertisement(0x16, _from_dotted("55.56.74.65.73.74"))) == (BleAdvEncCmd(0x10), BleAdvConfig())
    assert codec.decode_adv(BleAdvAdvertisement(0x16, _from_dotted("00.00.74.65.73.74"))) == (None, None)
    assert codec.decode_adv(BleAdvAdvertisement(0x00, _from_dotted("55.56.74.65.73.74"))) == (None, None)
    assert codec.ent_to_enc(ent_light_binary) == [BleAdvEncCmd(0x10)]
    assert codec.enc_to_ent(BleAdvEncCmd(0x10)) == [BleAdvEntAttr([ATTR_ON], {ATTR_ON: True}, LIGHT_TYPE, 0)]
