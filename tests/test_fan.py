"""Fan Entity tests."""

# ruff: noqa: S101
from unittest import mock

from ble_adv.codecs.const import ATTR_DIR, ATTR_ON, ATTR_OSC, ATTR_PRESET, ATTR_SPEED, ATTR_SPEED_COUNT, FAN_TYPE
from ble_adv.codecs.models import BleAdvEntAttr
from ble_adv.const import CONF_FANS, CONF_PRESETS, CONF_REFRESH_DIR_ON_START, CONF_REFRESH_OSC_ON_START, CONF_USE_DIR, CONF_USE_OSC
from ble_adv.fan import BleAdvFan, async_setup_entry, create_entity
from homeassistant.components.fan import DIRECTION_FORWARD, DIRECTION_REVERSE, FanEntityFeature
from homeassistant.const import CONF_TYPE
from homeassistant.core import HomeAssistant

from .conftest import _Device, create_base_entry

BASE_FAN_FEATURES = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF | FanEntityFeature.SET_SPEED


async def test_setup(hass: HomeAssistant) -> None:
    """Test async_setup_entry."""
    ent = await create_base_entry(hass, "ent_id", {CONF_FANS: [{CONF_TYPE: "3speed"}, {CONF_TYPE: "6speed"}]})
    add_ent_mock = mock.MagicMock()
    await async_setup_entry(hass, ent, add_ent_mock)
    add_ent_mock.assert_called_once()


async def test_fan_base(device: _Device) -> None:
    """Test fan base speed / on / off."""
    fan: BleAdvFan = create_entity({CONF_TYPE: "3speed"}, device, 0)
    assert fan.id == (FAN_TYPE, 0)
    assert fan.supported_features == BASE_FAN_FEATURES
    assert fan.preset_modes == []
    assert fan.forced_changed_attr_on_start() == []
    await fan.async_added_to_hass()
    assert fan.speed_count == 3
    assert fan.percentage == 100
    assert fan.get_attrs() == {ATTR_ON: False, ATTR_SPEED_COUNT: 3, ATTR_DIR: True, ATTR_OSC: False, ATTR_PRESET: None, ATTR_SPEED: 3}
    await fan.async_set_percentage(33)
    assert fan.percentage == 33
    assert fan.is_on
    assert fan.get_attrs() == {ATTR_ON: True, ATTR_SPEED_COUNT: 3, ATTR_DIR: True, ATTR_OSC: False, ATTR_PRESET: None, ATTR_SPEED: 1}
    device.assert_apply_change(fan, [ATTR_ON, ATTR_SPEED])
    await fan.async_turn_on()
    device.assert_no_change()
    await fan.async_set_percentage(0)
    assert fan.percentage == 33
    assert not fan.is_on
    assert fan.get_attrs() == {ATTR_ON: False, ATTR_SPEED_COUNT: 3, ATTR_DIR: True, ATTR_OSC: False, ATTR_PRESET: None, ATTR_SPEED: 1}
    device.assert_apply_change(fan, [ATTR_ON])
    await fan.async_turn_off()
    device.assert_no_change()
    await fan.async_turn_on()
    assert fan.percentage == 33
    assert fan.is_on
    assert fan.get_attrs() == {ATTR_ON: True, ATTR_SPEED_COUNT: 3, ATTR_DIR: True, ATTR_OSC: False, ATTR_PRESET: None, ATTR_SPEED: 1}
    device.assert_apply_change(fan, [ATTR_ON])
    await fan.async_turn_on(percentage=66)
    assert fan.percentage == 66
    assert fan.get_attrs() == {ATTR_ON: True, ATTR_SPEED_COUNT: 3, ATTR_DIR: True, ATTR_OSC: False, ATTR_PRESET: None, ATTR_SPEED: 2}
    device.assert_apply_change(fan, [ATTR_SPEED])
    await fan.async_turn_off()
    assert fan.percentage == 66
    assert fan.get_attrs() == {ATTR_ON: False, ATTR_SPEED_COUNT: 3, ATTR_DIR: True, ATTR_OSC: False, ATTR_PRESET: None, ATTR_SPEED: 2}
    device.assert_apply_change(fan, [ATTR_ON])
    fan.apply_attrs(BleAdvEntAttr([ATTR_ON], {ATTR_ON: False}, FAN_TYPE, 0))
    assert not fan.is_on
    fan.apply_attrs(BleAdvEntAttr([ATTR_ON], {ATTR_ON: True}, FAN_TYPE, 0))
    assert fan.is_on
    fan.apply_attrs(BleAdvEntAttr([ATTR_SPEED], {ATTR_ON: True, ATTR_SPEED_COUNT: 3, ATTR_SPEED: 3}, FAN_TYPE, 0))
    assert fan.percentage == 100
    fan.apply_attrs(BleAdvEntAttr([ATTR_SPEED], {ATTR_ON: True, ATTR_SPEED_COUNT: 6, ATTR_SPEED: 3}, FAN_TYPE, 0))
    assert fan.percentage == 50


