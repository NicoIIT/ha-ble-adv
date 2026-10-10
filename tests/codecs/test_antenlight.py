"""Antenlight Unit Tests."""

# ruff: noqa: S101

import pytest
from ble_adv.codecs.models import BleAdvAdvertisement

from . import CODECS, _TestEncoderBase, _TestEncoderFull


@pytest.mark.parametrize(
    _TestEncoderBase.PARAM_NAMES,
    [
        ("antenlight_v0", 0x16, "000061DC009D00000000C5"),
    ],
)
class TestEncoderAntenlight(_TestEncoderBase):
    """Antenlight Encoder tests."""


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # LIGHT OFF
        (
            "antenlight_v0",
            "02.01.1A.0C.16.00.00.61.DC.00.9D.00.00.00.00.C5",
            "cmd: 0x00, param: 0x00, args: [0,0,0]",
            "id: 0x000061DC, index: 0, tx: 157, seed: 0x0000",
            "light_0: ['on'] / {'on': False}",
        ),
        # LIGHT ON
        (
            "antenlight_v0",
            "02.01.1A.0C.16.00.00.61.DC.00.9E.00.01.00.00.C7",
            "cmd: 0x00, param: 0x00, args: [1,0,0]",
            "id: 0x000061DC, index: 0, tx: 158, seed: 0x0000",
            "light_0: ['on'] / {'on': True}",
        ),
    ],
)
class TestEncoderAntenlightFull(_TestEncoderFull):
    """Antenlight Encoder / Decoder Full tests."""


def test_invalid_checksum() -> None:
    """A buffer with an invalid checksum is rejected."""
    adv = BleAdvAdvertisement(0x16, bytes.fromhex("000061DC009D00000000C6"))
    assert CODECS["antenlight_v0"].decode_adv(adv) == (None, None)
