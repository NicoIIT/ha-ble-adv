"""Light Handling."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    LightEntity,
)
from homeassistant.components.light.const import (
    DEFAULT_MAX_KELVIN,
    DEFAULT_MIN_KELVIN,
    ColorMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .codecs.models import LIGHT_TYPE, LIGHT_TYPE_CWW, LIGHT_TYPE_ONOFF, LIGHT_TYPE_RGB
from .const import DOMAIN
from .device import BleAdvDevice, BleAdvEntAttr, BleAdvEntity, handle_change

_LOGGER = logging.getLogger(__name__)


class BleAdvLightError(Exception):
    """Light Error."""


def create_entity(options: dict[str, str | float], device: BleAdvDevice, index: int) -> BleAdvLightBase:
    """Create a Light Entity from the entry."""
    light_type: str = str(options["type"])
    min_br: int = int(options.get("min_brightness", 3))
    if light_type == LIGHT_TYPE_RGB:
        return BleAdvLightRGB(light_type, min_br, device, index)
    if light_type == LIGHT_TYPE_CWW:
        return BleAdvLightCWW(light_type, min_br, device, index)
    if light_type == LIGHT_TYPE_ONOFF:
        return BleAdvLightBinary(light_type, min_br, device, index)
    raise BleAdvLightError("Invalid Type")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Entr setup."""
    device: BleAdvDevice = hass.data[DOMAIN][entry.entry_id]
    entities = [create_entity(options, device, i) for i, options in enumerate(entry.data[LIGHT_TYPE])]
    async_add_entities(entities, True)


