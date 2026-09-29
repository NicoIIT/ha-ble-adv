# ruff: noqa: S101
"""Hxlight Unit Tests."""

import pytest
from ble_adv.codecs.models import BleAdvEntAttr

from . import CODECS, _TestEncoderBase, _TestEncoderFull, _TestEncoderFullAll


@pytest.mark.parametrize(
    ("attrs", "expected"),
    [
        ({"on": True, "effect": "nm"}, ["cmd: 0x03, param: 0x00, args: [1,0,0]"]),
        ({"on": True, "effect": None}, ["cmd: 0x01, param: 0x00, args: [1,0,0]", "cmd: 0x01, param: 0x00, args: [1,0,0]"]),
    ],
)
def test_turn_on_with_effect(attrs: dict, expected: list[str]) -> None:
    """Turning ON with Night Mode only sends Night Mode, as it switches the lamp on by itself."""
    ent_attr = BleAdvEntAttr(["on", "effect"], attrs, "light", 0)
    assert [repr(enc_cmd) for enc_cmd in CODECS["hxlight_v0"].ent_to_enc(ent_attr, "nm_as_effect")] == expected


@pytest.mark.parametrize(
    _TestEncoderBase.PARAM_NAMES,
    [
        ("hxlight_v0", 0xFF, "F0FF6DB643593A60A7A163E406B951FB284B19290CB45986A118"),
    ],
)
class TestEncoderHxlight(_TestEncoderBase):
    """Hxlight Encoder tests."""


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # LIGHT OFF
        (
            "hxlight_v0",
            "02.01.01.1B.FF.F0.FF.6D.B6.43.59.3A.60.A7.A1.63.E4.06.B9.51.FB.28.4B.19.29.0C.B4.59.86.A1.18",
            "cmd: 0x01, param: 0x00, args: [2,0,0]",
            "id: 0x0000F9F8, index: 1, tx: 2, seed: 0x0000",
            "light_0: ['on'] / {'on': False}",
        ),
        # LIGHT ON
        (
            "hxlight_v0",
            "02.01.01.1B.FF.F0.FF.6D.B6.43.59.3A.60.A7.A1.63.E4.06.B9.51.FB.2B.4B.19.2A.0C.B5.56.0A.CD.18",
            "cmd: 0x01, param: 0x00, args: [1,0,0]",
            "id: 0x0000F9F8, index: 1, tx: 3, seed: 0x0000",
            "light_0: ['on'] / {'on': True}",
        ),
        # LIGHT OFF - group 2
        (
            "hxlight_v0",
            "02.01.01.1B.FF.F0.FF.6D.B6.43.59.3A.60.A7.A1.63.E4.06.BA.51.FB.28.4B.19.29.0C.B0.52.5C.0C.18",
            "cmd: 0x01, param: 0x00, args: [2,0,0]",
            "id: 0x0000F9F8, index: 2, tx: 6, seed: 0x0000",
            "light_0: ['on'] / {'on': False}",
        ),
        # BRIGHTNESS 44%
        (
            "hxlight_v0",
            "02.01.01.1B.FF.F0.FF.6D.B6.43.59.3A.60.A7.A1.66.E4.06.B9.54.9F.06.4E.7D.07.0C.B3.59.C7.14.18",
            "cmd: 0x65, param: 0x05, args: [44,0,0]",
            "id: 0x0000F9F8, index: 1, tx: 5, seed: 0x0000",
            "light_0: ['br'] / {'sub_type': 'cww', 'br': 0.44}",
        ),
        # BRIGHTNESS 100%
        (
            "hxlight_v0",
            "02.01.01.1B.FF.F0.FF.6D.B6.43.59.3A.60.A7.A1.66.E4.06.B9.54.9F.4E.4E.7D.4F.0C.A7.AD.18.BD.18",
            "cmd: 0x65, param: 0x05, args: [100,0,0]",
            "id: 0x0000F9F8, index: 1, tx: 17, seed: 0x0000",
            "light_0: ['br'] / {'sub_type': 'cww', 'br': 1.0}",
        ),
        # BRIGHTNESS 1%
        (
            "hxlight_v0",
            "02.01.01.1B.FF.F0.FF.6D.B6.43.59.3A.60.A7.A1.66.E4.06.B9.54.9F.2B.4E.7D.2A.0C.A4.AA.5A.40.18",
            "cmd: 0x65, param: 0x05, args: [1,0,0]",
            "id: 0x0000F9F8, index: 1, tx: 18, seed: 0x0000",
            "light_0: ['br'] / {'sub_type': 'cww', 'br': 0.01}",
        ),
        # BRIGHTNESS 21% - group 2
        (
            "hxlight_v0",
            "02.01.01.1B.FF.F0.FF.6D.B6.43.59.3A.60.A7.A1.66.E4.06.BA.54.9F.3F.4E.7D.3E.0C.A1.A4.07.C8.18",
            "cmd: 0x65, param: 0x05, args: [21,0,0]",
            "id: 0x0000F9F8, index: 2, tx: 23, seed: 0x0000",
            "light_0: ['br'] / {'sub_type': 'cww', 'br': 0.21}",
        ),
        # COLOR TEMPERATURE COLD
        (
            "hxlight_v0",
            "02.01.01.1B.FF.F0.FF.6D.B6.43.59.3A.60.A7.A1.66.E4.06.B9.56.9F.4E.B4.7D.81.59.EF.CC.A3.1A.18",
            "cmd: 0x65, param: 0x07, args: [100,0,0]",
            "id: 0x0000F9F8, index: 1, tx: 89, seed: 0x0000",
            "light_0: ['ctr'] / {'sub_type': 'cww', 'ctr': 1.0}",
        ),
        # COLOR TEMPERATURE 53%
        (
            "hxlight_v0",
            "02.01.01.1B.FF.F0.FF.6D.B6.43.59.3A.60.A7.A1.66.E4.06.B9.56.9F.1F.9B.7D.81.59.EC.CD.B1.74.18",
            "cmd: 0x65, param: 0x07, args: [53,0,0]",
            "id: 0x0000F9F8, index: 1, tx: 90, seed: 0x0000",
            "light_0: ['ctr'] / {'sub_type': 'cww', 'ctr': 0.53}",
        ),
        # COLOR TEMPERATURE WARM
        (
            "hxlight_v0",
            "02.01.01.1B.FF.F0.FF.6D.B6.43.59.3A.60.A7.A1.66.E4.06.B9.56.9F.2A.D0.7D.81.59.ED.CA.CB.10.18",
            "cmd: 0x65, param: 0x07, args: [0,0,0]",
            "id: 0x0000F9F8, index: 1, tx: 91, seed: 0x0000",
            "light_0: ['ctr'] / {'sub_type': 'cww', 'ctr': 0.0}",
        ),
    ],
)
class TestEncoderHxlightFull(_TestEncoderFull):
    """Hxlight Encoder / Decoder Full tests."""


