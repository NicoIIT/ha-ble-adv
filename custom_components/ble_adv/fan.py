"""Fan Handling."""

from __future__ import annotations

import logging
from math import ceil
from typing import Any

from homeassistant.components.fan import (
    ATTR_DIRECTION,
    ATTR_OSCILLATING,
    ATTR_PERCENTAGE,
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

from .codecs.const import ATTR_DIR, ATTR_OSC, ATTR_SPEED, FAN_TYPE, FAN_TYPE_3SPEED
from .const import CONF_FANS, CONF_USE_DIR, CONF_USE_OSC, DOMAIN
from .device import BleAdvDevice, BleAdvEntAttr, BleAdvEntity, handle_change

_LOGGER = logging.getLogger(__name__)


def create_entity(options: dict[str, str], device: BleAdvDevice, index: int) -> BleAdvFan:
    """Create a Fan Entity from the entry."""
    features = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF | FanEntityFeature.SET_SPEED
    if options.get(CONF_USE_OSC, False):
        features |= FanEntityFeature.OSCILLATE
    if options.get(CONF_USE_DIR, False):
        features |= FanEntityFeature.DIRECTION

    return BleAdvFan(device, options[CONF_TYPE], features, index)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Entry setup."""
    device: BleAdvDevice = hass.data[DOMAIN][entry.entry_id]
    entities = [create_entity(options, device, i) for i, options in enumerate(entry.data[CONF_FANS])]
    async_add_entities(entities, True)


class BleAdvFan(BleAdvEntity, FanEntity):
    """Ble Adv Fan Entity."""

    _state_attributes = frozenset([(ATTR_PERCENTAGE, 100), (ATTR_DIRECTION, DIRECTION_FORWARD), (ATTR_OSCILLATING, False)])
    _attr_direction = None

    def __init__(self, device: BleAdvDevice, sub_type: str, features: FanEntityFeature, index: int) -> None:
        super().__init__(FAN_TYPE, sub_type, device, index)
        self._attr_supported_features: FanEntityFeature = features
        self._attr_speed_count: int = 3 if sub_type == FAN_TYPE_3SPEED else 6

    # redefining 'current_direction' as the attribute name is messy, and not the one defined in the last_state
    @property
    def current_direction(self) -> str | None:
        """Return the current direction of the fan."""
        return self._attr_direction

    def get_attrs(self) -> dict[str, Any]:
        """Get the attrs."""
        return {
            **super().get_attrs(),
            ATTR_DIR: self._attr_direction == DIRECTION_FORWARD,
            ATTR_OSC: self._attr_oscillating,
            ATTR_SPEED: ceil(
                percentage_to_ranged_value((1, self._attr_speed_count), self._attr_percentage if self._attr_percentage is not None else 0)
            ),
        }

    def apply_attrs(self, ent_attr: BleAdvEntAttr) -> None:
        """Apply the attributes to this Entity."""
        super().apply_attrs(ent_attr)
        if ATTR_DIR in ent_attr.chg_attrs:
            self._attr_direction = DIRECTION_FORWARD if ent_attr.attrs[ATTR_DIR] else DIRECTION_REVERSE
        if ATTR_OSC in ent_attr.chg_attrs:
            self._attr_oscillating = ent_attr.attrs[ATTR_OSC]  # type: ignore[none]
        if ATTR_SPEED in ent_attr.chg_attrs:
            self._attr_percentage = ranged_value_to_percentage((1, 6), ent_attr.attrs[ATTR_SPEED])  # type: ignore[none]

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

    @handle_change
    async def async_set_direction(self, direction: str) -> None:
        """Set the direction of the fan."""
        if not self._attr_is_on:
            self._set_state_percentage(self._attr_percentage)
        self._attr_direction = direction

    @handle_change
    async def async_oscillate(self, oscillating: bool) -> None:
        """Oscillate the fan."""
        if not self._attr_is_on:
            self._set_state_percentage(self._attr_percentage)
        self._attr_oscillating = oscillating
