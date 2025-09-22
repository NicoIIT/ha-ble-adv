"""Provides the BleAdvDevice."""

from __future__ import annotations

import logging
from collections.abc import MutableMapping
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .codecs.const import (
    ATTR_CMD,
    ATTR_CMD_PAIR,
    ATTR_CMD_TIMER,
    ATTR_CMD_TOGGLE,
    ATTR_CMD_UNPAIR,
    ATTR_ON,
    ATTR_SUB_TYPE,
    ATTR_TIME,
    DEVICE_TYPE,
)
from .codecs.models import BleAdvConfig, BleAdvEntAttr
from .const import CONF_FORCED_OFF, CONF_FORCED_ON, DOMAIN
from .coordinator import BleAdvBaseDevice, BleAdvCoordinator

_LOGGER = logging.getLogger(__name__)

ATTR_IS_ON = "is_on"
ATTR_AVAILABLE = "available"


class _DeviceLoggingAdapter(logging.LoggerAdapter):
    def process(self, msg: str, kwargs: MutableMapping[str, Any]) -> tuple[str, MutableMapping[str, Any]]:
        return (f"[{self.extra['name']}] {msg}", kwargs) if self.extra is not None else (msg, kwargs)


class BleAdvStateAttribute:
    """State Attribute properties."""

    def __init__(self, name: str, default: bool | int | str | tuple | None, chg_attrs: list[str], resets: list[str] | None = None) -> None:
        self.name: str = name
        self.default: bool | int | str | tuple | None = default
        self.chg_attrs: list[str] = chg_attrs
        self.resets: list[str] = resets if resets is not None else []


