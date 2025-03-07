"""Ble Adv component constants."""

from homeassistant.const import Platform

DOMAIN = "ble_adv"
PLATFORMS = []

CONF_COORDINATOR_ID = "coordinator_unique_id"

CONF_INDEX = "index"
CONF_CODEC_ID = "codec_id"
CONF_ADAPTER_ID = "adapter_id"
CONF_FORCED_ID = "forced_id"
CONF_PHONE_APP = "phone_app"
CONF_TYPE_NONE = "none"
CONF_TECHNICAL = "technical"
CONF_INTERVAL = "interval"
CONF_REPEAT = "repeat"
CONF_DURATION = "duration"
CONF_MIN_BRIGHTNESS = "min_brightness"
CONF_USE_DIR = "direction"
CONF_USE_OSC = "oscillating"
CONF_LIGHTS = "lights"
CONF_FANS = "fans"

PLATFORMS = [
    Platform.FAN,
    Platform.LIGHT,
]
