"""Zhi Jia Unit Tests."""

import pytest

from . import _TestEncoderBase, _TestEncoderFull


@pytest.mark.parametrize(
    _TestEncoderBase.PARAM_NAMES,
    [
        ("zhijia_v0", 0xFF, "F9.08.49.89.E4.E1.A2.3E.6C.95.0B.58.C9.38.28.07"),
        ("zhijia_v1", 0xFF, "F9.08.49.13.E1.2B.48.C3.33.4A.85.E5.C5.56.60.96.C4.A0.2C.89.BB.11.76.92.99.AA"),
        ("zhijia_vr1", 0xFF, "F0.FF.CF.5E.EC.CF.CC.CF.30.EF.CE.6A.CC.CD.67.C9.EC.28.C9"),
        ("zhiguang_v0", 0xFF, "F9.08.49.B2.CE.2C.91.3F.6D.94.0A.F2.FB.39.25.67"),
        ("zhiguang_v1", 0xFF, "F9.08.49.E6.29.AF.D4.17.38.AC.51.33.11.82.8D.42.10.76.F8.C4.78.FC.C8.46.23.8E"),
        ("zhiguang_v2", 0xFF, "22.9D.8D.36.4B.E9.0F.DA.D5.40.79.CA.69.A3.BF.5B.95.D5.D4.4A.5F.85.F6.9C.A9.19"),
    ],
)
class TestEncoderZhijia(_TestEncoderBase):
    """Zhi Jia Encoder tests."""


