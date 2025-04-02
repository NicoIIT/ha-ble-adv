"""Config flow tests."""

# ruff: noqa: S101
from ble_adv.config_flow import _CodecConfig


def test_codec_config() -> None:
    """Test codec config."""
    conf = _CodecConfig("codec_id", 12, 1)
    assert repr(conf) == "codec_id, 0xC, 1"
