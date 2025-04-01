"""FanLamp pro Unit Tests."""

import pytest

from . import _TestEncoderBase, _TestEncoderFull


@pytest.mark.parametrize(
    _TestEncoderBase.PARAM_NAMES,
    [
        ("fanlamp_pro_v1", 0x03, "77.F8.B6.5F.2B.5E.00.FC.31.51.50.FE.D2.08.24.0A.73.FC.08.66.F4.90.14.AF.B4.E5"),
        ("fanlamp_pro_v1", 0x03, "77.F8.B6.5F.2B.5E.00.FC.31.51.CC.FE.D2.4C.2E.0A.33.FC.7E.10.F4.E6.C0.1C.7B.74"),
        ("fanlamp_pro_v1", 0x03, "77.F8.B6.5F.2B.5E.00.FC.31.51.50.FE.D2.08.24.0A.3B.FC.D6.B8.4A.4E.31.20.A9.3E"),
        ("fanlamp_pro_v2", 0x03, "F0.08.10.80.B8.52.E1.22.C6.F2.D3.A7.67.7C.A4.9F.67.F6.B6.A2.22.8B.53.2B.01.6B"),
        ("fanlamp_pro_v3", 0x03, "F0.08.20.80.B8.52.E1.22.C6.F2.D3.A7.67.7C.A4.9F.67.F6.B6.B7.41.8B.53.2B.E9.59"),
        ("fanlamp_pro_v3", 0x03, "F0.08.20.80.8A.3F.2F.22.B9.F2.DB.03.FC.F8.68.C1.28.0C.1D.C3.6E.DA.19.48.88.61"),
        ("remote_v1", 0xFF, "56.55.18.87.52.B6.5F.2B.5E.00.FC.31.51.50.50.9A.08.24.0A.EC.FC.A9.7B.8E.0D.4A.67.60.57"),
        ("remote_v1", 0xFF, "56.55.18.87.52.B6.5F.2B.5E.00.FC.31.51.54.50.9A.08.24.0A.96.FC.F5.27.DB.51.D3.43.60.57"),
        ("remote_v3", 0x16, "F0.08.10.00.5B.B5.CC.F3.7B.EB.FC.C8.4A.F2.0A.2E.3F.FC.18.05.F7.AD.3B.BD.17.A6"),
        ("other_v1b", 0x16, "F9.08.49.13.F0.69.25.4E.31.51.BA.32.08.0A.24.CB.3B.7C.71.DC.8B.B8.97.08.D0.4C"),
        ("other_v1a", 0x03, "77.F8.B6.5F.2B.5E.00.FC.31.51.50.CB.92.08.24.CB.BB.FC.14.C6.9E.B0.E9.EA.73.A4"),
        ("other_v2", 0x16, "F0.08.10.80.0B.9B.DA.CF.BE.B3.DD.56.3B.E9.1C.FC.27.A9.3A.A5.38.2D.3F.D4.6A.50"),
        ("other_v3", 0x16, "F0.08.10.80.33.BC.2E.B0.49.EA.58.76.C0.1D.99.5E.9C.D6.B8.0E.6E.14.2B.A5.30.A9"),
    ],
)
class TestEncoderFanlamp(_TestEncoderBase):
    """Fanlamp Encoder tests."""


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # PAIR
        (
            "fanlamp_pro_v3",
            "02.01.19.1B.03.F0.08.20.80.B8.01.E1.22.C6.F2.D3.A7.67.44.A4.9F.67.F6.B6.78.45.8B.53.2B.B9.1B",
            "cmd: 0x28, param: 0x00, args: [0,0,0]",
            "id: 0xD2135C22, index: 2, tx: 117, seed: 0x2B53",
            "device_0: ['cmd'] / {'cmd': 'pair'}",
        ),
        (
            "fanlamp_pro_v1",
            "02.01.19.1B.03.77.F8.B6.5F.2B.5E.00.FC.31.51.CC.FE.D2.4C.2E.0A.5D.FC.AD.C3.F4.35.F3.2B.AF.85",
            "cmd: 0x28, param: 0x00, args: [0,0,0]",
            "id: 0x003D5022, index: 2, tx: 102, seed: 0x0006",
            "device_0: ['cmd'] / {'cmd': 'pair'}",
        ),
        (
            "fanlamp_pro_v2",
            "02.01.19.1B.03.F0.08.10.80.B8.01.E1.22.C6.F2.D3.A7.67.44.A4.9F.67.F6.B6.A2.22.8B.53.2B.E1.B5",
            "cmd: 0x28, param: 0x00, args: [0,0,0]",
            "id: 0xD2135C22, index: 2, tx: 117, seed: 0x2B53",
            "device_0: ['cmd'] / {'cmd': 'pair'}",
        ),
        # Timer 2H (120min / 7200s)
        (
            "fanlamp_pro_v3",
            "02.01.1A.1B.03.F0.08.20.80.B8.FA.E1.22.C6.F2.D3.A7.67.2D.A4.9F.1F.F6.B6.FD.E0.8B.53.2B.D7.97",
            "cmd: 0x41, param: 0x00, args: [120,0,0]",
            "id: 0xD2135C22, index: 2, tx: 142, seed: 0x2B53",
            "device_0: ['cmd'] / {'cmd': 'timer', 's': 7200.0}",
        ),
        (
            "fanlamp_pro_v1",
            "02.01.19.1B.03.77.F8.B6.5F.2B.5E.00.FC.31.51.52.FE.D2.16.24.0A.C5.FC.42.2C.F4.DA.A0.DB.D7.A0",
            "cmd: 0x51, param: 0x00, args: [120,0,0]",
            "id: 0x003D5022, index: 2, tx: 127, seed: 0x00F1",
            "device_0: ['cmd'] / {'cmd': 'timer', 's': 7200.0}",
        ),
        (
            "fanlamp_pro_v2",
            "02.01.19.1B.03.F0.08.10.80.B8.FA.E1.22.C6.F2.D3.A7.67.2D.A4.9F.1F.F6.B6.A2.22.8B.53.2B.3B.6E",
            "cmd: 0x41, param: 0x00, args: [120,0,0]",
            "id: 0xD2135C22, index: 2, tx: 142, seed: 0x2B53",
            "device_0: ['cmd'] / {'cmd': 'timer', 's': 7200.0}",
        ),
        # MAIN LIGHT OFF
        (
            "fanlamp_pro_v3",
            "02.01.19.1B.03.F0.08.20.80.B8.65.E1.22.C6.F2.D3.A7.67.7D.A4.9F.67.F6.B6.6B.65.8B.53.2B.2E.AA",
            "cmd: 0x11, param: 0x00, args: [0,0,0]",
            "id: 0xD2135C22, index: 2, tx: 17, seed: 0x2B53",
            "light_0: ['on'] / {'on': False}",
        ),
        (
            "fanlamp_pro_v1",
            "02.01.19.1B.03.77.F8.B6.5F.2B.5E.00.FC.31.51.50.FE.D2.08.24.0A.7B.FC.7C.12.F4.E4.60.70.21.7F",
            "cmd: 0x11, param: 0x00, args: [0,0,0]",
            "id: 0x003D5022, index: 2, tx: 2, seed: 0x008D",
            "light_0: ['on'] / {'on': False}",
        ),
        (
            "fanlamp_pro_v2",
            "02.01.19.1B.03.F0.08.10.80.B8.65.E1.22.C6.F2.D3.A7.67.7D.A4.9F.67.F6.B6.A2.22.8B.53.2B.B0.D9",
            "cmd: 0x11, param: 0x00, args: [0,0,0]",
            "id: 0xD2135C22, index: 2, tx: 17, seed: 0x2B53",
            "light_0: ['on'] / {'on': False}",
        ),
        # MAIN LIGHT ON
        (
            "fanlamp_pro_v3",
            "02.01.1A.1B.03.F0.08.20.80.B8.64.E1.22.C6.F2.D3.A7.67.7C.A4.9F.67.F6.B6.25.33.8B.53.2B.1A.20",
            "cmd: 0x10, param: 0x00, args: [0,0,0]",
            "id: 0xD2135C22, index: 2, tx: 16, seed: 0x2B53",
            "light_0: ['on'] / {'on': True}",
        ),
        (
            "fanlamp_pro_v1",
            "02.01.19.1B.03.77.F8.B6.5F.2B.5E.00.FC.31.51.D0.FE.D2.08.24.0A.BB.FC.1D.73.F4.85.8C.0B.7D.AC",
            "cmd: 0x10, param: 0x00, args: [0,0,0]",
            "id: 0x003D5022, index: 2, tx: 1, seed: 0x000B",
            "light_0: ['on'] / {'on': True}",
        ),
        (
            "fanlamp_pro_v2",
            "02.01.19.1B.03.F0.08.10.80.B8.64.E1.22.C6.F2.D3.A7.67.7C.A4.9F.67.F6.B6.A2.22.8B.53.2B.E6.DF",
            "cmd: 0x10, param: 0x00, args: [0,0,0]",
            "id: 0xD2135C22, index: 2, tx: 16, seed: 0x2B53",
            "light_0: ['on'] / {'on': True}",
        ),
        # BR 10 %
        (
            "fanlamp_pro_v1",
            "02.01.19.1B.03.77.F8.B6.5F.2B.5E.00.FC.31.51.5C.FE.D2.90.BC.0A.AE.FC.F7.99.F4.6F.F9.F5.1C.9A",
            "cmd: 0x21, param: 0x00, args: [25,25,0]",
            "id: 0x003D5022, index: 2, tx: 169, seed: 0x005C",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 0.09803921568627451, 'warm': 0.09803921568627451}",
        ),
        (
            "fanlamp_pro_v2",
            "02.01.19.1B.03.F0.08.10.80.B8.CC.E1.22.C6.F2.D3.A7.67.4D.A4.9F.67.EF.AF.A2.22.8B.53.2B.74.D4",
            "cmd: 0x21, param: 0x00, args: [0,25,25]",
            "id: 0xD2135C22, index: 2, tx: 184, seed: 0x2B53",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 0.09803921568627451, 'warm': 0.09803921568627451}",
        ),
        (
            "fanlamp_pro_v3",
            "02.01.19.1B.03.F0.08.20.80.B8.CC.E1.22.C6.F2.D3.A7.67.4D.A4.9F.67.EF.AF.0D.5B.8B.53.2B.00.FD",
            "cmd: 0x21, param: 0x00, args: [0,25,25]",
            "id: 0xD2135C22, index: 2, tx: 184, seed: 0x2B53",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 0.09803921568627451, 'warm': 0.09803921568627451}",
        ),
        # BR 100 %
        (
            "fanlamp_pro_v1",
            "02.01.19.1B.03.77.F8.B6.5F.2B.5E.00.FC.31.51.5C.FE.D2.F7.DB.0A.0F.FC.F8.96.F4.60.22.DA.37.AF",
            "cmd: 0x21, param: 0x00, args: [255,255,0]",
            "id: 0x003D5022, index: 2, tx: 44, seed: 0x00AC",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 1.0, 'warm': 1.0}",
        ),
        (
            "fanlamp_pro_v2",
            "02.01.19.1B.03.F0.08.10.80.B8.4F.E1.22.C6.F2.D3.A7.67.4D.A4.9F.67.09.49.A2.22.8B.53.2B.A2.8B",
            "cmd: 0x21, param: 0x00, args: [0,255,255]",
            "id: 0xD2135C22, index: 2, tx: 59, seed: 0x2B53",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 1.0, 'warm': 1.0}",
        ),
        (
            "fanlamp_pro_v3",
            "02.01.19.1B.03.F0.08.20.80.B8.4F.E1.22.C6.F2.D3.A7.67.4D.A4.9F.67.09.49.82.9F.8B.53.2B.AA.9C",
            "cmd: 0x21, param: 0x00, args: [0,255,255]",
            "id: 0xD2135C22, index: 2, tx: 59, seed: 0x2B53",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 1.0, 'warm': 1.0}",
        ),
        # COLD
        (
            "fanlamp_pro_v1",
            "02.01.1A.1B.03.77.F8.B6.5F.2B.5E.00.FC.31.51.5C.FE.D2.F7.24.0A.97.FC.14.7A.F4.8C.F4.B3.B8.84",
            "cmd: 0x21, param: 0x00, args: [255,0,0]",
            "id: 0x003D5022, index: 2, tx: 53, seed: 0x009B",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 1.0, 'warm': 0.0}",
        ),
        (
            "fanlamp_pro_v2",
            "02.01.19.1B.03.F0.08.10.80.B8.30.E1.22.C6.F2.D3.A7.67.4D.A4.9F.67.09.B6.A2.22.8B.53.2B.AF.E4",
            "cmd: 0x21, param: 0x00, args: [0,255,0]",
            "id: 0xD2135C22, index: 2, tx: 68, seed: 0x2B53",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 1.0, 'warm': 0.0}",
        ),
        (
            "fanlamp_pro_v3",
            "02.01.1A.1B.03.F0.08.20.80.B8.30.E1.22.C6.F2.D3.A7.67.4D.A4.9F.67.09.B6.12.05.8B.53.2B.19.7B",
            "cmd: 0x21, param: 0x00, args: [0,255,0]",
            "id: 0xD2135C22, index: 2, tx: 68, seed: 0x2B53",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 1.0, 'warm': 0.0}",
        ),
        # WARM
        (
            "fanlamp_pro_v1",
            "02.01.1A.1B.03.77.F8.B6.5F.2B.5E.00.FC.31.51.5C.FE.D2.08.DB.0A.E7.FC.B0.DE.F4.28.60.49.0E.E1",
            "cmd: 0x21, param: 0x00, args: [0,255,0]",
            "id: 0x003D5022, index: 2, tx: 59, seed: 0x00BE",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 0.0, 'warm': 1.0}",
        ),
        (
            "fanlamp_pro_v2",
            "02.01.1A.1B.03.F0.08.10.80.B8.3E.E1.22.C6.F2.D3.A7.67.4D.A4.9F.67.F6.49.A2.22.8B.53.2B.5F.61",
            "cmd: 0x21, param: 0x00, args: [0,0,255]",
            "id: 0xD2135C22, index: 2, tx: 74, seed: 0x2B53",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 0.0, 'warm': 1.0}",
        ),
        (
            "fanlamp_pro_v3",
            "02.01.1A.1B.03.F0.08.20.80.B8.3E.E1.22.C6.F2.D3.A7.67.4D.A4.9F.67.F6.49.C2.82.8B.53.2B.1E.45",
            "cmd: 0x21, param: 0x00, args: [0,0,255]",
            "id: 0xD2135C22, index: 2, tx: 74, seed: 0x2B53",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 0.0, 'warm': 1.0}",
        ),
        # FAN ON SPEED 2 / 6
        (
            "fanlamp_pro_v1",
            "02.01.19.1B.03.77.F8.B6.5F.2B.5E.00.FC.31.51.94.FE.D2.48.44.0A.35.FC.0A.64.F4.92.75.78.EE.EE",
            "cmd: 0x32, param: 0x00, args: [2,6,0]",
            "id: 0x003D5022, index: 2, tx: 112, seed: 0x00E3",
            "fan_0: ['on', 'speed'] / {'sub_type': '6speed', 'on': True, 'speed': 2.0}",
        ),
        (
            "fanlamp_pro_v3",
            "02.01.1A.1B.03.F0.08.20.80.B8.0B.E1.22.C6.F2.D3.A7.67.5D.A4.9F.47.F4.B6.5B.33.8B.53.2B.63.90",
            "cmd: 0x31, param: 0x00, args: [32,2,0]",
            "id: 0xD2135C22, index: 2, tx: 127, seed: 0x2B53",
            "fan_0: ['on', 'speed'] / {'sub_type': '6speed', 'on': True, 'speed': 2.0}",
        ),
        (
            "fanlamp_pro_v2",
            "02.01.1A.1B.03.F0.08.10.80.B8.0B.E1.22.C6.F2.D3.A7.67.5D.A4.9F.47.F4.B6.A2.22.8B.53.2B.B1.BD",
            "cmd: 0x31, param: 0x00, args: [32,2,0]",
            "id: 0xD2135C22, index: 2, tx: 127, seed: 0x2B53",
            "fan_0: ['on', 'speed'] / {'sub_type': '6speed', 'on': True, 'speed': 2.0}",
        ),
        # FAN OFF
        (
            "fanlamp_pro_v3",
            "02.01.1A.1B.03.F0.08.20.80.B8.F4.E1.22.C6.F2.D3.A7.67.5D.A4.9F.47.F6.B6.D9.13.8B.53.2B.E6.08",
            "cmd: 0x31, param: 0x00, args: [32,0,0]",
            "id: 0xD2135C22, index: 2, tx: 128, seed: 0x2B53",
            "fan_0: ['on'] / {'sub_type': '6speed', 'on': False}",
        ),
        (
            "fanlamp_pro_v1",
            "02.01.19.1B.03.77.F8.B6.5F.2B.5E.00.FC.31.51.54.FE.D2.08.24.0A.B5.FC.20.4E.F4.B8.F3.E9.7C.7D",
            "cmd: 0x31, param: 0x00, args: [0,0,0]",
            "id: 0x003D5022, index: 2, tx: 113, seed: 0x00B7",
            "fan_0: ['on'] / {'sub_type': '3speed', 'on': False}",  # hum sub_type '3speed' ... to be checked ...
        ),
        (
            "fanlamp_pro_v2",
            "02.01.19.1B.03.F0.08.10.80.B8.F4.E1.22.C6.F2.D3.A7.67.5D.A4.9F.47.F6.B6.A2.22.8B.53.2B.29.74",
            "cmd: 0x31, param: 0x00, args: [32,0,0]",
            "id: 0xD2135C22, index: 2, tx: 128, seed: 0x2B53",
            "fan_0: ['on'] / {'sub_type': '6speed', 'on': False}",
        ),
        # FAN Direction Reverse
        (
            "fanlamp_pro_v1",
            "02.01.1A.1B.03.77.F8.B6.5F.2B.5E.00.FC.31.51.70.FE.D2.88.24.0A.E5.FC.73.1D.F4.EB.32.FD.0A.4A",
            "cmd: 0x15, param: 0x00, args: [1,0,0]",
            "id: 0x003D5022, index: 2, tx: 123, seed: 0x007D",
            "fan_0: ['dir'] / {'dir': False}",
        ),
        (
            "fanlamp_pro_v2",
            "02.01.1A.1B.03.F0.08.10.80.B8.FE.E1.22.C6.F2.D3.A7.67.79.A4.9F.66.F6.B6.A2.22.8B.53.2B.8E.8F",
            "cmd: 0x15, param: 0x00, args: [1,0,0]",
            "id: 0xD2135C22, index: 2, tx: 138, seed: 0x2B53",
            "fan_0: ['dir'] / {'dir': False}",
        ),
        (
            "fanlamp_pro_v3",
            "02.01.1A.1B.03.F0.08.20.80.B8.FE.E1.22.C6.F2.D3.A7.67.79.A4.9F.66.F6.B6.6B.7A.8B.53.2B.59.33",
            "cmd: 0x15, param: 0x00, args: [1,0,0]",
            "id: 0xD2135C22, index: 2, tx: 138, seed: 0x2B53",
            "fan_0: ['dir'] / {'dir': False}",
        ),
        # FAN Direction Forward
        (
            "fanlamp_pro_v3",
            "02.01.1A.1B.03.F0.08.20.80.B8.FF.E1.22.C6.F2.D3.A7.67.79.A4.9F.67.F6.B6.E3.A9.8B.53.2B.B7.B9",
            "cmd: 0x15, param: 0x00, args: [0,0,0]",
            "id: 0xD2135C22, index: 2, tx: 139, seed: 0x2B53",
            "fan_0: ['dir'] / {'dir': True}",
        ),
        (
            "fanlamp_pro_v1",
            "02.01.19.1B.03.77.F8.B6.5F.2B.5E.00.FC.31.51.70.FE.D2.08.24.0A.05.FC.13.7D.F4.8B.D6.6B.FB.9C",
            "cmd: 0x15, param: 0x00, args: [0,0,0]",
            "id: 0x003D5022, index: 2, tx: 124, seed: 0x007B",
            "fan_0: ['dir'] / {'dir': True}",
        ),
        (
            "fanlamp_pro_v2",
            "02.01.19.1B.03.F0.08.10.80.B8.FF.E1.22.C6.F2.D3.A7.67.79.A4.9F.67.F6.B6.A2.22.8B.53.2B.42.16",
            "cmd: 0x15, param: 0x00, args: [0,0,0]",
            "id: 0xD2135C22, index: 2, tx: 139, seed: 0x2B53",
            "fan_0: ['dir'] / {'dir': True}",
        ),
        # FAN Oscillation ON
        (
            "fanlamp_pro_v3",
            "02.01.19.1B.03.F0.08.20.80.B8.F9.E1.22.C6.F2.D3.A7.67.7A.A4.9F.66.F6.B6.72.28.8B.53.2B.C9.45",
            "cmd: 0x16, param: 0x00, args: [1,0,0]",
            "id: 0xD2135C22, index: 2, tx: 141, seed: 0x2B53",
            "fan_0: ['osc'] / {'osc': True}",
        ),
        (
            "fanlamp_pro_v1",
            "02.01.19.1B.03.77.F8.B6.5F.2B.5E.00.FC.31.51.B0.FE.D2.88.24.0A.45.FC.25.4B.F4.BD.62.31.65.6E",
            "cmd: 0x16, param: 0x00, args: [1,0,0]",
            "id: 0x003D5022, index: 2, tx: 126, seed: 0x0017",
            "fan_0: ['osc'] / {'osc': True}",
        ),
        (
            "fanlamp_pro_v2",
            "02.01.19.1B.03.F0.08.10.80.B8.F9.E1.22.C6.F2.D3.A7.67.7A.A4.9F.66.F6.B6.A2.22.8B.53.2B.6B.CD",
            "cmd: 0x16, param: 0x00, args: [1,0,0]",
            "id: 0xD2135C22, index: 2, tx: 141, seed: 0x2B53",
            "fan_0: ['osc'] / {'osc': True}",
        ),
        # FAN Oscillation OFF
        (
            "fanlamp_pro_v3",
            "02.01.19.1B.03.F0.08.20.80.B8.F8.E1.22.C6.F2.D3.A7.67.7A.A4.9F.67.F6.B6.86.02.8B.53.2B.B0.35",
            "cmd: 0x16, param: 0x00, args: [0,0,0]",
            "id: 0xD2135C22, index: 2, tx: 140, seed: 0x2B53",
            "fan_0: ['osc'] / {'osc': False}",
        ),
        (
            "fanlamp_pro_v1",
            "02.01.19.1B.03.77.F8.B6.5F.2B.5E.00.FC.31.51.B0.FE.D2.08.24.0A.85.FC.82.EC.F4.1A.CA.85.24.05",
            "cmd: 0x16, param: 0x00, args: [0,0,0]",
            "id: 0x003D5022, index: 2, tx: 125, seed: 0x00F2",
            "fan_0: ['osc'] / {'osc': False}",
        ),
        (
            "fanlamp_pro_v2",
            "02.01.19.1B.03.F0.08.10.80.B8.F8.E1.22.C6.F2.D3.A7.67.7A.A4.9F.67.F6.B6.A2.22.8B.53.2B.A7.54",
            "cmd: 0x16, param: 0x00, args: [0,0,0]",
            "id: 0xD2135C22, index: 2, tx: 140, seed: 0x2B53",
            "fan_0: ['osc'] / {'osc': False}",
        ),
        # Second Light OFF
        (
            "fanlamp_pro_v3",
            "02.01.19.1B.03.F0.08.20.80.B8.F3.E1.22.C6.F2.D3.A7.67.7F.A4.9F.67.F6.B6.3C.F0.8B.53.2B.35.44",
            "cmd: 0x13, param: 0x00, args: [0,0,0]",
            "id: 0xD2135C22, index: 2, tx: 135, seed: 0x2B53",
            "light_1: ['on'] / {'on': False}",
        ),
        (
            "fanlamp_pro_v1",
            "02.01.19.1B.03.77.F8.B6.5F.2B.5E.00.FC.31.51.10.FE.D2.08.24.CB.25.FC.56.38.F4.CE.EB.D8.B3.EC",
            "cmd: 0x13, param: 0x00, args: [0,0,0]",
            "id: 0x003D5022, index: 2, tx: 120, seed: 0x00D9",
            "light_1: ['on'] / {'on': False}",
        ),
        (
            "fanlamp_pro_v2",
            "02.01.19.1B.03.F0.08.10.80.B8.F3.E1.22.C6.F2.D3.A7.67.7F.A4.9F.67.F6.B6.A2.22.8B.53.2B.97.3F",
            "cmd: 0x13, param: 0x00, args: [0,0,0]",
            "id: 0xD2135C22, index: 2, tx: 135, seed: 0x2B53",
            "light_1: ['on'] / {'on': False}",
        ),
        # Second Light ON
        (
            "fanlamp_pro_v3",
            "02.01.1A.1B.03.F0.08.20.80.B8.FC.E1.22.C6.F2.D3.A7.67.7E.A4.9F.67.F6.B6.AB.62.8B.53.2B.F4.5C",
            "cmd: 0x12, param: 0x00, args: [0,0,0]",
            "id: 0xD2135C22, index: 2, tx: 136, seed: 0x2B53",
            "light_1: ['on'] / {'on': True}",
        ),
        (
            "fanlamp_pro_v1",
            "02.01.19.1B.03.77.F8.B6.5F.2B.5E.00.FC.31.51.90.FE.D2.08.24.CB.A5.FC.AA.C4.F4.32.CC.A9.EC.9D",
            "cmd: 0x12, param: 0x00, args: [0,0,0]",
            "id: 0x003D5022, index: 2, tx: 121, seed: 0x00E6",
            "light_1: ['on'] / {'on': True}",
        ),
        (
            "fanlamp_pro_v2",
            "02.01.19.1B.03.F0.08.10.80.B8.FC.E1.22.C6.F2.D3.A7.67.7E.A4.9F.67.F6.B6.A2.22.8B.53.2B.FF.4D",
            "cmd: 0x12, param: 0x00, args: [0,0,0]",
            "id: 0xD2135C22, index: 2, tx: 136, seed: 0x2B53",
            "light_1: ['on'] / {'on': True}",
        ),
        # Second Light RGB Full RED
        (
            "fanlamp_pro_v2",
            "02.01.19.1B.03.F0.08.10.80.B8.09.E1.22.C6.F2.D3.A7.67.4E.A4.9F.98.F6.B6.A2.22.8B.53.2B.AD.B3",
            "cmd: 0x22, param: 0x00, args: [255,0,0]",
            "id: 0xD2135C22, index: 2, tx: 125, seed: 0x2B53",
            "light_1: ['rf', 'gf', 'bf'] / {'sub_type': 'rgb', 'rf': 1.0, 'gf': 0.0, 'bf': 0.0}",
        ),
        (
            "fanlamp_pro_v3",
            "02.01.19.1B.03.F0.08.20.80.B8.09.E1.22.C6.F2.D3.A7.67.4E.A4.9F.98.F6.B6.5C.74.8B.53.2B.1A.C6",
            "cmd: 0x22, param: 0x00, args: [255,0,0]",
            "id: 0xD2135C22, index: 2, tx: 125, seed: 0x2B53",
            "light_1: ['rf', 'gf', 'bf'] / {'sub_type': 'rgb', 'rf': 1.0, 'gf': 0.0, 'bf': 0.0}",
        ),
    ],
)
class TestEncoderFanlampFull(_TestEncoderFull):
    """Fanlamp Encoder / Decoder Full tests."""


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # Device ALL OFF (NO REVERSE)
        (
            "fanlamp_pro_v3",
            "02.01.1A.1B.03.F0.08.20.80.B8.E6.E1.22.C6.F2.D3.A7.67.03.A4.9F.67.F6.B6.62.B9.8B.53.2B.42.ED",
            "cmd: 0x6F, param: 0x00, args: [0,0,0]",
            "id: 0xD2135C22, index: 2, tx: 146, seed: 0x2B53",
            "device_0: ['on'] / {'on': False}",
        ),
        (
            "fanlamp_pro_v1",
            "02.01.19.1B.03.77.F8.B6.5F.2B.5E.00.FC.31.51.2E.FE.D2.08.24.0A.FA.FC.49.27.F4.D1.53.76.48.83",
            "cmd: 0x6F, param: 0x00, args: [0,0,0]",
            "id: 0x003D5022, index: 2, tx: 131, seed: 0x0021",
            "device_0: ['on'] / {'on': False}",
        ),
        (
            "fanlamp_pro_v2",
            "02.01.19.1B.03.F0.08.10.80.B8.E6.E1.22.C6.F2.D3.A7.67.03.A4.9F.67.F6.B6.A2.22.8B.53.2B.91.D1",
            "cmd: 0x6F, param: 0x00, args: [0,0,0]",
            "id: 0xD2135C22, index: 2, tx: 146, seed: 0x2B53",
            "device_0: ['on'] / {'on': False}",
        ),
        # Remote BR+
        (
            "remote_v1",
            "1E.FF.56.55.18.87.52.B6.5F.2B.5E.00.FC.31.51.5C.50.9A.08.24.0A.AB.D4.E7.35.AC.43.D3.F4.60.57",
            "cmd: 0x21, param: 0x14, args: [0,0,0]",
            "id: 0x00014057, index: 0, tx: 9, seed: 0x1A68",
            "light_0: ['cmd'] / {'sub_type': 'cww', 'cmd': 'B+', 'step': 0.1}",
        ),
        (
            "remote_v3",
            "02.01.02.1B.16.F0.08.10.00.64.91.72.52.33.F1.42.82.5B.F4.46.D9.50.51.C3.9B.CF.64.43.B7.A9.A6",
            "cmd: 0x21, param: 0x00, args: [20,0,0]",
            "id: 0x02227574, index: 0, tx: 10, seed: 0xB743",
            "light_0: ['cmd'] / {'sub_type': 'cww', 'cmd': 'B+', 'step': 0.1}",
        ),
        # Remote BR-
        (
            "remote_v1",
            "1E.FF.56.55.18.87.52.B6.5F.2B.5E.00.FC.31.51.5C.50.9A.08.24.0A.0B.E8.C7.15.F0.63.65.AF.60.57",
            "cmd: 0x21, param: 0x28, args: [0,0,0]",
            "id: 0x00014057, index: 0, tx: 12, seed: 0x206C",
            "light_0: ['cmd'] / {'sub_type': 'cww', 'cmd': 'B-', 'step': 0.1}",
        ),
        (
            "remote_v3",
            "02.01.02.1B.16.F0.08.10.00.51.CC.02.4C.52.E6.A1.88.42.58.81.10.78.44.C4.B1.F2.A0.B5.69.ED.B5",
            "cmd: 0x21, param: 0x00, args: [40,0,0]",
            "id: 0x02227574, index: 0, tx: 12, seed: 0x69B5",
            "light_0: ['cmd'] / {'sub_type': 'cww', 'cmd': 'B-', 'step': 0.1}",
        ),
        # Remote Cycle Color: WARM
        (
            "remote_v3",
            "02.01.02.1B.16.F0.08.10.00.84.55.BB.FF.9B.1A.E4.2D.0B.3B.D9.3D.9D.06.77.15.08.19.1E.1B.FD.03",
            "cmd: 0x21, param: 0x00, args: [64,0,255]",
            "id: 0x02227574, index: 0, tx: 127, seed: 0x1B1E",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 0.0, 'warm': 1.0}",
        ),
        (
            "remote_v1",
            "1E.FF.56.55.18.87.52.B6.5F.2B.5E.00.FC.31.51.5C.50.9A.08.DB.0A.C5.FE.65.B7.67.C1.1F.FD.60.57",
            "cmd: 0x21, param: 0x40, args: [0,255,0]",
            "id: 0x00014057, index: 0, tx: 127, seed: 0xC929",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 0.0, 'warm': 1.0}",
        ),
        # Remote Cycle Color: NATURAL
        (
            "remote_v3",
            "02.01.02.1B.16.F0.08.10.00.0C.49.56.CF.AA.39.0C.25.EB.5F.B9.7B.71.A0.15.07.1F.3B.CC.7C.F4.B6",
            "cmd: 0x21, param: 0x00, args: [64,255,255]",
            "id: 0x02227574, index: 0, tx: 128, seed: 0x7CCC",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 1.0, 'warm': 1.0}",
        ),
        (
            "remote_v1",
            "1E.FF.56.55.18.87.52.B6.5F.2B.5E.00.FC.31.51.5C.50.9A.F7.DB.0A.3A.FE.0A.D8.13.AE.7B.8B.60.57",
            "cmd: 0x21, param: 0x40, args: [255,255,0]",
            "id: 0x00014057, index: 0, tx: 128, seed: 0xE7DF",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 1.0, 'warm': 1.0}",
        ),
        # Remote Cycle Color: COLD
        (
            "remote_v3",
            "02.01.02.1B.16.F0.08.10.00.8E.95.81.42.F0.BB.82.17.05.2D.C4.FF.47.69.D6.66.BA.EB.33.1F.87.E4",
            "cmd: 0x21, param: 0x00, args: [64,255,0]",
            "id: 0x02227574, index: 0, tx: 129, seed: 0x1F33",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 1.0, 'warm': 0.0}",
        ),
        (
            "remote_v1",
            "1E.FF.56.55.18.87.52.B6.5F.2B.5E.00.FC.31.51.5C.50.9A.F7.24.0A.BA.FE.95.47.16.31.8F.8E.60.57",
            "cmd: 0x21, param: 0x40, args: [255,0,0]",
            "id: 0x00014057, index: 0, tx: 129, seed: 0x4726",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 1.0, 'warm': 0.0}",
        ),
        # Remote Night Mode
        (
            "remote_v3",
            "02.01.02.1B.16.F0.08.10.00.FE.1B.AA.BB.59.3A.64.88.1F.FB.1A.50.3E.8B.9B.AF.71.61.AD.A4.52.3A",
            "cmd: 0x23, param: 0x00, args: [0,0,0]",
            "id: 0x02227574, index: 0, tx: 44, seed: 0xA4AD",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 0.1, 'warm': 0.1}",
        ),
        (
            "remote_v1",
            "1E.FF.56.55.18.87.52.B6.5F.2B.5E.00.FC.31.51.1C.50.9A.08.24.0A.0F.FC.B1.63.03.15.6D.9D.60.57",
            "cmd: 0x23, param: 0x00, args: [0,0,0]",
            "id: 0x00014057, index: 0, tx: 44, seed: 0xEF02",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 0.1, 'warm': 0.1}",
        ),
    ],
)
class TestEncoderFanlampNoReverse(_TestEncoderFull):
    """Fanlamp Encoder / Decoder No Reverse tests."""

    _with_reverse = False
