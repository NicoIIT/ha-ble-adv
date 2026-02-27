"""Codecs Package."""

from typing import Any

from .agarce import CODECS as AGARCE_CODECS
from .fanlamp import FLCODECS, LSCODECS
from .le import CODECS as LE_CODECS
from .mantra import CODECS as MANTRA_CODECS
from .models import BleAdvCodec
from .remotes import CODECS as REMOTES_CODECS
from .ruixin import CODECS as RUIXIN_CODECS
from .rw import CODECS as RW_CODECS
from .smartelfin import CODECS as SMARTELFIN_CODECS
from .zhijia import CODECS as ZHIJIA_CODECS
from .zhimei import CODECS as ZHIMEI_CODECS

_PHONE_APPS_BASE = {
    "Fan Lamp Pro": [("fanlamp_pro_v2", [True, [0x20, 0x80, 0x00]]), ("fanlamp_pro_v2", [False, [0x10, 0x80, 0x00]]), "fanlamp_pro_v1"],
    "Lamp Smart Pro": [("lampsmart_pro_v2", [True, [0x30, 0x80, 0x00]]), ("lampsmart_pro_v2", [False, [0x10, 0x80, 0x00]]), "lampsmart_pro_v1"],
    "Zhi Jia": ["zhijia_v2", "zhijia_v1", "zhijia_v0"],
    "Zhi Guang": ["zhiguang_v2", "zhiguang_v1", "zhiguang_v0"],
    "Zhi Mei Deng Kong (Fan)": ["zhimei_fan_v1", "zhimei_fan_v0"],
    "Zhi Mei Deng Kong (Light only)": ["zhimei_v2", "zhimei_v1"],
    "Smart Light": ["agarce_v4", "agarce_v3"],
    "LE Light": ["lelight"],
    "RuiXin": ["ruixin_v0"],
    "RW.LIGHT": ["rwlight_mix"],
    "Smart Elfin": [("fanlamp_pro_v2", [True, [0x10, 0x80, 0x00]]), ("smartelfin_v0", [[0x64, 0xE5, 0xE3, 0xBA]])],
}

PHONE_APPS = {nm: [cp if isinstance(cp, tuple) else (cp, []) for cp in lst] for nm, lst in _PHONE_APPS_BASE.items()}


def get_codec_list() -> list[BleAdvCodec]:
    """Get codec list."""
    return [
        *FLCODECS,
        *LSCODECS,
        *ZHIJIA_CODECS,
        *ZHIMEI_CODECS,
        *AGARCE_CODECS,
        *REMOTES_CODECS,
        *MANTRA_CODECS,
        *LE_CODECS,
        *RUIXIN_CODECS,
        *RW_CODECS,
        *SMARTELFIN_CODECS,
    ]


def get_codecs() -> dict[str, BleAdvCodec]:
    """Get codec map."""
    return {x.codec_id: x for x in get_codec_list()}


DYN_CODEC_PARAM_MAP: dict[str, tuple[str, list[Any]]] = {
    "fanlamp_pro_v2": ("fanlamp_pro_v2", [False, [0x10, 0x80, 0x00]]),
    "fanlamp_pro_v3": ("fanlamp_pro_v2", [True, [0x20, 0x80, 0x00]]),
    "fanlamp_pro_v3/se": ("fanlamp_pro_v2", [True, [0x10, 0x80, 0x00]]),
    "fanlamp_pro_v3/s1": ("fanlamp_pro_v2", [True, [0x20, 0x81, 0x00]]),
    "fanlamp_pro_v3/s2": ("fanlamp_pro_v2", [True, [0x20, 0x82, 0x00]]),
    "fanlamp_pro_v3/s3": ("fanlamp_pro_v2", [True, [0x20, 0x83, 0x00]]),
    "fanlamp_pro_vi3": ("fanlamp_pro_v2", [True, [0x30, 0x80, 0x00]]),
    "fanlamp_pro_vi3/s1": ("fanlamp_pro_v2", [True, [0x30, 0x81, 0x00]]),
    "fanlamp_pro_vi3/s2": ("fanlamp_pro_v2", [True, [0x30, 0x82, 0x00]]),
    "fanlamp_pro_vi3/s3": ("fanlamp_pro_v2", [True, [0x30, 0x83, 0x00]]),
    "fanlamp_pro_v3/r3": ("fanlamp_pro_v2/r", [True, [0x10, 0x00, 0x55]]),
    "remote_v2": ("fanlamp_pro_v2/r", [False, [0x10, 0x00, 0x56]]),
    "remote_v3": ("fanlamp_pro_v2/r", [True, [0x10, 0x00, 0x56]]),
    "lampsmart_pro_v2": ("lampsmart_pro_v2", [False, [0x10, 0x80, 0x00]]),
    "lampsmart_pro_v3": ("lampsmart_pro_v2", [True, [0x30, 0x80, 0x00]]),
    "lampsmart_pro_v3/s1": ("lampsmart_pro_v2", [True, [0x30, 0x81, 0x00]]),
    "lampsmart_pro_v3/s2": ("lampsmart_pro_v2", [True, [0x30, 0x82, 0x00]]),
    "lampsmart_pro_v3/s3": ("lampsmart_pro_v2", [True, [0x30, 0x83, 0x00]]),
    "lampsmart_pro_v3/s0_1": ("lampsmart_pro_v2", [True, [0x20, 0x80, 0x00]]),
    "lampsmart_pro_v3/s1_1": ("lampsmart_pro_v2", [True, [0x20, 0x81, 0x00]]),
    "lampsmart_pro_v3/s2_1": ("lampsmart_pro_v2", [True, [0x20, 0x82, 0x00]]),
    "lampsmart_pro_v3/s3_1": ("lampsmart_pro_v2", [True, [0x20, 0x83, 0x00]]),
    "lampsmart_pro_vi3": ("lampsmart_pro_v2", [True, [0x21, 0x80, 0x00]]),
    "lampsmart_pro_vi3/s1": ("lampsmart_pro_v2", [True, [0x21, 0x81, 0x00]]),
    "lampsmart_pro_vi3/s2": ("lampsmart_pro_v2", [True, [0x21, 0x82, 0x00]]),
    "lampsmart_pro_vi3/s3": ("lampsmart_pro_v2", [True, [0x21, 0x83, 0x00]]),
    "remote_v21": ("lampsmart_pro_v2/r", [False, [0x10, 0x00, 0x56]]),
    "remote_v31": ("lampsmart_pro_v2/r", [True, [0x10, 0x00, 0x56]]),
    "other_v2": ("lampsmart_pro_v2/r", [False, [0x10, 0x80, 0x00]]),
    "other_v3": ("lampsmart_pro_v2/r", [True, [0x10, 0x80, 0x00]]),
    "lampsmart_pro_v2/r1": ("lampsmart_pro_v2/r", [False, [0x10, 0x00, 0x62]]),
    "lampsmart_pro_v3/r1": ("lampsmart_pro_v2/r", [True, [0x10, 0x00, 0x62]]),
    "smartelfin_v0": ("smartelfin_v0", [[0x64, 0xE5, 0xE3, 0xBA]]),
}


def dyn_codec_params(codec_id: str) -> tuple[str, list[Any]]:
    """Migrate a codec_id to a codec with dynamic parameters."""
    if (result := DYN_CODEC_PARAM_MAP.get(codec_id)) is not None:
        return result
    return codec_id, []
