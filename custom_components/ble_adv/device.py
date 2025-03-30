"""Provides the BleAdvDevice."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from functools import wraps
from typing import Any

from homeassistant.const import STATE_ON
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .adapters import BleAdvQueueItem
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
from .codecs.models import (
    AttrType,
    BleAdvAdvertisement,
    BleAdvCodec,
    BleAdvConfig,
    BleAdvEntAttr,
)
from .const import DOMAIN
from .coordinator import BleAdvCoordinator, MatchingCallback

_LOGGER = logging.getLogger(__name__)


def handle_change(method):  # noqa: ANN001, ANN201
    """Decorate entity methods applying changes.

    The state attributes are saved before the change
    and given to method 'async_after_change' that compares them to current
    and calls the relevant device method to process the change
    """

    @wraps(method)
    async def _impl(self: BleAdvEntity, *method_args, **method_kwargs):  # noqa: ANN002, ANN003, ANN202
        before_attrs = self.get_attrs()
        method_output = await method(self, *method_args, **method_kwargs)
        await self.async_after_change(before_attrs)
        return method_output

    return _impl


class BleAdvEntity(RestoreEntity):
    """Base Ble Adv Entity class."""

    _state_attributes: frozenset[tuple[str, Any]] = frozenset()
    _attr_has_entity_name = True

    def __init__(self, base_type: str, sub_type: str, device: BleAdvDevice, index: int = 0) -> None:
        self._device: BleAdvDevice = device
        self._index: int = index
        self._base_type: str = base_type
        self._sub_type: str = sub_type
        self._attr_device_info: DeviceInfo = device.device_info
        self._attr_unique_id: str = f"{device.unique_id}_{base_type}_{index}"
        self._attr_translation_key: str = f"{base_type}_{index}"
        self._device.add_entity(self)

    @property
    def available(self) -> bool:
        """Return True if the device is available."""
        return self._device.available

    @property
    def id(self) -> tuple[str, int]:
        """Entity ID."""
        return (self._base_type, self._index)

    # redefining 'is_on' as the one at ToggleEntity level, to override redefinitions by Base Entities
    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return self._attr_is_on

    def set_state_attribute(self, attr_name: str, attr_value: Any) -> None:  # noqa: ANN401
        """Set a state attribute, potentially using overriden '_set_state_<attr_name>' function."""
        set_fct_name = f"_set_state_{attr_name}"
        if hasattr(self, set_fct_name):
            getattr(self, set_fct_name)(attr_value)
        else:
            setattr(self, f"_attr_{attr_name}", attr_value)

    @handle_change
    async def async_turn_off(self, **_) -> None:  # noqa: ANN003
        """Turn off the Entity."""
        self._attr_is_on = False

    @handle_change
    async def async_turn_on(self, *_, **kwargs) -> None:  # noqa: ANN002, ANN003
        """Turn Entity on."""
        for attr_name, _ in self._state_attributes:
            if (val := kwargs.get(attr_name)) is not None:
                self.set_state_attribute(attr_name, val)
        self._attr_is_on = True

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes: saved attributes when the light is Off."""
        data: dict[str, Any] = {}
        if self._attr_is_on:
            return data
        for attribute, _ in self._state_attributes:
            data[f"last_{attribute}"] = getattr(self, f"_attr_{attribute}")
        return data

    def get_attrs(self) -> dict[str, Any]:
        """Get the attrs."""
        return {ATTR_ON: self._attr_is_on, ATTR_SUB_TYPE: self._sub_type}

    def apply_attrs(self, ent_attr: BleAdvEntAttr) -> None:
        """Apply Attributes to the Entity."""
        if ATTR_ON in ent_attr.chg_attrs:
            self._attr_is_on = ent_attr.attrs.get(ATTR_ON)
        if ATTR_CMD in ent_attr.chg_attrs and ent_attr.attrs.get(ATTR_CMD) == ATTR_CMD_TOGGLE:
            self._attr_is_on = not self._attr_is_on

    def forced_changed_attr_on_start(self) -> list[str]:
        """List Forced changed attributes on start."""
        return []

    async def async_after_change(self, before_attrs: dict[str, AttrType]) -> None:
        """Process to be done after change is detected on Entity."""
        attrs = self.get_attrs()
        changed_attrs = [x for x, y in attrs.items() if y != before_attrs.get(x)]
        if ATTR_ON in changed_attrs and attrs[ATTR_ON]:
            changed_attrs += self.forced_changed_attr_on_start()
        if changed_attrs:
            await self._device.apply_change(BleAdvEntAttr(changed_attrs, attrs, self._base_type, self._index))

    async def async_added_to_hass(self) -> None:
        """Restore state and state attributes."""
        await super().async_added_to_hass()

        if last_state := await self.async_get_last_state():
            is_on: bool = last_state.state == STATE_ON
            for attr_name, default_value in self._state_attributes:
                val = last_state.attributes.get(attr_name if is_on else f"last_{attr_name}")
                self.set_state_attribute(attr_name, val if val is not None else default_value)
            self._attr_is_on = is_on
        else:
            for attr_name, default_value in self._state_attributes:
                self.set_state_attribute(attr_name, default_value)
            self._attr_is_on = False


