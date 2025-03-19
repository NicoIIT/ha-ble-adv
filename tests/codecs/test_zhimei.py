"""FanLamp pro Unit Tests."""

import pytest

from . import _TestEncoderBase, _TestEncoderFull


@pytest.mark.parametrize(
    _TestEncoderBase.PARAM_NAMES,
    [
        ("zhimei_fan_v0", 0x03, "55.02.01.02.C0.B4.AA.66.55.33"),
        ("zhimei_v2", 0x03, "F9.08.49.B2.CE.2C.81.3B.6B.90.08.CE.EF.3D.6F.C8.10.11.12.13.14.15.16.17.18.19"),
        ("zhimei_v1b", 0xFF, "58.55.18.48.46.4B.4A.1C.AB.1F.B8.0E.B7.E1.7D.98.82.31.A5.7E.7E.DB.68.10.11.12.13.14.15"),
    ],
)
class TestEncoderZhimei(_TestEncoderBase):
    """Zhi Mei Encoder tests."""


@pytest.mark.parametrize(
    _TestEncoderBase.PARAM_NAMES,
    [
        ("zhimei_fan_v1", 0x03, "48.46.4B.4A.8F.D3.A4.49.9B.44.6E.EA.23.F5.B6.36.0F.ED.8F.DE.10.11.12.13.14.15"),
        ("zhimei_v1", 0x03, "48.46.4B.4A.1C.AB.1F.B8.0E.B7.E1.7D.98.82.31.A5.7E.7E.DB.68.10.11.12.13.14.15"),
    ],
)
class TestEncoderZhimeiWithDupes(_TestEncoderBase):
    """Zhi Mei Encoder tests with duplicated."""

    _dupe_allowed = True


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # PAIR
        (
            "zhimei_fan_v1",
            "02.01.1A.1B.03.48.46.4B.4A.9E.18.A6.3A.8C.35.5F.FB.14.04.B8.27.00.FC.5C.F7.10.11.12.13.14.15",
            "cmd: 0xB4, param: 0x00, args: [170,102,85]",
            "id: 0x0000C002, index: 2, tx: 18, seed: 0x005B",
            "device_0: ['cmd'] / {'cmd': 'pair'}",
        ),
        (
            "zhimei_fan_v0",
            "02.01.19.0B.03.55.02.12.02.C0.B4.AA.66.55.44",
            "cmd: 0xB4, param: 0x00, args: [170,102,85]",
            "id: 0x0000C002, index: 2, tx: 18, seed: 0x0000",
            "device_0: ['cmd'] / {'cmd': 'pair'}",
        ),
        # TIMER 2H (120min / 7200s)
        (
            "zhimei_fan_v0",
            "02.01.19.0B.03.55.02.13.02.C0.D4.02.00.00.02",
            "cmd: 0xD4, param: 0x00, args: [2,0,0]",
            "id: 0x0000C002, index: 2, tx: 19, seed: 0x0000",
            "device_0: ['cmd'] / {'cmd': 'timer', 's': 120.0}",
        ),
        (
            "zhimei_fan_v1",
            "02.01.19.1B.03.48.46.4B.4A.8F.F5.96.49.9B.44.6E.0A.23.37.53.75.68.22.BC.CC.10.11.12.13.14.15",
            "cmd: 0xD4, param: 0x00, args: [2,0,0]",
            "id: 0x0000C002, index: 2, tx: 19, seed: 0x0037",
            "device_0: ['cmd'] / {'cmd': 'timer', 's': 120.0}",
        ),
        # MAIN LIGHT OFF
        (
            "zhimei_fan_v1",
            "02.01.19.1B.03.48.46.4B.4A.9E.27.A7.3A.8C.35.5F.ED.14.B1.CD.EA.F0.C8.01.7B.10.11.12.13.14.15",
            "cmd: 0xA6, param: 0x00, args: [1,0,0]",
            "id: 0x0000C002, index: 2, tx: 21, seed: 0x0068",
            "light_0: ['on'] / {'on': False}",
        ),
        (
            "zhimei_fan_v0",
            "02.01.19.0B.03.55.02.15.02.C0.A6.01.00.00.D5",
            "cmd: 0xA6, param: 0x00, args: [1,0,0]",
            "id: 0x0000C002, index: 2, tx: 21, seed: 0x0000",
            "light_0: ['on'] / {'on': False}",
        ),
        # MAIN LIGHT ON
        (
            "zhimei_fan_v1",
            "02.01.19.1B.03.48.46.4B.4A.7B.8F.C5.5D.AF.58.82.C8.37.DE.6D.BA.B9.83.38.6B.10.11.12.13.14.15",
            "cmd: 0xA6, param: 0x00, args: [2,0,0]",
            "id: 0x0000C002, index: 2, tx: 22, seed: 0x00E5",
            "light_0: ['on'] / {'on': True}",
        ),
        (
            "zhimei_fan_v0",
            "02.01.19.0B.03.55.02.16.02.C0.A6.02.00.00.D7",
            "cmd: 0xA6, param: 0x00, args: [2,0,0]",
            "id: 0x0000C002, index: 2, tx: 22, seed: 0x0000",
            "light_0: ['on'] / {'on': True}",
        ),
        # BR 0 %
        (
            "zhimei_fan_v1",
            "02.01.19.1B.03.48.46.4B.4A.78.17.C1.5C.B2.5B.85.D8.36.26.2E.52.77.5B.36.A5.10.11.12.13.14.15",
            "cmd: 0xB5, param: 0x00, args: [0,0,0]",
            "id: 0x0000C002, index: 2, tx: 25, seed: 0x007E",
            "light_0: ['br'] / {'sub_type': 'cww', 'br': 0.0}",
        ),
        (
            "zhimei_fan_v0",
            "02.01.19.0B.03.55.02.19.02.C0.B5.00.00.00.E7",
            "cmd: 0xB5, param: 0x00, args: [0,0,0]",
            "id: 0x0000C002, index: 2, tx: 25, seed: 0x0000",
            "light_0: ['br'] / {'sub_type': 'cww', 'br': 0.0}",
        ),
        # BR 100%
        (
            "zhimei_fan_v1",
            "02.01.19.1B.03.48.46.4B.4A.E4.DA.66.F0.C6.EF.19.B4.CA.5E.3D.CA.3A.B3.5A.12.10.11.12.13.14.15",
            "cmd: 0xB5, param: 0x00, args: [0,3,232]",
            "id: 0x0000C002, index: 2, tx: 24, seed: 0x00D7",
            "light_0: ['br'] / {'sub_type': 'cww', 'br': 1.0}",
        ),
        (
            "zhimei_fan_v0",
            "02.01.19.0B.03.55.02.18.02.C0.B5.00.03.E8.D1",
            "cmd: 0xB5, param: 0x00, args: [0,3,232]",
            "id: 0x0000C002, index: 2, tx: 24, seed: 0x0000",
            "light_0: ['br'] / {'sub_type': 'cww', 'br': 1.0}",
        ),
        # COLD
        (
            "zhimei_fan_v0",
            "02.01.19.0B.03.55.02.1E.02.C0.B7.00.03.E8.D9",
            "cmd: 0xB7, param: 0x00, args: [0,3,232]",
            "id: 0x0000C002, index: 2, tx: 30, seed: 0x0000",
            "light_0: ['ctr'] / {'sub_type': 'cww', 'ctr': 1.0}",
        ),
        (
            "zhimei_fan_v1",
            "02.01.19.1B.03.48.46.4B.4A.07.CF.49.D1.23.CC.F6.55.AB.22.39.48.7C.EF.07.88.10.11.12.13.14.15",
            "cmd: 0xB7, param: 0x00, args: [0,3,232]",
            "id: 0x0000C002, index: 2, tx: 30, seed: 0x00A9",
            "light_0: ['ctr'] / {'sub_type': 'cww', 'ctr': 1.0}",
        ),
        # WARM
        (
            "zhimei_fan_v1",
            "02.01.19.1B.03.48.46.4B.4A.16.FF.3B.C2.14.BD.E7.64.9C.C1.D9.EB.E0.D8.5D.CB.10.11.12.13.14.15",
            "cmd: 0xB7, param: 0x00, args: [0,0,0]",
            "id: 0x0000C002, index: 2, tx: 33, seed: 0x00A8",
            "light_0: ['ctr'] / {'sub_type': 'cww', 'ctr': 0.0}",
        ),
        (
            "zhimei_fan_v0",
            "02.01.19.0B.03.55.02.21.02.C0.B7.00.00.00.F1",
            "cmd: 0xB7, param: 0x00, args: [0,0,0]",
            "id: 0x0000C002, index: 2, tx: 33, seed: 0x0000",
            "light_0: ['ctr'] / {'sub_type': 'cww', 'ctr': 0.0}",
        ),
        # FAN Speed 2/6
        (
            "zhimei_fan_v0",
            "02.01.19.0B.03.55.02.22.02.C0.D3.02.00.00.10",
            "cmd: 0xD3, param: 0x00, args: [2,0,0]",
            "id: 0x0000C002, index: 2, tx: 34, seed: 0x0000",
            "fan_0: ['on', 'speed'] / {'sub_type': '6speed', 'on': True, 'speed': 2.0}",
        ),
        (
            "zhimei_fan_v1",
            "02.01.19.1B.03.48.46.4B.4A.9E.82.B6.3A.8C.35.5F.18.14.3A.7F.80.63.4F.29.AB.10.11.12.13.14.15",
            "cmd: 0xD3, param: 0x00, args: [2,0,0]",
            "id: 0x0000C002, index: 2, tx: 34, seed: 0x00B5",
            "fan_0: ['on', 'speed'] / {'sub_type': '6speed', 'on': True, 'speed': 2.0}",
        ),
        # FAN OFF
        (
            "zhimei_fan_v1",
            "02.01.19.1B.03.48.46.4B.4A.51.7A.09.83.59.82.AC.C5.5D.B7.DE.D3.E8.3A.33.E0.10.11.12.13.14.15",
            "cmd: 0xD1, param: 0x00, args: [0,0,0]",
            "id: 0x0000C002, index: 2, tx: 40, seed: 0x00E2",
            "fan_0: ['on'] / {'on': False}",
        ),
        (
            "zhimei_fan_v0",
            "02.01.19.0B.03.55.02.28.02.C0.D1.00.00.00.12",
            "cmd: 0xD1, param: 0x00, args: [0,0,0]",
            "id: 0x0000C002, index: 2, tx: 40, seed: 0x0000",
            "fan_0: ['on'] / {'on': False}",
        ),
        # FAN Direction Reverse
        (
            "zhimei_fan_v0",
            "02.01.1A.0B.03.55.02.2B.02.C0.DA.00.00.00.1E",
            "cmd: 0xDA, param: 0x00, args: [0,0,0]",
            "id: 0x0000C002, index: 2, tx: 43, seed: 0x0000",
            "fan_0: ['dir'] / {'dir': False}",
        ),
        (
            "zhimei_fan_v1",
            "02.01.1A.1B.03.48.46.4B.4A.69.A3.A0.6B.C1.6A.94.22.45.BB.AB.3F.E4.A6.5C.D3.10.11.12.13.14.15",
            "cmd: 0xDA, param: 0x00, args: [0,0,0]",
            "id: 0x0000C002, index: 2, tx: 43, seed: 0x00E3",
            "fan_0: ['dir'] / {'dir': False}",
        ),
        # FAN Direction Forward
        (
            "zhimei_fan_v1",
            "02.01.19.1B.03.48.46.4B.4A.1C.AB.2C.B8.0E.B7.E1.90.92.CA.E3.EE.D3.BF.0C.66.10.11.12.13.14.15",
            "cmd: 0xD9, param: 0x00, args: [0,0,0]",
            "id: 0x0000C002, index: 2, tx: 42, seed: 0x006E",
            "fan_0: ['dir'] / {'dir': True}",
        ),
        (
            "zhimei_fan_v0",
            "02.01.19.0B.03.55.02.2A.02.C0.D9.00.00.00.1C",
            "cmd: 0xD9, param: 0x00, args: [0,0,0]",
            "id: 0x0000C002, index: 2, tx: 42, seed: 0x0000",
            "fan_0: ['dir'] / {'dir': True}",
        ),
        # FAN Oscillation ON
        (
            "zhimei_fan_v1",
            "02.01.19.1B.03.48.46.4B.4A.7B.53.9F.5D.AF.58.82.30.37.C8.09.33.D7.B9.AE.77.10.11.12.13.14.15",
            "cmd: 0xDE, param: 0x00, args: [1,0,0]",
            "id: 0x0000C002, index: 2, tx: 56, seed: 0x00A1",
            "fan_0: ['osc'] / {'osc': True}",
        ),
        (
            "zhimei_fan_v0",
            "02.01.19.0B.03.55.02.38.02.C0.DE.01.00.00.30",
            "cmd: 0xDE, param: 0x00, args: [1,0,0]",
            "id: 0x0000C002, index: 2, tx: 56, seed: 0x0000",
            "fan_0: ['osc'] / {'osc': True}",
        ),
        # FAN Oscillation OFF
        (
            "zhimei_fan_v0",
            "02.01.19.0B.03.55.02.2E.02.C0.DE.02.00.00.27",
            "cmd: 0xDE, param: 0x00, args: [2,0,0]",
            "id: 0x0000C002, index: 2, tx: 46, seed: 0x0000",
            "fan_0: ['osc'] / {'osc': False}",
        ),
        (
            "zhimei_fan_v1",
            "02.01.19.1B.03.48.46.4B.4A.78.B0.8C.5C.B2.5B.85.2F.36.51.28.09.4C.10.E8.97.10.11.12.13.14.15",
            "cmd: 0xDE, param: 0x00, args: [2,0,0]",
            "id: 0x0000C002, index: 2, tx: 46, seed: 0x00C5",
            "fan_0: ['osc'] / {'osc': False}",
        ),
    ],
)
class TestEncoderZhimeiFanFull(_TestEncoderFull):
    """Zhi Mei Fan Encoder / Decoder Fan Full tests."""


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # Night Mode (No Direct)
        (
            "zhimei_fan_v0",
            "02.01.19.0B.03.55.02.39.02.C0.A1.19.19.00.25",
            "cmd: 0xA1, param: 0x00, args: [25,25,0]",
            "id: 0x0000C002, index: 2, tx: 57, seed: 0x0000",
            "light_0: [] / {'sub_type': 'cww', 'cold': 0.1, 'warm': 0.1}",
        ),
        (
            "zhimei_fan_v1",
            "02.01.19.1B.03.48.46.4B.4A.1C.58.3D.B8.0E.B7.E1.68.92.82.4A.3F.24.E7.13.F8.10.11.12.13.14.15",
            "cmd: 0xA1, param: 0x00, args: [25,25,0]",
            "id: 0x0000C002, index: 2, tx: 57, seed: 0x0019",
            "light_0: [] / {'sub_type': 'cww', 'cold': 0.1, 'warm': 0.1}",
        ),
        # Button Switch COLD
        (
            "zhimei_fan_v0",
            "02.01.19.0B.03.55.02.3C.02.C0.A7.01.00.00.FD",
            "cmd: 0xA7, param: 0x00, args: [1,0,0]",
            "id: 0x0000C002, index: 2, tx: 60, seed: 0x0000",
            "light_0: [] / {'sub_type': 'cww', 'cold': 1, 'warm': 0}",
        ),
        (
            "zhimei_fan_v1",
            "02.01.19.1B.03.48.46.4B.4A.78.C1.9E.5C.B2.5B.85.C6.36.A9.0E.CE.F4.D8.61.20.10.11.12.13.14.15",
            "cmd: 0xA7, param: 0x00, args: [1,0,0]",
            "id: 0x0000C002, index: 2, tx: 60, seed: 0x00D4",
            "light_0: [] / {'sub_type': 'cww', 'cold': 1, 'warm': 0}",
        ),
        # Button Switch WARM
        (
            "zhimei_fan_v0",
            "02.01.1A.0B.03.55.02.3D.02.C0.A7.02.00.00.FF",
            "cmd: 0xA7, param: 0x00, args: [2,0,0]",
            "id: 0x0000C002, index: 2, tx: 61, seed: 0x0000",
            "light_0: [] / {'sub_type': 'cww', 'cold': 0, 'warm': 1}",
        ),
        (
            "zhimei_fan_v1",
            "02.01.1A.1B.03.48.46.4B.4A.B2.89.53.26.F8.21.4B.90.00.5A.32.18.43.87.14.A1.10.11.12.13.14.15",
            "cmd: 0xA7, param: 0x00, args: [2,0,0]",
            "id: 0x0000C002, index: 2, tx: 61, seed: 0x0036",
            "light_0: [] / {'sub_type': 'cww', 'cold': 0, 'warm': 1}",
        ),
        # Button Switch NATURAL
        (
            "zhimei_fan_v1",
            "02.01.1A.1B.03.48.46.4B.4A.0A.8E.31.CE.20.C9.F3.78.A8.B8.DE.C7.E5.A9.AE.FE.10.11.12.13.14.15",
            "cmd: 0xA7, param: 0x00, args: [3,0,0]",
            "id: 0x0000C002, index: 2, tx: 59, seed: 0x0055",
            "light_0: [] / {'sub_type': 'cww', 'cold': 1, 'warm': 1}",
        ),
        (
            "zhimei_fan_v0",
            "02.01.19.0B.03.55.02.3B.02.C0.A7.03.00.00.FE",
            "cmd: 0xA7, param: 0x00, args: [3,0,0]",
            "id: 0x0000C002, index: 2, tx: 59, seed: 0x0000",
            "light_0: [] / {'sub_type': 'cww', 'cold': 1, 'warm': 1}",
        ),
    ],
)
class TestEncoderZhimeiFanNoReverse(_TestEncoderFull):
    """Zhi Mei Fan Encoder / Decoder Fan No Reverse tests."""

    _with_reverse = False


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # PAIR
        (
            "zhimei_v2",
            "02.01.19.1B.03.F9.08.49.B2.CE.2C.9A.20.75.8B.15.D5.EF.26.C1.35.10.11.12.13.14.15.16.17.18.19",
            "cmd: 0xB4, param: 0x00, args: [0,0,0]",
            "id: 0x000002C0, index: 4, tx: 31, seed: 0x0000",
            "device_0: ['cmd'] / {'cmd': 'pair'}",
        ),
        (
            "zhimei_v1",
            "02.01.19.1B.03.48.46.4B.4A.1C.AB.1F.B8.0E.B7.E1.7D.98.82.31.A5.7E.7E.DB.68.10.11.12.13.14.15",
            "cmd: 0xB4, param: 0x00, args: [170,102,85]",
            "id: 0x0000C002, index: 4, tx: 31, seed: 0x006E",
            "device_0: ['cmd'] / {'cmd': 'pair'}",
        ),
        # TIMER 2H (120min / 7200s)
        (
            "zhimei_v1",
            "02.01.19.1B.03.48.46.4B.4A.1C.49.36.B8.0E.B7.E1.6C.98.C8.F3.E6.D5.B1.90.BA.10.11.12.13.14.15",
            "cmd: 0xA5, param: 0x00, args: [2,0,0]",
            "id: 0x0000C002, index: 4, tx: 32, seed: 0x0008",
            "device_0: ['cmd'] / {'cmd': 'timer', 's': 120.0}",
        ),
        (
            "zhimei_v2",
            "02.01.19.1B.03.F9.08.49.B2.CE.2C.A5.1D.4A.B4.3B.EA.EF.1B.94.D2.10.11.12.13.14.15.16.17.18.19",
            "cmd: 0xA5, param: 0x00, args: [2,0,0]",
            "id: 0x000002C0, index: 4, tx: 32, seed: 0x0000",
            "device_0: ['cmd'] / {'cmd': 'timer', 's': 120.0}",
        ),
        # MAIN LIGHT OFF
        (
            "zhimei_v2",
            "02.01.19.1B.03.F9.08.49.B2.CE.2C.A7.1D.48.B6.2E.E8.EF.1B.6B.DF.10.11.12.13.14.15.16.17.18.19",
            "cmd: 0xB2, param: 0x00, args: [0,0,0]",
            "id: 0x000002C0, index: 4, tx: 34, seed: 0x0000",
            "light_0: ['on'] / {'on': False}",
        ),
        (
            "zhimei_v1",
            "02.01.1A.1B.03.48.46.4B.4A.69.92.A7.6B.C1.6A.94.CA.43.29.72.51.76.38.CE.1E.10.11.12.13.14.15",
            "cmd: 0xB2, param: 0x00, args: [0,0,0]",
            "id: 0x0000C002, index: 4, tx: 34, seed: 0x00F2",
            "light_0: ['on'] / {'on': False}",
        ),
        # MAIN LIGHT ON
        (
            "zhimei_v1",
            "02.01.19.1B.03.48.46.4B.4A.9E.A0.B3.3A.8C.35.5F.F8.16.39.41.83.68.40.96.14.10.11.12.13.14.15",
            "cmd: 0xB3, param: 0x00, args: [0,0,0]",
            "id: 0x0000C002, index: 4, tx: 33, seed: 0x00D3",
            "light_0: ['on'] / {'on': True}",
        ),
        (
            "zhimei_v2",
            "02.01.19.1B.03.F9.08.49.B2.CE.2C.A4.1E.4B.B5.2C.EB.EF.18.ED.08.10.11.12.13.14.15.16.17.18.19",
            "cmd: 0xB3, param: 0x00, args: [0,0,0]",
            "id: 0x000002C0, index: 4, tx: 33, seed: 0x0000",
            "light_0: ['on'] / {'on': True}",
        ),
        # BR 0 %
        (
            "zhimei_v1",
            "02.01.19.1B.03.48.46.4B.4A.E1.E2.70.F3.C9.F2.1C.B1.CB.06.B2.A0.95.EB.AC.D7.10.11.12.13.14.15",
            "cmd: 0xB5, param: 0x00, args: [0,0,0]",
            "id: 0x0000C002, index: 4, tx: 35, seed: 0x00DA",
            "light_0: ['br'] / {'sub_type': 'cww', 'br': 0.0}",
        ),
        (
            "zhimei_v2",
            "02.01.19.1B.03.F9.08.49.B2.CE.2C.A6.1C.49.B7.28.E9.EF.1A.A1.CE.10.11.12.13.14.15.16.17.18.19",
            "cmd: 0xB5, param: 0x00, args: [0,0,0]",
            "id: 0x000002C0, index: 4, tx: 35, seed: 0x0000",
            "light_0: ['br'] / {'sub_type': 'cww', 'br': 0.0}",
        ),
        # BR 100%
        (
            "zhimei_v1",
            "02.01.19.1B.03.48.46.4B.4A.9E.09.B8.3A.8C.35.5F.FA.16.21.4E.7B.71.E0.31.45.10.11.12.13.14.15",
            "cmd: 0xB5, param: 0x00, args: [0,3,232]",
            "id: 0x0000C002, index: 4, tx: 36, seed: 0x004A",
            "light_0: ['br'] / {'sub_type': 'cww', 'br': 1.0}",
        ),
        (
            "zhimei_v2",
            "02.01.19.1B.03.F9.08.49.B2.CE.2C.49.F3.A6.5B.C7.06.07.1D.23.A9.10.11.12.13.14.15.16.17.18.19",
            "cmd: 0xB5, param: 0x00, args: [0,3,232]",
            "id: 0x000002C0, index: 4, tx: 36, seed: 0x0000",
            "light_0: ['br'] / {'sub_type': 'cww', 'br': 1.0}",
        ),
        # COLD
        (
            "zhimei_v2",
            "02.01.19.1B.03.F9.08.49.B2.CE.2C.48.F2.A7.5A.C4.07.07.1C.BE.D6.10.11.12.13.14.15.16.17.18.19",
            "cmd: 0xB7, param: 0x00, args: [0,3,232]",
            "id: 0x000002C0, index: 4, tx: 37, seed: 0x0000",
            "light_0: ['ctr'] / {'sub_type': 'cww', 'ctr': 1.0}",
        ),
        (
            "zhimei_v1",
            "02.01.19.1B.03.48.46.4B.4A.E4.8F.71.F0.C6.EF.19.B2.D0.4D.69.63.51.94.4A.DB.10.11.12.13.14.15",
            "cmd: 0xB7, param: 0x00, args: [0,3,232]",
            "id: 0x0000C002, index: 4, tx: 37, seed: 0x000A",
            "light_0: ['ctr'] / {'sub_type': 'cww', 'ctr': 1.0}",
        ),
        # WARM
        (
            "zhimei_v1",
            "02.01.19.1B.03.48.46.4B.4A.99.F8.B3.3B.91.3A.64.F7.13.B2.01.E4.E9.CF.B1.3C.10.11.12.13.14.15",
            "cmd: 0xB7, param: 0x00, args: [0,0,0]",
            "id: 0x0000C002, index: 4, tx: 38, seed: 0x003C",
            "light_0: ['ctr'] / {'sub_type': 'cww', 'ctr': 0.0}",
        ),
        (
            "zhimei_v2",
            "02.01.19.1B.03.F9.08.49.B2.CE.2C.A3.19.4C.B2.2F.EC.EF.1F.81.A2.10.11.12.13.14.15.16.17.18.19",
            "cmd: 0xB7, param: 0x00, args: [0,0,0]",
            "id: 0x000002C0, index: 4, tx: 38, seed: 0x0000",
            "light_0: ['ctr'] / {'sub_type': 'cww', 'ctr': 0.0}",
        ),
        # RGB Second Light RED (nearly...)
        (
            "zhimei_v2",
            "02.01.19.1B.03.F9.08.49.B2.CE.2C.9B.DE.74.99.6A.D4.EF.D8.7C.AF.10.11.12.13.14.15.16.17.18.19",
            "cmd: 0xCA, param: 0x00, args: [255,19,0]",
            "id: 0x000002C0, index: 4, tx: 30, seed: 0x0000",
            "light_1: ['rf', 'gf', 'bf'] / {'sub_type': 'rgb', 'rf': 1.0, 'gf': 0.07450980392156863, 'bf': 0.0}",
        ),
        (
            "zhimei_v1",
            "02.01.19.1B.03.48.46.4B.4A.51.20.D3.83.59.82.AC.DA.5B.F0.07.95.9E.E1.7F.1D.10.11.12.13.14.15",
            "cmd: 0xCA, param: 0x00, args: [255,19,0]",
            "id: 0x0000C002, index: 4, tx: 30, seed: 0x000C",
            "light_1: ['rf', 'gf', 'bf'] / {'sub_type': 'rgb', 'rf': 1.0, 'gf': 0.07450980392156863, 'bf': 0.0}",
        ),
        # Second Light ON
        (
            "zhimei_v1",
            "02.01.19.1B.03.48.46.4B.4A.07.F1.13.D1.23.CC.F6.44.AD.6D.54.3B.32.0C.9F.CA.10.11.12.13.14.15",
            "cmd: 0xA6, param: 0x00, args: [2,0,0]",
            "id: 0x0000C002, index: 4, tx: 40, seed: 0x008B",
            "light_1: ['on'] / {'on': True}",
        ),
        (
            "zhimei_v2",
            "02.01.19.1B.03.F9.08.49.B2.CE.2C.AD.15.42.BC.30.E2.EF.13.23.D0.10.11.12.13.14.15.16.17.18.19",
            "cmd: 0xA6, param: 0x00, args: [2,0,0]",
            "id: 0x000002C0, index: 4, tx: 40, seed: 0x0000",
            "light_1: ['on'] / {'on': True}",
        ),
        # Second Light OFF
        (
            "zhimei_v1",
            "02.01.19.1B.03.48.46.4B.4A.E4.FC.6F.F0.C6.EF.19.A3.D0.1C.DA.0D.81.DD.3A.2D.10.11.12.13.14.15",
            "cmd: 0xA6, param: 0x00, args: [1,0,0]",
            "id: 0x0000C002, index: 4, tx: 39, seed: 0x00F5",
            "light_1: ['on'] / {'on': False}",
        ),
        (
            "zhimei_v2",
            "02.01.19.1B.03.F9.08.49.B2.CE.2C.A2.19.4D.B3.3F.ED.EF.1F.2C.B5.10.11.12.13.14.15.16.17.18.19",
            "cmd: 0xA6, param: 0x00, args: [1,0,0]",
            "id: 0x000002C0, index: 4, tx: 39, seed: 0x0000",
            "light_1: ['on'] / {'on': False}",
        ),
    ],
)
class TestEncoderZhimeiFull(_TestEncoderFull):
    """Zhi Mei Fan Encoder / Decoder Full tests."""


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # Night Mode (No Direct)
        (
            "zhimei_v2",
            "02.01.19.1B.03.F9.08.49.B2.CE.2C.B6.15.5C.BE.2C.F9.EF.13.0B.B9.10.11.12.13.14.15.16.17.18.19",
            "cmd: 0xA1, param: 0x00, args: [25,25,0]",
            "id: 0x000002C0, index: 1, tx: 51, seed: 0x0000",
            "light_0: [] / {'sub_type': 'cww', 'cold': 0.1, 'warm': 0.1}",
        ),
        (
            "zhimei_v1",
            "02.01.19.1B.03.48.46.4B.4A.FF.B0.26.D9.2B.D4.FE.47.B2.9B.0F.F6.FB.AE.DD.F0.10.11.12.13.14.15",
            "cmd: 0xA1, param: 0x00, args: [25,25,0]",
            "id: 0x0000C002, index: 1, tx: 51, seed: 0x0042",
            "light_0: [] / {'sub_type': 'cww', 'cold': 0.1, 'warm': 0.1}",
        ),
        # Button Switch COLD
        (
            "zhimei_v1",
            "02.01.19.1B.03.48.46.4B.4A.7B.ED.8E.5D.AF.58.82.C9.36.B6.AE.3D.E1.0B.65.68.10.11.12.13.14.15",
            "cmd: 0xA7, param: 0x00, args: [1,0,0]",
            "id: 0x0000C002, index: 1, tx: 47, seed: 0x000B",
            "light_0: [] / {'sub_type': 'cww', 'cold': 1, 'warm': 0}",
        ),
        (
            "zhimei_v2",
            "02.01.19.1B.03.F9.08.49.B2.CE.2C.AA.11.40.BB.36.E5.EF.17.6A.9A.10.11.12.13.14.15.16.17.18.19",
            "cmd: 0xA7, param: 0x00, args: [1,0,0]",
            "id: 0x000002C0, index: 1, tx: 47, seed: 0x0000",
            "light_0: [] / {'sub_type': 'cww', 'cold': 1, 'warm': 0}",
        ),
        # Button Switch WARM
        (
            "zhimei_v2",
            "02.01.19.1B.03.F9.08.49.B2.CE.2C.B5.0D.5F.A4.29.FA.EF.0B.91.B1.10.11.12.13.14.15.16.17.18.19",
            "cmd: 0xA7, param: 0x00, args: [2,0,0]",
            "id: 0x000002C0, index: 1, tx: 48, seed: 0x0000",
            "light_0: [] / {'sub_type': 'cww', 'cold': 0, 'warm': 1}",
        ),
        (
            "zhimei_v1",
            "02.01.19.1B.03.48.46.4B.4A.0A.85.38.CE.20.C9.F3.78.A5.CD.BE.E9.D4.D4.EC.38.10.11.12.13.14.15",
            "cmd: 0xA7, param: 0x00, args: [2,0,0]",
            "id: 0x0000C002, index: 1, tx: 48, seed: 0x0022",
            "light_0: [] / {'sub_type': 'cww', 'cold': 0, 'warm': 1}",
        ),
        # Button Switch NATURAL
        (
            "zhimei_v2",
            "02.01.19.1B.03.F9.08.49.B2.CE.2C.B4.0D.5E.A5.28.FB.EF.0B.26.79.10.11.12.13.14.15.16.17.18.19",
            "cmd: 0xA7, param: 0x00, args: [3,0,0]",
            "id: 0x000002C0, index: 1, tx: 49, seed: 0x0000",
            "light_0: [] / {'sub_type': 'cww', 'cold': 1, 'warm': 1}",
        ),
        (
            "zhimei_v1",
            "02.01.19.1B.03.48.46.4B.4A.16.FF.2B.C2.14.BD.E7.74.99.AE.FA.FD.EF.AB.7A.6E.10.11.12.13.14.15",
            "cmd: 0xA7, param: 0x00, args: [3,0,0]",
            "id: 0x0000C002, index: 1, tx: 49, seed: 0x00A8",
            "light_0: [] / {'sub_type': 'cww', 'cold': 1, 'warm': 1}",
        ),
    ],
)
class TestEncoderZhimeiNoReverse(_TestEncoderFull):
    """Zhi Mei Fan Encoder / Decoder No Reverse tests."""

    _with_reverse = False
