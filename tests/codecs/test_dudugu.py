"""Dudugu Unit Tests."""

import pytest

from . import _TestEncoderBase, _TestEncoderFull


@pytest.mark.parametrize(
    _TestEncoderBase.PARAM_NAMES,
    [
        ("dudugu_v0", 0x03, "F8F24DDE7161546C4E85BAC92A6D70BFC3C6802090F5CB034192"),
    ],
)
class TestEncoderDudugu(_TestEncoderBase):
    """Dudugu Encoder tests."""


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # FAN OFF
        (
            "dudugu_v0",
            "0201021B03F8F26EFD5242774F6DA694EA094E539DE0E5A303B3D6E8204463",
            "cmd: 0x31, param: 0x00, args: [32,0,0]",
            "id: 0x3990765C, index: 4866, tx: 4, seed: 0x0073",
            "fan_0: ['on'] / {'speed_count': 6, 'on': False}",
        ),
        # FAN GEAR 1
        (
            "dudugu_v0",
            "0201021B03F8F274E748586D5577BC89F013544986FAFFB919A9CCF23A7CB5",
            "cmd: 0x31, param: 0x00, args: [32,1,0]",
            "id: 0x3990765C, index: 4866, tx: 3, seed: 0x0069",
            "fan_0: ['on', 'speed'] / {'speed_count': 6, 'on': True, 'speed': 1.0}",
        ),
        # FAN GEAR 2
        (
            "dudugu_v0",
            "0201021B03F8F2EF7CD3C3F6CEEC271C6B88CFD21E61642282325769A1F657",
            "cmd: 0x31, param: 0x00, args: [32,2,0]",
            "id: 0x3990765C, index: 4866, tx: 13, seed: 0x00F2",
            "fan_0: ['on', 'speed'] / {'speed_count': 6, 'on': True, 'speed': 2.0}",
        ),
        # FAN GEAR 3
        (
            "dudugu_v0",
            "0201021B03F8F2E675DACAFFC7E52E166281C6DB16686D2B8B3B5E60A89FBA",
            "cmd: 0x31, param: 0x00, args: [32,3,0]",
            "id: 0x3990765C, index: 4866, tx: 14, seed: 0x00FB",
            "fan_0: ['on', 'speed'] / {'speed_count': 6, 'on': True, 'speed': 3.0}",
        ),
        # FAN GEAR 4
        (
            "dudugu_v0",
            "0201021B03F8F2FE6DC2D2E7DFFD360F7A99DEC30970753393234678B0D7A2",
            "cmd: 0x31, param: 0x00, args: [32,4,0]",
            "id: 0x3990765C, index: 4866, tx: 15, seed: 0x00E3",
            "fan_0: ['on', 'speed'] / {'speed_count': 6, 'on': True, 'speed': 4.0}",
        ),
        # FAN GEAR 5
        (
            "dudugu_v0",
            "0201021B03F8F25BC86777427A5893B5DF3C7B66ADD5D0963686E3DD157B7C",
            "cmd: 0x31, param: 0x00, args: [32,5,0]",
            "id: 0x3990765C, index: 4866, tx: 16, seed: 0x0046",
            "fan_0: ['on', 'speed'] / {'speed_count': 6, 'on': True, 'speed': 5.0}",
        ),
        # FAN GEAR 6
        (
            "dudugu_v0",
            "0201021B03F8F261F25D4D784062A98EE506415C94EFEAAC0CBCD9E72FEA4E",
            "cmd: 0x31, param: 0x00, args: [32,6,0]",
            "id: 0x3990765C, index: 4866, tx: 17, seed: 0x007C",
            "fan_0: ['on', 'speed'] / {'speed_count': 6, 'on': True, 'speed': 6.0}",
        ),
        # Breeze Mode
        (
            "dudugu_v0",
            "0201021B03F8F2F467C8D8EDD5F73C247293D4EB077A7F3999294C72BA0664",
            "cmd: 0x33, param: 0x00, args: [2,0,0]",
            "id: 0x3990765C, index: 4866, tx: 46, seed: 0x00E9",
            "fan_0: ['preset'] / {'preset': 'breeze'}",
        ),
        # DIR Reverse
        (
            "dudugu_v0",
            "0201021B03F8F2C95AF5E5D0E8CA010769AEE9D43A474204A414714F87C723",
            "cmd: 0x15, param: 0x00, args: [0,0,0]",
            "id: 0x3990765C, index: 4866, tx: 48, seed: 0x00D4",
            "fan_0: ['dir'] / {'dir': False}",
        ),
        # DIR Forward
        (
            "dudugu_v0",
            "0201021B03F8F2B6258A9AAF97B57E7916D196AA45383D7BDB6B0E30F869E6",
            "cmd: 0x15, param: 0x00, args: [1,0,0]",
            "id: 0x3990765C, index: 4866, tx: 49, seed: 0x00AB",
            "fan_0: ['dir'] / {'dir': True}",
        ),
    ],
)
class TestEncoderDuduguFull(_TestEncoderFull):
    """Dudugu Encoder / Decoder Full tests."""


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # Timer 1 hour
        (
            "dudugu_v0",
            "0201021B03F8F27EED4252675F7DB69C8A195E5F8DF0F5B313A3C6F830C8C4",
            "cmd: 0x41, param: 0x00, args: [60,0,0]",
            "id: 0x3990765C, index: 4866, tx: 28, seed: 0x0063",
            "device_0: ['cmd'] / {'cmd': 'timer', 's': 3600.0}",
        ),
        # Timer 2 hours
        (
            "dudugu_v0",
            "0201021B03F8F22EBD1202370F2DE6CDDA490E4BDDA0A5E343F396A860C8AB",
            "cmd: 0x41, param: 0x00, args: [120,0,0]",
            "id: 0x3990765C, index: 4866, tx: 29, seed: 0x0033",
            "device_0: ['cmd'] / {'cmd': 'timer', 's': 7200.0}",
        ),
        # Timer 4 hours
        (
            "dudugu_v0",
            "0201021B03F8F28211BEAE9BA3814A6276E5A26F710C094FEF5F3A04CCE86F",
            "cmd: 0x41, param: 0x00, args: [240,0,0]",
            "id: 0x3990765C, index: 4866, tx: 30, seed: 0x009F",
            "device_0: ['cmd'] / {'cmd': 'timer', 's': 14400.0}",
        ),
        # Timer 8 hours
        (
            "dudugu_v0",
            "0201021B03F8F2D447E8F8CDF5D71C3520B3F429265A5F19B9096C529AC61C",
            "cmd: 0x41, param: 0x00, args: [224,1,0]",
            "id: 0x3990765C, index: 4866, tx: 31, seed: 0x00C9",
            "device_0: ['cmd'] / {'cmd': 'timer', 's': 28800.0}",
        ),
        # Cancel Timer
        (
            "dudugu_v0",
            "0201021B03F8F249DA756550684A81A4BD2E6954BAC7C2842494F1CF0706D1",
            "cmd: 0x41, param: 0x00, args: [0,0,0]",
            "id: 0x3990765C, index: 4866, tx: 19, seed: 0x0054",
            "device_0: ['cmd'] / {'cmd': 'timer', 's': 0.0}",
        ),
    ],
)
class TestEncoderDuduguNoDirect(_TestEncoderFull):
    """Dudugu Encoder / Decoder No Direct tests."""

    _with_reverse = False
