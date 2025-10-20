# ruff: noqa: S101
"""Codec Tests."""

from ble_adv.codecs import get_codecs
from ble_adv.codecs.models import BleAdvAdvertisement, BleAdvCodec

CODECS: dict[str, BleAdvCodec] = get_codecs()
# Disable tx_count bump by codecs
for codec in CODECS.values():
    codec._tx_step = 0  # noqa: SLF001
    codec._tx_max = max(256, codec._tx_max)  # noqa: SLF001


def _from_dotted(data: str) -> bytes:
    return bytes.fromhex(data.replace(".", ""))


class _TestEncoderBase:
    PARAM_NAMES: tuple[str, str, str] = ("enc_name", "ble_type", "data")

    _dupe_allowed = False

    def test_encoding(self, enc_name: str, ble_type: int, data: str) -> None:
        adv = BleAdvAdvertisement(ble_type, _from_dotted(data))
        codec = CODECS[enc_name]
        codec.debug_mode = True
        enc_cmd, conf = codec.decode_adv(adv)
        assert conf is not None
        assert enc_cmd is not None
        if conf.seed != 0:
            assert codec._seed_max != 0  # noqa: SLF001
        reenc = codec.encode_advs(enc_cmd, conf)[0]
        assert reenc == adv
        conf.seed = 0
        conf.id += 0x01
        conf.index = (conf.index + 1) % 256
        conf.tx_count = (conf.tx_count + 10) % 125
        reenc2 = codec.encode_advs(enc_cmd, conf)[0]
        enc_cmd2, conf2 = codec.decode_adv(reenc2)
        assert conf2 is not None
        assert enc_cmd2 is not None
        assert conf.id == conf2.id
        assert conf2.index in (conf.index, 0)
        assert conf2.tx_count in (conf.tx_count, 0)
        assert enc_cmd2 == enc_cmd
        if not self._dupe_allowed:
            adv = BleAdvAdvertisement(ble_type, _from_dotted(data))
            for codec_id, codec in CODECS.items():
                if codec_id != enc_name:
                    enc_cmd, conf = codec.decode_adv(adv)
                    assert conf is None
                    assert enc_cmd is None


class _TestMultiEncoderBase:
    PARAM_NAMES: tuple[str, str, str] = ("enc_name", "ble_type", "data")

    def test_encoding(self, enc_name: str, ble_type: int, data: str) -> None:
        adv = BleAdvAdvertisement(ble_type, _from_dotted(data))
        codec = CODECS[enc_name]
        codec.debug_mode = True
        enc_cmd, conf = codec.decode_adv(adv)
        assert conf is not None
        assert enc_cmd is not None
        reencs = codec.encode_advs(enc_cmd, conf)
        assert adv in reencs
        conf.id += 0x01
        reencs2 = codec.encode_advs(enc_cmd, conf)
        for reenc in reencs2:
            assert repr(codec.decode_adv(reenc)) == repr((enc_cmd, conf))


class _TestEncoderFull:
    PARAM_NAMES: tuple[str, str, str, str, str] = ("enc_name", "raw", "enc_str", "conf_str", "ent_str")

    _with_reverse = True

    def test_decode_reencode(self, enc_name: str, raw: str, enc_str: str, conf_str: str, ent_str: str) -> None:
        """Validate a decoding / re-encoding."""
        adv = BleAdvAdvertisement.FromRaw(_from_dotted(raw))
        codec = CODECS[enc_name]
        enc_cmd, conf = codec.decode_adv(adv)
        assert enc_cmd is not None
        assert repr(enc_cmd) == enc_str
        assert conf is not None
        assert repr(conf) == conf_str
        ent_attrs = codec.enc_to_ent(enc_cmd)
        assert len(ent_attrs) == 1
        assert repr(ent_attrs[0]) == ent_str
        enc_cmds = codec.ent_to_enc(ent_attrs[0])
        if self._with_reverse:
            assert len(enc_cmds) == 1
            assert enc_cmds[0] == enc_cmd
            assert adv in codec.encode_advs(enc_cmd, conf)