class MatchingDeviceCallback(MatchingCallback):
    """Callback checking if callback is matching the device."""

    def __init__(self, device: BleAdvMatchingDevice) -> None:
        self.device: BleAdvMatchingDevice = device

    async def handle(self, codec_id: str, adapter_id: str, config: BleAdvConfig, ent_attrs: list[BleAdvEntAttr]) -> bool:
        """Handle the callback."""
        if (
            (codec_id != self.device.codec_id)
            or (adapter_id != self.device.adapter_id)
            or (config.id != self.device.config.id)
            or (config.index != self.device.config.index)
        ):
            return False
        await self.device.async_on_command(ent_attrs)
        return True

    def __repr__(self) -> str:
        return f"adapter_id: {self.device.adapter_id}, codec_id: {self.device.codec_id}, config: {self.device.config}"


class BleAdvMatchingDevice(ABC):
    """Base Matching Device."""

    def __init__(
        self,
        reg_name: str,
        coordinator: BleAdvCoordinator,
        codec_id: str,
        adapter_id: str,
        config: BleAdvConfig,
    ) -> None:
        self.coordinator: BleAdvCoordinator = coordinator
        self.codec_id: str = codec_id
        self.adapter_id: str = adapter_id
        self.config: BleAdvConfig = config
        self.reg_name: str = reg_name

    @property
    def available(self) -> bool:
        """Return True if the device is available: if the adapter is available."""
        return self.adapter_id in self.coordinator.get_adapter_ids()

    async def register(self) -> None:
        """Register to coordinator."""
        await self.coordinator.register_callback(self.reg_name, MatchingDeviceCallback(self))

    async def unregister(self) -> None:
        """Unregister."""
        await self.coordinator.unregister_callback(self.reg_name)

    @abstractmethod
    async def async_on_command(self, ent_attrs: list[BleAdvEntAttr]) -> None:
        """Call on matching command received."""


class BleAdvRemote(BleAdvMatchingDevice):
    """Class representing a remote."""

    def __init__(self, name: str, codec_id: str, adapter_id: str, config: BleAdvConfig, coordinator: BleAdvCoordinator) -> None:
        super().__init__(name, coordinator, codec_id, adapter_id, config)
        self.device: BleAdvDevice | None = None

    async def async_on_command(self, ent_attrs: list[BleAdvEntAttr]) -> None:
        """Call on matching command received."""
        if self.device is not None:
            await self.device.async_on_command(ent_attrs)


