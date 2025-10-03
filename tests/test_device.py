"""Device and Base Entity tests."""

# ruff: noqa: S101
import asyncio
from typing import Any
from unittest import mock

from ble_adv.adapters import BleAdvQueueItem
from ble_adv.codecs.const import ATTR_CMD, ATTR_CMD_PAIR, ATTR_CMD_TIMER, ATTR_CMD_TOGGLE, ATTR_ON, ATTR_SUB_TYPE, ATTR_TIME, DEVICE_TYPE
from ble_adv.codecs.models import BleAdvAdvertisement, BleAdvConfig, BleAdvEncCmd, BleAdvEntAttr
from ble_adv.const import CONF_FORCED_OFF, CONF_FORCED_ON
from ble_adv.coordinator import BleAdvCoordinator
from ble_adv.device import ATTR_AVAILABLE, ATTR_IS_ON, BleAdvDevice, BleAdvEntity, BleAdvStateAttribute
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant, State

from .conftest import _Device

ATTR_STA = "sta"
ATTR_STB = "stb"


class _Entity(BleAdvEntity):
    _attr_is_on: bool = False
    _attr_available: bool = False
    _attr_sta: str = "INIT"
    _attr_stb: str = "INITB"
    _state_attributes = frozenset(
        [
            BleAdvStateAttribute(ATTR_IS_ON, False, [ATTR_ON]),
            BleAdvStateAttribute(ATTR_STA, "REST", [ATTR_CMD]),
            BleAdvStateAttribute(ATTR_STB, "RESTB", [ATTR_CMD]),
        ]
    )
    async_write_ha_state = mock.MagicMock()

    @property
    def sta(self) -> str:
        return self._attr_sta

    @property
    def stb(self) -> str:
        return self._attr_stb

    def get_attrs(self) -> dict[str, Any]:
        return {**super().get_attrs(), ATTR_CMD: f"{self._attr_sta}_{self._attr_stb}"}


async def test_device(hass: HomeAssistant) -> None:
    """Test device."""
    codec = mock.AsyncMock()
    codec.codec_id = "my_codec/sub"
    codec.match_id = "my_codec"
    codec.ent_to_enc = mock.MagicMock(return_value=[BleAdvEncCmd(0x10)])
    adv = BleAdvAdvertisement(0xFF, b"12345")
    codec.encode_advs = mock.MagicMock(return_value=[adv])
    coord = BleAdvCoordinator(hass, {codec.codec_id: codec}, ["hci"], 2000, [], [])
    coord.advertise = mock.AsyncMock()
    conf = BleAdvConfig(0xABCDEF, 1)
    device = BleAdvDevice(hass, "my_device", "device", codec.codec_id, ["my_adapter"], 1, 20, 100, conf, coord)
    assert device.device_info == {
        "identifiers": {("ble_adv", "my_device")},
        "name": "device",
        "hw_version": "my_adapter",
        "model": codec.codec_id,
        "model_id": "0xABCDEF / 1",
    }
    device.add_listener(codec.codec_id, conf)
    coord.add_device(device)
    ent0 = _Entity("ent_type", "ent_sub_type", device, 0)
    ent1 = _Entity("ent_type", "ent_sub_type", device, 1)
    assert not device.available
    ent0.set_state_attribute(ATTR_AVAILABLE, True)
    assert ent0.available
    device.update_availability()
    ent0.async_write_ha_state.assert_called_once()  # pyright: ignore[reportAttributeAccessIssue]
    ent0.async_write_ha_state.reset_mock()  # pyright: ignore[reportAttributeAccessIssue]
    assert not ent0.available
    on_cmd = BleAdvEntAttr([ATTR_ON], {ATTR_ON: True}, "ent_type", 0)
    await device.apply_change(on_cmd)
    coord.advertise.assert_called_once_with("my_adapter", "my_device", BleAdvQueueItem(0x10, 1, 100, 20, [adv.to_raw()], 2))
    assert not ent0.is_on
    await device.async_on_command([on_cmd])
    assert ent0.is_on
    ent0.async_write_ha_state.assert_called_once()  # pyright: ignore[reportAttributeAccessIssue]
    ent0.async_write_ha_state.reset_mock()  # pyright: ignore[reportAttributeAccessIssue]
    toggle_cmd = BleAdvEntAttr([ATTR_CMD], {ATTR_CMD: ATTR_CMD_TOGGLE}, "ent_type", 0)
    await device.async_on_command([toggle_cmd])
    assert not ent0.is_on
    ent0.async_write_ha_state.assert_called_once()  # pyright: ignore[reportAttributeAccessIssue]
    ent0.async_write_ha_state.reset_mock()  # pyright: ignore[reportAttributeAccessIssue]
    await device.async_on_command([toggle_cmd])
    assert ent0.is_on
    ent0.async_write_ha_state.assert_called_once()  # pyright: ignore[reportAttributeAccessIssue]
    ent0.async_write_ha_state.reset_mock()  # pyright: ignore[reportAttributeAccessIssue]
    timer_cmd = BleAdvEntAttr([ATTR_CMD], {ATTR_CMD: ATTR_CMD_TIMER, ATTR_TIME: 0.1}, DEVICE_TYPE, 0)
    await device.async_on_command([timer_cmd])
    await device.async_on_command([BleAdvEntAttr([ATTR_CMD_PAIR], {}, DEVICE_TYPE, 0)])
    await asyncio.sleep(0.1)
    assert ent0.is_on
    await device.async_on_command([timer_cmd])
    await asyncio.sleep(0.1)
    assert not ent0.is_on
    assert not ent1.is_on
    all_on_cmd = BleAdvEntAttr([ATTR_ON], {ATTR_ON: True}, DEVICE_TYPE, 0)
    assert not device.match("not_my_codec", "my_adapter", conf)
    assert not ent0.is_on
    assert not ent1.is_on
    assert not device.match("my_codec", "not_my_adapter", conf)
    assert device.match("my_codec", "my_adapter", conf)
    await device.async_on_command([all_on_cmd])
    assert ent0.is_on
    assert ent1.is_on
    all_off_cmd = BleAdvEntAttr([ATTR_ON], {ATTR_ON: False}, DEVICE_TYPE, 0)
    await device.async_on_command([all_off_cmd])
    assert not ent0.is_on
    assert not ent1.is_on


