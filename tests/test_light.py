"""Light Entities tests."""

# ruff: noqa: S101
from unittest import mock

from ble_adv.codecs.const import (
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
    ATTR_EFFECT,
    ATTR_GREEN,
    ATTR_GREEN_F,
    ATTR_ON,
    ATTR_RED,
    ATTR_RED_F,
    ATTR_STEP,
    ATTR_SUB_TYPE,
    ATTR_WARM,
    LIGHT_TYPE,
    LIGHT_TYPE_CWW,
    LIGHT_TYPE_ONOFF,
    LIGHT_TYPE_RGB,
)
from ble_adv.codecs.models import BleAdvEntAttr
from ble_adv.const import CONF_EFFECTS, CONF_LIGHTS, CONF_REVERSED
from ble_adv.light import async_setup_entry, create_entity
from homeassistant.components.light.const import ColorMode, LightEntityFeature
from homeassistant.const import CONF_TYPE
from homeassistant.core import HomeAssistant

from .conftest import _Device, create_base_entry


def ctbr(ct: float, br: float, cold: float, warm: float) -> dict[str, float]:
    """CT and BR dict. CT == 0.0 => Full COLD."""
    return {ATTR_BR: br, ATTR_COLD: cold, ATTR_WARM: warm, ATTR_CT: ct, ATTR_CT_REV: 1.0 - ct}


def rgbr(r: float, g: float, b: float, br: float) -> dict[str, float]:
    """RGB and BR dict."""
    return {ATTR_BR: br, ATTR_RED: r, ATTR_GREEN: g, ATTR_BLUE: b, ATTR_RED_F: r * br, ATTR_GREEN_F: g * br, ATTR_BLUE_F: b * br}


async def test_setup(hass: HomeAssistant) -> None:
    """Test async_setup_entry."""
    ent = await create_base_entry(hass, "ent_id", {CONF_LIGHTS: [{CONF_TYPE: LIGHT_TYPE_CWW}, {CONF_TYPE: LIGHT_TYPE_ONOFF}]})
    add_ent_mock = mock.MagicMock()
    await async_setup_entry(hass, ent, add_ent_mock)
    add_ent_mock.assert_called_once()


async def test_light_binary(device: _Device) -> None:
    """Test binary light / on / off."""
    light = create_entity({CONF_TYPE: LIGHT_TYPE_ONOFF}, device, 0)
    await light.async_added_to_hass()
    assert light.id == (LIGHT_TYPE, 0)
    assert light.supported_color_modes == {ColorMode.ONOFF}
    assert light.forced_changed_attr_on_start() == []
    assert light.get_attrs() == {ATTR_ON: False, ATTR_SUB_TYPE: LIGHT_TYPE_ONOFF}
    await light.async_turn_on()
    assert light.is_on
    assert light.get_attrs() == {ATTR_ON: True, ATTR_SUB_TYPE: LIGHT_TYPE_ONOFF}
    device.assert_apply_change(light, [ATTR_ON])
    await light.async_turn_on()
    device.assert_no_change()
    light.apply_attrs(BleAdvEntAttr([ATTR_ON], {ATTR_ON: False}, LIGHT_TYPE, 0))
    assert not light.is_on
    light.apply_attrs(BleAdvEntAttr([ATTR_ON], {ATTR_ON: True}, LIGHT_TYPE, 0))
    assert light.is_on


