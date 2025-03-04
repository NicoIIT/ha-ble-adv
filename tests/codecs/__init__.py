# ruff: noqa: S101, A005
"""Codec Tests."""

from ble_adv.codecs import get_codecs
from ble_adv.codecs.models import BleAdvAdvertisement

CODECS = get_codecs()


class _TestEncoderBase:
    PARAM_NAMES: tuple[str, str, str] = ("enc_name", "ble_type", "data")

    def test_encoding(self, enc_name: str, ble_type: int, data: str) -> None:
        adv = BleAdvAdvertisement(ble_type, bytes([int(x, 16) for x in data.split(".")]))
        for codec_id, codec in CODECS.items():
            enc_cmd, conf = codec.decode_adv(adv)
            if codec_id == enc_name:
                assert conf is not None
                assert enc_cmd is not None
                reenc = codec.encode_adv(enc_cmd, conf)
                assert reenc == adv
            else:
                assert conf is None