@pytest.mark.parametrize(
    _TestEncoderFull.PARAM_NAMES,
    [
        # NIGHT MODE
        (
            "hxlight_v0",
            "02.01.01.1B.FF.F0.FF.6D.B6.43.59.3A.60.A7.A1.66.E4.06.B9.51.F9.2B.4B.1B.2A.0C.B3.59.D3.6F.18",
            "cmd: 0x03, param: 0x00, args: [1,0,0]",
            "id: 0x0000F9F8, index: 1, tx: 5, seed: 0x0000",
            "light_0: ['on', 'cold', 'warm'] / {'sub_type': 'cww', 'on': True, 'cold': 0.0, 'warm': 0.02}",
        ),
        # NIGHT MODE - newer app check bytes
        (
            "hxlight_v0",
            "02.01.01.1B.FF.F0.FF.6D.B6.43.59.3A.60.A7.A1.66.E4.06.B9.51.F9.2B.4B.1B.81.59.AB.15.9C.64.18",
            "cmd: 0x03, param: 0x00, args: [1,0,0]",
            "id: 0x0000F9F8, index: 1, tx: 29, seed: 0x0000",
            "light_0: ['on', 'cold', 'warm'] / {'sub_type': 'cww', 'on': True, 'cold': 0.0, 'warm': 0.02}",
        ),
        # LIGHT OFF - newer app check bytes
        (
            "hxlight_v0",
            "02.01.01.1B.FF.F0.FF.6D.B6.43.59.3A.60.A7.A1.63.E4.06.B9.51.FB.28.4B.19.81.59.C1.B7.31.DC.18",
            "cmd: 0x01, param: 0x00, args: [2,0,0]",
            "id: 0x0000F9F8, index: 1, tx: 119, seed: 0x0000",
            "light_0: ['on'] / {'on': False}",
        ),
        # PRESET BRIGHT
        (
            "hxlight_v0",
            "02.01.01.1B.FF.F0.FF.6D.B6.43.59.3A.60.A7.A1.66.E4.06.B9.51.F4.2B.4B.16.81.59.EA.54.06.AE.18",
            "cmd: 0x0E, param: 0x00, args: [1,0,0]",
            "id: 0x0000F9F8, index: 1, tx: 92, seed: 0x0000",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 1.0, 'warm': 0.0}",
        ),
        # PRESET COMFORTABLE
        (
            "hxlight_v0",
            "02.01.01.1B.FF.F0.FF.6D.B6.43.59.3A.60.A7.A1.66.E4.06.B9.51.F4.29.4B.16.81.59.EB.53.DA.F4.18",
            "cmd: 0x0E, param: 0x00, args: [3,0,0]",
            "id: 0x0000F9F8, index: 1, tx: 93, seed: 0x0000",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 0.5, 'warm': 0.5}",
        ),
        # PRESET WARM
        (
            "hxlight_v0",
            "02.01.01.1B.FF.F0.FF.6D.B6.43.59.3A.60.A7.A1.66.E4.06.B9.51.F4.28.4B.16.81.59.E8.53.67.41.18",
            "cmd: 0x0E, param: 0x00, args: [2,0,0]",
            "id: 0x0000F9F8, index: 1, tx: 94, seed: 0x0000",
            "light_0: ['cold', 'warm'] / {'sub_type': 'cww', 'cold': 0.0, 'warm': 1.0}",
        ),
        # LIGHT ON - no footer app
        (
            "hxlight_v0/nf",
            "02.01.01.1A.FF.F0.FF.6D.B6.43.59.3A.60.A7.A1.66.28.F5.B9.51.FB.2B.4B.10.2A.0D.B4.93.8A.99",
            "cmd: 0x01, param: 0x00, args: [1,0,0]",
            "id: 0x0000350B, index: 1, tx: 2, seed: 0x0000",
            "light_0: ['on'] / {'on': True}",
        ),
        # LIGHT OFF - no footer app
        (
            "hxlight_v0/nf",
            "02.01.01.1A.FF.F0.FF.6D.B6.43.59.3A.60.A7.A1.66.28.F5.B9.51.FB.28.4B.10.2A.0D.B5.91.2E.0B",
            "cmd: 0x01, param: 0x00, args: [2,0,0]",
            "id: 0x0000350B, index: 1, tx: 3, seed: 0x0000",
            "light_0: ['on'] / {'on': False}",
        ),
        # BRIGHTNESS UP - no footer app
        (
            "hxlight_v0/nf",
            "02.01.01.1A.FF.F0.FF.6D.B6.43.59.3A.60.A7.A1.66.28.F5.B9.51.F2.2B.4B.10.2A.0D.9C.C2.76.9B",
            "cmd: 0x08, param: 0x00, args: [1,0,0]",
            "id: 0x0000350B, index: 1, tx: 42, seed: 0x0000",
            "light_0: ['cmd'] / {'sub_type': 'cww', 'cmd': 'B+', 'step': 0.1}",
        ),
        # BRIGHTNESS DOWN - no footer app
        (
            "hxlight_v0/nf",
            "02.01.01.1A.FF.F0.FF.6D.B6.43.59.3A.60.A7.A1.66.28.F5.B9.51.F2.28.4B.10.2A.0D.96.CD.9F.36",
            "cmd: 0x08, param: 0x00, args: [2,0,0]",
            "id: 0x0000350B, index: 1, tx: 32, seed: 0x0000",
            "light_0: ['cmd'] / {'sub_type': 'cww', 'cmd': 'B-', 'step': 0.1}",
        ),
        # LIGHT ON - no footer app, group 2
        (
            "hxlight_v0/nf",
            "02.01.01.1A.FF.F0.FF.6D.B6.43.59.3A.60.A7.A1.66.28.F5.BA.51.FB.2B.4B.10.2A.0D.07.43.68.2B",
            "cmd: 0x01, param: 0x00, args: [1,0,0]",
            "id: 0x0000350B, index: 2, tx: 177, seed: 0x0000",
            "light_0: ['on'] / {'on': True}",
        ),
        # LIGHT ON - no footer app, group 0 (all)
        (
            "hxlight_v0/nf",
            "02.01.01.1A.FF.F0.FF.6D.B6.43.59.3A.60.A7.A1.66.28.F5.B8.51.FB.2B.4B.10.2A.0D.FC.2A.41.15",
            "cmd: 0x01, param: 0x00, args: [1,0,0]",
            "id: 0x0000350B, index: 0, tx: 74, seed: 0x0000",
            "light_0: ['on'] / {'on': True}",
        ),
        # LIGHT OFF - no footer app, other id
        (
            "hxlight_v0/nf",
            "02.01.01.1A.FF.F0.FF.6D.B6.43.59.3A.60.A7.A1.66.1F.3E.B8.51.FB.28.4B.10.2A.0D.95.4E.B7.8B",
            "cmd: 0x01, param: 0x00, args: [2,0,0]",
            "id: 0x000002C0, index: 0, tx: 35, seed: 0x0000",
            "light_0: ['on'] / {'on': False}",
        ),
    ],
)
class TestEncoderHxlightDecodeOnly(_TestEncoderFull):
    """Hxlight decode only tests: frames emitted with check bytes / commands not reproduced by the encoder."""

    _with_reverse = False


