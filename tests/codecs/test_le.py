"""Remotes Unit Tests."""

import pytest

from . import _TestEncoderBase


@pytest.mark.parametrize(
    _TestEncoderBase.PARAM_NAMES,
    [
        ("lelight", 0xFF, "FF.FF.FF.FF.0C.01.5F.74.E3.8C.76.A9.C4.89.89.89.C6.00.00.00.00.00.00.00.00"),  # Lamp id 21, lamp Off
    ],
)
class TestEncoderLe(_TestEncoderBase):
    """Le Encoder tests."""