async def test_light_cww(device: _Device) -> None:
    """Test Cold / Warm White light."""
    light = create_entity({CONF_TYPE: LIGHT_TYPE_CWW}, device, 0)
    await light.async_added_to_hass()
    assert light.id == (LIGHT_TYPE, 0)
    assert light.supported_color_modes == {ColorMode.COLOR_TEMP}
    assert light.forced_changed_attr_on_start() == []
    assert light.get_attrs() == {ATTR_ON: False, ATTR_SUB_TYPE: LIGHT_TYPE_CWW, **ctbr(0.0, 1.0, 1.0, 0.0)}
    await light.async_turn_on()
    assert light.is_on
    assert light.get_attrs() == {ATTR_ON: True, ATTR_SUB_TYPE: LIGHT_TYPE_CWW, **ctbr(0.0, 1.0, 1.0, 0.0)}
    device.assert_apply_change(light, [ATTR_ON])
    await light.async_turn_on()
    device.assert_no_change()
    light.apply_attrs(BleAdvEntAttr([ATTR_ON], {ATTR_ON: False}, LIGHT_TYPE, 0))
    assert not light.is_on
    light.apply_attrs(BleAdvEntAttr([ATTR_ON], {ATTR_ON: True}, LIGHT_TYPE, 0))
    assert light.is_on
    await light.async_turn_off()
    assert not light.is_on
    assert light.get_attrs() == {ATTR_ON: False, ATTR_SUB_TYPE: LIGHT_TYPE_CWW, **ctbr(0.0, 1.0, 1.0, 0.0)}
    device.assert_apply_change(light, [ATTR_ON])
    await light.async_turn_on(brightness=127)
    assert light.is_on
    assert light.get_attrs() == {ATTR_ON: True, ATTR_SUB_TYPE: LIGHT_TYPE_CWW, **ctbr(0.0, 127.0 / 255.0, 127.0 / 255.0, 0.0)}
    device.assert_apply_change(light, [ATTR_ON, ATTR_BR, ATTR_WARM, ATTR_COLD])
    await light.async_turn_on(brightness=255, color_temp_kelvin=2000)
    assert light.is_on
    assert light.get_attrs() == {ATTR_ON: True, ATTR_SUB_TYPE: LIGHT_TYPE_CWW, **ctbr(1.0, 1.0, 0.0, 1.0)}
    device.assert_apply_change(light, [ATTR_BR, ATTR_WARM, ATTR_COLD, ATTR_CT, ATTR_CT_REV])
    await light.async_turn_on(color_temp_kelvin=6535)
    assert light.is_on
    assert light.get_attrs() == {ATTR_ON: True, ATTR_SUB_TYPE: LIGHT_TYPE_CWW, **ctbr(0.0, 1.0, 1.0, 0.0)}
    device.assert_apply_change(light, [ATTR_WARM, ATTR_COLD, ATTR_CT, ATTR_CT_REV])
    light.apply_attrs(BleAdvEntAttr([ATTR_BR], {ATTR_BR: 0.5}, LIGHT_TYPE, 0))
    assert light.brightness == 127
    light.apply_attrs(BleAdvEntAttr([ATTR_CT], {ATTR_CT: 1.0}, LIGHT_TYPE, 0))
    assert light.color_temp_kelvin == 2000
    light.apply_attrs(BleAdvEntAttr([ATTR_CT_REV], {ATTR_CT_REV: 1.0}, LIGHT_TYPE, 0))
    assert light.color_temp_kelvin == 6535
    light.apply_attrs(BleAdvEntAttr([ATTR_CMD], {ATTR_CMD: ATTR_CMD_CT_UP, ATTR_STEP: 0.1}, LIGHT_TYPE, 0))
    assert light.color_temp_kelvin == 6081
    light.apply_attrs(BleAdvEntAttr([ATTR_CMD], {ATTR_CMD: ATTR_CMD_CT_DOWN, ATTR_STEP: 0.1}, LIGHT_TYPE, 0))
    assert light.color_temp_kelvin == 6534
    light.apply_attrs(BleAdvEntAttr([ATTR_WARM, ATTR_COLD], {ATTR_WARM: 1.0, ATTR_COLD: 0.0}, LIGHT_TYPE, 0))
    assert light.brightness == 255
    assert light.color_temp_kelvin == 2000


