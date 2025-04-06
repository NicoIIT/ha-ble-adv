"""Light Handling."""

from __future__ import annotations

from typing import Any, Self

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_COLOR_TEMP_KELVIN, ATTR_EFFECT, ATTR_RGB_COLOR, LightEntity
from homeassistant.components.light.const import DEFAULT_MAX_KELVIN, DEFAULT_MIN_KELVIN, ColorMode, LightEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .codecs.const import (
    ATTR_BLUE,
    ATTR_BLUE_F,
    ATTR_BR,
    ATTR_CMD,
    ATTR_CMD_BR_DOWN,
    ATTR_CMD_BR_UP,
    ATTR_CMD_CT_DOWN,
    ATTR_CMD_CT_UP,
    ATTR_COLD,
    ATTR_CT,
    ATTR_CT_REV,
    ATTR_GREEN,
    ATTR_GREEN_F,
    ATTR_RED,
    ATTR_RED_F,
    ATTR_STEP,
    ATTR_WARM,
    LIGHT_TYPE,
    LIGHT_TYPE_CWW,
    LIGHT_TYPE_ONOFF,
    LIGHT_TYPE_RGB,
)
from .const import CONF_EFFECTS, CONF_LIGHTS, CONF_MIN_BRIGHTNESS, CONF_REFRESH_ON_START, CONF_REVERSED, DOMAIN
from .device import BleAdvDevice, BleAdvEntAttr, BleAdvEntity


class BleAdvLightError(Exception):
    """Light Error."""


