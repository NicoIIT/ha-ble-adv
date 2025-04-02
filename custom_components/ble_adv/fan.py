"""Fan Handling."""

from __future__ import annotations

import logging
from math import ceil
from typing import Any

from homeassistant.components.fan import (
    ATTR_DIRECTION,
    ATTR_OSCILLATING,
    ATTR_PERCENTAGE,
    ATTR_PRESET_MODE,
    DIRECTION_FORWARD,
    DIRECTION_REVERSE,
    FanEntity,
    FanEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import percentage_to_ranged_value, ranged_value_to_percentage

from .codecs.const import ATTR_DIR, ATTR_OSC, ATTR_PRESET, ATTR_SPEED, ATTR_SUB_TYPE, FAN_TYPE, FAN_TYPE_3SPEED
from .const import (
    CONF_FANS,
    CONF_PRESETS,
    CONF_REFRESH_ON_START,
    CONF_USE_DIR,
    CONF_USE_OSC,
    DOMAIN,
)
from .device import BleAdvDevice, BleAdvEntAttr, BleAdvEntity, handle_change

_LOGGER = logging.getLogger(__name__)


def create_entity(options: dict[str, Any], device: BleAdvDevice, index: int) -> BleAdvFan:
    """Create a Fan Entity from the entry."""
    features = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF | FanEntityFeature.SET_SPEED
    presets = options.get(CONF_PRESETS, [])
    if options.get(CONF_USE_OSC, False):
        features |= FanEntityFeature.OSCILLATE
    if options.get(CONF_USE_DIR, False):
        features |= FanEntityFeature.DIRECTION
    if len(presets) > 0:
        features |= FanEntityFeature.PRESET_MODE
    refresh_on_start = options.get(CONF_REFRESH_ON_START, False)
    return BleAdvFan(device, options[CONF_TYPE], index, features, refresh_on_start, presets)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Entry setup."""
    device: BleAdvDevice = hass.data[DOMAIN][entry.entry_id]
    entities = [create_entity(options, device, i) for i, options in enumerate(entry.data[CONF_FANS]) if CONF_TYPE in options]
    async_add_entities(entities, True)


class BleAdvFan(BleAdvEntity, FanEntity):
    """Ble Adv Fan Entity."""

    _state_attributes = frozenset([(ATTR_PERCENTAGE, 100), (ATTR_DIRECTION, DIRECTION_FORWARD), (ATTR_OSCILLATING, False), (ATTR_PRESET_MODE, None)])
    _attr_direction = None
    _attr_preset_mode = None

    def __init__(
        self, device: BleAdvDevice, sub_type: str, index: int, features: FanEntityFeature, refresh_on_start: bool, presets: list[str]
    ) -> None:
        super().__init__(FAN_TYPE, sub_type, device, index)
        self._attr_supported_features: FanEntityFeature = features
        self._attr_speed_count: int = self._get_speed_count_from_type(sub_type)
        self._refresh_on_start: bool = refresh_on_start
        self._attr_preset_modes = presets

    # redefining 'current_direction' as the attribute name is messy, and not the one defined in the last_state
    @property
    def current_direction(self) -> str | None:
        """Return the current direction of the fan."""
        return self._attr_direction

    def _get_speed_count_from_type(self, sub_type: str) -> int:
        """Convert the Fan sub_type into the number of speed."""
        return 3 if sub_type == FAN_TYPE_3SPEED else 6

    def get_attrs(self) -> dict[str, Any]:
        """Get the attrs."""
        return {
            **super().get_attrs(),
            ATTR_DIR: self._attr_direction == DIRECTION_FORWARD,
            ATTR_OSC: self._attr_oscillating,
            ATTR_PRESET: self._attr_preset_mode,
            ATTR_SPEED: ceil(
                percentage_to_ranged_value((1, self._attr_speed_count), self._attr_percentage if self._attr_percentage is not None else 0)
            ),
        }

    def forced_changed_attr_on_start(self) -> list[str]:
        """List Forced changed attributes on start."""
        forced_attrs = []
        if self._refresh_on_start:
            if self._attr_supported_features & FanEntityFeature.OSCILLATE:
                forced_attrs.append(ATTR_OSC)
            if self._attr_supported_features & FanEntityFeature.DIRECTION:
                forced_attrs.append(ATTR_DIR)
        return forced_attrs

    def apply_attrs(self, ent_attr: BleAdvEntAttr) -> None:
        """Apply the attributes to this Entity."""
        super().apply_attrs(ent_attr)
        if ATTR_DIR in ent_attr.chg_attrs:
            self._attr_direction = DIRECTION_FORWARD if ent_attr.attrs[ATTR_DIR] else DIRECTION_REVERSE
        if ATTR_OSC in ent_attr.chg_attrs:
            self._attr_oscillating = ent_attr.attrs[ATTR_OSC]  # type: ignore[none]
        if ATTR_SPEED in ent_attr.chg_attrs:
            recv_speed_count = self._get_speed_count_from_type(ent_attr.attrs[ATTR_SUB_TYPE])
            self._attr_percentage = ranged_value_to_percentage((1, recv_speed_count), ent_attr.attrs[ATTR_SPEED])

    def _set_state_percentage(self, percentage: int | None) -> None:
        """Set the speed percentage of the fan."""
        if percentage is not None and percentage > 0:
            self._attr_percentage = percentage
            self._attr_is_on = True
        else:
            self._attr_is_on = False

    @handle_change
    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        self._set_state_percentage(percentage)
        self._attr_preset_mode = None

    @handle_change
    async def async_set_direction(self, direction: str) -> None:
        """Set the direction of the fan."""
        if self._attr_is_on:
            self._attr_direction = direction

    @handle_change
    async def async_oscillate(self, oscillating: bool) -> None:
        """Oscillate the fan."""
        if self._attr_is_on:
            self._attr_oscillating = oscillating

    @handle_change
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        if self._attr_is_on:
            self._attr_preset_mode = preset_mode
