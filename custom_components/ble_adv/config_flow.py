"""Config Flow for BLE ADV."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from random import randint
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import section
from homeassistant.helpers import selector

from . import get_coordinator
from .codecs import PHONE_APPS
from .codecs.models import FAN_TYPE, LIGHT_TYPE, BleAdvConfig, BleAdvEntAttr
from .const import CONF_ADAPTER_ID, CONF_CODEC_ID, CONF_FORCED_ID, CONF_INDEX, CONF_PHONE_APP, DOMAIN
from .coordinator import BleAdvCoordinator, MatchingCallback
from .device import BleAdvDevice

_LOGGER = logging.getLogger(__name__)

type CodecFoundCallback = Callable[[str, str, BleAdvConfig], Awaitable[None]]


class _MatchingAllCallback(MatchingCallback):
    def __init__(self, callback: CodecFoundCallback) -> None:
        self.callback: CodecFoundCallback = callback

    def __repr__(self) -> str:
        return "Matching ALL"

    async def handle(self, codec_id: str, adapter_id: str, config: BleAdvConfig, ent_attrs: list[BleAdvEntAttr]) -> bool:  # noqa: ARG002
        await self.callback(codec_id, adapter_id, config)
        return True


class _CodecConfig(BleAdvConfig):
    def __init__(self, codec_id: str, adapter_id: str, config_id: int, index: int) -> None:
        """Init with codec, adapter, id and index."""
        super().__init__(config_id, index)
        self.codec_id: str = codec_id
        self.adapter_id: str = adapter_id

    def __repr__(self) -> str:
        return f"{self.codec_id}##{self.adapter_id}##0x{self.id:X}##{self.index:d}"


class BleAdvConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BLE ADV."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.configs: list[_CodecConfig] = []
        self.selected_config: int = -1
        self.pair_done: bool = False
        self.blink_done = False
        self._clean_datetime = None

    def _selected_conf_str(self) -> str:
        return f"{self.selected_config + 1}/{len(self.configs)}: {self.configs[self.selected_config]}"

    async def _async_on_new_config(self, codec_id: str, adapter_id: str, config: BleAdvConfig) -> None:
        self.configs.append(_CodecConfig(codec_id, adapter_id, config.id, config.index))

    async def _async_wait_for_config(self) -> None:
        i = 0
        while not self.configs and i < 100:
            i += 1
            await asyncio.sleep(0.1)

    async def _async_start_listen_to_config(self) -> None:
        if self._clean_datetime is None:
            await self._coordinator.register_callback(self.flow_id, _MatchingAllCallback(self._async_on_new_config))
            self._clean_datetime = datetime.now() + timedelta(seconds=35)
            self.hass.async_create_task(self._async_delayed_stop())
        else:
            self._clean_datetime = datetime.now() + timedelta(seconds=35)

    async def _async_stop_listen_to_config(self) -> None:
        if self._clean_datetime is not None:
            await self._coordinator.unregister_callback(self.flow_id)
            self._clean_datetime = None

    async def _async_delayed_stop(self) -> None:
        while (self._clean_datetime is not None) and (self._clean_datetime > datetime.now()):
            await asyncio.sleep(1)
        await self._async_stop_listen_to_config()

    def _get_device(self, name: str, config: _CodecConfig) -> BleAdvDevice:
        return BleAdvDevice(self.hass, _LOGGER, name, name, config.codec_id, config.adapter_id, 3, 20, config, self._coordinator)

    async def _async_blink_light(self) -> None:
        config = self.configs[self.selected_config]
        tmp_device: BleAdvDevice = self._get_device("cf", config)
        await tmp_device.async_start()
        on_cmd = BleAdvEntAttr(["on"], {"on": True}, "light", 0)
        off_cmd = BleAdvEntAttr(["on"], {"on": False}, "light", 0)
        await tmp_device.apply_change(on_cmd)
        await asyncio.sleep(1)
        await tmp_device.apply_change(off_cmd)
        await asyncio.sleep(1)
        await tmp_device.apply_change(on_cmd)
        await asyncio.sleep(1)
        await tmp_device.apply_change(off_cmd)
        await tmp_device.async_stop()

    async def _async_pair_all(self) -> None:
        pair_cmd = BleAdvEntAttr(["pair"], {}, "device", 0)
        for i, config in enumerate(self.configs):
            tmp_device: BleAdvDevice = self._get_device(f"cf{i}", config)
            await tmp_device.async_start()
            await tmp_device.apply_change(pair_cmd)
            await asyncio.sleep(0.3)
            await tmp_device.async_stop()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:  # noqa: ARG002
        """Handle the user step to setup a device."""
        self._coordinator: BleAdvCoordinator = await get_coordinator(self.hass)
        install_types = ["wait_config", "manual", "pair"]
        return self.async_show_menu(step_id="user", menu_options=install_types)

    async def async_step_manual(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manual input step."""
        if user_input is not None:
            self.configs.append(
                _CodecConfig(
                    user_input[CONF_CODEC_ID], user_input[CONF_ADAPTER_ID], int(f"0x{user_input[CONF_FORCED_ID]}", 16), int(user_input[CONF_INDEX])
                )
            )
            return await self.async_step_blink()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ADAPTER_ID): vol.In(list(self._coordinator.adapters.keys())),
                vol.Required(CONF_CODEC_ID): vol.In(list(self._coordinator.codecs.keys())),
                vol.Required(CONF_FORCED_ID): selector.TextSelector(selector.TextSelectorConfig(prefix="0x")),
                vol.Required(CONF_INDEX): selector.NumberSelector(
                    selector.NumberSelectorConfig(step=1, min=0, max=255, mode=selector.NumberSelectorMode.BOX)
                ),
            }
        )

        return self.async_show_form(step_id="manual", data_schema=data_schema)

    async def async_step_pair(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Pair Step."""
        if user_input is not None:
            gen_id = randint(0xFF, 0xFFF5)
            adapter_id = user_input[CONF_ADAPTER_ID]
            for codec_id in PHONE_APPS[user_input[CONF_PHONE_APP]]:
                self.configs.append(_CodecConfig(codec_id, adapter_id, gen_id, 1))
            await self._async_pair_all()
            return await self.async_step_blink()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ADAPTER_ID): vol.In(list(self._coordinator.adapters.keys())),
                vol.Required(CONF_PHONE_APP): vol.In(list(PHONE_APPS.keys())),
            }
        )
        return self.async_show_form(step_id="pair", data_schema=data_schema)

    async def async_step_wait_config(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:  # noqa: ARG002
        """Wait for listened config Step."""
        if not self.configs:
            await self._async_start_listen_to_config()
            return self.async_show_progress(
                step_id="wait_config",
                progress_action="wait_config",
                progress_task=self.hass.async_create_task(self._async_wait_for_config()),
            )
        self.wait_for_agg = False
        return self.async_show_progress_done(next_step_id="agg_config")

    async def async_step_agg_config(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:  # noqa: ARG002
        """Supplementary wait for other config Step."""
        if not self.wait_for_agg:
            self.wait_for_agg = True
            return self.async_show_progress(
                step_id="agg_config",
                progress_action="agg_config",
                progress_task=self.hass.async_create_task(asyncio.sleep(2.0)),
            )
        await self._async_stop_listen_to_config()
        return self.async_show_progress_done(next_step_id="blink")

    async def async_step_blink(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:  # noqa: ARG002
        """Blink Step."""
        if not self.blink_done:
            self.blink_done = True
            self.selected_config = self.selected_config + 1
            if self.selected_config < len(self.configs):
                return self.async_show_progress(
                    step_id="blink",
                    progress_action="blink",
                    progress_task=self.hass.async_create_task(self._async_blink_light()),
                    description_placeholders={"conf": self._selected_conf_str()},
                )
            return self.async_abort(reason="no_config")
        return self.async_show_progress_done(next_step_id="confirm")

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:  # noqa: ARG002
        """Confirm choice Step."""
        return self.async_show_menu(
            step_id="confirm", menu_options=["confirm_yes", "confirm_no"], description_placeholders={"conf": self._selected_conf_str()}
        )

    async def async_step_confirm_yes(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:  # noqa: ARG002
        """Confirm YES Step."""
        config = self.configs[self.selected_config]
        await self.async_set_unique_id(f"{config}")
        self._abort_if_unique_id_configured()

        return await self.async_step_finalize()

    async def async_step_confirm_no(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:  # noqa: ARG002
        """Confirm NO Step."""
        self.blink_done = False
        return await self.async_step_blink()

    async def async_step_finalize(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Finalize Step, also handling Reconfigure."""
        is_reconfig = self.source == SOURCE_RECONFIGURE
        if is_reconfig:
            entry = self._get_reconfigure_entry()
            data: dict[str, Any] = entry.data.copy()
            codec_id = data[CONF_CODEC_ID]
        else:
            data: dict[str, Any] = {"technical": {"interval": 20, "repeat": 2}}
            codec_id = self.configs[self.selected_config].codec_id

        if user_input is None:
            acodec = self._coordinator.codecs[codec_id]
            data_schema = vol.Schema({})
            if not is_reconfig:
                data_schema = data_schema.extend({vol.Required(CONF_NAME): str})
            data_schema = data_schema.extend(
                {
                    vol.Required(f"{LIGHT_TYPE}_{ind}"): section(
                        vol.Schema(
                            {
                                vol.Required("type"): selector.SelectSelector(
                                    selector.SelectSelectorConfig(
                                        translation_key=f"ble_adv_type_{LIGHT_TYPE}",
                                        mode=selector.SelectSelectorMode.DROPDOWN,
                                        options=self._compute_type_options(data, LIGHT_TYPE, ind, [*st, "none"]),
                                    )
                                ),
                                vol.Optional(
                                    "min_brightness", default=self._compute_default(data, LIGHT_TYPE, ind, "min_brightness", 3)
                                ): selector.NumberSelector(
                                    selector.NumberSelectorConfig(step=1, min=1, max=15, mode=selector.NumberSelectorMode.BOX)
                                ),
                            }
                        )
                    )
                    for ind, st in enumerate(acodec.get_features(LIGHT_TYPE))
                    if st is not None
                }
            )
            data_schema = data_schema.extend(
                {
                    vol.Required(f"{FAN_TYPE}_{ind}"): section(
                        vol.Schema(
                            {
                                vol.Required("type"): selector.SelectSelector(
                                    selector.SelectSelectorConfig(
                                        translation_key=f"ble_adv_type_{FAN_TYPE}",
                                        mode=selector.SelectSelectorMode.DROPDOWN,
                                        options=self._compute_type_options(data, FAN_TYPE, ind, [*st, "none"]),
                                    )
                                ),
                                vol.Required("direction", default=self._compute_default(data, FAN_TYPE, ind, "direction", False)): bool,
                                vol.Required("oscillating", default=self._compute_default(data, FAN_TYPE, ind, "oscillating", False)): bool,
                            }
                        )
                    )
                    for ind, st in enumerate(acodec.get_features(FAN_TYPE))
                    if st is not None
                }
            )
            data_schema = data_schema.extend(
                {
                    vol.Required("technical"): section(
                        vol.Schema(
                            {
                                vol.Optional("interval", default=(data["technical"]["interval"])): selector.NumberSelector(
                                    selector.NumberSelectorConfig(step=1, min=20, max=100, mode=selector.NumberSelectorMode.BOX)
                                ),
                                vol.Optional("repeat", default=(data["technical"]["repeat"])): selector.NumberSelector(
                                    selector.NumberSelectorConfig(step=1, min=1, max=10, mode=selector.NumberSelectorMode.BOX)
                                ),
                            }
                        )
                    )
                }
            )

            return self.async_show_form(step_id="finalize", data_schema=data_schema, errors={})

        if is_reconfig:
            data[FAN_TYPE] = self._convert_entity_dict(FAN_TYPE, user_input)
            data[LIGHT_TYPE] = self._convert_entity_dict(LIGHT_TYPE, user_input)
            data["technical"] = user_input["technical"]
            return self.async_update_reload_and_abort(entry, data_updates=data)

        config = self.configs[self.selected_config]
        user_input[CONF_CODEC_ID] = config.codec_id
        user_input[CONF_ADAPTER_ID] = config.adapter_id
        user_input[CONF_FORCED_ID] = config.id
        user_input[CONF_INDEX] = config.index
        user_input[FAN_TYPE] = self._convert_entity_dict(FAN_TYPE, user_input)
        user_input[LIGHT_TYPE] = self._convert_entity_dict(LIGHT_TYPE, user_input)
        return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

    def _convert_entity_dict(self, ent_type: str, user_input: dict[str, Any]) -> list[Any]:
        list_type = []
        for i in range(3):
            ent_conf = user_input.pop(f"{ent_type}_{i}", None)
            if ent_conf is not None and ent_conf["type"] != "none":
                list_type.append(ent_conf)
        return list_type

    def _compute_default(
        self, data: dict[str, Any] | None, bt: str, ind: int, option: str, default: str | int | bool | None
    ) -> str | int | bool | None:
        eff_default = default
        if data and (bt in data) and ind < len(data[bt]):
            eff_default = data[bt][ind].get(option, default)
        return eff_default

    def _compute_type_options(self, data: dict[str, Any] | None, bt: str, ind: int, options: list[Any]) -> list[Any]:
        eff_default = self._compute_default(data, bt, ind, "type", "none")
        return [eff_default] + [opt for opt in options if opt != eff_default]

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:  # noqa: ARG002
        """Reconfigure Step."""
        self._coordinator = await get_coordinator(self.hass)
        return await self.async_step_finalize()
