"""Codecs Package."""

from .agarce import CODECS as AGARCE_CODECS
from .fanlamp import FLCODECS, LSCODECS
from .le import CODECS as LE_CODECS
from .mantra import CODECS as MANTRA_CODECS
from .models import BleAdvCodec
from .remotes import CODECS as REMOTES_CODECS
from .ruixin import CODECS as RUIXIN_CODECS
from .zhijia import CODECS as ZHIJIA_CODECS
from .zhimei import CODECS as ZHIMEI_CODECS

PHONE_APPS = {
    "Fan Lamp Pro": ["fanlamp_pro_v3", "fanlamp_pro_v2", "fanlamp_pro_v1"],
    "Lamp Smart Pro": ["lampsmart_pro_v3", "lampsmart_pro_v2", "lampsmart_pro_v1"],
    "Zhi Jia": ["zhijia_v2", "zhijia_v1", "zhijia_v0"],
    "Zhi Guang": ["zhiguang_v2", "zhiguang_v1", "zhiguang_v0"],
    "Zhi Mei Deng Kong (Fan)": ["zhimei_fan_v1", "zhimei_fan_v0"],
    "Zhi Mei Deng Kong (Light only)": ["zhimei_v2", "zhimei_v1"],
    "Smart Light": ["agarce_v4", "agarce_v3"],
    "LE Light": ["lelight"],
    "RuiXin": ["ruixin_v0"],
}


def get_codec_list() -> list[BleAdvCodec]:
    """Get codec list."""
    return [*FLCODECS, *LSCODECS, *ZHIJIA_CODECS, *ZHIMEI_CODECS, *AGARCE_CODECS, *REMOTES_CODECS, *MANTRA_CODECS, *LE_CODECS, *RUIXIN_CODECS]


def get_codecs() -> dict[str, BleAdvCodec]:
    """Get codec map."""
    return {x.codec_id: x for x in get_codec_list()}