async def test_entity(device: _Device) -> None:
    """Test entity."""
    ent = _Entity("ent_type", "ent_sub_type", device, 0)
    device.add_entity.assert_called_once_with(ent)
    assert ent.available
    assert not ent.is_on
    assert ent.id == ("ent_type", 0)
    assert ent.sta == "INIT"
    await ent.async_added_to_hass()
    assert ent.sta == "REST"
    ent.set_state_attribute(ATTR_STA, "VALA")
    assert ent.sta == "VALA"
    ent.set_state_attribute(ATTR_STB, "VALB")
    assert ent.stb == "VALB"
    assert ent.extra_state_attributes == {"last_is_on": False, "last_sta": "VALA", "last_stb": "VALB"}
    last_state = State("ble_adv.my_ent", STATE_ON, {ATTR_IS_ON: True, ATTR_STA: "SAVA", ATTR_STB: "SAVB"})
    ent.async_get_last_state = mock.AsyncMock(return_value=last_state)
    await ent.async_added_to_hass()
    assert ent.sta == "SAVA"
    assert ent.forced_changed_attr_on_start() == []
    await ent.async_turn_off()
    assert ent.get_attrs() == {ATTR_ON: False, ATTR_SUB_TYPE: "ent_sub_type", ATTR_CMD: "SAVA_SAVB"}
    device.assert_apply_change(ent, [ATTR_ON])
    await ent.async_turn_on()
    assert ent.get_attrs() == {ATTR_ON: True, ATTR_SUB_TYPE: "ent_sub_type", ATTR_CMD: "SAVA_SAVB"}
    device.assert_apply_change(ent, [ATTR_ON])
    await ent.async_turn_on(sta="VALAAA")
    assert ent.get_attrs() == {ATTR_ON: True, ATTR_SUB_TYPE: "ent_sub_type", ATTR_CMD: "VALAAA_SAVB"}
    device.assert_apply_change(ent, [ATTR_CMD])
    ent.set_forced_cmds([CONF_FORCED_ON])
    await ent.async_turn_on()
    device.assert_apply_change(ent, [ATTR_ON])
    await ent.async_turn_off()
    device.assert_apply_change(ent, [ATTR_ON])
    await ent.async_turn_off()
    device.assert_no_change()
    ent.set_forced_cmds([CONF_FORCED_OFF])
    await ent.async_turn_off()
    device.assert_apply_change(ent, [ATTR_ON])