async def test_fan_dir(device: _Device) -> None:
    """Test fan direction."""
    fan: BleAdvFan = create_entity({CONF_TYPE: "3speed", CONF_USE_DIR: True, CONF_REFRESH_DIR_ON_START: False}, device, 1)
    assert fan.id == (FAN_TYPE, 1)
    assert fan.supported_features == BASE_FAN_FEATURES | FanEntityFeature.DIRECTION
    assert fan.forced_changed_attr_on_start() == []
    await fan.async_added_to_hass()
    assert fan.current_direction == DIRECTION_FORWARD
    assert fan.get_attrs() == {ATTR_ON: False, ATTR_SPEED_COUNT: 3, ATTR_DIR: True, ATTR_OSC: False, ATTR_PRESET: None, ATTR_SPEED: 3}
    await fan.async_set_direction(DIRECTION_REVERSE)
    assert fan.current_direction == DIRECTION_REVERSE
    assert fan.is_on
    assert fan.get_attrs() == {ATTR_ON: True, ATTR_SPEED_COUNT: 3, ATTR_DIR: False, ATTR_OSC: False, ATTR_PRESET: None, ATTR_SPEED: 3}
    device.assert_apply_change(fan, [ATTR_ON, ATTR_DIR])
    await fan.async_set_direction(DIRECTION_REVERSE)
    device.assert_no_change()
    fan.apply_attrs(BleAdvEntAttr([ATTR_DIR], {ATTR_ON: True, ATTR_DIR: True}, FAN_TYPE, 1))
    assert fan.current_direction == DIRECTION_FORWARD
    fan.apply_attrs(BleAdvEntAttr([ATTR_DIR], {ATTR_ON: True, ATTR_DIR: False}, FAN_TYPE, 1))
    assert fan.current_direction == DIRECTION_REVERSE


async def test_fan_dir_on_switch_on(device: _Device) -> None:
    """Test fan direction setup to previous state on switch on."""
    fan: BleAdvFan = create_entity({CONF_TYPE: "3speed", CONF_USE_DIR: True, CONF_REFRESH_DIR_ON_START: True}, device, 1)
    assert fan.id == (FAN_TYPE, 1)
    assert fan.supported_features == BASE_FAN_FEATURES | FanEntityFeature.DIRECTION
    assert fan.forced_changed_attr_on_start() == [ATTR_DIR]
    await fan.async_added_to_hass()
    assert fan.current_direction == DIRECTION_FORWARD
    assert fan.get_attrs() == {ATTR_ON: False, ATTR_SPEED_COUNT: 3, ATTR_DIR: True, ATTR_OSC: False, ATTR_PRESET: None, ATTR_SPEED: 3}
    await fan.async_turn_on()
    assert fan.is_on
    assert fan.get_attrs() == {ATTR_ON: True, ATTR_SPEED_COUNT: 3, ATTR_DIR: True, ATTR_OSC: False, ATTR_PRESET: None, ATTR_SPEED: 3}
    device.assert_apply_change(fan, [ATTR_ON, ATTR_DIR])


async def test_fan_osc(device: _Device) -> None:
    """Test fan oscillating."""
    fan: BleAdvFan = create_entity({CONF_TYPE: "3speed", CONF_USE_OSC: True, CONF_REFRESH_OSC_ON_START: False}, device, 2)
    assert fan.id == (FAN_TYPE, 2)
    assert fan.supported_features == BASE_FAN_FEATURES | FanEntityFeature.OSCILLATE
    assert fan.forced_changed_attr_on_start() == []
    await fan.async_added_to_hass()
    assert not fan.oscillating
    assert fan.get_attrs() == {ATTR_ON: False, ATTR_SPEED_COUNT: 3, ATTR_DIR: True, ATTR_OSC: False, ATTR_PRESET: None, ATTR_SPEED: 3}
    await fan.async_oscillate(True)
    assert fan.oscillating
    assert fan.is_on
    assert fan.get_attrs() == {ATTR_ON: True, ATTR_SPEED_COUNT: 3, ATTR_DIR: True, ATTR_OSC: True, ATTR_PRESET: None, ATTR_SPEED: 3}
    device.assert_apply_change(fan, [ATTR_ON, ATTR_OSC])
    await fan.async_oscillate(True)
    device.assert_no_change()
    fan.apply_attrs(BleAdvEntAttr([ATTR_OSC], {ATTR_ON: True, ATTR_OSC: True}, FAN_TYPE, 1))
    assert fan.oscillating
    fan.apply_attrs(BleAdvEntAttr([ATTR_OSC], {ATTR_ON: True, ATTR_OSC: False}, FAN_TYPE, 1))
    assert not fan.oscillating


