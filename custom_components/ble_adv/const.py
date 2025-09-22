"""Ble Adv component constants."""

from homeassistant.const import Platform

DOMAIN = "ble_adv"
PLATFORMS = [Platform.LIGHT, Platform.FAN]

CONF_COORDINATOR_ID = "coordinator_unique_id"

CONF_LAST_VERSION = 6

CONF_INDEX = "index"
CONF_CODEC_ID = "codec_id"
CONF_ADAPTER_ID = "adapter_id"
CONF_ADAPTER_IDS = "adapter_ids"
CONF_FORCED_ID = "forced_id"
CONF_PHONE_APP = "phone_app"
CONF_TYPE_NONE = "none"
CONF_RAW = "raw"
CONF_TECHNICAL = "technical"
CONF_INTERVAL = "interval"
CONF_REPEAT = "repeat"
CONF_REPEATS = "repeats"
CONF_DURATION = "duration"
CONF_FORCED_CMDS = "forced_cmds"
CONF_FORCED_ON = "turn_on"
CONF_FORCED_OFF = "turn_off"
CONF_DEVICE_QUEUE = "device_queue"
CONF_MIN_BRIGHTNESS = "min_brightness"
CONF_USE_DIR = "direction"
CONF_USE_OSC = "oscillating"
CONF_REFRESH_DIR_ON_START = "refresh_dir_on_start"
CONF_REFRESH_OSC_ON_START = "refresh_osc_on_start"
CONF_PRESETS = "presets"
CONF_EFFECTS = "effects"
CONF_REFRESH_ON_START = "refresh_on_start"
CONF_REVERSED = "reversed"
CONF_LIGHTS = "lights"
CONF_FANS = "fans"
CONF_REMOTE = "remote"
CONF_MAX_ENTITY_NB = 3  # The max nb of entity that the config can handle in translations json files

# Taken from https://www.bluetooth.com/specifications/assigned-numbers/
CONF_GOOGLE_LCC_UUIDS = [
    0xFEF4,
    0xFEF3,
    0xFED8,
    0xFEAA,
    0xFEA0,
    0xFE9F,
    0xFE56,
    0xFE55,
    0xFE50,
    0xFE2C,
    0xFE27,
    0xFE26,
    0xFE19,
    0xFDF0,
    0xFDE2,
    0xFD96,
    0xFD8C,
    0xFD87,
    0xFD63,
    0xFD62,
    0xFD36,
    0xFCF1,
    0xFCCF,
    0xFCB1,
    0xFC73,
    0xFC56,
]

CONF_APPLE_INC_UUIDS = [
    0xFED4,
    0xFED3,
    0xFED2,
    0xFED1,
    0xFED0,
    0xFECF,
    0xFECE,
    0xFECD,
    0xFECC,
    0xFECB,
    0xFECA,
    0xFEC9,
    0xFEC8,
    0xFEC7,
    0xFE8B,
    0xFE8A,
    0xFE25,
    0xFD6F,
]