@pytest.mark.parametrize(
    _TestEncoderFullAll.PARAM_NAMES,
    [
        # NIGHT MODE as effect
        (
            "hxlight_v0",
            [],
            "nm_as_effect",
            "02.01.01.1B.FF.F0.FF.6D.B6.43.59.3A.60.A7.A1.66.E4.06.B9.51.F9.2B.4B.1B.2A.0C.B3.59.D3.6F.18",
            "cmd: 0x03, param: 0x00, args: [1,0,0]",
            "id: 0x0000F9F8, index: 1, tx: 5, seed: 0x0000",
            "light_0: ['effect'] / {'effect': 'nm'}",
        ),
        # LIGHT ON
        (
            "hxlight_v0",
            [],
            "nm_as_effect",
            "02.01.01.1B.FF.F0.FF.6D.B6.43.59.3A.60.A7.A1.63.E4.06.B9.51.FB.2B.4B.19.2A.0C.B5.56.0A.CD.18",
            "cmd: 0x01, param: 0x00, args: [1,0,0]",
            "id: 0x0000F9F8, index: 1, tx: 3, seed: 0x0000",
            "light_0: ['on'] / {'on': True}",
        ),
    ],
)
class TestEncoderHxlightSets(_TestEncoderFullAll):
    """Hxlight Encoder / Decoder tests on translator sets."""
