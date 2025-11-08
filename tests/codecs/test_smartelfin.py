"""Smart Elfin Unit Tests."""

import pytest

from . import _TestEncoderBase, _TestEncoderBaseSec, _TestEncoderFull


@pytest.mark.parametrize(
    _TestEncoderBase.PARAM_NAMES,
    [
        ("fanlamp_pro_v3/se", 0x03, "F0081080822A727FB6B7541A6D2BB6A6AF675C904775906DAB03"),
    ],
)
class TestEncoderSmartElfin(_TestEncoderBase):
    """Smart Elfin Encoder tests."""


@pytest.mark.parametrize(
    _TestEncoderBaseSec.PARAM_NAMES,
    [
        ("smartelfin_v0", 0x07, "5746545895B13D3864E5E3BA00FB0103", 0x16, "000084C7B141C2F7"),
    ],
)
class TestEncoderSmartElfin2(_TestEncoderBaseSec):
    """Smart Elfin Encoder tests."""


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # PAIR
        (
            "smartelfin_v0",
            "02011A1107574654585C5B7F3064E5E3BA00FB01030916358D8BF900F18805",
            "cmd: 0xFB, param: 0x00, args: [1,3,0]",
            "id: 0x007F5B5C, index: 0, tx: 48, seed: 0x0000",
            "device_0: ['cmd'] / {'cmd': 'pair'}",
        ),
        # UNPAIR
        (
            "smartelfin_v0",
            "02011A1107574654585C5B7F2E64E5E3BA00FD01000916349D57E02F1D1327",
            "cmd: 0xFD, param: 0x00, args: [1,0,0]",
            "id: 0x007F5B5C, index: 0, tx: 46, seed: 0x0000",
            "device_0: ['cmd'] / {'cmd': 'unpair'}",
        ),
        # Main Light ON
        (
            "smartelfin_v0",
            "02011A1107574654585C5B7F0864E5E3BA0F03010109164A49868C42440149",
            "cmd: 0x03, param: 0x0F, args: [1,1,0]",
            "id: 0x007F5B5C, index: 0, tx: 8, seed: 0x0000",
            "light_0: ['on'] / {'on': True}",
        ),
        # Main Light OFF
        (
            "smartelfin_v0",
            "02011A1107574654585C5B7F0A64E5E3BA0F030100091649396E2747B7E681",
            "cmd: 0x03, param: 0x0F, args: [1,0,0]",
            "id: 0x007F5B5C, index: 0, tx: 10, seed: 0x0000",
            "light_0: ['on'] / {'on': False}",
        ),
        # Full COLD
        (
            "smartelfin_v0",
            "02011A1107574654585C5B7F0464E5E3BA000F01640916AAB4934C4A02484F",
            "cmd: 0x0F, param: 0x00, args: [1,100,0]",
            "id: 0x007F5B5C, index: 0, tx: 4, seed: 0x0000",
            "light_0: ['ctr'] / {'sub_type': 'cww', 'ctr': 1.0}",
        ),
        # Full WARM
        (
            "smartelfin_v0",
            "02011A1107574654585C5B7F0664E5E3BA000F0100091646BF491CDB901368",
            "cmd: 0x0F, param: 0x00, args: [1,0,0]",
            "id: 0x007F5B5C, index: 0, tx: 6, seed: 0x0000",
            "light_0: ['ctr'] / {'sub_type': 'cww', 'ctr': 0.0}",
        ),
        # Second Light ON (NOT CONFIRMED)
        (
            "smartelfin_v0",
            "02011A1107574654585C5B7F2664E5E3BA0F06010109164D58B880F5FA1DBE",
            "cmd: 0x06, param: 0x0F, args: [1,1,0]",
            "id: 0x007F5B5C, index: 0, tx: 38, seed: 0x0000",
            "light_1: ['on'] / {'on': True}",
        ),
        # Second Light OFF (NOT CONFIRMED)
        (
            "smartelfin_v0",
            "02011A1107574654585C5B7F2864E5E3BA0F06010009164C8B65DD5EBA3148",
            "cmd: 0x06, param: 0x0F, args: [1,0,0]",
            "id: 0x007F5B5C, index: 0, tx: 40, seed: 0x0000",
            "light_1: ['on'] / {'on': False}",
        ),
        # Fan Speed 1
        (
            "smartelfin_v0",
            "02011A1107574654585C5B7F5064E5E3BA0002010A09164399E5675BBFE7F5",
            "cmd: 0x02, param: 0x00, args: [1,10,0]",
            "id: 0x007F5B5C, index: 0, tx: 80, seed: 0x0000",
            "fan_0: ['on', 'speed'] / {'speed_count': 6, 'on': True, 'speed': 1.0}",
        ),
        # Fan Speed 6
        (
            "smartelfin_v0",
            "02011A1107574654585C5B7F5464E5E3BA0002013C0916754FDE2549B35C8A",
            "cmd: 0x02, param: 0x00, args: [1,60,0]",
            "id: 0x007F5B5C, index: 0, tx: 84, seed: 0x0000",
            "fan_0: ['on', 'speed'] / {'speed_count': 6, 'on': True, 'speed': 6.0}",
        ),
        # Fan OFF
        (
            "smartelfin_v0",
            "02011A1107574654585C5B7F5664E5E3BA00020100091639998DFB7F217045",
            "cmd: 0x02, param: 0x00, args: [1,0,0]",
            "id: 0x007F5B5C, index: 0, tx: 86, seed: 0x0000",
            "fan_0: ['on'] / {'speed_count': 6, 'on': False}",
        ),
        # Fan OSC ON
        (
            "smartelfin_v0",
            "02011A1107574654585C5B7F6E64E5E3BA0F05010109164C6C5D178043F843",
            "cmd: 0x05, param: 0x0F, args: [1,1,0]",
            "id: 0x007F5B5C, index: 0, tx: 110, seed: 0x0000",
            "fan_0: ['osc'] / {'osc': True}",
        ),
        # Fan OSC OFF
        (
            "smartelfin_v0",
            "02011A1107574654585C5B7F7064E5E3BA0F05010009164BDEB16F24113D8C",
            "cmd: 0x05, param: 0x0F, args: [1,0,0]",
            "id: 0x007F5B5C, index: 0, tx: 112, seed: 0x0000",
            "fan_0: ['osc'] / {'osc': False}",
        ),
        # Fan DIR FORWARD
        (
            "smartelfin_v0",
            "02011A1107574654585C5B7F7264E5E3BA0F04010109164B063DEF5F344D83",
            "cmd: 0x04, param: 0x0F, args: [1,1,0]",
            "id: 0x007F5B5C, index: 0, tx: 114, seed: 0x0000",
            "fan_0: ['dir'] / {'dir': True}",
        ),
        # FAN DIR REVERSE
        (
            "smartelfin_v0",
            "02011A1107574654585C5B7F7464E5E3BA0F04010209164CB56F4556E16976",
            "cmd: 0x04, param: 0x0F, args: [1,2,0]",
            "id: 0x007F5B5C, index: 0, tx: 116, seed: 0x0000",
            "fan_0: ['dir'] / {'dir': False}",
        ),
        # Fan PRESET SLEEP
        (
            "smartelfin_v0",
            "02011A1107574654585C5B7F8A64E5E3BA0F010102091649F70F4A690BF99B",
            "cmd: 0x01, param: 0x0F, args: [1,2,0]",
            "id: 0x007F5B5C, index: 0, tx: 138, seed: 0x0000",
            "fan_0: ['preset'] / {'preset': 'sleep'}",
        ),
        # Fan PRESET BREEZE
        (
            "smartelfin_v0",
            "02011A1107574654585C5B7F8864E5E3BA0F01010109164828D0B500878AD7",
            "cmd: 0x01, param: 0x0F, args: [1,1,0]",
            "id: 0x007F5B5C, index: 0, tx: 136, seed: 0x0000",
            "fan_0: ['preset'] / {'preset': 'breeze'}",
        ),
        # NOT IMPLEMENTED APP SHORTCUTS
        # //("smartelfin_v0","02011A1107574654585C5B7F8C64E5E3BA0F07010009164DF1A546110D9DC5","cmd: 0x07, param: 0x0F, args: [1,0,0]","id: 0x007F5B5C, index: 0, tx: 140, seed: 0x0000","")
        # //("smartelfin_v0","02011A1107574654585C5B7F8E64E5E3BA0F07010109164E34CE15AB601C1C","cmd: 0x07, param: 0x0F, args: [1,1,0]","id: 0x007F5B5C, index: 0, tx: 142, seed: 0x0000","")
        # //("smartelfin_v0","02011A1107574654585C5B7F9064E5E3BA0F08010009164E27B778BB320C8D","cmd: 0x08, param: 0x0F, args: [1,0,0]","id: 0x007F5B5C, index: 0, tx: 144, seed: 0x0000","")
        # //("smartelfin_v0","02011A1107574654585C5B7F9264E5E3BA0F08010109164FD916B2BFE5718A","cmd: 0x08, param: 0x0F, args: [1,1,0]","id: 0x007F5B5C, index: 0, tx: 146, seed: 0x0000","")
    ],
)
class TestEncoderSmartElfinFull(_TestEncoderFull):
    """Fanlamp Encoder / Decoder Full tests."""


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # Timer 2H
        (
            "smartelfin_v0",
            "02011A1107574654585C5B7FA864E5E3BA0009020009163B7CE0995C1D456F",
            "cmd: 0x09, param: 0x00, args: [2,0,0]",
            "id: 0x007F5B5C, index: 0, tx: 168, seed: 0x0000",
            "device_0: ['cmd'] / {'cmd': 'timer', 's': 7200}",
        ),
        # Timer 4H
        (
            "smartelfin_v0",
            "02011A1107574654585C5B7FAA64E5E3BA000902010916DF2192D3432366AA",
            "cmd: 0x09, param: 0x00, args: [2,1,0]",
            "id: 0x007F5B5C, index: 0, tx: 170, seed: 0x0000",
            "device_0: ['cmd'] / {'cmd': 'timer', 's': 14400}",
        ),
        # Night Mode button
        (
            "smartelfin_v0",
            "02011A1107574654585C5B7F3364E5E3BA00130205091605552371629F0F88",
            "cmd: 0x13, param: 0x00, args: [2,5,0]",
            "id: 0x007F5B5C, index: 0, tx: 51, seed: 0x0000",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 0.1, 'warm': 0.1}",
        ),
        # Warm Light button
        (
            "smartelfin_v0",
            "02011A1107574654585C5B7F3764E5E3BA00130264091600AF2175C5B02818",
            "cmd: 0x13, param: 0x00, args: [2,100,0]",
            "id: 0x007F5B5C, index: 0, tx: 55, seed: 0x0000",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 0.0, 'warm': 1.0}",
        ),
        # Cold Light button
        (
            "smartelfin_v0",
            "02011A1107574654585C5B7F3B64E5E3BA00130200091664AF31127BFC0E64",
            "cmd: 0x13, param: 0x00, args: [2,0,0]",
            "id: 0x007F5B5C, index: 0, tx: 59, seed: 0x0000",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 1.0, 'warm': 0.0}",
        ),
        # Fan PRESET Reset
        (
            "smartelfin_v0",
            "02011A1107574654585C5B7F8664E5E3BA0F0101000916474D763AB46BB3FB",
            "cmd: 0x01, param: 0x0F, args: [1,0,0]",
            "id: 0x007F5B5C, index: 0, tx: 134, seed: 0x0000",
            "fan_0: ['preset'] / {'preset': None}",
        ),
        (
            "fanlamp_pro_v3/se",
            "02011A1B03F008108093E641A144C24BFC1CB29406646DA1DB8731861C3685",
            "cmd: 0x33, param: 0x00, args: [0,0,0]",
            "id: 0x7F5B5C01, index: 0, tx: 100, seed: 0x1C86",
            "fan_0: ['preset'] / {'preset': None}",
        ),
    ],
)
class TestEncoderSmartElfinNoReverse(_TestEncoderFull):
    """Smart Elfin Encoder / Decoder No Reverse tests."""

    _with_reverse = False


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # ALL OFF
        (
            "smartelfin_v0",
            "0201021107574654585F95501064E5E3BA000101000916000084C7B141C2F7",
            "cmd: 0x01, param: 0x00, args: [1,0,0]",
            "id: 0x0050955F, index: 0, tx: 16, seed: 0x0000",
            "device_0: ['on'] / {'on': False}",
        ),
        # Main Light Toggle
        (
            "smartelfin_v0",
            "0201021107574654585F95503F64E5E3BA0F0301020916000084C7B141C2F7",
            "cmd: 0x03, param: 0x0F, args: [1,2,0]",
            "id: 0x0050955F, index: 0, tx: 63, seed: 0x0000",
            "light_0: ['on'] / {'on': 'toggle'}",
        ),
        # BR+
        (
            "smartelfin_v0",
            "0201021107574654585F95507C64E5E3BA000C01010916000084C7B141C2F7",
            "cmd: 0x0C, param: 0x00, args: [1,1,0]",
            "id: 0x0050955F, index: 0, tx: 124, seed: 0x0000",
            "light_0: ['cmd'] / {'sub_type': 'cww', 'cmd': 'B+', 'step': 0.1}",
        ),
        # BR-
        (
            "smartelfin_v0",
            "0201021107574654585F95504364E5E3BA000C01020916000084C7B141C2F7",
            "cmd: 0x0C, param: 0x00, args: [1,2,0]",
            "id: 0x0050955F, index: 0, tx: 67, seed: 0x0000",
            "light_0: ['cmd'] / {'sub_type': 'cww', 'cmd': 'B-', 'step': 0.1}",
        ),
        # K+
        (
            "smartelfin_v0",
            "0201021107574654585F9550AF64E5E3BA000D01010916000084C7B141C2F7",
            "cmd: 0x0D, param: 0x00, args: [1,1,0]",
            "id: 0x0050955F, index: 0, tx: 175, seed: 0x0000",
            "light_0: ['cmd'] / {'sub_type': 'cww', 'cmd': 'K+', 'step': 0.1}",
        ),
        # K-
        (
            "smartelfin_v0",
            "0201021107574654585F9550DA64E5E3BA000D01020916000084C7B141C2F7",
            "cmd: 0x0D, param: 0x00, args: [1,2,0]",
            "id: 0x0050955F, index: 0, tx: 218, seed: 0x0000",
            "light_0: ['cmd'] / {'sub_type': 'cww', 'cmd': 'K-', 'step': 0.1}",
        ),
        # Fan DIR Toggle and FAN ON
        (
            "smartelfin_v0",
            "0201021107574654585F95501164E5E3BA0F0401030916000084C7B141C2F7",
            "cmd: 0x04, param: 0x0F, args: [1,3,0]",
            "id: 0x0050955F, index: 0, tx: 17, seed: 0x0000",
            "fan_0: ['dir', 'on'] / {'dir': 'toggle', 'on': True}",
        ),
        # Fan OSC Toggle
        (
            "smartelfin_v0",
            "0201021107574654585F95503964E5E3BA0F0501020916000084C7B141C2F7",
            "cmd: 0x05, param: 0x0F, args: [1,2,0]",
            "id: 0x0050955F, index: 0, tx: 57, seed: 0x0000",
            "fan_0: ['osc'] / {'osc': 'toggle'}",
        ),
    ],
)
class TestEncoderSmartElfinRemote(_TestEncoderFull):
    """Smart Elfin Encoder / Decoder Remote tests."""

    _with_reverse = False