async def test_light_cww_reversed(device: _Device) -> None:
    """Test Cold / Warm White light, reversed."""
    light = create_entity({CONF_TYPE: LIGHT_TYPE_CWW, CONF_REVERSED: True}, device, 0)
    await light.async_added_to_hass()
    assert light.id == (LIGHT_TYPE, 0)
    assert light.supported_color_modes == {ColorMode.COLOR_TEMP}
    assert light.forced_changed_attr_on_start() == []
    assert light.get_attrs() == {ATTR_ON: False, ATTR_SUB_TYPE: LIGHT_TYPE_CWW, **ctbr(1.0, 1.0, 0.0, 1.0)}
    await light.async_turn_on()
    assert light.is_on
    assert light.get_attrs() == {ATTR_ON: True, ATTR_SUB_TYPE: LIGHT_TYPE_CWW, **ctbr(1.0, 1.0, 0.0, 1.0)}
    device.assert_apply_change(light, [ATTR_ON])
    await light.async_turn_on()
    device.assert_no_change()
    light.apply_attrs(BleAdvEntAttr([ATTR_ON], {ATTR_ON: False}, LIGHT_TYPE, 0))
    assert not light.is_on
    light.apply_attrs(BleAdvEntAttr([ATTR_ON], {ATTR_ON: True}, LIGHT_TYPE, 0))
    assert light.is_on
    await light.async_turn_off()
    assert not light.is_on
    assert light.get_attrs() == {ATTR_ON: False, ATTR_SUB_TYPE: LIGHT_TYPE_CWW, **ctbr(1.0, 1.0, 0.0, 1.0)}
    device.assert_apply_change(light, [ATTR_ON])
    await light.async_turn_on(brightness=123)
    assert light.is_on
    assert light.get_attrs() == {ATTR_ON: True, ATTR_SUB_TYPE: LIGHT_TYPE_CWW, **ctbr(1.0, 123.0 / 255.0, 0.0, 123.0 / 255.0)}
    device.assert_apply_change(light, [ATTR_ON, ATTR_BR, ATTR_WARM, ATTR_COLD])
    await light.async_turn_on(brightness=255, color_temp_kelvin=2000)
    assert light.is_on
    assert light.get_attrs() == {ATTR_ON: True, ATTR_SUB_TYPE: LIGHT_TYPE_CWW, **ctbr(0.0, 1.0, 1.0, 0.0)}
    device.assert_apply_change(light, [ATTR_BR, ATTR_WARM, ATTR_COLD, ATTR_CT, ATTR_CT_REV])
    await light.async_turn_on(color_temp_kelvin=6535)
    assert light.is_on
    assert light.get_attrs() == {ATTR_ON: True, ATTR_SUB_TYPE: LIGHT_TYPE_CWW, **ctbr(1.0, 1.0, 0.0, 1.0)}
    device.assert_apply_change(light, [ATTR_WARM, ATTR_COLD, ATTR_CT, ATTR_CT_REV])


