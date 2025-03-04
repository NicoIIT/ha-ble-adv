"""Codecs Package."""  # noqa: A005

from abc import ABC  # noqa: F401

from .fanlamp import (
    TRANS_FANLAMP_V1,
    TRANS_FANLAMP_V2,
    FanLampEncoderV1,
    FanLampEncoderV2,
)
from .models import BleAdvCodec

CODECS = [
    # FanLamp Pro android App
    FanLampEncoderV1(0x83, False).id("fanlamp_pro_v1").header([0x77, 0xF8]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V1),
    FanLampEncoderV2([0x10, 0x80, 0x00], 0x0400, False).id("fanlamp_pro_v2").header([0xF0, 0x08]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V2),
    FanLampEncoderV2([0x20, 0x80, 0x00], 0x0400, True).id("fanlamp_pro_v3").header([0xF0, 0x08]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V2),
    # LampSmart Pro android App
    FanLampEncoderV1(0x81, False).id("lampsmart_pro_v1").header([0x77, 0xF8]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V1),
    FanLampEncoderV2([0x10, 0x80, 0x00], 0x0100, False).id("lampsmart_pro_v2").header([0xF0, 0x08]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V2),
    FanLampEncoderV2([0x30, 0x80, 0x00], 0x0100, True).id("lampsmart_pro_v3").header([0xF0, 0x08]).ble(0x19, 0x03).add_translators(TRANS_FANLAMP_V2),
    # FanLamp remotes
    FanLampEncoderV1(0x83, False, True, 0x00, 0x9372).id("remote_v1").header([0x56, 0x55, 0x18, 0x87, 0x52]).ble(0x00, 0xFF).add_translators(TRANS_FANLAMP_V1),
    FanLampEncoderV2([0x10, 0x00, 0x56], 0x0400, True).id("remote_v3").header([0xF0, 0x08]).ble(0x02, 0x16).add_translators(TRANS_FANLAMP_V2),
    FanLampEncoderV2([0x10, 0x00, 0x56], 0x0100, True).id("remote_v31").header([0xF0, 0x08]).ble(0x02, 0x16).add_translators(TRANS_FANLAMP_V2),
    # Legacy variants from no known apps, initially present in ESPHome component. Still used by some remotes
    FanLampEncoderV1(0x81, True, True, 0x55).id("other_v1b").header([0xF9, 0x08]).ble(0x02, 0x16).add_translators(TRANS_FANLAMP_V1),
    FanLampEncoderV1(0x81, True, True).id("other_v1a").header([0x77, 0xF8]).ble(0x02, 0x03).add_translators(TRANS_FANLAMP_V1),
    FanLampEncoderV2([0x10, 0x80, 0x00], 0x0100, False).id("other_v2").header([0xF0, 0x08]).ble(0x19, 0x16).add_translators(TRANS_FANLAMP_V2),
    FanLampEncoderV2([0x10, 0x80, 0x00], 0x0100, True).id("other_v3").header([0xF0, 0x08]).ble(0x19, 0x16).add_translators(TRANS_FANLAMP_V2),
]  # fmt: skip

PHONE_APPS = {
    "Fan Lamp Pro": ["fanlamp_pro_v3", "fanlamp_pro_v2", "fanlamp_pro_v1"],
    "Lamp Smart Pro": ["lampsmart_pro_v3", "lampsmart_pro_v2", "lampsmart_pro_v1"],
    "Other (legacy)": ["other_v1a", "other_v1b"],
}


def get_codecs() -> dict[str, BleAdvCodec]:
    """Get all codecs."""
    return {x.codec_id: x for x in CODECS}
