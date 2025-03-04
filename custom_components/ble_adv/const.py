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

PLATFORMS = [
    Platform.FAN,
    Platform.LIGHT,
]
