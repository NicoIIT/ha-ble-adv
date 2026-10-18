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

from .codecs.const import (
    ATTR_DIR,
    ATTR_ON,
    ATTR_OSC,
    ATTR_PRESET,
    ATTR_SPEED,
    ATTR_SPEED_COUNT,
    FAN_TYPE,
)
from .const import (
    CONF_FANS,
    CONF_FORCED_CMDS,
    CONF_PRESET_SLEEP,
    CONF_PRESET_TURBO,
    CONF_PRESET_WORK,
    CONF_PRESETS,
    CONF_REFRESH_DIR_ON_START,
    CONF_REFRESH_OSC_ON_START,
    CONF_USE_DIR,
    CONF_USE_OSC,
    DOMAIN,
    PRESET_MODE_SLEEP,
    PRESET_MODE_TURBO,
    PRESET_MODE_WORK,
)
from .device import ATTR_IS_ON, BleAdvDevice, BleAdvEntAttr, BleAdvEntity, BleAdvStateAttribute


def get_speed_presets(options: dict[str, Any], max_speed: int) -> dict[str, int]:
    """Extract speed presets from configured options respecting max_speed limits."""
    presets: dict[str, int] = {}
    preset_definitions = [
        (PRESET_MODE_SLEEP, CONF_PRESET_SLEEP),
        (PRESET_MODE_WORK, CONF_PRESET_WORK),
        (PRESET_MODE_TURBO, CONF_PRESET_TURBO),
    ]
    for name, conf_key in preset_definitions:
        val = options.get(conf_key)
        if val is not None and str(val) != "none" and str(val).isdigit():
            spd = int(val)
            if 1 <= spd <= max_speed:
                presets[name] = spd
    return presets