async def test_light_rgb(device: _Device) -> None:
    """Test RGB light."""
    light = create_entity({CONF_TYPE: LIGHT_TYPE_RGB, CONF_EFFECTS: ["RGB", "RGBK"]}, device, 0)
    await light.async_added_to_hass()
    assert light.id == (LIGHT_TYPE, 0)
    assert light.supported_color_modes == {ColorMode.RGB}
    assert light.forced_changed_attr_on_start() == [ATTR_EFFECT]
    assert light.supported_features == LightEntityFeature.EFFECT
    assert light.get_attrs() == {ATTR_ON: False, ATTR_SUB_TYPE: LIGHT_TYPE_RGB, **rgbr(1.0, 1.0, 1.0, 1.0), ATTR_EFFECT: None}
    await light.async_turn_on()
    assert light.is_on
    assert light.get_attrs() == {ATTR_ON: True, ATTR_SUB_TYPE: LIGHT_TYPE_RGB, **rgbr(1.0, 1.0, 1.0, 1.0), ATTR_EFFECT: None}
    device.assert_apply_change(light, [ATTR_ON, ATTR_EFFECT])
    await light.async_turn_on()
    device.assert_no_change()
    light.apply_attrs(BleAdvEntAttr([ATTR_ON], {ATTR_ON: False}, LIGHT_TYPE, 0))
    assert not light.is_on
    light.apply_attrs(BleAdvEntAttr([ATTR_ON], {ATTR_ON: True}, LIGHT_TYPE, 0))
    assert light.is_on
    await light.async_turn_on(effect="RGB")
    assert light.get_attrs() == {ATTR_ON: True, ATTR_SUB_TYPE: LIGHT_TYPE_RGB, **rgbr(1.0, 1.0, 1.0, 1.0), ATTR_EFFECT: "RGB"}
    device.assert_apply_change(light, [ATTR_EFFECT])
    await light.async_turn_off()
    assert light.get_attrs() == {ATTR_ON: False, ATTR_SUB_TYPE: LIGHT_TYPE_RGB, **rgbr(1.0, 1.0, 1.0, 1.0), ATTR_EFFECT: "RGB"}
    device.assert_apply_change(light, [ATTR_ON])
    await light.async_turn_on()
    assert light.get_attrs() == {ATTR_ON: True, ATTR_SUB_TYPE: LIGHT_TYPE_RGB, **rgbr(1.0, 1.0, 1.0, 1.0), ATTR_EFFECT: "RGB"}
    device.assert_apply_change(light, [ATTR_ON, ATTR_EFFECT])
    mid_f = 127.0 / 255.0
    await light.async_turn_on(rgb_color=(127, 255, 255))
    assert light.get_attrs() == {ATTR_ON: True, ATTR_SUB_TYPE: LIGHT_TYPE_RGB, **rgbr(mid_f, 1.0, 1.0, 1.0), ATTR_EFFECT: None}
    device.assert_apply_change(light, [ATTR_RED, ATTR_RED_F, ATTR_GREEN, ATTR_GREEN_F, ATTR_BLUE, ATTR_BLUE_F])
    light.apply_attrs(BleAdvEntAttr([ATTR_RED, ATTR_GREEN, ATTR_BLUE], {ATTR_RED: 1.0, ATTR_GREEN: 1.0, ATTR_BLUE: 1.0}, LIGHT_TYPE, 0))
    assert light.get_attrs() == {ATTR_ON: True, ATTR_SUB_TYPE: LIGHT_TYPE_RGB, **rgbr(1.0, 1.0, 1.0, 1.0), ATTR_EFFECT: None}
    light.apply_attrs(BleAdvEntAttr([ATTR_RED_F, ATTR_GREEN_F, ATTR_BLUE_F], {ATTR_RED_F: 0.5, ATTR_GREEN_F: 0.5, ATTR_BLUE_F: 0.5}, LIGHT_TYPE, 0))
    assert light.get_attrs() == {ATTR_ON: True, ATTR_SUB_TYPE: LIGHT_TYPE_RGB, **rgbr(1.0, 1.0, 1.0, mid_f), ATTR_EFFECT: None}
    light.apply_attrs(BleAdvEntAttr([ATTR_RED, ATTR_GREEN, ATTR_BLUE], {ATTR_RED: 0.5, ATTR_GREEN: 0.5, ATTR_BLUE: 0.5}, LIGHT_TYPE, 0))
    assert light.get_attrs() == {ATTR_ON: True, ATTR_SUB_TYPE: LIGHT_TYPE_RGB, **rgbr(mid_f, mid_f, mid_f, mid_f), ATTR_EFFECT: None}
    light.apply_attrs(BleAdvEntAttr([ATTR_EFFECT], {ATTR_EFFECT: "RGBK"}, LIGHT_TYPE, 0))
    assert light.get_attrs() == {ATTR_ON: True, ATTR_SUB_TYPE: LIGHT_TYPE_RGB, **rgbr(mid_f, mid_f, mid_f, mid_f), ATTR_EFFECT: "RGBK"}
    light.apply_attrs(BleAdvEntAttr([ATTR_CMD], {ATTR_CMD: ATTR_CMD_BR_DOWN, ATTR_STEP: 0.1}, LIGHT_TYPE, 0))
    assert light.get_attrs() == {ATTR_ON: True, ATTR_SUB_TYPE: LIGHT_TYPE_RGB, **rgbr(mid_f, mid_f, mid_f, 101.0 / 255.0), ATTR_EFFECT: None}
    light.apply_attrs(BleAdvEntAttr([ATTR_CMD], {ATTR_CMD: ATTR_CMD_BR_UP, ATTR_STEP: 0.1}, LIGHT_TYPE, 0))
    assert light.get_attrs() == {ATTR_ON: True, ATTR_SUB_TYPE: LIGHT_TYPE_RGB, **rgbr(mid_f, mid_f, mid_f, 126.0 / 255.0), ATTR_EFFECT: None}
    light.apply_attrs(BleAdvEntAttr([ATTR_BR], {ATTR_BR: 1.0}, LIGHT_TYPE, 0))
    assert light.get_attrs() == {ATTR_ON: True, ATTR_SUB_TYPE: LIGHT_TYPE_RGB, **rgbr(mid_f, mid_f, mid_f, 1.0), ATTR_EFFECT: None}
