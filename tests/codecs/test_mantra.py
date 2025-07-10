"""Mantra Unit Tests."""

import pytest

from . import _TestEncoderBase, _TestEncoderFull


@pytest.mark.parametrize(
    _TestEncoderBase.PARAM_NAMES,
    [
        ("mantra_v0", 0xFF, "4E.6F.72.0E.03.93.06.48.F4.6E.BE.4E.BB.53.0B.70.BB.AD.6C.67"),
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
            "cmd: 0x02, param: 0x00, args: [44,1,6]",
            "id: 0x0000C5F0, index: 0, tx: 1095, seed: 0x0000",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'warm': 0.0, 'cold': 0.17254901960784313, 'br': 0.17254901960784313, 'ctr': 1.0}",
        ),
        # BR 100 %
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.04.4B.06.4F.5A.C1.47.F5.A2.7F.46.64.A7.63.34.01",
            "cmd: 0x02, param: 0x00, args: [255,7,6]",
            "id: 0x0000C5F0, index: 0, tx: 1099, seed: 0x0000",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'warm': 0.0, 'cold': 1.0, 'br': 1.0, 'ctr': 1.0}",
        ),
        # COLD
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.04.53.06.4F.43.67.59.7A.38.23.16.D2.3B.02.24.ED",
            "cmd: 0x02, param: 0x00, args: [255,7,6]",
            "id: 0x0000C5F0, index: 0, tx: 1107, seed: 0x0000",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'warm': 0.0, 'cold': 1.0, 'br': 1.0, 'ctr': 1.0}",
        ),
        # WARM
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.04.5A.06.4F.4A.E9.12.4F.E0.D1.5F.4D.01.A0.CA.42",
            "cmd: 0x02, param: 0xFF, args: [0,7,0]",
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
        # FAN SPEED 21
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.04.60.06.4E.73.1F.A7.B4.FF.D0.3C.40.D7.4A.D8.D6",
            "cmd: 0x03, param: 0x01, args: [22,0,0]",
            "id: 0x0000C5F0, index: 0, tx: 1120, seed: 0x0000",
            "fan_0: ['speed'] / {'sub_type': '6speed', 'on': True, 'speed': 4.258064516129032}",
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
        # FAN Direction Forward - TO BE VALIDATED / ADDED
        # Fan Sleep mode
        (
            "mantra_v0",
            "02.01.1A.15.FF.4E.6F.72.0E.04.62.06.4C.71.38.DA.D5.A2.5D.3F.4D.B5.BD.1B.3F",
            "cmd: 0x01, param: 0x0E, args: [0,0,0]",
            "id: 0x0000C5F0, index: 0, tx: 1122, seed: 0x0000",
            "fan_0: ['preset'] / {'preset': 'sleep'}",
        ),
        # Fan Breeze mode - TO BE VALIDATED / ADDED
    ],
)
class TestEncoderMantraFull(_TestEncoderFull):
    """Mantra Encoder / Decoder Full tests."""
