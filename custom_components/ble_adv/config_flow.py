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
from homeassistant.const import CONF_DEVICE, CONF_NAME, CONF_TYPE
from homeassistant.data_entry_flow import section
from homeassistant.helpers import selector

from . import get_coordinator
from .codecs import PHONE_APPS
from .codecs.const import ATTR_ON, FAN_TYPE, LIGHT_TYPE
from .codecs.models import BleAdvCodec, BleAdvConfig, BleAdvEntAttr
from .const import (
    CONF_ADAPTER_ID,
    CONF_CODEC_ID,
    CONF_DURATION,
    CONF_FANS,
    CONF_FORCED_ID,
    CONF_INDEX,
    CONF_INTERVAL,
    CONF_LIGHTS,
    CONF_MIN_BRIGHTNESS,
    CONF_PHONE_APP,
    CONF_REFRESH_ON_START,
    CONF_REPEAT,
    CONF_REVERSED,
    CONF_TECHNICAL,
    CONF_TYPE_NONE,
    CONF_USE_DIR,
    CONF_USE_OSC,
    DOMAIN,
)
from .coordinator import BleAdvCoordinator, MatchingCallback
from .device import BleAdvDevice

_LOGGER = logging.getLogger(__name__)

type CodecFoundCallback = Callable[[str, str, BleAdvConfig], Awaitable[None]]
type EntDefault = tuple[dict[str, Any], list[str]]


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

    def _selected_conf_placeholders(self) -> dict[str, str]:
        conf = self.configs[self.selected_config]
        return {
            "nb": str(self.selected_config + 1),
            "tot": str(len(self.configs)),
            "adapter": conf.adapter_id,
            "codec": conf.codec_id,
            "id": f"0x{conf.id:X}",
            "index": str(conf.index),
        }

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
        return BleAdvDevice(self.hass, _LOGGER, name, name, config.codec_id, config.adapter_id, 3, 20, 200, config, self._coordinator)

    async def _async_blink_light(self) -> None:
        config = self.configs[self.selected_config]
        tmp_device: BleAdvDevice = self._get_device("cf", config)
        await tmp_device.async_start()
        on_cmd = BleAdvEntAttr([ATTR_ON], {ATTR_ON: True}, LIGHT_TYPE, 0)
        off_cmd = BleAdvEntAttr([ATTR_ON], {ATTR_ON: False}, LIGHT_TYPE, 0)
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
        if not self._coordinator.has_available_adapters():
            return self.async_abort(reason="no_adapters")
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
                    description_placeholders=self._selected_conf_placeholders(),
                )
            return self.async_abort(reason="no_config")
        return self.async_show_progress_done(next_step_id="confirm")

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:  # noqa: ARG002
        """Confirm choice Step."""
        return self.async_show_menu(
            step_id="confirm",
            menu_options=["confirm_yes", "confirm_no", "confirm_retry"],
            description_placeholders=self._selected_conf_placeholders(),
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

    async def async_step_confirm_retry(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:  # noqa: ARG002
        """Confirm Retry Step."""
        self.blink_done = False
        self.selected_config = self.selected_config - 1
        return await self.async_step_blink()

    async def async_step_finalize(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Finalize Step, also handling Reconfigure in order to share the config in translation files."""
        if self.source == SOURCE_RECONFIGURE:
            return await self._async_reconfigure(user_input)
        return await self._async_finalize(user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Reconfigure Step."""
        self._coordinator = await get_coordinator(self.hass)
        return await self._async_reconfigure(user_input)

    async def _async_finalize(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            data = self._from_user_input(user_input)
            conf_name = user_input[CONF_NAME]
            if len(data[CONF_LIGHTS]) > 0 or len(data[CONF_FANS]) > 0:
                config = self.configs[self.selected_config]
                data[CONF_DEVICE] = {
                    CONF_NAME: conf_name,
                    CONF_CODEC_ID: config.codec_id,
                    CONF_ADAPTER_ID: config.adapter_id,
                    CONF_FORCED_ID: config.id,
                    CONF_INDEX: config.index,
                }
                return self.async_create_entry(title=conf_name, data=data)
            errors["base"] = "missing_entity"
        else:
            data = {CONF_LIGHTS: [], CONF_FANS: [], CONF_TECHNICAL: {}}
            conf_name = ""

        codec_id = self.configs[self.selected_config].codec_id
        data_schema = vol.Schema({vol.Required(CONF_NAME, default=conf_name): str})
        data_schema = data_schema.extend(self._get_data_schema(codec_id, data))
        return self.async_show_form(step_id="finalize", data_schema=data_schema, errors=errors)

    async def _async_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors = {}
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            data = self._from_user_input(user_input)
            if len(data[CONF_LIGHTS]) > 0 or len(data[CONF_FANS]) > 0:
                return self.async_update_reload_and_abort(entry, data_updates=data)
            errors["base"] = "missing_entity"
        else:
            data = {CONF_LIGHTS: entry.data[CONF_LIGHTS], CONF_FANS: entry.data[CONF_FANS], CONF_TECHNICAL: entry.data[CONF_TECHNICAL]}

        codec_id = entry.data[CONF_DEVICE][CONF_CODEC_ID]
        data_schema = vol.Schema(self._get_data_schema(codec_id, data))
        # We voluntarilly call 'finalize' step to share configuration in translation files
        return self.async_show_form(step_id="finalize", data_schema=data_schema, errors=errors)

    def _from_user_input(self, user_input: dict[str, Any]) -> dict[str, Any]:
        return {
            CONF_LIGHTS: self._convert_to_list(LIGHT_TYPE, user_input),
            CONF_FANS: self._convert_to_list(FAN_TYPE, user_input),
            CONF_TECHNICAL: user_input[CONF_TECHNICAL],
        }

    def _convert_to_list(self, ent_type: str, user_input: dict[str, Any]) -> list[Any]:
        """Convert from {'ligth_0':{opts0}, 'ligth_1':{opts1},, ...] to [{opts0}, {opts1}, ...]."""
        return [x for x in [user_input.get(f"{ent_type}_{i}") for i in range(3)] if x is not None and x.get(CONF_TYPE) != CONF_TYPE_NONE]

    def _get_default_data(self, types: list[Any], options: list[dict[str, Any]]) -> list[EntDefault]:
        opts = options + [{}] * (len(types) - len(options))
        return [(opts[i], [*feature, CONF_TYPE_NONE]) for i, feature in enumerate(types) if feature is not None]

    def _get_data_schema(self, codec_id: str, prev: dict[str, Any]) -> dict:
        codec: BleAdvCodec = self._coordinator.codecs[codec_id]
        def_lights = self._get_default_data(codec.get_features(LIGHT_TYPE), prev.get(CONF_LIGHTS, []))
        def_fans = self._get_default_data(codec.get_features(FAN_TYPE), prev.get(CONF_FANS, []))
        def_tech = prev.get(CONF_TECHNICAL, [])
        return {
            **{
                vol.Required(f"{LIGHT_TYPE}_{i}"): section(
                    vol.Schema(
                        {
                            vol.Required(CONF_TYPE, default=opts.get(CONF_TYPE, CONF_TYPE_NONE)): self._get_selector(LIGHT_TYPE, types),
                            vol.Optional(CONF_MIN_BRIGHTNESS, default=opts.get(CONF_MIN_BRIGHTNESS, 3)): selector.NumberSelector(
                                selector.NumberSelectorConfig(step=1, min=1, max=15, mode=selector.NumberSelectorMode.BOX)
                            ),
                            vol.Required(CONF_REFRESH_ON_START, default=opts.get(CONF_REFRESH_ON_START, False)): bool,
                            vol.Required(CONF_REVERSED, default=opts.get(CONF_REVERSED, False)): bool,
                        }
                    ),
                    {"collapsed": (CONF_TYPE not in opts) and (i > 0)},
                )
                for i, (opts, types) in enumerate(def_lights)
            },
            **{
                vol.Required(f"{FAN_TYPE}_{i}"): section(
                    vol.Schema(
                        {
                            vol.Required(CONF_TYPE, default=opts.get(CONF_TYPE, CONF_TYPE_NONE)): self._get_selector(FAN_TYPE, types),
                            vol.Required(CONF_USE_DIR, default=opts.get(CONF_USE_DIR, False)): bool,
                            vol.Required(CONF_USE_OSC, default=opts.get(CONF_USE_OSC, False)): bool,
                            vol.Required(CONF_REFRESH_ON_START, default=opts.get(CONF_REFRESH_ON_START, False)): bool,
                        }
                    ),
                    {"collapsed": (CONF_TYPE not in opts) and (i > 0)},
                )
                for i, (opts, types) in enumerate(def_fans)
            },
            vol.Required(CONF_TECHNICAL): section(
                vol.Schema(
                    {
                        vol.Optional(CONF_DURATION, default=def_tech.get(CONF_DURATION, 850)): selector.NumberSelector(
                            selector.NumberSelectorConfig(step=50, min=100, max=1000, mode=selector.NumberSelectorMode.SLIDER)
                        ),
                        vol.Optional(CONF_INTERVAL, default=def_tech.get(CONF_INTERVAL, 20)): selector.NumberSelector(
                            selector.NumberSelectorConfig(step=10, min=20, max=100, mode=selector.NumberSelectorMode.BOX)
                        ),
                        vol.Optional(CONF_REPEAT, default=def_tech.get(CONF_REPEAT, 2)): selector.NumberSelector(
                            selector.NumberSelectorConfig(step=1, min=1, max=10, mode=selector.NumberSelectorMode.BOX)
                        ),
                    }
                ),
                {"collapsed": True},
            ),
        }

    def _get_selector(self, key: str, types: list[str]) -> selector.SelectSelector:
        return selector.SelectSelector(
            selector.SelectSelectorConfig(
                translation_key=key,
                mode=selector.SelectSelectorMode.DROPDOWN,
                options=types,
            )
        )