async def test_fan_osc_on_switch_on(device: _Device) -> None:
    """Test fan oscillating setup to previous state on switch on."""
    fan: BleAdvFan = create_entity({CONF_TYPE: "3speed", CONF_USE_OSC: True, CONF_REFRESH_OSC_ON_START: True}, device, 2)
    assert fan.id == (FAN_TYPE, 2)
    assert fan.supported_features == BASE_FAN_FEATURES | FanEntityFeature.OSCILLATE
    assert fan.forced_changed_attr_on_start() == [ATTR_OSC]
    await fan.async_added_to_hass()
    await fan.async_turn_on()
    assert fan.is_on
    assert fan.get_attrs() == {ATTR_ON: True, ATTR_SPEED_COUNT: 3, ATTR_DIR: True, ATTR_OSC: False, ATTR_PRESET: None, ATTR_SPEED: 3}
    device.assert_apply_change(fan, [ATTR_ON, ATTR_OSC])


async def test_fan_preset(device: _Device) -> None:
    """Test fan presets."""
    fan: BleAdvFan = create_entity({CONF_TYPE: "6speed", CONF_PRESETS: ["PRES1", "PRES2"]}, device, 3)
    assert fan.id == (FAN_TYPE, 3)
    assert fan.supported_features == BASE_FAN_FEATURES | FanEntityFeature.PRESET_MODE
    assert fan.preset_modes == ["PRES1", "PRES2"]
    assert fan.forced_changed_attr_on_start() == [ATTR_PRESET]
    await fan.async_added_to_hass()
    assert fan.speed_count == 6
    assert fan.percentage == 100
    assert fan.get_attrs() == {ATTR_ON: False, ATTR_SPEED_COUNT: 6, ATTR_DIR: True, ATTR_OSC: False, ATTR_PRESET: None, ATTR_SPEED: 6}
    await fan.async_set_preset_mode("PRES1")
    assert fan.preset_mode == "PRES1"
    assert fan.is_on
    assert fan.get_attrs() == {ATTR_ON: True, ATTR_SPEED_COUNT: 6, ATTR_DIR: True, ATTR_OSC: False, ATTR_PRESET: "PRES1", ATTR_SPEED: 0}
    device.assert_apply_change(fan, [ATTR_ON, ATTR_PRESET])
    await fan.async_set_preset_mode("PRES1")
    device.assert_no_change()
    await fan.async_turn_off()
    assert not fan.is_on
    assert fan.get_attrs() == {ATTR_ON: False, ATTR_SPEED_COUNT: 6, ATTR_DIR: True, ATTR_OSC: False, ATTR_PRESET: "PRES1", ATTR_SPEED: 0}
    device.assert_apply_change(fan, [ATTR_ON])
    await fan.async_turn_on()
    assert fan.is_on
    assert fan.get_attrs() == {ATTR_ON: True, ATTR_SPEED_COUNT: 6, ATTR_DIR: True, ATTR_OSC: False, ATTR_PRESET: "PRES1", ATTR_SPEED: 0}
    device.assert_apply_change(fan, [ATTR_ON, ATTR_PRESET])
    await fan.async_turn_on(percentage=50)
    assert fan.is_on
    assert fan.get_attrs() == {ATTR_ON: True, ATTR_SPEED_COUNT: 6, ATTR_DIR: True, ATTR_OSC: False, ATTR_PRESET: None, ATTR_SPEED: 3}
    device.assert_apply_change(fan, [ATTR_SPEED])
    await fan.async_turn_on(preset_mode="PRES2")
    assert fan.is_on
    assert fan.get_attrs() == {ATTR_ON: True, ATTR_SPEED_COUNT: 6, ATTR_DIR: True, ATTR_OSC: False, ATTR_PRESET: "PRES2", ATTR_SPEED: 0}
    device.assert_apply_change(fan, [ATTR_PRESET])
    fan.apply_attrs(BleAdvEntAttr([ATTR_PRESET], {ATTR_ON: True, ATTR_PRESET: "PRES1"}, FAN_TYPE, 3))
    assert fan.preset_mode == "PRES1"
    assert fan.percentage == 0
    fan.apply_attrs(BleAdvEntAttr([ATTR_SPEED], {ATTR_ON: True, ATTR_SPEED_COUNT: 6, ATTR_SPEED: 3}, FAN_TYPE, 0))
    assert fan.percentage == 50
    assert fan.preset_mode is None
