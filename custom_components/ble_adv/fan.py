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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import percentage_to_ranged_value, ranged_value_to_percentage

from .codecs.models import FAN_TYPE
from .const import DOMAIN
from .device import BleAdvDevice, BleAdvEntAttr, BleAdvEntity, handle_change

_LOGGER = logging.getLogger(__name__)


def create_entity(options: dict[str, str], device: BleAdvDevice, index: int) -> BleAdvFan:
    """Create a Fan Entity from the entry."""
    features = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF | FanEntityFeature.SET_SPEED
    if options.get("oscillating", False):
        features |= FanEntityFeature.OSCILLATE
    if options.get("direction", False):
        features |= FanEntityFeature.DIRECTION

    return BleAdvFan(device, options["type"], features, index)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Entry setup."""
    device: BleAdvDevice = hass.data[DOMAIN][entry.entry_id]
    entities = [create_entity(options, device, i) for i, options in enumerate(entry.data[FAN_TYPE])]
    async_add_entities(entities, True)


class BleAdvFan(FanEntity, BleAdvEntity):
    """Ble Adv Fan Entity."""

    _restored_attributes = [(ATTR_PERCENTAGE, 100), (ATTR_DIRECTION, DIRECTION_FORWARD), (ATTR_OSCILLATING, False)]
    _attr_direction = None

    def __init__(self, device: BleAdvDevice, fan_type: str, features: FanEntityFeature, index: int) -> None:
        super().__init__(FAN_TYPE, device, index)
        self._type: str = fan_type
        self._attr_supported_features: FanEntityFeature = features
        self._attr_speed_count: int = 3 if fan_type == "3speed" else 6

    # redefining 'is_on' as the one at FanEntity level overrides the one at ToggleEntity level
    # and is based on 'percentage' and 'modes', which means we have to put 0 as percentage to switch the Fan OFF
    # but then when we switch it back ON we 'lost' the percentage... and have to save it somewhere else
    # and it would then not be restored on HA restart...
    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return self._attr_is_on

    # redefining 'current_direction' as the attribute name is messy, and not the one defined in the last_state
    @property
    def current_direction(self) -> str | None:
        """Return the current direction of the fan."""
        return self._attr_direction

    def get_attrs(self) -> dict[str, Any]:
        """Get the attrs."""
        return {
            "on": self._attr_is_on,
            "type": self._type,
            "dir": self._attr_direction == DIRECTION_FORWARD,
            "osc": self._attr_oscillating,
            "speed": ceil(percentage_to_ranged_value((1, self._attr_speed_count), self._attr_percentage if self._attr_percentage is not None else 0)),
        }

    def apply_attrs(self, ent_attr: BleAdvEntAttr) -> None:
        """Apply the attributes to this Entity."""
        super().apply_attrs(ent_attr)
        if "dir" in ent_attr.chg_attrs:
            self._attr_direction = DIRECTION_FORWARD if ent_attr.attrs["dir"] else DIRECTION_REVERSE
        if "osc" in ent_attr.chg_attrs:
            self._attr_oscillating = ent_attr.attrs["osc"]  # type: ignore[none]
        if "speed" in ent_attr.chg_attrs:
            self._attr_percentage = ranged_value_to_percentage((1, 6), ent_attr.attrs["speed"])  # type: ignore[none]

    async def _async_set_percentage(self, percentage: int | None) -> None:
        """Set the speed percentage of the fan."""
        if percentage is not None and percentage > 0:
            self._attr_percentage = percentage
            self._attr_is_on = True
        else:
            self._attr_is_on = False

    @handle_change
    async def async_turn_off(self, **kwargs) -> None:  # noqa: ANN003, ARG002
        """Turn off the fan."""
        self._attr_is_on = False

    @handle_change
    async def async_turn_on(self, speed: str | None = None, percentage: int | None = None, preset_mode: str | None = None, **kwargs) -> None:  # noqa: ANN003, ARG002
        """Turn on the fan."""
        await self._async_set_percentage(percentage if percentage is not None else self._attr_percentage)

    @handle_change
    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        await self._async_set_percentage(percentage)

    @handle_change
    async def async_set_direction(self, direction: str) -> None:
        """Set the direction of the fan."""
        if not self._attr_is_on:
            await self._async_set_percentage(self._attr_percentage)
        self._attr_direction = direction

    @handle_change
    async def async_oscillate(self, oscillating: bool) -> None:
        """Oscillate the fan."""
        if not self._attr_is_on:
            await self._async_set_percentage(self._attr_percentage)
        self._attr_oscillating = oscillating
