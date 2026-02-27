"""Test global init and codec consistency."""

# ruff: noqa: S101
from ble_adv.codecs import PHONE_APPS, get_codec_list


def test_codec_unique_id() -> None:
    """Check if each codec id is unique."""
    id_list = [x.codec_id for x in get_codec_list()]
    assert len(id_list) == len(set(id_list))


def test_exist_match_id() -> None:
    """Check if match_id exists for codec."""
    match_id_list = [x.match_id for x in get_codec_list()]
    id_list = [x.codec_id for x in get_codec_list()]
    assert all(x in id_list for x in match_id_list)


def test_exist_phone_app() -> None:
    """Check that all codecs referenced in PHONE_APPS exist."""
    id_list = [x.codec_id for x in get_codec_list()]
    for app_name, phone_app_ids in PHONE_APPS.items():
        ids = [phone_app_id[0] for phone_app_id in phone_app_ids]
        assert all(x in id_list for x in ids), f"Not all id exist for {app_name}"
