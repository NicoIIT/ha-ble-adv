"""LE Unit Tests."""

import pytest

from . import _TestEncoderBase, _TestEncoderFull


@pytest.mark.parametrize(
    _TestEncoderBase.PARAM_NAMES,
    [
        ("lelight", 0xFF, "FF.FF.FF.FF.0C.01.5F.74.E3.8C.76.A9.C4.89.89.89.C6.00.00.00.00.00.00.00.00"),  # Lamp id 21, lamp Off
    ],
)
class TestEncoderLe(_TestEncoderBase):
    """Le Encoder tests."""


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # Timer 2H (120min / 7200s)
        (
            "lelight",
            "02.01.1A.1A.FF.FF.FF.FF.FF.0E.01.5F.74.E3.8C.76.99.77.AA.8B.88.94.A8.C5.00.00.00.00.00.00",
            "cmd: 0x22, param: 0x03, args: [0,28,32]",
            "id: 0x8CE3745F, index: 17, tx: 255, seed: 0x0000",
            "device_0: ['cmd'] / {'cmd': 'timer', 's': 7200.0}",
        ),
        # MAIN LIGHT ON
        (
            "lelight",
            "02.01.1A.1A.FF.FF.FF.FF.FF.0C.01.5F.74.E3.8C.76.99.7A.88.89.89.31.00.00.00.00.00.00.00.00",
            "cmd: 0x00, param: 0x01, args: [1,0,0]",
            "id: 0x8CE3745F, index: 17, tx: 242, seed: 0x0000",
            "light_0: ['on'] / {'on': True}",
        ),
        # MAIN LIGHT OFF
        (
            "lelight",
            "02.01.1A.1A.FF.FF.FF.FF.FF.0C.01.5F.74.E3.8C.76.99.7B.89.89.89.3F.00.00.00.00.00.00.00.00",
            "cmd: 0x01, param: 0x01, args: [1,0,0]",
            "id: 0x8CE3745F, index: 17, tx: 243, seed: 0x0000",
            "light_0: ['on'] / {'on': False}",
        ),
        # BR 10 %
        (
            "lelight",
            "02.01.1A.1A.FF.FF.FF.FF.FF.0D.01.5F.74.E3.8C.76.99.7C.80.8A.88.EC.C3.00.00.00.00.00.00.00",
            "cmd: 0x08, param: 0x02, args: [0,100,0]",
            "id: 0x8CE3745F, index: 17, tx: 244, seed: 0x0000",
            "light_0: ['br'] / {'sub_type': 'cww', 'br': 0.1}",
        ),
        # BR 100 %
        (
            "lelight",
            "02.01.19.1A.FF.FF.FF.FF.FF.0D.01.5F.74.E3.8C.76.99.7D.80.8A.8B.60.4B.00.00.00.00.00.00.00",
            "cmd: 0x08, param: 0x02, args: [3,232,0]",
            "id: 0x8CE3745F, index: 17, tx: 245, seed: 0x0000",
            "light_0: ['br'] / {'sub_type': 'cww', 'br': 1.0}",
        ),
        # COLD
        (
            "lelight",
            "02.01.1A.1A.FF.FF.FF.FF.FF.0D.01.5F.74.E3.8C.76.99.7E.85.8A.08.88.A0.00.00.00.00.00.00.00",
            "cmd: 0x0D, param: 0x02, args: [128,0,0]",
            "id: 0x8CE3745F, index: 17, tx: 246, seed: 0x0000",
            "light_0: ['ct'] / {'sub_type': 'cww', 'ct': 0.0}",
        ),
        # WARM
        (
            "lelight",
            "02.01.1A.1A.FF.FF.FF.FF.FF.0D.01.5F.74.E3.8C.76.99.7F.85.8A.88.08.AF.00.00.00.00.00.00.00",
            "cmd: 0x0D, param: 0x02, args: [0,128,0]",
            "id: 0x8CE3745F, index: 17, tx: 247, seed: 0x0000",
            "light_0: ['ctr'] / {'sub_type': 'cww', 'ctr': 0.0}",
        ),
        # RGB RED
        (
            "lelight",
            "02.01.19.1A.FF.FF.FF.FF.FF.0E.01.5F.74.E3.8C.76.9A.70.9E.8B.77.88.88.14.00.00.00.00.00.00",
            "cmd: 0x16, param: 0x03, args: [255,0,0]",
            "id: 0x8CE3745F, index: 18, tx: 248, seed: 0x0000",
            "light_0: ['rf', 'gf', 'bf'] / {'sub_type': 'rgb', 'rf': 1.0, 'gf': 0.0, 'bf': 0.0}",
        ),
        # FAN ON
        (
            "lelight",
            "02.01.19.1A.FF.FF.FF.FF.FF.0C.01.5F.74.E3.8C.76.99.71.A9.89.89.19.00.00.00.00.00.00.00.00",
            "cmd: 0x21, param: 0x01, args: [1,0,0]",
            "id: 0x8CE3745F, index: 17, tx: 249, seed: 0x0000",
            "fan_0: ['on', 'speed'] / {'speed_count': 3, 'on': True, 'speed': 1}",
        ),
        # FAN SPEED 2
        (
            "lelight",
            "02.01.1A.1A.FF.FF.FF.FF.FF.0C.01.5F.74.E3.8C.76.99.72.A9.89.8A.07.00.00.00.00.00.00.00.00",
            "cmd: 0x21, param: 0x01, args: [2,0,0]",
            "id: 0x8CE3745F, index: 17, tx: 250, seed: 0x0000",
            "fan_0: ['on', 'speed'] / {'speed_count': 3, 'on': True, 'speed': 2}",
        ),
        # FAN OFF
        (
            "lelight",
            "02.01.19.1A.FF.FF.FF.FF.FF.0C.01.5F.74.E3.8C.76.99.73.A9.89.88.18.00.00.00.00.00.00.00.00",
            "cmd: 0x21, param: 0x01, args: [0,0,0]",
            "id: 0x8CE3745F, index: 17, tx: 251, seed: 0x0000",
            "fan_0: ['on'] / {'on': False}",
        ),
        # FAN Direction Forward
        (
            "lelight",
            "02.01.19.1A.FF.FF.FF.FF.FF.0C.01.5F.74.E3.8C.76.99.74.A9.89.08.87.00.00.00.00.00.00.00.00",
            "cmd: 0x21, param: 0x01, args: [128,0,0]",
            "id: 0x8CE3745F, index: 17, tx: 252, seed: 0x0000",
            "fan_0: ['dir'] / {'speed_count': 3, 'dir': True}",
        ),
        # FAN Direction Reverse
        (
            "lelight",
            "02.01.1A.1A.FF.FF.FF.FF.FF.0C.01.5F.74.E3.8C.76.99.75.A9.89.09.85.00.00.00.00.00.00.00.00",
            "cmd: 0x21, param: 0x01, args: [129,0,0]",
            "id: 0x8CE3745F, index: 17, tx: 253, seed: 0x0000",
            "fan_0: ['dir'] / {'speed_count': 3, 'dir': False}",
        ),
    ],
)
class TestEncoderLeFull(_TestEncoderFull):
    """LE Encoder / Decoder Full tests."""
