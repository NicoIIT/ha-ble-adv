"""Test global init and codec consistency."""

# ruff: noqa: S101
from ble_adv.codecs import get_codec_list


def test_codec_unique_id() -> None:
    """Check if each codec id is unique."""
    id_list = [x.codec_id for x in get_codec_list()]
    assert len(id_list) == len(set(id_list))


def test_exist_match_id() -> None:
    """Check if match_id exists for codec."""
    match_id_list = [x.match_id for x in get_codec_list()]
    id_list = [x.codec_id for x in get_codec_list()]
    assert all(x in id_list for x in match_id_list)
