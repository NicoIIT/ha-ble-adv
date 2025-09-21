"""Remotes Unit Tests."""

import pytest

from . import _TestEncoderBase


@pytest.mark.parametrize(
    _TestEncoderBase.PARAM_NAMES,
    [
        ("remote_v4", 0xFF, "F0.FF.00.55.8F.24.04.08.65.79"),
    ],
)
class TestEncoderRemotes(_TestEncoderBase):
    """Remote Encoder tests."""