def create_entity(options: dict[str, str | float], device: BleAdvDevice, index: int) -> BleAdvLightBase:
    """Create a Light Entity from the entry."""
    light_type: str = str(options[CONF_TYPE])
    min_br: int = int(options.get(CONF_MIN_BRIGHTNESS, 3))
    refresh_on_start = bool(options.get(CONF_REFRESH_ON_START, False))
    if light_type == LIGHT_TYPE_RGB:
        return BleAdvLightRGB(light_type, device, index, min_br, refresh_on_start).set_effects(options.get(CONF_EFFECTS, []))  # type: ignore[none]
    if light_type == LIGHT_TYPE_CWW:
        return BleAdvLightCWW(light_type, device, index, min_br, refresh_on_start).set_reverse_cw(bool(options.get(CONF_REVERSED, False)))
    if light_type == LIGHT_TYPE_ONOFF:
        return BleAdvLightBinary(light_type, device, index)
    raise BleAdvLightError("Invalid Type")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Entr setup."""
    device: BleAdvDevice = hass.data[DOMAIN][entry.entry_id]
    entities = [create_entity(options, device, i) for i, options in enumerate(entry.data[CONF_LIGHTS]) if CONF_TYPE in options]
    async_add_entities(entities, True)


class BleAdvLightBase(BleAdvEntity, LightEntity):
    """Base Light."""

    def __init__(self, sub_type: str, device: BleAdvDevice, index: int) -> None:
        super().__init__(LIGHT_TYPE, sub_type, device, index)


class BleAdvLightBinary(BleAdvLightBase):
    """Binary Light."""

    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_color_mode = ColorMode.ONOFF


class BleAdvLightWithBrightness(BleAdvLightBase):
    """Base Light with Brightness."""

    def __init__(self, sub_type: str, device: BleAdvDevice, index: int, min_br: float, refresh_on_start: bool) -> None:
        super().__init__(sub_type, device, index)
        self._min_brighntess = float(min_br / 100.0)
        self._refresh_on_start = refresh_on_start

    def _pct(self, val: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
        return min(max_val, max(min_val, val))

    def _set_state_brightness(self, brightness: int) -> None:
        self._set_br(brightness / 255.0)

    def _set_br(self, br: float) -> None:
        self._attr_brightness = int(255.0 * self._pct(br, self._min_brighntess))

    def _get_br(self) -> float:
        return self._attr_brightness / 255.0 if self._attr_brightness is not None else 0

    def get_attrs(self) -> dict[str, Any]:
        """Get the attrs."""
        return {**super().get_attrs(), ATTR_BR: self._get_br()}

    def forced_changed_attr_on_start(self) -> list[str]:
        """List Forced changed attributes on start."""
        return [ATTR_BR] if self._refresh_on_start else []

    def apply_attrs(self, ent_attr: BleAdvEntAttr) -> None:
        """Apply attributes to entity."""
        super().apply_attrs(ent_attr)
        if ATTR_BR in ent_attr.chg_attrs:
            self._set_br(ent_attr.get_attr_as_float(ATTR_BR))
        elif ATTR_CMD in ent_attr.chg_attrs:
            if ent_attr.attrs.get(ATTR_CMD) == ATTR_CMD_BR_UP:
                self._set_br(self._get_br() + ent_attr.get_attr_as_float(ATTR_STEP))
            elif ent_attr.attrs.get(ATTR_CMD) == ATTR_CMD_BR_DOWN:
                self._set_br(self._get_br() - ent_attr.get_attr_as_float(ATTR_STEP))


class BleAdvLightRGB(BleAdvLightWithBrightness):
    """RGB Light."""

    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB
    _state_attributes = frozenset([(ATTR_BRIGHTNESS, 255), (ATTR_RGB_COLOR, (255, 255, 255)), (ATTR_EFFECT, None)])

    def set_effects(self, effects: list[Any]) -> Self:
        """Set Effects."""
        self._attr_effect_list = effects
        self._attr_supported_features |= LightEntityFeature.EFFECT if len(effects) > 0 else 0
        return self

    async def async_turn_on(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        """Override base turn_on to reset effect."""
        self._attr_effect = None
        await super().async_turn_on(self, *args, **kwargs)

    def _get_rgb(self) -> tuple[float, float, float]:
        """Get RGB tuple."""
        if self._attr_rgb_color is not None:
            return (self._attr_rgb_color[0] / 255.0, self._attr_rgb_color[1] / 255.0, self._attr_rgb_color[2] / 255.0)
        return (0, 0, 0)

    def _set_rgb(self, r: float, g: float, b: float) -> None:
        self._attr_rgb_color = (int(self._pct(r) * 255), int(self._pct(g) * 255), int(self._pct(b) * 255))

    def get_attrs(self) -> dict[str, Any]:
        """Get the attrs."""
        br = self._get_br()
        r, g, b = self._get_rgb()
        return {
            **super().get_attrs(),
            ATTR_RED: r,
            ATTR_GREEN: g,
            ATTR_BLUE: b,
            ATTR_RED_F: r * br,
            ATTR_GREEN_F: g * br,
            ATTR_BLUE_F: b * br,
            ATTR_EFFECT: self._attr_effect,
        }

    def forced_changed_attr_on_start(self) -> list[str]:
        """List Forced changed attributes on start."""
        forced_attrs = super().forced_changed_attr_on_start()
        return [*forced_attrs, ATTR_RED, ATTR_RED_F, ATTR_GREEN, ATTR_GREEN_F, ATTR_BLUE, ATTR_BLUE_F] if forced_attrs else []

    def apply_attrs(self, ent_attr: BleAdvEntAttr) -> None:
        """Apply attributes to entity."""
        super().apply_attrs(ent_attr)
        if ATTR_RED in ent_attr.chg_attrs or ATTR_GREEN in ent_attr.chg_attrs or ATTR_BLUE in ent_attr.chg_attrs:
            self._set_rgb(ent_attr.get_attr_as_float(ATTR_RED), ent_attr.get_attr_as_float(ATTR_GREEN), ent_attr.get_attr_as_float(ATTR_BLUE))
        elif ATTR_RED_F in ent_attr.chg_attrs or ATTR_GREEN_F in ent_attr.chg_attrs or ATTR_BLUE_F in ent_attr.chg_attrs:
            r = ent_attr.get_attr_as_float(ATTR_RED_F)
            g = ent_attr.get_attr_as_float(ATTR_GREEN_F)
            b = ent_attr.get_attr_as_float(ATTR_BLUE_F)
            br = max(r, g, b)
            self._set_br(br)
            self._set_rgb(r / br, g / br, b / br)


class BleAdvLightCWW(BleAdvLightWithBrightness):
    """CWW Light."""

    _attr_min_color_temp_kelvin = DEFAULT_MIN_KELVIN  # 2000K => Full WARM
    _attr_max_color_temp_kelvin = DEFAULT_MAX_KELVIN  # 6535K => Full COLD
    _attr_supported_color_modes = {ColorMode.COLOR_TEMP}
    _attr_color_mode = ColorMode.COLOR_TEMP
    _state_attributes = frozenset([(ATTR_BRIGHTNESS, 255), (ATTR_COLOR_TEMP_KELVIN, DEFAULT_MAX_KELVIN)])

    def set_reverse_cw(self, reverse_cw: bool) -> Self:
        """Reverse Cold / Warm."""
        self._reverse_cw = reverse_cw
        return self

    def _set_ct(self, ct_percent: float) -> None:
        """Set Color Temperature from float [0.0 -> 1.0].

        if no 'reversed' option:
            Input 0.0 for COLD / DEFAULT_MAX_KELVIN
            Input 1.0 for WARM / DEFAULT_MIN_KELVIN
        if 'reversed' option:
            Input 1.0 for COLD / DEFAULT_MAX_KELVIN
            Input 0.0 for WARM / DEFAULT_MIN_KELVIN
        """
        ctr = ct_percent if self._reverse_cw else 1.0 - ct_percent
        self._attr_color_temp_kelvin = int(DEFAULT_MIN_KELVIN + (DEFAULT_MAX_KELVIN - DEFAULT_MIN_KELVIN) * self._pct(ctr))

    def _add_to_ct(self, step: float) -> None:
        """Add step to Color Temperature from float [0.0 -> 1.0].

        if no 'reversed' option:
            add step
        if 'reversed' option:
            remove step
        """
        self._set_ct((self._get_ct() - step) if self._reverse_cw else (self._get_ct() + step))

    def _get_ct(self) -> float:
        """Get Color Temperature as float [0.0 -> 1.0].

        if no 'reversed' option:
            returns 0.0 for COLD / DEFAULT_MAX_KELVIN
            returns 1.0 for WARM / DEFAULT_MIN_KELVIN
        if reversed option:
            returns 1.0 for COLD / DEFAULT_MAX_KELVIN
            returns 0.0 for WARM / DEFAULT_MIN_KELVIN
        """
        kelvin = self._attr_color_temp_kelvin if self._attr_color_temp_kelvin is not None else DEFAULT_MIN_KELVIN
        ctr = (kelvin - DEFAULT_MIN_KELVIN) / float(DEFAULT_MAX_KELVIN - DEFAULT_MIN_KELVIN)
        return ctr if self._reverse_cw else 1.0 - ctr

    def get_attrs(self) -> dict[str, Any]:
        """Get the attrs."""
        br = self._get_br()
        ct = self._get_ct()
        # //  For constant_brightness
        # //  cold = (1.0 - ct)
        # //  warm = ct
        cold = min(1.0, (1.0 - ct) * 2.0)
        warm = min(1.0, ct * 2.0)
        return {**super().get_attrs(), ATTR_CT: ct, ATTR_CT_REV: 1.0 - ct, ATTR_WARM: br * warm, ATTR_COLD: br * cold}

    def forced_changed_attr_on_start(self) -> list[str]:
        """List Forced changed attributes on start."""
        forced_attrs = super().forced_changed_attr_on_start()
        return [*forced_attrs, ATTR_CT, ATTR_CT_REV, ATTR_COLD, ATTR_WARM] if forced_attrs else []

    def apply_attrs(self, ent_attr: BleAdvEntAttr) -> None:
        """Apply attributes to entity."""
        super().apply_attrs(ent_attr)
        if ATTR_COLD in ent_attr.chg_attrs and ATTR_WARM in ent_attr.chg_attrs:
            cold = ent_attr.get_attr_as_float(ATTR_COLD)
            warm = ent_attr.get_attr_as_float(ATTR_WARM)
            self._set_br(max(cold, warm))
            self._set_ct(1.0 - ((cold / warm) / 2.0) if (cold < warm) else ((warm / cold) / 2.0))
            # // For constant brightness:
            # // self._set_ct(warm / (cold + warm))
        elif ATTR_COLD in ent_attr.chg_attrs:
            self._set_ct(ent_attr.get_attr_as_float(ATTR_COLD))
        elif ATTR_WARM in ent_attr.chg_attrs:
            self._set_ct(1.0 - ent_attr.get_attr_as_float(ATTR_WARM))
        elif ATTR_CT in ent_attr.chg_attrs:
            self._set_ct(ent_attr.get_attr_as_float(ATTR_CT))
        elif ATTR_CT_REV in ent_attr.chg_attrs:
            self._set_ct(1.0 - ent_attr.get_attr_as_float(ATTR_CT_REV))
        elif ATTR_CMD in ent_attr.chg_attrs:
            if ent_attr.attrs.get(ATTR_CMD) == ATTR_CMD_CT_UP:
                self._add_to_ct(ent_attr.get_attr_as_float(ATTR_STEP))
            elif ent_attr.attrs.get(ATTR_CMD) == ATTR_CMD_CT_DOWN:
                self._add_to_ct(-ent_attr.get_attr_as_float(ATTR_STEP))