class BleAdvDevice(BleAdvMatchingDevice):
    """Class to control the device."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        unique_id: str,
        name: str,
        codec_id: str,
        adapter_id: str,
        repeat: int,
        interval: int,
        duration: int,
        config: BleAdvConfig,
        coordinator: BleAdvCoordinator,
    ) -> None:
        super().__init__(unique_id, coordinator, codec_id, adapter_id, config)
        self.hass: HomeAssistant = hass
        self.logger: logging.Logger = logger
        self.unique_id: str = unique_id
        self.name: str = name
        self.repeat: int = int(repeat)
        self.interval: int = int(interval)
        self.duration: int = int(duration)
        self.entities: dict[Any, BleAdvEntity] = {}
        self._timer_cancel: CALLBACK_TYPE | None = None
        self.remotes: list[BleAdvRemote] = []

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            name=self.name,
            hw_version=self.adapter_id,
            model=self.codec_id,
            model_id=f"0x{self.config.id:X} / {self.config.index}",
        )

    def add_entity(self, ent: BleAdvEntity) -> None:
        """Add entity to this device."""
        self.entities[ent.id] = ent

    def link_remote(self, remote: BleAdvRemote) -> None:
        """Link a remote to this device."""
        remote.device = self
        self.remotes.append(remote)

    async def async_start(self) -> None:
        """Start the Device: register to coordinator."""
        await self.register()
        for remote in self.remotes:
            await remote.register()

    async def async_stop(self) -> None:
        """Stop the device: unregister."""
        for remote in self.remotes:
            await remote.register()
        await self.unregister()

    async def apply_change(self, ent_attr: BleAdvEntAttr) -> None:
        """Apply changes."""
        self.logger.info(f"Tx: {self.config.tx_count}, Changes {ent_attr}")
        await self._async_cancel_timer()
        try:
            acodec: BleAdvCodec = self.coordinator.codecs[self.codec_id]
            enc_cmds = acodec.ent_to_enc(ent_attr)
            for enc_cmd in enc_cmds:
                self.logger.info(f"Cmd: {enc_cmd}")
                self.config.tx_count = (self.config.tx_count + 1) % 125
                adv: BleAdvAdvertisement = acodec.encode_adv(enc_cmd, self.config)
                qi: BleAdvQueueItem = BleAdvQueueItem(enc_cmd.cmd, self.repeat, self.duration, self.interval, adv.to_raw())
                await self.coordinator.advertise(self.adapter_id, self.unique_id, qi)
        except Exception:
            _LOGGER.exception("Exception applying changes")

    async def async_on_command(self, ent_attrs: list[BleAdvEntAttr]) -> None:
        """Process commands received."""
        for ent_attr in ent_attrs:
            if ent_attr.base_type == DEVICE_TYPE:
                await self._async_on_device_command(ent_attr)
            else:
                ent = self.entities.get(ent_attr.id)
                if ent is not None and (ent.is_on or (ATTR_ON in ent_attr.chg_attrs and ent_attr.attrs[ATTR_ON])):
                    ent.apply_attrs(ent_attr)
                    ent.async_write_ha_state()

    async def _async_on_device_command(self, ent_attr: BleAdvEntAttr) -> None:
        self.logger.info(f"Device Command received: {ent_attr}")
        if ATTR_CMD in ent_attr.chg_attrs:
            cmd = ent_attr.attrs.get(ATTR_CMD)
            if cmd == ATTR_CMD_TIMER:
                expire = dt_util.utcnow() + timedelta(seconds=ent_attr.attrs[ATTR_TIME])  # type: ignore[none]
                self.logger.info(f"Set Timer to expire at: {expire}")
                await self._async_cancel_timer()
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
            self.logger.info("Timer cancelled.")

    async def _async_timeout(self, _: datetime) -> None:
        self.logger.info("Timer expired: switch all entities OFF.")
        await self._async_cmd_all(BleAdvEntAttr([ATTR_ON], {ATTR_ON: False}, "", 0))

    async def _async_cmd_all(self, ent_attr: BleAdvEntAttr) -> None:
        for ent in self.entities.values():
            ent.apply_attrs(ent_attr)
            ent.async_write_ha_state()