def create_entity(options: dict[str, Any], device: BleAdvDevice, index: int) -> BleAdvFan:
    """Create a Fan Entity from the entry."""
    features = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF | FanEntityFeature.SET_SPEED
    presets = list(options.get(CONF_PRESETS, []))
    speed_count = int(options[CONF_TYPE][:-5])
    speed_presets = get_speed_presets(options, speed_count)

    if options.get(CONF_USE_OSC, False):
        features |= FanEntityFeature.OSCILLATE
    if options.get(CONF_USE_DIR, False):
        features |= FanEntityFeature.DIRECTION
    if len(presets) > 0 or len(speed_presets) > 0:
        features |= FanEntityFeature.PRESET_MODE

    fan = BleAdvFan(device, index, speed_count, features, presets, speed_presets)
    fan.refresh_dir_on_start = options.get(CONF_REFRESH_DIR_ON_START, False)
    fan.refresh_osc_on_start = options.get(CONF_REFRESH_OSC_ON_START, False)
    fan.set_forced_cmds(options.get(CONF_FORCED_CMDS, []))

    return fan


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Entry setup."""
    device: BleAdvDevice = getattr(entry, "runtime_data", None) or hass.data[DOMAIN][entry.entry_id]
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
            BleAdvStateAttribute(ATTR_PRESET_MODE, None, [ATTR_PRESET]),
        ]
    )
    _attr_direction = None

    refresh_dir_on_start: bool = False
    refresh_osc_on_start: bool = False

    def __init__(
        self,
        device: BleAdvDevice,
        index: int,
        speed_count: int,
        features: FanEntityFeature,
        presets: list[str],
        speed_presets: dict[str, int] | None = None,
    ) -> None:
        super().__init__(FAN_TYPE, None, device, index)
        self._attr_supported_features: FanEntityFeature = features
        self._attr_speed_count: int = speed_count
        self._hardware_presets: list[str] = list(presets)
        self._speed_presets: dict[str, int] = speed_presets or {}
        self._attr_preset_modes = list(self._speed_presets.keys()) + [p for p in presets if p not in self._speed_presets]

    @property
    def current_direction(self) -> str | None:
        """Return the current direction of the fan."""
        return self._attr_direction

    @property
    def percentage(self) -> int | None:
        """Return the percentage of the fan."""
        return 0 if self._attr_preset_mode in self._hardware_presets else self._attr_percentage

    def _match_speed_preset(self, preset_mode: str) -> int | None:
        """Match preset mode string or localized alias to corresponding speed level."""
        if preset_mode in self._speed_presets:
            return self._speed_presets[preset_mode]
        norm = preset_mode.lower().strip()
        for name, spd in self._speed_presets.items():
            if name.lower() == norm:
                return spd
            if norm in ("sleep", "sleep_mode", "dormir", "modo dormir", "schlafmodus", "sommeil") and name == PRESET_MODE_SLEEP:
                return spd
            if norm in ("work", "work_mode", "trabalho", "modo trabalho", "arbeitsmodus", "travail", "trabajo") and name == PRESET_MODE_WORK:
                return spd
            if norm in ("turbo", "turbo_mode", "calor extremo", "extremo", "turbomodus", "mode turbo") and name == PRESET_MODE_TURBO:
                return spd
        return None

    def get_attrs(self) -> dict[str, Any]:
        """Get the attrs."""
        eff_percentage = self._attr_percentage if self._attr_percentage is not None else 0
        preset_attr = self._attr_preset_mode if self._attr_preset_mode in self._hardware_presets else None
        return {
            **super().get_attrs(),
            ATTR_SPEED_COUNT: self._attr_speed_count,
            ATTR_DIR: self._attr_direction == DIRECTION_FORWARD,
            ATTR_OSC: self._attr_oscillating,
            ATTR_PRESET: preset_attr,
            ATTR_SPEED: ceil(percentage_to_ranged_value((1, self._attr_speed_count), eff_percentage)),
        }

    def forced_changed_attr_on_start(self) -> list[str]:
        """List Forced changed attributes on start."""
        forced_attrs = []
        if self._attr_supported_features & FanEntityFeature.PRESET_MODE and self._attr_preset_mode in self._hardware_presets:
            forced_attrs.append(ATTR_PRESET)
        if self.refresh_osc_on_start and self._attr_supported_features & FanEntityFeature.OSCILLATE:
            forced_attrs.append(ATTR_OSC)
        if self.refresh_dir_on_start and self._attr_supported_features & FanEntityFeature.DIRECTION:
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
            speed_count = ent_attr.attrs.get(ATTR_SPEED_COUNT, self._attr_speed_count)
            speed_val = ent_attr.attrs[ATTR_SPEED]
            self._attr_percentage = ranged_value_to_percentage((1, speed_count), speed_val)
            self._attr_preset_mode = next((name for name, spd in self._speed_presets.items() if spd == speed_val), None)
        if ATTR_PRESET in ent_attr.chg_attrs:
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
            self._attr_preset_mode = None
            await self._handle_state_change({ATTR_IS_ON: False})
        else:
            speed_val = ceil(percentage_to_ranged_value((1, self._attr_speed_count), percentage))
            self._attr_preset_mode = next((name for name, spd in self._speed_presets.items() if spd == speed_val), None)
            await self._handle_state_change({ATTR_IS_ON: True, ATTR_PERCENTAGE: percentage})

    async def async_set_direction(self, direction: str) -> None:
        """Set the direction of the fan."""
        await self._handle_state_change({ATTR_IS_ON: True, ATTR_DIRECTION: direction})

    async def async_oscillate(self, oscillating: bool) -> None:
        """Oscillate the fan."""
        await self._handle_state_change({ATTR_IS_ON: True, ATTR_OSCILLATING: oscillating})

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        target_speed = self._match_speed_preset(preset_mode)
        if target_speed is not None:
            target_percent = ranged_value_to_percentage((1, self._attr_speed_count), target_speed)
            display_name = next((name for name, spd in self._speed_presets.items() if spd == target_speed), preset_mode)
            self._attr_preset_mode = display_name
            await self.async_set_percentage(target_percent)
        else:
            await self._handle_state_change({ATTR_IS_ON: True, ATTR_PRESET_MODE: preset_mode})
