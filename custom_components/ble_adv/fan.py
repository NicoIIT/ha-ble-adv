"""Fan Handling."""

from __future__ import annotations

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

from .codecs.const import ATTR_DIR, ATTR_ON, ATTR_OSC, ATTR_PRESET, ATTR_SPEED, ATTR_SUB_TYPE, FAN_TYPE, FAN_TYPE_3SPEED
from .const import (
    CONF_FANS,
    CONF_PRESETS,
    CONF_REFRESH_DIR_ON_START,
    CONF_REFRESH_OSC_ON_START,
    CONF_USE_DIR,
    CONF_USE_OSC,
    DOMAIN,
)
from .device import ATTR_IS_ON, BleAdvDevice, BleAdvEntAttr, BleAdvEntity, BleAdvStateAttribute


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
    refresh_dir_on_start = options.get(CONF_REFRESH_DIR_ON_START, False)
    refresh_osc_on_start = options.get(CONF_REFRESH_OSC_ON_START, False)
    return BleAdvFan(device, options[CONF_TYPE], index, features, refresh_dir_on_start, refresh_osc_on_start, presets)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Entry setup."""
    device: BleAdvDevice = hass.data[DOMAIN][entry.entry_id]
    entities = [create_entity(options, device, i) for i, options in enumerate(entry.data[CONF_FANS]) if CONF_TYPE in options]
    async_add_entities(entities, True)


class BleAdvFan(BleAdvEntity, FanEntity):
    """Ble Adv Fan Entity."""

    _state_attributes = frozenset(
        [
            BleAdvStateAttribute(ATTR_IS_ON, False, [ATTR_ON]),
            BleAdvStateAttribute(ATTR_PERCENTAGE, 100, [ATTR_SPEED], [ATTR_PRESET_MODE]),
            BleAdvStateAttribute(ATTR_DIRECTION, DIRECTION_FORWARD, [ATTR_DIR]),
            BleAdvStateAttribute(ATTR_OSCILLATING, False, [ATTR_OSC]),
            BleAdvStateAttribute(ATTR_PRESET_MODE, None, [ATTR_PRESET], [ATTR_PERCENTAGE]),
        ]
    )
    _attr_direction = None

    def __init__(
        self,
        device: BleAdvDevice,
        sub_type: str,
        index: int,
        features: FanEntityFeature,
        refresh_dir_on_start: bool,
        refresh_osc_on_start: bool,
        presets: list[str],
    ) -> None:
        super().__init__(FAN_TYPE, sub_type, device, index)
        self._attr_supported_features: FanEntityFeature = features
        self._attr_speed_count: int = self._get_speed_count_from_type(sub_type)
        self._refresh_dir_on_start: bool = refresh_dir_on_start
        self._refresh_osc_on_start: bool = refresh_osc_on_start
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
        eff_percentage = self._attr_percentage if self._attr_percentage is not None else 0
        return {
            **super().get_attrs(),
            ATTR_DIR: self._attr_direction == DIRECTION_FORWARD,
            ATTR_OSC: self._attr_oscillating,
            ATTR_PRESET: self._attr_preset_mode,
            ATTR_SPEED: ceil(percentage_to_ranged_value((1, self._attr_speed_count), eff_percentage)),
        }

    def forced_changed_attr_on_start(self) -> list[str]:
        """List Forced changed attributes on start."""
        forced_attrs = []
        if self._attr_supported_features & FanEntityFeature.PRESET_MODE:
            forced_attrs.append(ATTR_PRESET)
        if self._refresh_osc_on_start and self._attr_supported_features & FanEntityFeature.OSCILLATE:
            forced_attrs.append(ATTR_OSC)
        if self._refresh_dir_on_start and self._attr_supported_features & FanEntityFeature.DIRECTION:
            forced_attrs.append(ATTR_DIR)
        return forced_attrs

    def apply_attrs(self, ent_attr: BleAdvEntAttr) -> None:
        """Apply the attributes to this Entity."""
        super().apply_attrs(ent_attr)
        if ATTR_DIR in ent_attr.chg_attrs:
            new_val = self.change_bool(self._attr_direction == DIRECTION_FORWARD, ent_attr.attrs[ATTR_DIR])
            self._attr_direction = DIRECTION_FORWARD if new_val else DIRECTION_REVERSE
        if ATTR_OSC in ent_attr.chg_attrs:
            self._attr_oscillating = self.change_bool(self._attr_oscillating, ent_attr.attrs[ATTR_OSC])
        if ATTR_SPEED in ent_attr.chg_attrs:
            self._attr_preset_mode = None
            recv_speed_count = self._get_speed_count_from_type(ent_attr.attrs[ATTR_SUB_TYPE])
            self._attr_percentage = ranged_value_to_percentage((1, recv_speed_count), ent_attr.attrs[ATTR_SPEED])
        if ATTR_PRESET in ent_attr.chg_attrs:
            self._attr_percentage = 0
            self._attr_preset_mode = ent_attr.attrs[ATTR_PRESET]

    async def async_turn_on(self, percentage: int | None = None, preset_mode: str | None = None, **kwargs) -> None:  # noqa: ANN003
        """Turn Entity on / set percentage / preset mode. Percentage is taking precedence over preset_mode."""
        if (percent := kwargs.get(ATTR_PERCENTAGE, percentage)) is not None:
            await self.async_set_percentage(percent)
        elif (preset := kwargs.get(ATTR_PRESET_MODE, preset_mode)) is not None:
            await self.async_set_preset_mode(preset)
        else:
            await self._handle_state_change({ATTR_IS_ON: True})

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        if percentage == 0:
            await self._handle_state_change({ATTR_IS_ON: False})
        else:
            await self._handle_state_change({ATTR_IS_ON: True, ATTR_PERCENTAGE: percentage})

    async def async_set_direction(self, direction: str) -> None:
        """Set the direction of the fan."""
        await self._handle_state_change({ATTR_IS_ON: True, ATTR_DIRECTION: direction})

    async def async_oscillate(self, oscillating: bool) -> None:
        """Oscillate the fan."""
        await self._handle_state_change({ATTR_IS_ON: True, ATTR_OSCILLATING: oscillating})

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        await self._handle_state_change({ATTR_IS_ON: True, ATTR_PRESET_MODE: preset_mode})
