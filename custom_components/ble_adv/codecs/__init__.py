"""Codecs Package."""

from .fanlamp import CODECS as FANLAMP_CODECS
from .models import BleAdvCodec
from .zhijia import CODECS as ZHIJIA_CODECS
from .zhimei import CODECS as ZHIMEI_CODECS

PHONE_APPS = {
    "Fan Lamp Pro": ["fanlamp_pro_v3", "fanlamp_pro_v2", "fanlamp_pro_v1"],
    "Lamp Smart Pro": ["lampsmart_pro_v3", "lampsmart_pro_v2", "lampsmart_pro_v1"],
    "Zhi Jia": ["zhijia_v2", "zhijia_v1", "zhijia_v0"],
    "Other (legacy)": ["other_v1a", "other_v1b"],
}


def get_codecs() -> dict[str, BleAdvCodec]:
    """Get all codecs."""
    return {x.codec_id: x for x in [*FANLAMP_CODECS, *ZHIJIA_CODECS, *ZHIMEI_CODECS]}
