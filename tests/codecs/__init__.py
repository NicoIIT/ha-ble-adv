# ruff: noqa: S101, A005
"""Codec Tests."""

from ble_adv.codecs import get_codecs
from ble_adv.codecs.models import BleAdvAdvertisement, BleAdvCodec

CODECS: dict[str, BleAdvCodec] = get_codecs()


def _from_dotted(data: str) -> bytes:
    return bytes([int(x, 16) for x in data.split(".")])


class _TestEncoderBase:
    PARAM_NAMES: tuple[str, str, str] = ("enc_name", "ble_type", "data")

    def test_encoding(self, enc_name: str, ble_type: int, data: str) -> None:
        adv = BleAdvAdvertisement(ble_type, _from_dotted(data))
        codec = CODECS[enc_name]
        enc_cmd, conf = codec.decode_adv(adv)
        assert conf is not None
        assert enc_cmd is not None
        reenc = codec.encode_adv(enc_cmd, conf)
        assert reenc == adv
        conf.seed = 0
        conf.id += 0x01
        conf.index += 1
        conf.tx_count = (conf.tx_count + 10) % 125
        reenc2 = codec.encode_adv(enc_cmd, conf)
        enc_cmd2, conf2 = codec.decode_adv(reenc2)
        assert conf2 is not None
        assert enc_cmd2 is not None
        assert conf.id == conf2.id
        assert conf.index == conf2.index
        assert conf.tx_count == conf2.tx_count
        assert enc_cmd2 == enc_cmd

    def test_not_encoding(self, enc_name: str, ble_type: int, data: str) -> None:
        adv = BleAdvAdvertisement(ble_type, _from_dotted(data))
        for codec_id, codec in CODECS.items():
            if codec_id != enc_name:
                enc_cmd, conf = codec.decode_adv(adv)
                assert conf is None
                assert enc_cmd is None
