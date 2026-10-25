"""Remotes Unit Tests."""

import pytest

from . import _TestEncoderBase, _TestEncoderFull


@pytest.mark.parametrize(
    _TestEncoderBase.PARAM_NAMES,
    [
        ("remote_v4", 0xFF, "F0.FF.00.55.8F.24.04.08.65.79"),
        ("remote_v5", 0x16, "FF.F0.31.D2.D7.31.52.31.CE.28.31.81.30.31.A3.42.28.D4.31"),
    ],
)
class TestEncoderRemotes(_TestEncoderBase):
    """Remote Encoder tests."""


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # ON (tx odd => 0xB0)
        (
            "remote_v5",
            "02.01.1A.14.16.FF.F0.31.D2.D7.31.52.31.CE.28.31.81.30.31.A3.42.28.D4.31",
            "cmd: 0xB0, param: 0x00, args: [0,0,0]",
            "id: 0x9219FFE6, index: 1, tx: 99, seed: 0x0000",
            "light_0: ['on'] / {'on': True}",
        ),
        # ON (tx even => 0xAF)
        (
            "remote_v5",
            "02.01.1A.14.16.FF.F0.31.CA.D7.31.55.31.CE.28.31.9E.30.31.A3.45.28.CB.31",
            "cmd: 0xB0, param: 0x00, args: [0,0,0]",
            "id: 0x9219FFE6, index: 1, tx: 100, seed: 0x0000",
            "light_0: ['on'] / {'on': True}",
        ),
        # OFF
        (
            "remote_v5",
            "02.01.1A.14.16.FF.F0.31.9F.D7.31.09.31.CE.28.31.97.30.31.A3.19.28.C2.31",
            "cmd: 0xA6, param: 0x00, args: [0,0,0]",
            "id: 0x9219FFE6, index: 1, tx: 56, seed: 0x0000",
            "light_0: ['on'] / {'on': False}",
        ),
        # Second remote, different id: ON (tx odd)
        (
            "remote_v5",
            "02.01.1A.14.16.FF.F0.31.5A.0B.31.06.31.CE.28.31.81.30.31.7F.16.28.D4.31",
            "cmd: 0xB0, param: 0x00, args: [0,0,0]",
            "id: 0x4E19FF3A, index: 1, tx: 55, seed: 0x0000",
            "light_0: ['on'] / {'on': True}",
        ),
        # Second remote: ON (tx even => 0xAF)
        (
            "remote_v5",
            "02.01.1A.14.16.FF.F0.31.4A.0B.31.09.31.CE.28.31.9E.30.31.7F.19.28.CB.31",
            "cmd: 0xB0, param: 0x00, args: [0,0,0]",
            "id: 0x4E19FF3A, index: 1, tx: 56, seed: 0x0000",
            "light_0: ['on'] / {'on': True}",
        ),
        # Second remote: OFF
        (
            "remote_v5",
            "02.01.1A.14.16.FF.F0.31.F6.0B.31.BC.31.CE.28.31.97.30.31.7F.AC.28.C2.31",
            "cmd: 0xA6, param: 0x00, args: [0,0,0]",
            "id: 0x4E19FF3A, index: 1, tx: 141, seed: 0x0000",
            "light_0: ['on'] / {'on': False}",
        ),
    ],
)
class TestEncoderRemotesFull(_TestEncoderFull):
    """Remote Encoder / Decoder Full tests."""
