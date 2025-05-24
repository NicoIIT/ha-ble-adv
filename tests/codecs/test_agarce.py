"""Agarce Unit Tests."""

# ruff: noqa: S101
import pytest
from ble_adv.codecs.agarce import TRANS, AgarceEncoder
from ble_adv.codecs.const import (
    ATTR_DIR,
    ATTR_ON,
    ATTR_OSC,
    ATTR_PRESET,
    ATTR_PRESET_BREEZE,
    ATTR_SPEED,
    ATTR_SUB_TYPE,
    FAN_TYPE,
    FAN_TYPE_6SPEED,
    LIGHT_TYPE,
    LIGHT_TYPE_CWW,
    LIGHT_TYPE_ONOFF,
)

from . import _TestEncoderBase, _TestEncoderFull


@pytest.mark.parametrize(
    _TestEncoderBase.PARAM_NAMES,
    [
        ("agarce_v4", 0xFF, "F9.09.04.DD.10.45.A5.DC.10.4F.D4.B5.97.77.AA.D4.01.46.E1.53"),  # PAIR
        ("agarce_v4", 0xFF, "F9.09.84.D1.04.4F.B1.C8.1C.43.C0.A1.9B.6A.BE.AC.68.8A.C7.09"),  # LIGHT ON
    ],
)
class TestEncoderAgarce(_TestEncoderBase):
    """Agarce Encoder tests."""


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # PAIR
        (
            "agarce_v4",
            "02.01.1A.15.FF.F9.09.04.67.02.5F.B7.CE.AA.F5.C6.A7.2D.CD.B8.C6.BB.FC.13.9F",
            "cmd: 0x00, param: 0x00, args: [1,0,0]",
            "id: 0x100061C8, index: 17, tx: 146, seed: 0x0267",
            "device_0: ['cmd'] / {'cmd': 'pair'}",
        ),
        # UNPAIR
        (
            "agarce_v4",
            "02.01.1A.15.FF.F9.09.04.8F.0E.B6.BB.C2.42.1D.CA.AB.C5.25.B5.CA.53.14.1F.97",
            "cmd: 0x00, param: 0x00, args: [0,0,0]",
            "id: 0x100061C8, index: 17, tx: 147, seed: 0x0E8F",
            "device_0: ['cmd'] / {'cmd': 'unpair'}",
        ),
        # LIGHT ON
        (
            "agarce_v4",
            "02.01.1A.15.FF.F9.09.84.AE.08.9E.BD.C4.63.3C.CC.AD.E4.15.B2.A0.17.F5.61.29",
            "cmd: 0x10, param: 0x00, args: [1,100,100]",
            "id: 0x100061C8, index: 17, tx: 154, seed: 0x08AE",
            "light_0: ['on'] / {'on': True, 'ctr': 1.0, 'br': 1.0}",
        ),
        # LIGHT OFF
        (
            "agarce_v4",
            "02.01.1A.15.FF.F9.09.84.0B.91.3A.24.5D.C6.99.55.34.41.B0.2A.39.B2.50.F8.11",
            "cmd: 0x10, param: 0x00, args: [0,100,100]",
            "id: 0x100061C8, index: 17, tx: 155, seed: 0x910B",
            "light_0: ['on'] / {'on': False, 'ctr': 1.0, 'br': 1.0}",
        ),
        # BR 1%
        (
            "agarce_v4",
            "02.01.19.15.FF.F9.09.84.75.CE.7E.7B.02.B8.E7.0A.6B.3F.FE.11.03.A8.2E.14.11",
            "cmd: 0x20, param: 0x00, args: [100,1,0]",
            "id: 0x100061C8, index: 17, tx: 161, seed: 0xCE75",
            "light_0: ['ctr', 'br'] / {'sub_type': 'cww', 'ctr': 1.0, 'br': 0.01}",
        ),
        # BR 100%
        (
            "agarce_v4",
            "02.01.19.15.FF.F9.09.84.A4.2D.AA.98.E1.69.36.E9.88.EE.2F.F2.85.79.FF.6D.01",
            "cmd: 0x20, param: 0x00, args: [100,100,0]",
            "id: 0x100061C8, index: 17, tx: 164, seed: 0x2DA4",
            "light_0: ['ctr', 'br'] / {'sub_type': 'cww', 'ctr': 1.0, 'br': 1.0}",
        ),
        # COLD
        (
            "agarce_v4",
            "02.01.19.15.FF.F9.09.84.EB.BD.EB.08.71.26.79.79.18.A1.60.62.15.36.B0.F3.11",
            "cmd: 0x20, param: 0x00, args: [100,100,0]",
            "id: 0x100061C8, index: 17, tx: 170, seed: 0xBDEB",
            "light_0: ['ctr', 'br'] / {'sub_type': 'cww', 'ctr': 1.0, 'br': 1.0}",
        ),
        # WARM
        (
            "agarce_v4",
            "02.01.19.15.FF.F9.09.84.99.19.9C.AC.D5.54.0B.DD.BC.D3.12.A2.B1.44.C2.30.B9",
            "cmd: 0x20, param: 0x00, args: [0,100,0]",
            "id: 0x100061C8, index: 17, tx: 175, seed: 0x1999",
            "light_0: ['ctr', 'br'] / {'sub_type': 'cww', 'ctr': 0.0, 'br': 1.0}",
        ),
        # FAN ON, Speed 1
        (
            "agarce_v4",
            "02.01.1A.15.FF.F9.09.84.7A.06.60.B3.CA.B7.E8.C2.A3.30.51.2C.CA.AE.21.80.AB",
            "cmd: 0x80, param: 0x00, args: [145,0,9]",
            "id: 0x100061C8, index: 17, tx: 176, seed: 0x067A",
            "fan_0: ['speed', 'on'] / {'sub_type': '6speed', 'speed': 1, 'on': True, 'dir': False, 'osc': False, 'preset': None}",
        ),
        # FAN OFF
        (
            "agarce_v4",
            "02.01.1A.15.FF.F9.09.84.6D.88.76.3D.44.A0.FF.4C.2D.27.46.32.44.B8.36.BE.17",
            "cmd: 0x80, param: 0x00, args: [1,0,8]",
            "id: 0x100061C8, index: 17, tx: 177, seed: 0x886D",
            "fan_0: ['on'] / {'sub_type': '6speed', 'speed': 1, 'on': False, 'dir': True, 'osc': False, 'preset': None}",
        ),
        # FAN DIR Reverse
        (
            "agarce_v4",
            "02.01.1A.15.FF.F9.09.84.C1.1D.D8.A8.D1.0C.53.D9.B8.8B.EA.37.D1.1E.9A.A7.7F",
            "cmd: 0x80, param: 0x00, args: [145,0,2]",
            "id: 0x100061C8, index: 17, tx: 179, seed: 0x1DC1",
            "fan_0: ['dir'] / {'sub_type': '6speed', 'speed': 1, 'on': True, 'dir': False, 'osc': False, 'preset': None}",
        ),
        # FAN OSC ON
        (
            "agarce_v4",
            "02.01.19.15.FF.F9.09.84.9B.C7.84.72.0B.56.09.03.62.D1.B0.FD.0A.56.C0.42.8B",
            "cmd: 0x80, param: 0x00, args: [129,1,16]",
            "id: 0x100061C8, index: 17, tx: 181, seed: 0xC79B",
            "fan_0: ['osc'] / {'sub_type': '6speed', 'speed': 1, 'on': True, 'dir': True, 'osc': True, 'preset': None}",
        ),
        # FAN Natural Wind
        (
            "agarce_v4",
            "02.01.1A.15.FF.F9.09.84.F2.16.91.A3.DA.3F.60.D2.B3.B8.D9.0C.DB.2B.A9.FB.05",
            "cmd: 0x80, param: 0x00, args: [161,1,4]",
            "id: 0x100061C8, index: 17, tx: 201, seed: 0x16F2",
            "fan_0: ['preset'] / {'sub_type': '6speed', 'speed': 1, 'on': True, 'dir': True, 'osc': True, 'preset': 'breeze'}",
        ),
    ],
)
class TestEncoderAgarceFull(_TestEncoderFull):
    """Agarce Encoder / Decoder Full tests."""


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # Device ALL OFF
        (
            "agarce_v4",
            "02.01.1A.15.FF.F9.09.84.6A.5E.76.EB.92.A7.F8.9A.FB.20.B1.E4.92.D3.31.1F.DD",
            "cmd: 0x70, param: 0x00, args: [1,0,100]",
            "id: 0x100061C8, index: 17, tx: 182, seed: 0x5E6A",
            "device_0: ['on'] / {'on': False}",
        ),
        (
            "agarce_v4",
            "02.01.19.15.FF.F9.09.84.12.A3.01.16.6F.DF.80.67.06.58.C9.18.6F.AB.49.E0.07",
            "cmd: 0x70, param: 0x00, args: [0,0,100]",
            "id: 0x100061C8, index: 17, tx: 185, seed: 0xA312",
            "device_0: ['on'] / {'on': False}",
        ),
        # DEVICE ALL ON
        (
            "agarce_v4",
            "02.01.1A.15.FF.F9.09.84.D9.F8.C4.4D.34.14.4B.3C.5D.93.02.83.34.60.82.F9.B9",
            "cmd: 0x70, param: 0x00, args: [192,0,100]",
            "id: 0x100061C8, index: 17, tx: 183, seed: 0xF8D9",
            "device_0: ['on'] / {'on': True}",
        ),
        (
            "agarce_v4",
            "02.01.1A.15.FF.F9.09.84.8E.D7.9F.62.1B.43.1C.13.72.C4.55.AD.1B.37.D5.DB.B1",
            "cmd: 0x70, param: 0x00, args: [193,0,100]",
            "id: 0x100061C8, index: 17, tx: 187, seed: 0xD78E",
            "device_0: ['on'] / {'on': True}",
        ),
    ],
)
class TestEncoderAgarceNoReverse(_TestEncoderFull):
    """Agarce Encoder / Decoder No Reverse tests."""

    _with_reverse = False


def test_supported_features() -> None:
    """Test the specific supported features."""
    codec = AgarceEncoder().add_translators(TRANS)
    assert codec.get_supported_features(LIGHT_TYPE) == [{ATTR_ON: {False, True}, ATTR_SUB_TYPE: {LIGHT_TYPE_ONOFF, LIGHT_TYPE_CWW}}]
    assert codec.get_supported_features(FAN_TYPE) == [
        {
            ATTR_SUB_TYPE: {FAN_TYPE_6SPEED},
            ATTR_PRESET: {ATTR_PRESET_BREEZE},
            ATTR_SPEED: {0, 1, 2, 3, 4, 5},
            ATTR_ON: {False, True},
            ATTR_DIR: {False, True},
            ATTR_OSC: {False, True},
        }
    ]
