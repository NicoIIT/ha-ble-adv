"""RuiXin Unit Tests."""

import pytest

from . import _TestEncoderBase, _TestEncoderFull


@pytest.mark.parametrize(
    _TestEncoderBase.PARAM_NAMES,
    [
        ("ruixin_v0", 0xFF, "FFFF010203046972360E2434E97E2837D2292A2B2C2D2E2F300B"),  # PAIR
        ("ruixin_v0/r1", 0xFF, "00000052584B6972360EABAB1DBEADADC0B0B1B2BABCBEC6C885131415"),  # ALL OFF
    ],
)
class TestEncoderRuiXin(_TestEncoderBase):
    """Remote Encoder tests."""


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # PAIR
        (
            "ruixin_v0",
            "1B.FF.FF.FF.01.02.03.04.69.72.36.0E.24.34.E9.7E.28.37.D2.29.2A.2B.2C.2D.2E.2F.30.0B",
            "cmd: 0xAA, param: 0x00, args: [0,0,0]",
            "id: 0x100259C5, index: 0, tx: 0, seed: 0x3424",
            "device_0: ['cmd'] / {'cmd': 'pair'}",
        ),
        # MAIN LIGHT ON
        (
            "ruixin_v0",
            "1B.FF.FF.FF.01.02.03.04.69.72.36.0E.89.67.4E.E3.8E.9C.8E.8E.8F.90.91.92.93.94.95.C8",
            "cmd: 0x01, param: 0x00, args: [0,0,0]",
            "id: 0x100359C5, index: 0, tx: 0, seed: 0x6789",
            "light_0: ['on'] / {'on': True}",
        ),
        # MAIN LIGHT OFF
        (
            "ruixin_v0",
            "1B.FF.FF.FF.01.02.03.04.69.72.36.0E.2E.64.F3.88.33.41.34.33.34.35.36.37.38.39.3A.6E",
            "cmd: 0x02, param: 0x00, args: [0,0,0]",
            "id: 0x100359C5, index: 0, tx: 0, seed: 0x642E",
            "light_0: ['on'] / {'on': False}",
        ),
        # BR 60 %
        (
            "ruixin_v0",
            "1B.FF.FF.FF.01.02.03.04.69.72.36.0E.21.50.E6.7B.25.34.31.BC.27.28.29.2A.2B.2C.2D.00",
            "cmd: 0x0C, param: 0x00, args: [150,0,0]",
            "id: 0x100259C5, index: 0, tx: 0, seed: 0x5021",
            "light_0: ['br'] / {'sub_type': 'cww', 'br': 0.6}",
        ),
        # BR 100 %
        (
            "ruixin_v0",
            "1B.FF.FF.FF.01.02.03.04.69.72.36.0E.A6.5C.6B.00.AA.B9.B6.A5.AC.AD.AE.AF.B0.B1.B2.E9",
            "cmd: 0x0C, param: 0x00, args: [250,0,0]",
            "id: 0x100259C5, index: 0, tx: 0, seed: 0x5CA6",
            "light_0: ['br'] / {'sub_type': 'cww', 'br': 1.0}",
        ),
        # WARM 100%
        (
            "ruixin_v0",
            "1B.FF.FF.FF.01.02.03.04.69.72.36.0E.30.60.F5.8A.34.43.41.2F.36.37.38.39.3A.3B.3C.74",
            "cmd: 0x0D, param: 0x00, args: [250,0,0]",
            "id: 0x100259C5, index: 0, tx: 0, seed: 0x6030",
            "light_0: ['ct'] / {'sub_type': 'cww', 'ct': 1.0}",
        ),
        # WARM 50%
        (
            "ruixin_v0",
            "1B.FF.FF.FF.01.02.03.04.69.72.36.0E.AD.3C.72.07.B1.C0.BE.31.B3.B4.B5.B6.B7.B8.B9.76",
            "cmd: 0x0D, param: 0x00, args: [127,0,0]",
            "id: 0x100259C5, index: 0, tx: 0, seed: 0x3CAD",
            "light_0: ['ct'] / {'sub_type': 'cww', 'ct': 0.508}",
        ),
        # FAN SPEED 10%
        (
            "ruixin_v0",
            "1B.FF.FF.FF.01.02.03.04.69.72.36.0E.9D.32.62.F7.A1.B0.B1.AC.A3.A4.A5.A6.A7.A8.A9.F4",
            "cmd: 0x10, param: 0x00, args: [10,0,0]",
            "id: 0x100259C5, index: 0, tx: 0, seed: 0x329D",
            "fan_0: ['on', 'speed'] / {'sub_type': '100speed', 'on': True, 'speed': 10.0}",
        ),
        # FAN OFF
        (
            "ruixin_v0",
            "1B.FF.FF.FF.01.02.03.04.69.72.36.0E.7E.35.43.D8.82.91.86.83.84.85.86.87.88.89.8A.BF",
            "cmd: 0x04, param: 0x00, args: [0,0,0]",
            "id: 0x100259C5, index: 0, tx: 0, seed: 0x357E",
            "fan_0: ['on'] / {'on': False}",
        ),
        # FAN Direction Reverse
        (
            "ruixin_v0",
            "1B.FF.FF.FF.01.02.03.04.69.72.36.0E.B4.75.79.0E.B9.C7.BD.B9.BA.BB.BC.BD.BE.BF.C0.F7",
            "cmd: 0x05, param: 0x00, args: [0,0,0]",
            "id: 0x100359C5, index: 0, tx: 0, seed: 0x75B4",
            "fan_0: ['dir'] / {'dir': False}",
        ),
        # FAN Direction Forward
        (
            "ruixin_v0",
            "1B.FF.FF.FF.01.02.03.04.69.72.36.0E.CC.76.91.26.D1.DF.D6.D1.D2.D3.D4.D5.D6.D7.D8.10",
            "cmd: 0x06, param: 0x00, args: [0,0,0]",
            "id: 0x100359C5, index: 0, tx: 0, seed: 0x76CC",
            "fan_0: ['dir'] / {'dir': True}",
        ),
    ],
)
class TestEncoderRuiXinFull(_TestEncoderFull):
    """RuiXin Encoder / Decoder Full tests."""


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # Button ALL OFF
        (
            "ruixin_v0/r1",
            "1E.FF.00.00.00.52.58.4B.69.72.36.0E.AB.AB.1D.BE.AD.AD.C0.B0.B1.B2.BA.BC.BE.C6.C8.85.13.14.15",
            "cmd: 0x11, param: 0x00, args: [0,0,0]",
            "id: 0xFF001272, index: 0, tx: 0, seed: 0xABAB",
            "device_0: ['on'] / {'on': False}",
        ),
        # Button Light Toggle
        (
            "ruixin_v0/r1",
            "1E.FF.00.00.00.52.58.4B.69.72.36.0E.94.94.06.A7.96.96.B9.99.9A.9B.A3.A5.A7.AF.B1.7E.13.14.15",
            "cmd: 0x21, param: 0x00, args: [0,0,0]",
            "id: 0xFF001272, index: 0, tx: 0, seed: 0x9494",
            "light_0: ['cmd'] / {'cmd': 'toggle'}",
        ),
        # Button FAN ON
        (
            "ruixin_v0",
            "1B.FF.FF.FF.01.02.03.04.69.72.36.0E.1E.38.E3.78.22.31.25.23.24.25.26.27.28.29.2A.5E",
            "cmd: 0x03, param: 0x00, args: [0,0,0]",
            "id: 0x100259C5, index: 0, tx: 0, seed: 0x381E",
            "fan_0: ['on'] / {'on': True}",
        ),
        # Button Switch COLD
        (
            "ruixin_v0",
            "1B.FF.FF.FF.01.02.03.04.69.72.36.0E.3A.4D.FF.94.3E.4D.45.3F.40.41.42.43.44.45.46.7E",
            "cmd: 0x07, param: 0x00, args: [0,0,0]",
            "id: 0x100259C5, index: 0, tx: 0, seed: 0x4D3A",
            "light_0: ['br', 'ct'] / {'sub_type': 'cww', 'br': 1.0, 'ct': 0.0}",
        ),
        # Button Switch WARM
        (
            "ruixin_v0",
            "1B.FF.FF.FF.01.02.03.04.69.72.36.0E.3A.4E.FF.94.3E.4D.47.3F.40.41.42.43.44.45.46.80",
            "cmd: 0x09, param: 0x00, args: [0,0,0]",
            "id: 0x100259C5, index: 0, tx: 0, seed: 0x4E3A",
            "light_0: ['br', 'ct'] / {'sub_type': 'cww', 'br': 1.0, 'ct': 1.0}",
        ),
        # Button Switch NATURAL
        (
            "ruixin_v0",
            "1B.FF.FF.FF.01.02.03.04.69.72.36.0E.E8.4B.AD.42.EC.FB.F4.ED.EE.EF.F0.F1.F2.F3.F4.2D",
            "cmd: 0x08, param: 0x00, args: [0,0,0]",
            "id: 0x100259C5, index: 0, tx: 0, seed: 0x4BE8",
            "light_0: ['br', 'ct'] / {'sub_type': 'cww', 'br': 0.5, 'ct': 0.5}",
        ),
        # Button K+ (Colder -> K- ...)
        (
            "ruixin_v0/r1",
            "1E.FF.00.00.00.52.58.4B.69.72.36.0E.74.74.E6.87.76.76.A0.79.7A.7B.83.85.87.8F.91.65.13.14.15",
            "cmd: 0x28, param: 0x00, args: [0,0,0]",
            "id: 0xFF001272, index: 0, tx: 0, seed: 0x7474",
            "light_0: ['cmd', 'step'] / {'sub_type': 'cww', 'cmd': 'K-', 'step': 0.08333333333333333}",
        ),
        # Button K- (Warmer -> K+ ...)
        (
            "ruixin_v0/r1",
            "1E.FF.00.00.00.52.58.4B.69.72.36.0E.6A.6A.DC.7D.6C.6C.95.6F.70.71.79.7B.7D.85.87.5A.13.14.15",
            "cmd: 0x27, param: 0x00, args: [0,0,0]",
            "id: 0xFF001272, index: 0, tx: 0, seed: 0x6A6A",
            "light_0: ['cmd', 'step'] / {'sub_type': 'cww', 'cmd': 'K+', 'step': 0.08333333333333333}",
        ),
        # Button BR+
        (
            "ruixin_v0/r1",
            "1E.FF.00.00.00.52.58.4B.69.72.36.0E.62.62.D4.75.64.64.8B.67.68.69.71.73.75.7D.7F.50.13.14.15",
            "cmd: 0x25, param: 0x00, args: [0,0,0]",
            "id: 0xFF001272, index: 0, tx: 0, seed: 0x6262",
            "light_0: ['cmd', 'step'] / {'sub_type': 'cww', 'cmd': 'B+', 'step': 0.08333333333333333}",
        ),
        # Button BR-
        (
            "ruixin_v0/r1",
            "1E.FF.00.00.00.52.58.4B.69.72.36.0E.7B.7B.ED.8E.7D.7D.A5.80.81.82.8A.8C.8E.96.98.6A.13.14.15",
            "cmd: 0x26, param: 0x00, args: [0,0,0]",
            "id: 0xFF001272, index: 0, tx: 0, seed: 0x7B7B",
            "light_0: ['cmd', 'step'] / {'sub_type': 'cww', 'cmd': 'B-', 'step': 0.08333333333333333}",
        ),
        # NOT IMPLEMENTED:
        # App TIMER ON (not understood...):
        #     0x0E / 0x00 / 0x0A(10) / 0x00: Timer 00:10:00        "1BFFFFFF010203046972360E88684DE28D9B9A8D988F9091929394DE",
        #     0x0E / 0x17(23) / 0xFE / 0x0B: Timer 23:10:59        "1BFFFFFF010203046972360E626A27BC6775747E66746A6B6C6D6ECE",
        #     0x0E / 0x17(23) / 0xFE / 0xD0: Timer 23:10:00        "1BFFFFFF010203046972360E576C1CB15C6A69735B2E5F6061626388",
        #     0x0E / 0x17(23) / 0xF4 / 0xD0: Timer 23:00:00        "1BFFFFFF010203046972360EED6EB247F200FF09E7C4F5F6F7F8F914",
        # App TIMER OFF (with timer on):
        #     0x0F: Timer Cancel                                   "1BFFFFFF010203046972360E526917AC5765655758595A5B5C5D5E9F",
        # Remote Color Switch (unique code, no possibility to distinguish between colors):
        #     0x22: Light Color Temp Toggle                        "1EFF00000052584B6972360E949406A79696BA999A9BA3A5A7AFB17F131415"
    ],
)
class TestEncoderRuiXinNoReverse(_TestEncoderFull):
    """RuiXin Encoder / Decoder Fan Only Reverse tests."""

    _with_reverse = False