class BleAdvEntity(RestoreEntity):
    """Base Ble Adv Entity class."""

    _state_attributes: frozenset[BleAdvStateAttribute] = frozenset()
    _attr_has_entity_name = True

    def __init__(self, base_type: str, sub_type: str, device: BleAdvDevice, index: int = 0) -> None:
        self._device: BleAdvDevice = device
        self._index: int = index
        self._base_type: str = base_type
        self._sub_type: str = sub_type
        self._attr_device_info: DeviceInfo = device.device_info
        self._attr_unique_id: str = f"{device.unique_id}_{base_type}_{index}"
        self._attr_translation_key: str = f"{base_type}_{index}"
        self._attr_available = self._device.available
        self._forced_attrs: dict[str, list[Any]] = {}
        self._device.add_entity(self)
        self.logger = _DeviceLoggingAdapter(_LOGGER, {"name": f"{device.name}/{base_type}_{index}"})

    def set_forced_cmds(self, cmds: list[str]) -> None:
        """Set the commands to be forced."""
        if CONF_FORCED_ON in cmds:
            self._forced_attrs.setdefault(ATTR_ON, []).append(True)
        if CONF_FORCED_OFF in cmds:
            self._forced_attrs.setdefault(ATTR_ON, []).append(False)

    @property
    def id(self) -> tuple[str, int]:
        """Entity ID."""
        return (self._base_type, self._index)

    # redefining 'is_on' as the one at ToggleEntity level, to override redefinitions by Base Entities
    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return self._attr_is_on

    def get_state_attribute(self, attr_name: str) -> Any:  # noqa: ANN401
        """Get a state attribute value."""
        return getattr(self, f"_attr_{attr_name}")

    def set_state_attribute(self, attr_name: str, attr_value: Any) -> bool:  # noqa: ANN401
        """Set a state attribute."""
        prev_value = self.get_state_attribute(attr_name)
        setattr(self, f"_attr_{attr_name}", attr_value)
        return attr_value != prev_value

    async def _handle_state_change(self, chg_map: dict[str, Any]) -> None:
        chg_attrs = []
        forced_chg_attrs = []
        for state_attr in self._state_attributes:
            if state_attr.name in chg_map:
                if self.set_state_attribute(state_attr.name, chg_map.get(state_attr.name)):
                    chg_attrs += state_attr.chg_attrs
                    for attr_reset in state_attr.resets:
                        self.set_state_attribute(attr_reset, None)
                forced_chg_attrs += state_attr.chg_attrs
        attrs = self.get_attrs()
        if any(attr_val in self._forced_attrs.get(attr_name, []) for (attr_name, attr_val) in attrs.items()):
            chg_attrs = forced_chg_attrs
        if chg_attrs:
            if ATTR_ON in chg_attrs and attrs[ATTR_ON]:
                chg_attrs += self.forced_changed_attr_on_start()
            await self._device.apply_change(BleAdvEntAttr(list(set(chg_attrs)), attrs, self._base_type, self._index))

    async def async_turn_off(self, **_) -> None:  # noqa: ANN003
        """Turn off the Entity."""
        await self._handle_state_change({ATTR_IS_ON: False})

    async def async_turn_on(self, *_, **kwargs) -> None:  # noqa: ANN002, ANN003
        """Turn on the Entity."""
        await self._handle_state_change({ATTR_IS_ON: True, **kwargs})

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes: saved attributes when the entity is Off."""
        if self._attr_is_on:
            return {ATTR_IS_ON: True}
        data: dict[str, Any] = {}
        for state_attr in self._state_attributes:
            data[f"last_{state_attr.name}"] = self.get_state_attribute(state_attr.name)
        return data

    def get_attrs(self) -> dict[str, Any]:
        """Get the attrs."""
        return {ATTR_ON: self._attr_is_on, ATTR_SUB_TYPE: self._sub_type}

    def change_bool(self, cur: bool | None, new: bool | str) -> bool:
        """Help function for bool attributes working with Toggle."""
        if isinstance(new, str) and new == ATTR_CMD_TOGGLE:
            return not cur if cur is not None else True
        return bool(new)

    def apply_attrs(self, ent_attr: BleAdvEntAttr) -> None:
        """Apply Attributes to the Entity."""
        if ATTR_ON in ent_attr.chg_attrs:
            self._attr_is_on = self.change_bool(self._attr_is_on, ent_attr.attrs.get(ATTR_ON, False))
        if ATTR_CMD in ent_attr.chg_attrs and ent_attr.attrs.get(ATTR_CMD) == ATTR_CMD_TOGGLE:
            self._attr_is_on = not self._attr_is_on

    def forced_changed_attr_on_start(self) -> list[str]:
        """List Forced changed attributes on start."""
        return []

    async def async_added_to_hass(self) -> None:
        """Restore state and state attributes."""
        await super().async_added_to_hass()

        if last_state := await self.async_get_last_state():
            self.logger.debug(f"Restoring state from last_state: {last_state.attributes}")
            for state_attr in self._state_attributes:
                val = last_state.attributes.get(f"last_{state_attr.name}", last_state.attributes.get(state_attr.name, state_attr.default))
                self.set_state_attribute(state_attr.name, val)
        else:
            self.logger.debug(f"Initialize state from default: { {x.name: x.default for x in self._state_attributes} }")
            for state_attr in self._state_attributes:
                self.set_state_attribute(state_attr.name, state_attr.default)


class BleAdvDevice(BleAdvBaseDevice):
    """Class to control the device."""

    def __init__(
        self,
        hass: HomeAssistant,
        unique_id: str,
        name: str,
        codec_id: str,
        adapter_ids: list[str],
        repeat: int,
        interval: int,
        duration: int,
        config: BleAdvConfig,
        coordinator: BleAdvCoordinator,
    ) -> None:
        super().__init__(coordinator, unique_id, codec_id, adapter_ids, int(repeat), int(interval), int(duration), config)
        self.hass: HomeAssistant = hass
        self.name: str = name
        self._entities: list[BleAdvEntity] = []
        self._timer_cancel: CALLBACK_TYPE | None = None
        self.logger = _DeviceLoggingAdapter(_LOGGER, {"name": self.name})

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            name=self.name,
            hw_version=", ".join(self.adapter_ids),
            model=self.codec_id,
            model_id=f"0x{self.config.id:X} / {self.config.index}",
        )

    def update_availability(self) -> None:
        """Update availability."""
        for ent in self._entities:
            if ent.set_state_attribute(ATTR_AVAILABLE, self.available):
                ent.async_write_ha_state()

    def add_entity(self, ent: BleAdvEntity) -> None:
        """Add entity to this device."""
        self._entities.append(ent)

    async def apply_change(self, ent_attr: BleAdvEntAttr) -> None:
        """Apply changes."""
        self.logger.info(f"Applying Changes: {ent_attr}")
        await self._async_cancel_timer()
        try:
            await self.advertise(ent_attr)
        except Exception:
            self.logger.exception("Exception applying changes")

    async def async_on_command(self, ent_attrs: list[BleAdvEntAttr]) -> None:
        """Process commands received."""
        self.logger.info(f"Receiving Changes: {ent_attrs}")
        await self._async_cancel_timer()
        for ent_attr in ent_attrs:
            if ent_attr.base_type == DEVICE_TYPE:
                await self._async_on_device_command(ent_attr)
            else:
                for ent in self._entities:
                    if ent.id == ent_attr.id and (
                        ent.is_on
                        or (ATTR_ON in ent_attr.chg_attrs and ent.change_bool(ent.is_on, ent_attr.attrs[ATTR_ON]))
                        or (ATTR_CMD in ent_attr.chg_attrs and ent_attr.attrs[ATTR_CMD] == ATTR_CMD_TOGGLE)
                    ):
                        ent.apply_attrs(ent_attr)
                        ent.async_write_ha_state()

    async def _async_on_device_command(self, ent_attr: BleAdvEntAttr) -> None:
        self.logger.debug(f"Device Command received: {ent_attr}")
        if ATTR_CMD in ent_attr.chg_attrs:
            cmd = ent_attr.attrs.get(ATTR_CMD)
            if cmd == ATTR_CMD_TIMER:
                expire = dt_util.utcnow() + timedelta(seconds=ent_attr.attrs[ATTR_TIME])  # type: ignore[none]
                self.logger.info(f"Set Timer to expire at: {expire}")
                self._timer_cancel = async_track_point_in_utc_time(self.hass, self._async_timeout, expire)
            elif cmd in (ATTR_CMD_PAIR, ATTR_CMD_UNPAIR):
                pass
            else:
                self.logger.warning(f"Unexpected command '{cmd}'.")
        else:
            await self._async_cmd_all(ent_attr)

    async def _async_cancel_timer(self) -> None:
        if self._timer_cancel:
            self._timer_cancel()
            self._timer_cancel = None
            self.logger.info("Existing Timer cancelled.")

    async def _async_timeout(self, _: datetime) -> None:
        self.logger.info("Timer expired: switch all entities OFF.")
        await self._async_cmd_all(BleAdvEntAttr([ATTR_ON], {ATTR_ON: False}, "", 0))

    async def _async_cmd_all(self, ent_attr: BleAdvEntAttr) -> None:
        for ent in self._entities:
            ent.apply_attrs(ent_attr)
            ent.async_write_ha_state()