@pytest.mark.parametrize(
    _TestEncoderBase.PARAM_NAMES,
    [
        ("zhijia_v2", 0xFF, "22.9D.AB.CB.5F.CF.2F.FC.F3.5F.52.EC.4D.85.00.6E.87.99.F2.4A.5F.85.F6.9C.A9.19"),
        ("zhijia_v2_fl", 0xFF, "22.9D.AB.CB.5F.CF.2F.FC.F3.5F.52.EC.4D.85.00.6E.87.99.F2.4A.5F.85.F6.9C.A9.19"),
    ],
)
class TestEncoderZhijiaDupe(_TestEncoderBase):
    """Zhi Jia Encoder tests with duplicate codecs."""

    _dupe_allowed = True


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # PAIR
        (
            "zhijia_v1",
            "02.01.1A.1B.FF.F9.08.49.13.E1.2B.48.C3.03.4A.85.D7.C5.54.60.96.C4.A0.2C.89.89.11.76.92.9C.7A",
            "cmd: 0xA2, param: 0x00, args: [0,0,0]",
            "id: 0x00E15324, index: 1, tx: 48, seed: 0x0000",
            "device_0: ['cmd'] / {'cmd': 'pair'}",
        ),
        (
            "zhijia_v0",
            "02.01.1A.11.FF.F9.08.49.89.E4.E1.BB.27.77.8C.12.41.C9.21.1B.20",
            "cmd: 0xB4, param: 0x00, args: [0,0,0]",
            "id: 0x00005324, index: 1, tx: 24, seed: 0x0000",
            "device_0: ['cmd'] / {'cmd': 'pair'}",
        ),
        (
            "zhijia_v2",
            "02.01.1A.1B.FF.22.9D.9D.C9.69.F9.2F.CA.C7.69.52.DA.7B.B3.36.6E.87.AF.C4.4A.5F.85.F6.9C.A9.19",
            "cmd: 0xA2, param: 0x00, args: [0,0,0]",
            "id: 0x00E15324, index: 1, tx: 49, seed: 0x0000",
            "device_0: ['cmd'] / {'cmd': 'pair'}",
        ),
        # TIMER 2H (120min / 7200s)
        (
            "zhijia_v2",
            "02.01.1A.1B.FF.22.9D.49.4F.BF.2F.AB.1C.11.BF.D6.77.AD.65.E0.EA.78.02.12.4A.5F.85.F6.9C.A9.19",
            "cmd: 0xD9, param: 0x00, args: [2,0,0]",
            "id: 0x00E15324, index: 1, tx: 99, seed: 0x0000",
            "device_0: ['cmd'] / {'cmd': 'timer', 's': 120.0}",
        ),
        (
            "zhijia_v0",
            "02.01.1A.11.FF.F9.08.49.89.E4.E1.92.0E.5E.A5.5A.68.C9.08.3D.59",
            "cmd: 0xD5, param: 0x00, args: [0,0,0]",
            "id: 0x00005324, index: 1, tx: 49, seed: 0x0000",
            "device_0: ['cmd'] / {'cmd': 'timer', 's': 120}",
        ),
        (
            "zhijia_v1",
            "02.01.1A.1B.FF.F9.08.49.13.E1.2B.48.C1.28.4A.85.85.C5.54.60.96.BF.A0.2C.89.DB.11.0D.92.A4.3E",
            "cmd: 0xD9, param: 0x00, args: [2,0,0]",
            "id: 0x00E15324, index: 1, tx: 98, seed: 0x0000",
            "device_0: ['cmd'] / {'cmd': 'timer', 's': 120.0}",
        ),
        # MAIN LIGHT OFF
        (
            "zhijia_v0",
            "02.01.1A.11.FF.F9.08.49.89.E4.E1.E1.7D.2D.D6.4E.1B.C9.7B.18.BC",
            "cmd: 0xB2, param: 0x00, args: [0,0,0]",
            "id: 0x00005324, index: 1, tx: 66, seed: 0x0000",
            "light_0: ['on'] / {'on': False}",
        ),
        (
            "zhijia_v1",
            "02.01.1A.1B.FF.F9.08.49.13.E1.2B.48.C3.04.4A.85.D4.C5.54.60.96.C0.A0.2C.89.8A.11.72.92.5B.92",
            "cmd: 0xA6, param: 0x00, args: [0,0,0]",
            "id: 0x00E15324, index: 1, tx: 51, seed: 0x0000",
            "light_0: ['on'] / {'on': False}",
        ),
        (
            "zhijia_v2",
            "02.01.1A.1B.FF.22.9D.63.32.97.07.D4.34.39.97.A9.20.85.4D.C8.95.78.55.3A.4A.5F.85.F6.9C.A9.19",
            "cmd: 0xA6, param: 0x00, args: [0,0,0]",
            "id: 0x00E15324, index: 1, tx: 52, seed: 0x0000",
            "light_0: ['on'] / {'on': False}",
        ),
        # MAIN LIGHT ON
        (
            "zhijia_v2",
            "02.01.1A.1B.FF.22.9D.F1.CC.05.95.28.A6.A9.05.55.B1.17.DF.5A.69.87.C4.A8.4A.5F.85.F6.9C.A9.19",
            "cmd: 0xA5, param: 0x00, args: [0,0,0]",
            "id: 0x00E15324, index: 3, tx: 90, seed: 0x0000",
            "light_0: ['on'] / {'on': True}",
        ),
        (
            "zhijia_v0",
            "02.01.1A.11.FF.F9.08.49.89.E4.E1.F6.6A.38.C1.58.0C.C9.6C.81.3E",
            "cmd: 0xB3, param: 0x00, args: [0,0,0]",
            "id: 0x00005324, index: 3, tx: 85, seed: 0x0000",
            "light_0: ['on'] / {'on': True}",
        ),
        (
            "zhijia_v1",
            "02.01.1A.1B.FF.F9.08.49.13.E1.2B.48.C3.6F.4A.85.BE.C5.56.60.96.C3.A0.2C.89.E0.11.71.92.AE.3B",
            "cmd: 0xA5, param: 0x00, args: [0,0,0]",
            "id: 0x00E15324, index: 3, tx: 89, seed: 0x0000",
            "light_0: ['on'] / {'on': True}",
        ),
        # BR 0 %
        (
            "zhijia_v0",
            "02.01.1A.11.FF.F9.08.49.89.E4.E1.BC.20.70.8B.14.46.C9.26.20.E4",
            "cmd: 0xB5, param: 0x00, args: [0,0,0]",
            "id: 0x00005324, index: 1, tx: 31, seed: 0x0000",
            "light_0: ['br'] / {'sub_type': 'cww', 'br': 0.0}",
        ),
        (
            "zhijia_v1",
            "02.01.1A.1B.FF.F9.08.49.13.E1.2B.48.C3.02.4A.85.D9.C5.54.60.96.CB.A0.2C.89.87.11.79.92.32.58",
            "cmd: 0xAD, param: 0x00, args: [0,0,0]",
            "id: 0x00E15324, index: 1, tx: 62, seed: 0x0000",
            "light_0: ['br'] / {'sub_type': 'cww', 'br': 0.0}",
        ),
        (
            "zhijia_v2",
            "02.01.1A.1B.FF.22.9D.63.39.97.07.DF.34.39.97.A2.2B.85.4D.C8.9E.78.5E.3A.4A.5F.85.F6.9C.A9.19",
            "cmd: 0xAD, param: 0x00, args: [0,0,0]",
            "id: 0x00E15324, index: 1, tx: 63, seed: 0x0000",
            "light_0: ['br'] / {'sub_type': 'cww', 'br': 0.0}",
        ),
        # BR 100%
        (
            "zhijia_v1",
            "02.01.1A.1B.FF.F9.08.49.13.E1.2B.48.39.82.4A.85.A3.C5.54.60.96.CB.A0.2C.89.FD.11.79.92.16.8D",
            "cmd: 0xAD, param: 0x00, args: [250,0,0]",
            "id: 0x00E15324, index: 1, tx: 68, seed: 0x0000",
            "light_0: ['br'] / {'sub_type': 'cww', 'br': 1.0}",
        ),
        (
            "zhijia_v0",
            "02.01.1A.11.FF.F9.08.49.89.E4.E1.69.F5.A5.5D.C1.93.21.1B.12.FA",
            "cmd: 0xB5, param: 0x00, args: [0,3,232]",
            "id: 0x00005324, index: 1, tx: 34, seed: 0x0000",
            "light_0: ['br'] / {'sub_type': 'cww', 'br': 1.0}",
        ),
        (
            "zhijia_v2",
            "02.01.1A.1B.FF.22.9D.E3.C3.ED.7D.DF.4E.43.ED.A2.51.FF.37.B2.9E.78.24.40.4A.5F.85.F6.9C.A9.19",
            "cmd: 0xAD, param: 0x00, args: [250,0,0]",
            "id: 0x00E15324, index: 1, tx: 69, seed: 0x0000",
            "light_0: ['br'] / {'sub_type': 'cww', 'br': 1.0}",
        ),
        # COLD
        (
            "zhijia_v2",
            "02.01.1A.1B.FF.22.9D.EF.C5.1B.8B.23.B8.B5.1B.5E.A4.09.C1.44.62.87.D1.B6.4A.5F.85.F6.9C.A9.19",
            "cmd: 0xAE, param: 0x00, args: [0,0,0]",
            "id: 0x00E15324, index: 1, tx: 79, seed: 0x0000",
            "light_0: ['ct'] / {'sub_type': 'cww', 'ct': 0.0}",
        ),
        (
            "zhijia_v0",
            "02.01.1A.11.FF.F9.08.49.89.E4.E1.84.18.48.B3.2E.7E.C9.1E.30.29",
            "cmd: 0xB7, param: 0x00, args: [0,0,0]",
            "id: 0x00005324, index: 1, tx: 39, seed: 0x0000",
            "light_0: ['ct'] / {'sub_type': 'cww', 'ct': 0.0}",
        ),
        (
            "zhijia_v1",
            "02.01.1A.1B.FF.F9.08.49.13.E1.2B.48.C3.71.4A.85.A9.C5.54.60.96.C8.A0.2C.89.F7.11.7A.92.44.C8",
            "cmd: 0xAE, param: 0x00, args: [0,0,0]",
            "id: 0x00E15324, index: 1, tx: 78, seed: 0x0000",
            "light_0: ['ct'] / {'sub_type': 'cww', 'ct': 0.0}",
        ),
        # WARM
        (
            "zhijia_v2",
            "02.01.1A.1B.FF.22.9D.0D.3F.03.93.23.A0.AD.03.5E.BC.11.D9.5C.62.87.C9.AE.4A.5F.85.F6.9C.A9.19",
            "cmd: 0xAE, param: 0x00, args: [250,0,0]",
            "id: 0x00E15324, index: 1, tx: 87, seed: 0x0000",
            "light_0: ['ct'] / {'sub_type': 'cww', 'ct': 1.0}",
        ),
        (
            "zhijia_v0",
            "02.01.1A.11.FF.F9.08.49.89.E4.E1.60.FC.AC.54.CA.9A.21.12.F5.A2",
            "cmd: 0xB7, param: 0x00, args: [0,3,232]",
            "id: 0x00005324, index: 1, tx: 43, seed: 0x0000",
            "light_0: ['ct'] / {'sub_type': 'cww', 'ct': 1.0}",
        ),
        (
            "zhijia_v1",
            "02.01.1A.1B.FF.F9.08.49.13.E1.2B.48.39.93.4A.85.B1.C5.54.60.96.C8.A0.2C.89.EF.11.7A.92.6B.A9",
            "cmd: 0xAE, param: 0x00, args: [250,0,0]",
            "id: 0x00E15324, index: 1, tx: 86, seed: 0x0000",
            "light_0: ['ct'] / {'sub_type': 'cww', 'ct': 1.0}",
        ),
        # RGB BR 0%
        (
            "zhijia_v2",
            "02.01.1A.1B.FF.22.9D.E9.A6.1D.8D.45.BE.B6.1D.38.C4.0F.C7.42.04.87.B1.B0.4A.5F.85.F6.9C.A9.19",
            "cmd: 0xC8, param: 0x00, args: [0,0,0]",
            "id: 0x00E15324, index: 4, tx: 47, seed: 0x0000",
            "light_0: ['br'] / {'sub_type': 'rgb', 'br': 0.0}",
        ),
        # RGB BR 100%
        (
            "zhijia_v2",
            "02.01.1A.1B.FF.22.9D.F1.A3.FF.6F.BA.5C.54.FF.C7.26.ED.25.A0.FB.78.53.52.4A.5F.85.F6.9C.A9.19",
            "cmd: 0xC8, param: 0x00, args: [250,0,0]",
            "id: 0x00E15324, index: 4, tx: 50, seed: 0x0000",
            "light_0: ['br'] / {'sub_type': 'rgb', 'br': 1.0}",
        ),
        # RGB RED (mainly)
        (
            "zhijia_v2",
            "02.01.1A.1B.FF.22.9D.A1.EE.AF.7D.FA.43.04.AF.C5.74.BD.75.F0.BB.78.01.02.4A.5F.85.F6.9C.A9.19",
            "cmd: 0xCA, param: 0x00, args: [250,66,79]",
            "id: 0x00E15324, index: 4, tx: 34, seed: 0x0000",
            "light_0: ['r', 'g', 'b'] / {'sub_type': 'rgb', 'r': 1.0, 'g': 0.264, 'b': 0.316}",
        ),
        # FAN Speed 2/3
        (
            "zhijia_v2",
            "02.01.1A.1B.FF.22.9D.FD.BE.09.99.58.AA.A7.09.25.CD.1B.D3.56.19.87.B8.A4.4A.5F.85.F6.9C.A9.19",
            "cmd: 0xD5, param: 0x00, args: [0,0,0]",
            "id: 0x00E15324, index: 1, tx: 38, seed: 0x0000",
            "fan_0: ['on'] / {'sub_type': '3speed', 'on': True, 'speed': 2}",
        ),
        (
            "zhijia_v0",
            "02.01.1A.11.FF.F9.08.49.89.E4.E1.98.04.54.AF.54.62.C9.02.7D.81",
            "cmd: 0xD1, param: 0x00, args: [0,0,0]",
            "id: 0x00005324, index: 1, tx: 59, seed: 0x0000",
            "fan_0: ['on'] / {'sub_type': '3speed', 'on': True, 'speed': 2}",
        ),
        (
            "zhijia_v1",
            "02.01.1A.1B.FF.F9.08.49.13.E1.2B.48.C3.61.4A.85.C2.C5.54.60.96.B3.A0.2C.89.9C.11.01.92.2A.FE",
            "cmd: 0xD5, param: 0x00, args: [0,0,0]",
            "id: 0x00E15324, index: 1, tx: 37, seed: 0x0000",
            "fan_0: ['on'] / {'sub_type': '3speed', 'on': True, 'speed': 2}",
        ),
        # FAN OFF
        (
            "zhijia_v2",
            "02.01.1A.1B.FF.22.9D.F1.BC.05.95.5A.A6.AB.05.27.C3.17.DF.5A.1B.87.B6.A8.4A.5F.85.F6.9C.A9.19",
            "cmd: 0xD7, param: 0x00, args: [0,0,0]",
            "id: 0x00E15324, index: 1, tx: 40, seed: 0x0000",
            "fan_0: ['on'] / {'on': False}",
        ),
        (
            "zhijia_v0",
            "02.01.1A.11.FF.F9.08.49.89.E4.E1.9F.03.53.A8.5A.65.C9.05.9E.A0",
            "cmd: 0xD8, param: 0x00, args: [0,0,0]",
            "id: 0x00005324, index: 1, tx: 60, seed: 0x0000",
            "fan_0: ['on'] / {'on': False}",
        ),
        (
            "zhijia_v1",
            "02.01.1A.1B.FF.F9.08.49.13.E1.2B.48.C3.61.4A.85.C0.C5.54.60.96.B1.A0.2C.89.9E.11.03.92.D9.F4",
            "cmd: 0xD7, param: 0x00, args: [0,0,0]",
            "id: 0x00E15324, index: 1, tx: 39, seed: 0x0000",
            "fan_0: ['on'] / {'on': False}",
        ),
        # FAN Direction Reverse
        (
            "zhijia_v0",
            "02.01.1A.11.FF.F9.08.49.89.E4.E1.9D.01.51.AA.5A.67.C9.07.3E.14",
            "cmd: 0xDA, param: 0x00, args: [0,0,0]",
            "id: 0x00005324, index: 1, tx: 62, seed: 0x0000",
            "fan_0: ['dir'] / {'dir': False}",
        ),
        (
            "zhijia_v1",
            "02.01.1A.1B.FF.F9.08.49.13.E1.2B.48.C3.60.4A.85.CC.C5.54.60.96.BC.A0.2C.89.92.11.0E.92.84.DC",
            "cmd: 0xDA, param: 0x00, args: [0,0,0]",
            "id: 0x00E15324, index: 1, tx: 43, seed: 0x0000",
            "fan_0: ['dir'] / {'dir': False}",
        ),
        (
            "zhijia_v2",
            "02.01.1A.1B.FF.22.9D.07.4E.F3.63.A8.50.5D.F3.D5.38.E1.29.AC.E9.78.4D.5E.4A.5F.85.F6.9C.A9.19",
            "cmd: 0xDA, param: 0x00, args: [0,0,0]",
            "id: 0x00E15324, index: 1, tx: 44, seed: 0x0000",
            "fan_0: ['dir'] / {'dir': False}",
        ),
        # FAN Direction Forward
        (
            "zhijia_v0",
            "02.01.1A.11.FF.F9.08.49.89.E4.E1.9C.00.50.AB.58.66.C9.06.18.77",
            "cmd: 0xD9, param: 0x00, args: [0,0,0]",
            "id: 0x00005324, index: 1, tx: 63, seed: 0x0000",
            "fan_0: ['dir'] / {'dir': True}",
        ),
        (
            "zhijia_v2",
            "02.01.1A.1B.FF.22.9D.FB.B0.0F.9F.56.AC.A1.0F.2B.C5.1D.D5.50.17.87.B0.A2.4A.5F.85.F6.9C.A9.19",
            "cmd: 0xDB, param: 0x00, args: [0,0,0]",
            "id: 0x00E15324, index: 1, tx: 46, seed: 0x0000",
            "fan_0: ['dir'] / {'dir': True}",
        ),
        (
            "zhijia_v1",
            "02.01.1A.1B.FF.F9.08.49.13.E1.2B.48.C3.67.4A.85.CA.C5.54.60.96.BD.A0.2C.89.94.11.0F.92.D4.A0",
            "cmd: 0xDB, param: 0x00, args: [0,0,0]",
            "id: 0x00E15324, index: 1, tx: 45, seed: 0x0000",
            "fan_0: ['dir'] / {'dir': True}",
        ),
        # Second Light OFF
        (
            "zhijia_v2",
            "02.01.1A.1B.FF.22.9D.71.24.85.15.C2.26.2B.85.BF.24.97.5F.DA.83.78.51.28.4A.5F.85.F6.9C.A9.19",
            "cmd: 0xB0, param: 0x00, args: [0,0,0]",
            "id: 0x00E15324, index: 1, tx: 48, seed: 0x0000",
            "light_1: ['on'] / {'on': False}",
        ),
        (
            "zhijia_v0",
            "02.01.1A.11.FF.F9.08.49.89.E4.E1.E3.7D.2F.D4.58.19.C9.7B.2A.94",
            "cmd: 0xA6, param: 0x00, args: [2,0,0]",
            "id: 0x00005324, index: 1, tx: 64, seed: 0x0000",
            "light_1: ['on'] / {'on': False}",
        ),
        (
            "zhijia_v1",
            "02.01.1A.1B.FF.F9.08.49.13.E1.2B.48.C3.0E.4A.85.C8.C5.54.60.96.D6.A0.2C.89.96.11.64.92.BF.64",
            "cmd: 0xB0, param: 0x00, args: [0,0,0]",
            "id: 0x00E15324, index: 1, tx: 47, seed: 0x0000",
            "light_1: ['on'] / {'on': False}",
        ),
        # Second Light ON
        (
            "zhijia_v2",
            "02.01.1A.1B.FF.22.9D.93.C4.67.F7.22.C4.C9.67.5F.D9.75.BD.38.63.87.AC.CA.4A.5F.85.F6.9C.A9.19",
            "cmd: 0xAF, param: 0x00, args: [0,0,0]",
            "id: 0x00E15324, index: 1, tx: 50, seed: 0x0000",
            "light_1: ['on'] / {'on': True}",
        ),
        (
            "zhijia_v0",
            "02.01.1A.11.FF.F9.08.49.89.E4.E1.E2.7F.2E.D5.59.18.C9.79.34.48",
            "cmd: 0xA6, param: 0x00, args: [1,0,0]",
            "id: 0x00005324, index: 1, tx: 65, seed: 0x0000",
            "light_1: ['on'] / {'on': True}",
        ),
        (
            "zhijia_v1",
            "02.01.1A.1B.FF.F9.08.49.13.E1.2B.48.C3.0F.4A.85.D6.C5.54.60.96.C9.A0.2C.89.88.11.7B.92.89.11",
            "cmd: 0xAF, param: 0x00, args: [0,0,0]",
            "id: 0x00E15324, index: 1, tx: 49, seed: 0x0000",
            "light_1: ['on'] / {'on': True}",
        ),
    ],
)
class TestEncoderZhijiaFull(_TestEncoderFull):
    """Zhi Jia Encoder / Decoder Full tests."""


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # Night Mode (No Direct)
        (
            "zhijia_v0",
            "02.01.1A.11.FF.F9.08.49.89.E4.E1.FB.7E.35.D5.47.01.C9.78.EE.2A",
            "cmd: 0xA1, param: 0x00, args: [25,25,0]",
            "id: 0x00005324, index: 3, tx: 88, seed: 0x0000",
            "light_0: [] / {'sub_type': 'cww', 'cold': 0.1, 'warm': 0.1}",
        ),
        (
            "zhijia_v1",
            "02.01.1A.1B.FF.F9.08.49.13.E1.2B.48.DA.6B.4A.9C.B8.C5.56.60.96.C1.A0.2C.89.E6.11.73.92.AF.A2",
            "cmd: 0xA7, param: 0x00, args: [25,25,0]",
            "id: 0x00E15324, index: 3, tx: 95, seed: 0x0000",
            "light_0: [] / {'sub_type': 'cww', 'cold': 0.1, 'warm': 0.1}",
        ),
        (
            "zhijia_v2",
            "02.01.1A.1B.FF.22.9D.36.28.DB.52.CC.78.77.DB.A8.6D.C9.01.84.8D.78.18.76.4A.5F.85.F6.9C.A9.19",
            "cmd: 0xA7, param: 0x00, args: [25,25,0]",
            "id: 0x00E15324, index: 3, tx: 96, seed: 0x0000",
            "light_0: [] / {'sub_type': 'cww', 'cold': 0.1, 'warm': 0.1}",
        ),
        # Button Natural Light (No Direct)
        (
            "zhijia_v0",
            "02.01.1A.11.FF.F9.08.49.89.E4.E1.C0.A3.0E.08.79.3A.C9.A5.F1.93",
            "cmd: 0xA4, param: 0x00, args: [255,255,0]",
            "id: 0x00005324, index: 3, tx: 99, seed: 0x0000",
            "light_0: [] / {'sub_type': 'cww', 'cold': 1, 'warm': 1}",
        ),
        (
            "zhijia_v2",
            "02.01.1A.1B.FF.22.9D.2F.C4.21.4B.20.82.8D.21.A7.98.33.FB.7E.61.78.ED.8C.4A.5F.85.F6.9C.A9.19",
            "cmd: 0xA8, param: 0x00, args: [250,250,0]",
            "id: 0x00E15324, index: 3, tx: 118, seed: 0x0000",
            "light_0: [] / {'sub_type': 'cww', 'cold': 1, 'warm': 1}",
        ),
        (
            "zhijia_v1",
            "02.01.1A.1B.FF.F9.08.49.13.E1.2B.48.39.4E.4A.7F.92.C5.56.60.96.CE.A0.2C.89.CC.11.7C.92.A6.1B",
            "cmd: 0xA8, param: 0x00, args: [250,250,0]",
            "id: 0x00E15324, index: 3, tx: 117, seed: 0x0000",
            "light_0: [] / {'sub_type': 'cww', 'cold': 1, 'warm': 1}",
        ),
        # Button WARM (No Direct)
        (
            "zhijia_v2",
            "02.01.1A.1B.FF.22.9D.DB.3E.2F.45.20.8C.83.2F.A7.96.3D.F5.70.61.78.E3.82.4A.5F.85.F6.9C.A9.19",
            "cmd: 0xA8, param: 0x00, args: [0,250,0]",
            "id: 0x00E15324, index: 3, tx: 120, seed: 0x0000",
            "light_0: [] / {'sub_type': 'cww', 'cold': 0, 'warm': 1}",
        ),
        (
            "zhijia_v0",
            "02.01.1A.11.FF.F9.08.49.89.E4.E1.C7.5B.09.0F.79.3D.C9.5D.8D.9D",
            "cmd: 0xA3, param: 0x00, args: [0,255,0]",
            "id: 0x00005324, index: 3, tx: 100, seed: 0x0000",
            "light_0: [] / {'sub_type': 'cww', 'cold': 0, 'warm': 1}",
        ),
        (
            "zhijia_v1",
            "02.01.1A.1B.FF.F9.08.49.13.E1.2B.48.C3.B6.4A.7F.90.C5.56.60.96.CE.A0.2C.89.CE.11.7C.92.19.FC",
            "cmd: 0xA8, param: 0x00, args: [0,250,0]",
            "id: 0x00E15324, index: 3, tx: 119, seed: 0x0000",
            "light_0: [] / {'sub_type': 'cww', 'cold': 0, 'warm': 1}",
        ),
        # Button COLD
        (
            "zhijia_v1",
            "02.01.1A.1B.FF.F9.08.49.13.E1.2B.48.39.B8.4A.85.9E.C5.56.60.96.CE.A0.2C.89.C0.11.7C.92.ED.77",
            "cmd: 0xA8, param: 0x00, args: [250,0,0]",
            "id: 0x00E15324, index: 3, tx: 121, seed: 0x0000",
            "light_0: [] / {'sub_type': 'cww', 'cold': 1, 'warm': 0}",
        ),
        (
            "zhijia_v2",
            "02.01.1A.1B.FF.22.9D.D9.C4.D7.47.DA.74.7B.D7.A7.6E.C5.0D.88.9B.78.1B.7A.4A.5F.85.F6.9C.A9.19",
            "cmd: 0xA8, param: 0x00, args: [250,0,0]",
            "id: 0x00E15324, index: 3, tx: 122, seed: 0x0000",
            "light_0: [] / {'sub_type': 'cww', 'cold': 1, 'warm': 0}",
        ),
        (
            "zhijia_v0",
            "02.01.1A.11.FF.F9.08.49.89.E4.E1.C6.A5.08.F1.79.3C.C9.A3.5A.B3",
            "cmd: 0xA2, param: 0x00, args: [255,0,0]",
            "id: 0x00005324, index: 3, tx: 101, seed: 0x0000",
            "light_0: [] / {'sub_type': 'cww', 'cold': 1, 'warm': 0}",
        ),
    ],
)
class TestEncoderZhijiaNoReverse(_TestEncoderFull):
    """Zhi Jia Encoder / Decoder No Reverse tests."""

    _with_reverse = False
