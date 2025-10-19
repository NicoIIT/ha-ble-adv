"""Mantra Unit Tests."""

import pytest

from . import _TestEncoderBase, _TestEncoderFull


@pytest.mark.parametrize(
    _TestEncoderBase.PARAM_NAMES,
    [
        ("mantra_v0", 0xFF, "4E.6F.72.0E.03.93.06.48.F4.6E.BE.4E.BB.53.0B.70.BB.AD.6C.67"),
        ("mantra_v0/ios", 0x05, "4E.6F.72.0E.05.9C.06.4D.92.0E.D1.3E.F2.8E.3B.65.39.B0.E0.76.04.03.02.01"),
    ],
)
class TestEncoderMantra(_TestEncoderBase):
    """Mantra Encoder tests."""


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # Timer 2H (120min / 7200s)
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.04.36.06.4C.20.A2.67.36.44.8E.C0.CC.39.14.FE.87",
            "cmd: 0x01, param: 0x0A, args: [0,0,0]",
            "id: 0x0000C5F0, index: 0, tx: 1078, seed: 0x0000",
            "device_0: ['cmd'] / {'cmd': 'timer', 's': 120}",
        ),
        # MAIN LIGHT ON
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.04.38.06.4C.2E.56.15.10.D4.2D.EB.8C.15.D3.B5.18",
            "cmd: 0x01, param: 0x05, args: [0,0,0]",
            "id: 0x0000C5F0, index: 0, tx: 1080, seed: 0x0000",
            "light_0: ['on'] / {'on': True}",
        ),
        # MAIN LIGHT OFF
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.04.37.06.4C.21.B1.D9.86.EA.48.4A.C1.88.6F.1F.73",
            "cmd: 0x01, param: 0x06, args: [0,0,0]",
            "id: 0x0000C5F0, index: 0, tx: 1079, seed: 0x0000",
            "light_0: ['on'] / {'on': False}",
        ),
        # BR 10 %
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.04.47.06.4F.56.12.48.B2.6F.51.6E.EC.EF.53.6F.77",
            "cmd: 0x02, param: 0x00, args: [44,1,6,44,255]",
            "id: 0x0000C5F0, index: 0, tx: 1095, seed: 0x0000",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'warm': 0.0, 'cold': 0.17254901960784313, 'br': 0.17254901960784313, 'ctr': 1.0}",
        ),
        # BR 100 %
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.04.4B.06.4F.5A.C1.47.F5.A2.7F.46.64.A7.63.34.01",
            "cmd: 0x02, param: 0x00, args: [255,7,6,255,255]",
            "id: 0x0000C5F0, index: 0, tx: 1099, seed: 0x0000",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'warm': 0.0, 'cold': 1.0, 'br': 1.0, 'ctr': 1.0}",
        ),
        # COLD
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.04.53.06.4F.43.67.59.7A.38.23.16.D2.3B.02.24.ED",
            "cmd: 0x02, param: 0x00, args: [255,7,6,255,255]",
            "id: 0x0000C5F0, index: 0, tx: 1107, seed: 0x0000",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'warm': 0.0, 'cold': 1.0, 'br': 1.0, 'ctr': 1.0}",
        ),
        # WARM
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.04.5A.06.4F.4A.E9.12.4F.E0.D1.5F.4D.01.A0.CA.42",
            "cmd: 0x02, param: 0xFF, args: [0,7,0,255,0]",
            "id: 0x0000C5F0, index: 0, tx: 1114, seed: 0x0000",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'warm': 1.0, 'cold': 0.0, 'br': 1.0, 'ctr': 0.0}",
        ),
        # FAN ON
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.04.5B.06.4C.4B.FA.AC.FF.4E.17.21.40.B7.DB.D4.B6",
            "cmd: 0x01, param: 0x07, args: [0,0,0]",
            "id: 0x0000C5F0, index: 0, tx: 1115, seed: 0x0000",
            "fan_0: ['on'] / {'on': True}",
        ),
        # FAN OFF
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.04.5C.06.4C.4C.80.95.EC.06.46.BC.60.A1.B8.71.79",
            "cmd: 0x01, param: 0x08, args: [0,0,0]",
            "id: 0x0000C5F0, index: 0, tx: 1116, seed: 0x0000",
            "fan_0: ['on'] / {'on': False}",
        ),
        # FAN Direction Reverse
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.04.61.06.4C.72.0C.19.04.51.16.AF.5B.66.31.39.22",
            "cmd: 0x01, param: 0x14, args: [0,0,0]",
            "id: 0x0000C5F0, index: 0, tx: 1121, seed: 0x0000",
            "fan_0: ['dir'] / {'dir': False}",
        ),
        # Fan Sleep mode
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.04.62.06.4C.71.38.DA.D5.A2.5D.3F.4D.B5.BD.1B.3F",
            "cmd: 0x01, param: 0x0E, args: [0,0,0]",
            "id: 0x0000C5F0, index: 0, tx: 1122, seed: 0x0000",
            "fan_0: ['preset'] / {'preset': 'sleep'}",
        ),
    ],
)
class TestEncoderMantraV0Full(_TestEncoderFull):
    """Mantra Encoder / Decoder V0 Full tests."""


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # FAN SPEED 21/30
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.04.60.06.4E.73.1F.A7.B4.FF.D0.3C.40.D7.4A.D8.D6",
            "cmd: 0x03, param: 0x01, args: [22,0,0]",
            "id: 0x0000C5F0, index: 0, tx: 1120, seed: 0x0000",
            "fan_0: ['speed'] / {'speed_count': 31, 'on': True, 'speed': 22.0}",
        ),
    ],
)
class TestEncoderMantraNoReverse(_TestEncoderFull):
    """Mantra Encoder / Decoder No Reverse tests."""

    _with_reverse = False


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # Fan ON
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.13.6A.06.4B.38.77.36.F4.D5.3D.DB.5A.62.D8.93.98",
            "cmd: 0x10, param: 0x21, args: [123,129,0]",
            "id: 0x0000FD56, index: 1, tx: 874, seed: 0x0000",
            "fan_0: ['on'] / {'on': True}",
        ),
        # Fan OFF
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.13.6B.06.4B.39.64.88.44.7B.FB.5C.57.53.A3.72.6C",
            "cmd: 0x10, param: 0x20, args: [123,1,0]",
            "id: 0x0000FD56, index: 1, tx: 875, seed: 0x0000",
            "fan_0: ['on'] / {'on': False}",
        ),
        # Light ON
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.13.6E.06.4B.3C.39.CC.36.6E.27.F3.EC.27.37.14.4A",
            "cmd: 0x10, param: 0x11, args: [251,1,0]",
            "id: 0x0000FD56, index: 1, tx: 878, seed: 0x0000",
            "light_0: ['on'] / {'on': True}",
        ),
        # Light OFF
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.13.6F.06.4B.3D.2A.72.86.C0.E1.74.61.96.4C.F5.BE",
            "cmd: 0x10, param: 0x10, args: [123,1,0]",
            "id: 0x0000FD56, index: 1, tx: 879, seed: 0x0000",
            "light_0: ['on'] / {'on': False}",
        ),
        # K+ / 100%
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.13.70.06.4B.23.F6.55.1A.12.EC.B3.77.1C.4E.40.9D",
            "cmd: 0x10, param: 0x15, args: [251,1,0]",
            "id: 0x0000FD56, index: 1, tx: 880, seed: 0x0000",
            "light_0: ['ctr'] / {'ctr': 1.0}",
        ),
        # K- / 85%
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.13.71.06.4B.22.E5.EB.AA.BC.2A.34.6A.AD.35.A1.69",
            "cmd: 0x10, param: 0x14, args: [235,1,0]",
            "id: 0x0000FD56, index: 1, tx: 881, seed: 0x0000",
            "light_0: ['ctr'] / {'ctr': 0.8571428571428571}",
        ),
        # BR+ / 100%
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.13.72.06.4B.21.D1.28.7B.4F.61.B9.7C.7E.B9.83.74",
            "cmd: 0x10, param: 0x13, args: [235,1,0]",
            "id: 0x0000FD56, index: 1, tx: 882, seed: 0x0000",
            "light_0: ['br'] / {'br': 1.0}",
        ),
        # BR- / 90%
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.13.73.06.4B.20.C2.96.CB.E1.A7.3E.70.CF.C2.62.80",
            "cmd: 0x10, param: 0x12, args: [234,1,0]",
            "id: 0x0000FD56, index: 1, tx: 883, seed: 0x0000",
            "light_0: ['br'] / {'br': 0.9}",
        ),
        # FAN+ / 2
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.13.78.06.4B.2B.6B.A0.9F.64.D8.B5.1A.14.91.4F.39",
            "cmd: 0x10, param: 0x23, args: [251,130,0]",
            "id: 0x0000FD56, index: 1, tx: 888, seed: 0x0000",
            "fan_0: ['speed'] / {'speed_count': 8, 'speed': 2}",
        ),
        # FAN- / 1
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.13.79.06.4B.2A.78.1E.2F.CA.1E.32.17.A6.EA.AE.CD",
            "cmd: 0x10, param: 0x22, args: [251,129,0]",
            "id: 0x0000FD56, index: 1, tx: 889, seed: 0x0000",
            "fan_0: ['speed'] / {'speed_count': 8, 'speed': 1}",
        ),
        # FAN Sleep mode ON
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.13.7A.06.4B.29.4C.DD.FE.39.55.BC.01.65.66.8C.D0",
            "cmd: 0x10, param: 0x26, args: [251,145,0]",
            "id: 0x0000FD56, index: 1, tx: 890, seed: 0x0000",
            "fan_0: ['preset', 'speed'] / {'speed_count': 8, 'speed': 1, 'preset': 'sleep'}",
        ),
        # FAN Sleep mode OFF
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.13.7B.06.4B.28.5F.63.4E.97.93.3A.0C.C4.1D.6D.24",
            "cmd: 0x10, param: 0x26, args: [251,129,0]",
            "id: 0x0000FD56, index: 1, tx: 891, seed: 0x0000",
            "fan_0: ['preset', 'speed'] / {'speed_count': 8, 'speed': 1, 'preset': None}",
        ),
        # FAN Breeze mode ON
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.13.1A.06.4B.4F.D4.A7.C0.50.24.FD.DB.24.E2.CF.63",
            "cmd: 0x10, param: 0x25, args: [251,161,0]",
            "id: 0x0000FD56, index: 1, tx: 794, seed: 0x0000",
            "fan_0: ['preset', 'speed'] / {'speed_count': 8, 'speed': 1, 'preset': 'breeze'}",
        ),
        # FAN Breeze mode OFF
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.13.19.06.4B.4C.E0.64.11.A3.6F.77.CD.D7.6E.ED.7E",
            "cmd: 0x10, param: 0x25, args: [251,129,0]",
            "id: 0x0000FD56, index: 1, tx: 793, seed: 0x0000",
            "fan_0: ['preset', 'speed'] / {'speed_count': 8, 'speed': 1, 'preset': None}",
        ),
        # FAN DIR Forward
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.13.1C.06.4B.49.BD.20.63.B6.B3.E8.F6.A3.FA.8B.58",
            "cmd: 0x10, param: 0x24, args: [251,129,0]",
            "id: 0x0000FD56, index: 1, tx: 796, seed: 0x0000",
            "fan_0: ['dir'] / {'dir': True}",
        ),
        # FAN DIR Reverse
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.13.1B.06.4B.4E.C7.19.70.FE.E2.7A.D6.F5.99.2E.97",
            "cmd: 0x10, param: 0x24, args: [251,193,0]",
            "id: 0x0000FD56, index: 1, tx: 795, seed: 0x0000",
            "fan_0: ['dir'] / {'dir': False}",
        ),
    ],
)
class TestEncoderMantraV0Remote(_TestEncoderFull):
    """Mantra Encoder / Decoder V0 Remote tests."""

    _with_reverse = False


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # Light ON
        (
            "mantra_v1",
            "02011A15FF4E6F720F050E064D08CD1F02C525577DF1E82471",
            "cmd: 0x01, param: 0x01, args: [0,0,0]",
            "id: 0x0000C051, index: 0, tx: 1294, seed: 0x0000",
            "light_0: ['on'] / {'on': True}",
        ),
        # Light OFF
        (
            "mantra_v1",
            "02011A15FF4E6F720F050F064D09DEA1B26BE3D2704093C585",
            "cmd: 0x01, param: 0x02, args: [0,0,0]",
            "id: 0x0000C051, index: 0, tx: 1295, seed: 0x0000",
            "light_0: ['on'] / {'on': False}",
        ),
        # FULL COLD, BR 100%
        (
            "mantra_v1",
            "02011A15FF4E6F720F0528064E2CD34EB4FB6283197E8AA124",
            "cmd: 0x02, param: 0x00, args: [255,7,6,255,255]",
            "id: 0x0000C051, index: 0, tx: 1320, seed: 0x0000",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'warm': 0.0, 'cold': 1.0, 'br': 1.0, 'ctr': 1.0}",
        ),
        # FULL WARM, BR 100%
        (
            "mantra_v1",
            "02011A15FF4E6F720F0523064E277A78E07E1DC69D26DF8C62",
            "cmd: 0x02, param: 0xFF, args: [0,7,0,255,0]",
            "id: 0x0000C051, index: 0, tx: 1315, seed: 0x0000",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'warm': 1.0, 'cold': 0.0, 'br': 1.0, 'ctr': 0.0}",
        ),
        # FULL WARM, BR 1%
        (
            "mantra_v1",
            "02011A15FF4E6F720F053C064E39A65F7CAC10FB1CABDBD1BE",
            "cmd: 0x02, param: 0x00, args: [23,0,6,23,255]",
            "id: 0x0000C051, index: 0, tx: 1340, seed: 0x0000",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'warm': 0.0, 'cold': 0.09019607843137255, 'br': 0.09019607843137255, 'ctr': 1.0}",
        ),
    ],
)
class TestEncoderMantraV1Full(_TestEncoderFull):
    """Mantra Encoder / Decoder V1 Full tests."""


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # BR+
        (
            "mantra_v1",
            "02011A15FF4E6F720F040C064C1954D2CD5E2E52D7E8FE1313",
            "cmd: 0x01, param: 0x05, args: [0,0,0]",
            "id: 0x0000C051, index: 0, tx: 1036, seed: 0x0000",
            "light_0: ['cmd'] / {'sub_type': 'cww', 'cmd': 'B+', 'step': 0.14285714285714285}",
        ),
        # BR-
        (
            "mantra_v1",
            "02011A15FF4E6F720F03FE064B9F367587B46B59033266B9F5",
            "cmd: 0x01, param: 0x06, args: [0,0,0]",
            "id: 0x0000C051, index: 0, tx: 1022, seed: 0x0000",
            "light_0: ['cmd'] / {'sub_type': 'cww', 'cmd': 'B-', 'step': 0.14285714285714285}",
        ),
        # K+
        (
            "mantra_v1",
            "02011A15FF4E6F720F02CE064ABFC4F8364655F0DF71456CA7",
            "cmd: 0x01, param: 0x03, args: [0,0,0]",
            "id: 0x0000C051, index: 0, tx: 718, seed: 0x0000",
            "light_0: ['cmd'] / {'sub_type': 'cww', 'cmd': 'K+', 'step': 0.16666666666666666}",
        ),
        # K-
        (
            "mantra_v1",
            "02011A15FF4E6F720F02B0064AC6931B2453EFF19E3BB87BC3",
            "cmd: 0x01, param: 0x04, args: [0,0,0]",
            "id: 0x0000C051, index: 0, tx: 688, seed: 0x0000",
            "light_0: ['cmd'] / {'sub_type': 'cww', 'cmd': 'K-', 'step': 0.16666666666666666}",
        ),
        # BR 30%
        (
            "mantra_v1",
            "02011A15FF4E6F720F0214064A69756FA4536626C66CDB38C5",
            "cmd: 0x01, param: 0x0C, args: [0,0,0]",
            "id: 0x0000C051, index: 0, tx: 532, seed: 0x0000",
            "light_0: ['br'] / {'br': 0.3}",
        ),
        # BR 50%
        (
            "mantra_v1",
            "02011A15FF4E6F720F0222064A5C50D51881499886F3015D27",
            "cmd: 0x01, param: 0x07, args: [0,0,0]",
            "id: 0x0000C051, index: 0, tx: 546, seed: 0x0000",
            "light_0: ['br'] / {'br': 0.5}",
        ),
        # BR 70%
        (
            "mantra_v1",
            "02011A15FF4E6F720F023F064A40AB8FE50EC9590B1BF42BED",
            "cmd: 0x01, param: 0x08, args: [0,0,0]",
            "id: 0x0000C051, index: 0, tx: 575, seed: 0x0000",
            "light_0: ['br'] / {'br': 0.7}",
        ),
        # BR 100%
        (
            "mantra_v1",
            "02011A15FF4E6F720F026A064A10228CB646DC258726262FA1",
            "cmd: 0x01, param: 0x09, args: [0,0,0]",
            "id: 0x0000C051, index: 0, tx: 618, seed: 0x0000",
            "light_0: ['br'] / {'br': 1.0}",
        ),
    ],
)
class TestEncoderMantraV1Remote(_TestEncoderFull):
    """Mantra Encoder / Decoder V1 Remote tests."""

    _with_reverse = False