class BleAdvLightBase(LightEntity, BleAdvEntity):
    """Base Light."""

    def __init__(self, light_type: str, min_br: float, device: BleAdvDevice, index: int) -> None:
        super().__init__(LIGHT_TYPE, device, index)
        self._light_type: str = light_type
        self._min_brighntess = int(min_br / 100.0)

    @handle_change
    async def async_turn_off(self, **kwargs) -> None:  # noqa: ANN003, ARG002
        """Turn off the fan."""
        self._attr_is_on = False

    def _pct(self, val: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
        return min(max_val, max(min_val, val))

    def _set_brightness(self, br: float) -> None:
        """Set Brightness taking into account the min."""
        self._attr_brightness = int(255.0 * self._pct(br, self._min_brighntess))

    def _get_brightness(self) -> float:
        """Get Brightness."""
        return self._attr_brightness / 255.0 if self._attr_brightness is not None else 0

    def get_change_rate(self, before_attrs: dict[str, Any], after_attrs: dict[str, Any]) -> float:
        """Compute change rate."""
        br_before = before_attrs.get("br", 0) if before_attrs.get("on") else 0
        br_after_on = before_attrs.get("br", 0)
        br_after = after_attrs.get("br", 0) if after_attrs.get("on") else 0
        _LOGGER.info(f"{br_before} / {br_after_on} / {br_after}")
        return max(abs(br_after - br_after_on), abs(br_after_on - br_before))

    def get_attrs(self) -> dict[str, Any]:
        """Get the attrs."""
        return {"on": self._attr_is_on, "type": self._light_type}


class BleAdvLightBinary(BleAdvLightBase):
    """Binary Light."""

    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_color_mode = ColorMode.ONOFF

    @handle_change
    async def async_turn_on(self, **kwargs) -> None:  # noqa: ANN003, ARG002
        """Turn device on."""
        self._attr_is_on = True


class BleAdvLightRGB(BleAdvLightBase):
    """RGB Light."""

    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB
    _restored_attributes = [(ATTR_BRIGHTNESS, 255), (ATTR_RGB_COLOR, (255, 255, 255))]

    @handle_change
    async def async_turn_on(self, **kwargs) -> None:  # noqa: ANN003
        """Turn device on."""
        if ATTR_BRIGHTNESS in kwargs:
            self._set_brightness(kwargs[ATTR_BRIGHTNESS])
        if ATTR_RGB_COLOR in kwargs:
            self._attr_rgb_color = kwargs[ATTR_RGB_COLOR]
        self._attr_is_on = True

    def _get_rgb(self) -> tuple[float, float, float]:
        """Get RGB tuple."""
        if self._attr_rgb_color is not None:
            return (self._attr_rgb_color[0] / 255.0, self._attr_rgb_color[1] / 255.0, self._attr_rgb_color[2] / 255.0)
        return (0, 0, 0)

    def _set_rgb(self, r: float, g: float, b: float) -> None:
        self._attr_rgb_color = (int(self._pct(r) * 255), int(self._pct(g) * 255), int(self._pct(b) * 255))

    def get_attrs(self) -> dict[str, Any]:
        """Get the attrs."""
        br = self._get_brightness()
        r, g, b = self._get_rgb()
        return {
            **super().get_attrs(),
            "br": br,
            "r": r,
            "g": g,
            "b": b,
            "rf": r * br,
            "gf": g * br,
            "bf": b * br,
        }

    def apply_attrs(self, ent_attr: BleAdvEntAttr) -> None:
        """Apply attributes to entity."""
        super().apply_attrs(ent_attr)
        if "br" in ent_attr.chg_attrs:
            self._set_brightness(ent_attr.get_attr_as_float("br"))
        elif "r" in ent_attr.chg_attrs or "g" in ent_attr.chg_attrs or "b" in ent_attr.chg_attrs:
            self._set_rgb(ent_attr.get_attr_as_float("r"), ent_attr.get_attr_as_float("g"), ent_attr.get_attr_as_float("b"))
        elif "rf" in ent_attr.chg_attrs or "gf" in ent_attr.chg_attrs or "bf" in ent_attr.chg_attrs:
            r = ent_attr.get_attr_as_float("rf")
            g = ent_attr.get_attr_as_float("gf")
            b = ent_attr.get_attr_as_float("bf")
            br = max(r, g, b)
            self._set_brightness(br)
            self._set_rgb(r / br, g / br, b / br)
        elif "cmd" in ent_attr.chg_attrs:
            if ent_attr.attrs.get("cmd") == "B+":
                self._set_brightness(self._get_brightness() + ent_attr.get_attr_as_float("step"))
            elif ent_attr.attrs.get("cmd") == "B-":
                self._set_brightness(self._get_brightness() - ent_attr.get_attr_as_float("step"))


class BleAdvLightCWW(BleAdvLightBase):
    """CWW Light."""

    _attr_min_color_temp_kelvin = DEFAULT_MIN_KELVIN
    _attr_max_color_temp_kelvin = DEFAULT_MAX_KELVIN
    _attr_supported_color_modes = {ColorMode.COLOR_TEMP}
    _attr_color_mode = ColorMode.COLOR_TEMP
    _restored_attributes = [(ATTR_BRIGHTNESS, 255), (ATTR_COLOR_TEMP_KELVIN, DEFAULT_MAX_KELVIN)]

    @handle_change
    async def async_turn_on(self, **kwargs) -> None:  # noqa: ANN003
        """Turn device on."""
        if ATTR_BRIGHTNESS in kwargs:
            self._set_brightness(kwargs[ATTR_BRIGHTNESS])
        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            self._attr_color_temp_kelvin = kwargs[ATTR_COLOR_TEMP_KELVIN]
        self._attr_is_on = True

    def _set_ct(self, ct_percent: float) -> None:
        self._attr_color_temp_kelvin = int(DEFAULT_MIN_KELVIN + (DEFAULT_MAX_KELVIN - DEFAULT_MIN_KELVIN) * self._pct(ct_percent))

    def _get_ct(self) -> float:
        kelvin = self._attr_color_temp_kelvin if self._attr_color_temp_kelvin is not None else DEFAULT_MIN_KELVIN
        return (kelvin - DEFAULT_MIN_KELVIN) / float(DEFAULT_MAX_KELVIN - DEFAULT_MIN_KELVIN)

    def get_attrs(self) -> dict[str, Any]:
        """Get the attrs."""
        br = self._get_brightness()
        ct = self._get_ct()
        return {
            **super().get_attrs(),
            "br": br,
            "ct": ct,
            "warm": br * (1.0 - ct),
            "cold": br * ct,
        }

    def apply_attrs(self, ent_attr: BleAdvEntAttr) -> None:
        """Apply attributes to entity."""
        super().apply_attrs(ent_attr)
        if "cold" in ent_attr.chg_attrs and "warm" in ent_attr.chg_attrs:
            cold = ent_attr.get_attr_as_float("cold")
            warm = ent_attr.get_attr_as_float("warm")
            self._set_brightness(max(cold, warm))
            self._set_ct(cold / (cold + warm))
        elif "cold" in ent_attr.chg_attrs and "br" in ent_attr.chg_attrs:
            self._set_brightness(ent_attr.get_attr_as_float("br"))
            self._set_ct(ent_attr.get_attr_as_float("cold"))
        elif "warm" in ent_attr.chg_attrs and "br" in ent_attr.chg_attrs:
            self._set_brightness(ent_attr.get_attr_as_float("br"))
            self._set_ct(1.0 - ent_attr.get_attr_as_float("cold"))
        elif "br" in ent_attr.chg_attrs:
            self._set_brightness(ent_attr.get_attr_as_float("br"))
        elif "ct" in ent_attr.chg_attrs:
            self._set_ct(ent_attr.get_attr_as_float("ct"))
        elif "cmd" in ent_attr.chg_attrs:
            if ent_attr.attrs.get("cmd") == "B+":
                self._set_brightness(self._get_brightness() + ent_attr.get_attr_as_float("step"))
            elif ent_attr.attrs.get("cmd") == "B-":
                self._set_brightness(self._get_brightness() - ent_attr.get_attr_as_float("step"))
            elif ent_attr.attrs.get("cmd") == "K+":
                self._set_ct(self._get_ct() + ent_attr.get_attr_as_float("step"))
            elif ent_attr.attrs.get("cmd") == "K-":
                self._set_ct(self._get_ct() - ent_attr.get_attr_as_float("step"))
