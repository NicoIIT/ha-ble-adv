"""RW Unit Tests."""

import pytest

from . import _TestEncoderBase, _TestEncoderFull


@pytest.mark.parametrize(
    _TestEncoderBase.PARAM_NAMES,
    [
        ("rwlight_mix", 0xFF, "DDB2DA6C9F017A34965ADCD5A6DBF7E8090371A774AE28E73764"),
        ("rwlight_mix/ios", 0x03, "DDB2DA6C9F017A34D668F12686E4C8270903718A747C280A8AD7"),
    ],
)
class TestEncoderRw(_TestEncoderBase):
    """RW Encoder tests."""


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # CWW ON
        (
            "rwlight_mix",
            "02011A1BFFDDB2DA6C9F017A342E0CA0A9DA8DA14E090371DB742D28323033",
            "cmd: 0x01, param: 0x00, args: [0,0,0]",
            "id: 0x00018B5D, index: 0, tx: 67, seed: 0x00BF",
            "light_0: ['on'] / {'on': True}",
        ),
        # CWW OFF
        (
            "rwlight_mix",
            "02011A1BFFDDB2DA6C9F017A34EB8920295A0824CB0903715B74AD28374656",
            "cmd: 0x02, param: 0x00, args: [0,0,0]",
            "id: 0x00018B5D, index: 0, tx: 66, seed: 0x001F",
            "light_0: ['on'] / {'on': False}",
        ),
        # CWW CT 50%
        (
            "rwlight_mix",
            "02011A1BFFDDB2DA6C9F017A3405794E4734F8D4970903713574C328A9ACA8",
            "cmd: 0x0C, param: 0x00, args: [53,0,0]",
            "id: 0x00018B5D, index: 0, tx: 52, seed: 0x0066",
            "light_0: ['ctr'] / {'sub_type': 'cww', 'ctr': 0.53}",
        ),
        # CWW CT FULL WHITE
        (
            "rwlight_mix",
            "02011A1BFFDDB2DA6C9F017A341D210E0774A08C4509037175748328B137B1",
            "cmd: 0x0C, param: 0x00, args: [100,0,0]",
            "id: 0x00018B5D, index: 0, tx: 54, seed: 0x007E",
            "light_0: ['ctr'] / {'sub_type': 'cww', 'ctr': 1.0}",
        ),
        # CWW BR 0%
        (
            "rwlight_mix",
            "02011A1BFFDDB2DA6C9F017A347C4EE0E99ACFE30C0903719B746D2830FE9A",
            "cmd: 0x0B, param: 0x00, args: [0,0,0]",
            "id: 0x00018B5D, index: 0, tx: 65, seed: 0x00FF",
            "light_0: ['br'] / {'sub_type': 'cww', 'br': 0.0}",
        ),
        # CWW BR 100%
        (
            "rwlight_mix",
            "02011A1BFFDDB2DA6C9F017A3499F5BEB7C4745891090371C5743328D57A2D",
            "cmd: 0x0B, param: 0x00, args: [100,0,0]",
            "id: 0x00018B5D, index: 0, tx: 59, seed: 0x0058",
            "light_0: ['br'] / {'sub_type': 'cww', 'br': 1.0}",
        ),
        # Effect Reading
        (
            "rwlight_mix",
            "02011A1BFFDDB2DA6C9F017A34D7C7020B78466A8509037179748F285BC079",
            "cmd: 0x08, param: 0x00, args: [0,0,0]",
            "id: 0x00018B5D, index: 0, tx: 6, seed: 0x0029",
            "light_0: ['effect'] / {'sub_type': 'cww', 'effect': 'Reading'}",
        ),
        # Effect Theater
        (
            "rwlight_mix",
            "02011A1BFFDDB2DA6C9F017A343F5F828BF8DEF21D090371F9740F2843CDEA",
            "cmd: 0x07, param: 0x00, args: [0,0,0]",
            "id: 0x00018B5D, index: 0, tx: 7, seed: 0x0031",
            "light_0: ['effect'] / {'sub_type': 'cww', 'effect': 'Theater'}",
        ),
        # Effect Party
        (
            "rwlight_mix",
            "02011A1BFFDDB2DA6C9F017A34A545727B08C4E8070903710974FF28A96FB6",
            "cmd: 0x09, param: 0x00, args: [0,0,0]",
            "id: 0x00018B5D, index: 0, tx: 8, seed: 0x0066",
            "light_0: ['effect'] / {'sub_type': 'cww', 'effect': 'Party'}",
        ),
        # Effect Night Light
        (
            "rwlight_mix",
            "02011A1BFFDDB2DA6C9F017A343494F2FB881539D609037189747F28F80D3E",
            "cmd: 0x0A, param: 0x00, args: [0,0,0]",
            "id: 0x00018B5D, index: 0, tx: 9, seed: 0x00EC",
            "light_0: ['effect'] / {'sub_type': 'cww', 'effect': 'Night Light'}",
        ),
        # RGB ON
        (
            "rwlight_mix",
            "02011A1BFFDDB2DA6C9F017A342B2F8A83F0AE826D090371F17407283BFA23",
            "cmd: 0x31, param: 0x00, args: [0,0,0]",
            "id: 0x00018B5D, index: 0, tx: 23, seed: 0x002F",
            "light_1: ['on'] / {'sub_type': 'rgb', 'on': True}",
        ),
        # RGB OFF
        (
            "rwlight_mix",
            "02011A1BFFDDB2DA6C9F017A34F9CD7A73004C608F0903710174F728293A19",
            "cmd: 0x32, param: 0x00, args: [0,0,0]",
            "id: 0x00018B5D, index: 0, tx: 24, seed: 0x0067",
            "light_1: ['on'] / {'sub_type': 'rgb', 'on': False}",
        ),
        # RGB RED, BR 50%
        (
            "rwlight_mix",
            "02011A1BFFDDB2DA6C9F017A34605A2A2350DBF7E80903715174EB28A27AA1",
            "cmd: 0x48, param: 0x00, args: [15,0,50]",
            "id: 0x00018B5D, index: 0, tx: 18, seed: 0x0084",
            "light_1: ['br', 'r', 'g', 'b'] / {'sub_type': 'rgb', 'br': 0.5, 'r': 1.0, 'g': 0.0, 'b': 0.0}",
        ),
        # RGB GREEN, BR 50%
        (
            "rwlight_mix",
            "02011A1BFFDDB2DA6C9F017A34D58F4A43300E22C209037131748B2817FF2E",
            "cmd: 0x48, param: 0x00, args: [240,0,50]",
            "id: 0x00018B5D, index: 0, tx: 20, seed: 0x0029",
            "light_1: ['br', 'r', 'g', 'b'] / {'sub_type': 'rgb', 'br': 0.5, 'r': 0.0, 'g': 1.0, 'b': 0.0}",
        ),
        # RGB BLUE, BR 50%
        (
            "rwlight_mix",
            "02011A1BFFDDB2DA6C9F017A34BB61CAC3B0E0CC2309037141740B288944A7",
            "cmd: 0x48, param: 0x00, args: [0,15,50]",
            "id: 0x00018B5D, index: 0, tx: 21, seed: 0x005F",
            "light_1: ['br', 'r', 'g', 'b'] / {'sub_type': 'rgb', 'br': 0.5, 'r': 0.0, 'g': 0.0, 'b': 1.0}",
        ),
        # RGB BLUE, BR 0%
        (
            "rwlight_mix",
            "02011A1BFFDDB2DA6C9F017A3491D7565F2C567A95090371DD74DB28EFF5F7",
            "cmd: 0x48, param: 0x00, args: [0,15,0]",
            "id: 0x00018B5D, index: 0, tx: 44, seed: 0x000B",
            "light_1: ['br', 'r', 'g', 'b'] / {'sub_type': 'rgb', 'br': 0.0, 'r': 0.0, 'g': 0.0, 'b': 1.0}",
        ),
        # RGB BLUE, BR 100%
        (
            "rwlight_mix",
            "02011A1BFFDDB2DA6C9F017A3416A8AEA7D42905EA090371257405284EDD11",
            "cmd: 0x48, param: 0x00, args: [0,15,100]",
            "id: 0x00018B5D, index: 0, tx: 51, seed: 0x00EA",
            "light_1: ['br', 'r', 'g', 'b'] / {'sub_type': 'rgb', 'br': 1.0, 'r': 0.0, 'g': 0.0, 'b': 1.0}",
        ),
        # RGB Effect RGB / Flash
        (
            "rwlight_mix",
            "02011A1BFFDDB2DA6C9F017A34BE52121B68D3FF1009037169749F28DE64B1",
            "cmd: 0x3F, param: 0x00, args: [0,0,0]",
            "id: 0x00018B5D, index: 0, tx: 14, seed: 0x0088",
            "light_1: ['effect'] / {'sub_type': 'rgb', 'effect': 'rgb'}",
        ),
        # RGB Effect Strobe
        (
            "rwlight_mix",
            "02011A1BFFDDB2DA6C9F017A344B67929BE8E6CA25090371E9741F286BE74A",
            "cmd: 0x3D, param: 0x00, args: [0,0,0]",
            "id: 0x00018B5D, index: 0, tx: 15, seed: 0x0025",
            "light_1: ['effect'] / {'sub_type': 'rgb', 'effect': 'Strobe'}",
        ),
        # RGB Effect Fade
        (
            "rwlight_mix",
            "02011A1BFFDDB2DA6C9F017A34C87C6A6310FDD13E0903711174E72888BCDC",
            "cmd: 0x3B, param: 0x00, args: [0,0,0]",
            "id: 0x00018B5D, index: 0, tx: 16, seed: 0x00E2",
            "light_1: ['effect'] / {'sub_type': 'rgb', 'effect': 'Fade'}",
        ),
        # RGB Effect Smooth
        (
            "rwlight_mix",
            "02011A1BFFDDB2DA6C9F017A34B69CEAE3901D31DE09037191746728E89C19",
            "cmd: 0x43, param: 0x00, args: [0,0,0]",
            "id: 0x00018B5D, index: 0, tx: 17, seed: 0x00E4",
            "light_1: ['effect'] / {'sub_type': 'rgb', 'effect': 'Smooth'}",
        ),
        # FAN ON
        (
            "rwlight_mix",
            "02011A1BFFDDB2DA6C9F017A34DA2D737A09AC806F0903718874FE28403899",
            "cmd: 0x61, param: 0x00, args: [0,1,0]",
            "id: 0x00018B5D, index: 0, tx: 136, seed: 0x00F0",
            "fan_0: ['on'] / {'on': True}",
        ),
        # FAN OFF
        (
            "rwlight_mix",
            "02011A1BFFDDB2DA6C9F017A347403F3FA8982AE4109037188747E286E24BE",
            "cmd: 0x61, param: 0x00, args: [0,0,0]",
            "id: 0x00018B5D, index: 0, tx: 137, seed: 0x0085",
            "fan_0: ['on'] / {'on': False}",
        ),
        # FAN SPEED 100
        (
            "rwlight_mix",
            "02011A1BFFDDB2DA6C9F017A34CB9C131A691D31DE0903714E749E28375D35",
            "cmd: 0x62, param: 0x00, args: [0,100,0]",
            "id: 0x00018B5D, index: 0, tx: 142, seed: 0x007B",
            "fan_0: ['speed'] / {'speed_count': 100, 'speed': 100.0}",
        ),
        # FAN SPEED 3/100
        (
            "rwlight_mix",
            "02011A1BFFDDB2DA6C9F017A34852EEFE695AF836C090371547462289FCE1D",
            "cmd: 0x62, param: 0x00, args: [0,3,0]",
            "id: 0x00018B5D, index: 0, tx: 177, seed: 0x0009",
            "fan_0: ['speed'] / {'speed_count': 100, 'speed': 3.0}",
        ),
    ],
)
class TestEncoderRwFull(_TestEncoderFull):
    """RW Encoder / Decoder Full tests."""
