"""Codecs Package."""

from .agarce import CODECS as AGARCE_CODECS
from .fanlamp import CODECS as FANLAMP_CODECS
from .models import BleAdvCodec
from .remotes import CODECS as REMOTES_CODECS
from .zhijia import CODECS as ZHIJIA_CODECS
from .zhimei import CODECS as ZHIMEI_CODECS

PHONE_APPS = {
    "Fan Lamp Pro": ["fanlamp_pro_v3", "fanlamp_pro_v2", "fanlamp_pro_v1"],
    "Lamp Smart Pro": ["lampsmart_pro_v3", "lampsmart_pro_v2", "lampsmart_pro_v1"],
    "Zhi Jia": ["zhijia_v2", "zhijia_v1", "zhijia_v0"],
    "Zhi Guang": ["zhiguang_v2", "zhiguang_v1", "zhiguang_v0"],
    "Zhi Mei Deng Kong (Fan)": ["zhimei_fan_v1", "zhimei_fan_v0"],
    "Zhi Mei Deng Kong (Light only)": ["zhimei_v2", "zhimei_v1"],
    "Smart Lights": ["agarce_v4", "agarce_v3"],
    "Other (legacy)": ["other_v1a", "other_v1b"],
    "Physical Remotes (FanLamp)": ["remote_v1", "remote_v2", "remote_v21", "remote_v3", "remote_v31"],
    "Physical Remotes (Others)": ["zhijia_vr1", "remote_v4", "zhimei_fan_vr1"],
}


def get_codecs() -> dict[str, BleAdvCodec]:
    """Get all codecs."""
    return {x.codec_id: x for x in [*FANLAMP_CODECS, *ZHIJIA_CODECS, *ZHIMEI_CODECS, *AGARCE_CODECS, *REMOTES_CODECS]}
