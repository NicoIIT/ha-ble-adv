"""Config Flow for BLE ADV."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from http import HTTPStatus
from random import randint
from typing import Any

import voluptuous as vol
from aiohttp import web
from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_DEVICE, CONF_NAME, CONF_TYPE
from homeassistant.data_entry_flow import section
from homeassistant.helpers import selector
from homeassistant.helpers.http import HomeAssistantView
from homeassistant.helpers.json import ExtendedJSONEncoder

from . import get_coordinator
from .codecs import PHONE_APPS
from .codecs.const import (
    ATTR_CMD,
    ATTR_CMD_PAIR,
    ATTR_DIR,
    ATTR_EFFECT,
    ATTR_ON,
    ATTR_OSC,
    ATTR_PRESET,
    ATTR_SUB_TYPE,
    DEVICE_TYPE,
    FAN_TYPE,
    LIGHT_TYPE,
    LIGHT_TYPE_CWW,
    LIGHT_TYPE_RGB,
)
from .codecs.models import BleAdvCodec, BleAdvConfig, BleAdvEntAttr
from .const import (
    CONF_ADAPTER_ID,
    CONF_ADAPTER_IDS,
    CONF_CODEC_ID,
    CONF_DURATION,
    CONF_EFFECTS,
    CONF_FANS,
    CONF_FORCED_ID,
    CONF_INDEX,
    CONF_INTERVAL,
    CONF_LAST_VERSION,
    CONF_LIGHTS,
    CONF_MAX_ENTITY_NB,
    CONF_MIN_BRIGHTNESS,
    CONF_PHONE_APP,
    CONF_PRESETS,
    CONF_REFRESH_DIR_ON_START,
    CONF_REFRESH_ON_START,
    CONF_REFRESH_OSC_ON_START,
    CONF_REMOTE,
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

type CodecFoundCallback = Callable[[str, str, str, BleAdvConfig], Awaitable[None]]

WAIT_MAX_SECONDS = 10


class _MatchingAllCallback(MatchingCallback):
    def __init__(self, callback: CodecFoundCallback) -> None:
        self.callback: CodecFoundCallback = callback

    def __repr__(self) -> str:
        return "Matching ALL"

    async def handle(self, codec_id: str, match_id: str, adapter_id: str, config: BleAdvConfig, __: list[BleAdvEntAttr]) -> bool:
        await self.callback(codec_id, match_id, adapter_id, config)
        return True


class _CodecConfig(BleAdvConfig):
    def __init__(self, codec_id: str, config_id: int, index: int) -> None:
        """Init with codec, adapter, id and index."""
        super().__init__(config_id, index)
        self.codec_id: str = codec_id

    def __repr__(self) -> str:
        return f"{self.codec_id} - 0x{self.id:X} - {self.index:d}"

    def __eq__(self, comp: _CodecConfig) -> bool:
        return (self.codec_id == comp.codec_id) and (self.id == comp.id) and (self.index == comp.index)

    def __hash__(self) -> int:
        return hash([self.codec_id, self.id, self.index])


type WebResponseCallback = Callable[[], Awaitable[web.Response]]


class BleAdvConfigView(HomeAssistantView):
    """Config Flow related api view."""

    url: str = f"/api/{DOMAIN}/config_flow/{{flow_id}}"
    name: str = f"api:{DOMAIN}:config_flow"
    requires_auth: bool = False

    def __init__(self, flow_id: str, response: WebResponseCallback) -> None:
        self._flow_id: str = flow_id
        self._response = response
        self._called_once = False

    @property
    def full_url(self) -> str:
        """Get the full url."""
        return self.url.format(flow_id=self._flow_id)

    async def get(self, _: web.Request, flow_id: str) -> web.Response:
        """Process call."""
        # Security as there is no auth: the flow_id must match the flow.flow_id
        # We ensure the view cannot be called more than once
        # as it is not possible to unregister the view
        if self._called_once or self._flow_id != flow_id:
            _LOGGER.error(f"Invalid flow_id given: {flow_id}")
            return web.Response(status=HTTPStatus.NOT_FOUND)
        self._called_once = True
        return await self._response()


class BleAdvConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BLE ADV."""

    VERSION = CONF_LAST_VERSION

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.configs: dict[str, list[_CodecConfig]] = {}
        self.selected_adapter_id: str = ""
        self.selected_config: int = 0
        self.pair_done: bool = False
        self._blink_task = None
        self._wait_task = None
        self._clean_datetime = None

        self._data: dict[str, Any] = {}
        self._conf_name: str = ""
        self._finalize_requested: bool = False

    def _selected_adapter_confs(self) -> list[_CodecConfig]:
        return self.configs[self.selected_adapter_id]

    def _selected_conf(self) -> _CodecConfig:
        return self._selected_adapter_confs()[self.selected_config]

    def _selected_conf_placeholders(self) -> dict[str, str]:
        conf = self._selected_conf()
        return {
            "nb": str(self.selected_config + 1),
            "tot": str(len(self._selected_adapter_confs())),
            "codec": conf.codec_id,
            "id": f"0x{conf.id:X}",
            "index": str(conf.index),
        }

    def _remote_conf_placeholders(self) -> dict[str, str]:
        conf = self._data[CONF_REMOTE]
        return {
            "codec": conf[CONF_CODEC_ID],
            "id": f"0x{conf[CONF_FORCED_ID]:X}",
            "index": str(conf[CONF_INDEX]),
        }

    async def _async_on_new_config(self, codec_id: str, match_id: str, adapter_id: str, config: BleAdvConfig) -> None:
        confs = self.configs.setdefault(adapter_id, [])
        if (match_conf := _CodecConfig(match_id, config.id, config.index)) not in confs:
            confs.append(match_conf)
        if (new_conf := _CodecConfig(codec_id, config.id, config.index)) not in confs:
            confs.append(new_conf)

    async def _async_wait_for_config(self, nb_seconds: int) -> None:
        i = 0
        while not self.configs and i < (10 * nb_seconds):
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

    def _get_device(self, name: str, config: _CodecConfig, duration: int | None = None) -> BleAdvDevice:
        codec: BleAdvCodec = self._coordinator.codecs[config.codec_id]
        return BleAdvDevice(
            self.hass,
            name,
            name,
            config.codec_id,
            [self.selected_adapter_id],
            codec.repeat,
            codec.interval,
            duration if duration is not None else codec.duration,
            config,
            self._coordinator,
        )

    async def _async_blink_light(self) -> None:
        config = self._selected_conf()
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
        pair_cmd = BleAdvEntAttr([ATTR_CMD], {ATTR_CMD: ATTR_CMD_PAIR}, DEVICE_TYPE, 0)
        for i, config in enumerate(self._selected_adapter_confs()):
            tmp_device: BleAdvDevice = self._get_device(f"cf{i}", config, 300)
            await tmp_device.async_start()
            await tmp_device.apply_change(pair_cmd)
            await asyncio.sleep(0.3)
            await tmp_device.async_stop()
        await asyncio.sleep(2)

    async def view_called(self) -> None:
        """BleAdvConfigView has been called: continue flow."""
        await self.hass.config_entries.flow.async_configure(flow_id=self.flow_id, user_input={})

    async def async_step_user(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the user step to setup a device."""
        self._coordinator: BleAdvCoordinator = await get_coordinator(self.hass)
        if not self._coordinator.has_available_adapters():
            return self.async_abort(reason="no_adapters")
        return self.async_show_menu(step_id="user", menu_options=["wait_config", "manual", "pair", "tools"])

    async def async_step_tools(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Tooling Step."""
        return self.async_show_menu(step_id="tools", menu_options=["diag"])

    async def async_step_diag(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Diagnostic step."""
        if user_input is not None:
            return self.async_external_step_done(next_step_id="tools")

        async def diag_resp() -> web.Response:
            data = await self._coordinator.full_diagnostic_dump()
            await self.view_called()
            return web.Response(
                body=json.dumps(data, indent=2, cls=ExtendedJSONEncoder),
                content_type="application/json",
                headers={"Content-Disposition": 'attachment; filename="ble_adv_diag.json"'},
            )

        diag_view = BleAdvConfigView(self.flow_id, diag_resp)
        self.hass.http.register_view(diag_view)
        return self.async_external_step(url=diag_view.full_url)

    async def async_step_manual(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manual input step."""
        if user_input is not None:
            self.selected_adapter_id = user_input[CONF_ADAPTER_ID]
            self.configs[self.selected_adapter_id] = [
                _CodecConfig(user_input[CONF_CODEC_ID], int(f"0x{user_input[CONF_FORCED_ID]}", 16), int(user_input[CONF_INDEX]))
            ]
            return await self.async_step_blink()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ADAPTER_ID): vol.In(self._coordinator.get_adapter_ids()),
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
            self.selected_adapter_id = user_input[CONF_ADAPTER_ID]
            self.configs.setdefault(self.selected_adapter_id, []).clear()
            for codec_id in PHONE_APPS[user_input[CONF_PHONE_APP]]:
                self.configs[self.selected_adapter_id].append(_CodecConfig(codec_id, gen_id, 1))
            await self._async_pair_all()
            return await self.async_step_confirm_pair()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ADAPTER_ID): vol.In(self._coordinator.get_adapter_ids()),
                vol.Required(CONF_PHONE_APP): vol.In(list(PHONE_APPS.keys())),
            }
        )
        return self.async_show_form(step_id="pair", data_schema=data_schema)

    async def async_step_confirm_pair(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the confirm that pair worked OK."""
        return self.async_show_menu(step_id="confirm_pair", menu_options=["pair", "confirm_no_abort", "blink"])

    async def async_step_wait_config(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Wait for listened config Step."""
        if not self.configs:
            if self._wait_task is None:
                await self._async_start_listen_to_config()
                self._wait_task = self.hass.async_create_task(self._async_wait_for_config(WAIT_MAX_SECONDS))
            if self._wait_task.done():
                self._wait_task = None
                return self.async_show_progress_done(next_step_id="no_config")
            return self.async_show_progress(
                step_id="wait_config",
                progress_action="wait_config",
                progress_task=self._wait_task,
                description_placeholders={"max_seconds": str(WAIT_MAX_SECONDS)},
            )
        self.wait_for_agg = False
        return self.async_show_progress_done(next_step_id="agg_config")

    async def async_step_no_config(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """No Config found, abort or retry."""
        return self.async_show_menu(step_id="no_config", menu_options=["wait_config", "abort_config"])

    async def async_step_abort_config(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """No Config found, abort."""
        return self.async_abort(reason="no_config")

    async def async_step_agg_config(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Supplementary wait for other config Step."""
        if not self.wait_for_agg:
            self.wait_for_agg = True
            return self.async_show_progress(
                step_id="agg_config",
                progress_action="agg_config",
                progress_task=self.hass.async_create_task(asyncio.sleep(3.0)),
            )
        await self._async_stop_listen_to_config()
        return self.async_show_progress_done(next_step_id="choose_adapter")

    async def async_step_choose_adapter(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Choose adapter."""
        if user_input is None:
            _LOGGER.info(f"Configs listened: {self.configs}")
        if len(self.configs) != 1:
            if user_input is not None:
                self.selected_adapter_id = user_input[CONF_ADAPTER_ID]
                return await self.async_step_blink()

            data_schema = vol.Schema({vol.Required(CONF_ADAPTER_ID): vol.In(list(self.configs.keys()))})
            return self.async_show_form(step_id="choose_adapter", data_schema=data_schema)

        self.selected_adapter_id = next(iter(self.configs))
        return await self.async_step_blink()

    async def async_step_blink(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Blink Step."""
        if self._blink_task is None:
            self._blink_task = self.hass.async_create_task(self._async_blink_light())
        if self._blink_task.done():
            self._blink_task = None
            return self.async_show_progress_done(next_step_id="confirm")
        return self.async_show_progress(
            step_id="blink",
            progress_action="blink",
            progress_task=self._blink_task,
            description_placeholders=self._selected_conf_placeholders(),
        )

    async def async_step_confirm(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Confirm choice Step."""
        nb_confs = len(self._selected_adapter_confs())
        opts = ["confirm_yes", "confirm_no_abort" if self.selected_config == (nb_confs - 1) else "confirm_no_another", "confirm_retry_last"]
        if nb_confs > 1:
            opts.append("confirm_retry_all")
        return self.async_show_menu(step_id="confirm", menu_options=opts, description_placeholders=self._selected_conf_placeholders())

    async def async_step_confirm_yes(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Confirm YES Step."""
        conf = self._selected_conf()
        await self.async_set_unique_id(f"{conf.codec_id}##0x{conf.id:X}##{conf.index:d}", raise_on_progress=False)
        self._abort_if_unique_id_configured()
        codec: BleAdvCodec = self._coordinator.codecs[conf.codec_id]
        self._data = {
            CONF_DEVICE: {CONF_CODEC_ID: conf.codec_id, CONF_FORCED_ID: conf.id, CONF_INDEX: conf.index},
            CONF_LIGHTS: [{}] * CONF_MAX_ENTITY_NB,
            CONF_FANS: [{}] * CONF_MAX_ENTITY_NB,
            CONF_TECHNICAL: {
                CONF_ADAPTER_IDS: [self.selected_adapter_id],
                CONF_DURATION: codec.duration,
                CONF_INTERVAL: codec.interval,
                CONF_REPEAT: codec.repeat,
            },
        }
        return await self.async_step_configure()

    async def async_step_confirm_no_another(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Confirm NO, try another Step."""
        self.selected_config = self.selected_config + 1
        return await self.async_step_blink()

    async def async_step_confirm_no_abort(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Confirm NO, abort Step."""
        return self.async_abort(reason="no_config")

    async def async_step_confirm_retry_last(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Confirm Retry Step."""
        return await self.async_step_blink()

    async def async_step_confirm_retry_all(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Confirm Retry ALL Step."""
        self.selected_config = 0
        self.selected_adapter_id = ""
        return await self.async_step_choose_adapter()

    async def async_step_configure(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Configure choice Step."""
        return self.async_show_menu(
            step_id="configure",
            menu_options=["config_entities", "config_remote", "config_technical", "finalize"],
        )

    def _has_one_entity(self) -> bool:
        return any(x.get(CONF_TYPE, CONF_TYPE_NONE) != CONF_TYPE_NONE for x in [*self._data[CONF_LIGHTS], *self._data[CONF_FANS]])

    async def async_step_config_entities(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Configure Entities Step."""
        errors = {}
        if user_input is not None:
            self._data[CONF_LIGHTS] = self._convert_to_list(LIGHT_TYPE, user_input)
            self._data[CONF_FANS] = self._convert_to_list(FAN_TYPE, user_input)
            if self._has_one_entity():
                if self._finalize_requested:
                    return await self.async_step_finalize()
                return await self.async_step_configure()
            errors["base"] = "missing_entity"

        codec: BleAdvCodec = self._coordinator.codecs[self._data[CONF_DEVICE][CONF_CODEC_ID]]
        sections: dict[str, tuple[dict[vol.Schemable, Any], bool]] = {}

        # Build one section for each Light supported by the codec
        for i, feats in enumerate(codec.get_supported_features(LIGHT_TYPE)):
            if ATTR_SUB_TYPE in feats:
                opts = self._data[CONF_LIGHTS][i]
                types = [*feats[ATTR_SUB_TYPE], CONF_TYPE_NONE]
                schema_opts: dict[vol.Schemable, Any] = {
                    vol.Required(CONF_TYPE, default=opts.get(CONF_TYPE, CONF_TYPE_NONE)): self._get_selector(LIGHT_TYPE, types),
                }
                if LIGHT_TYPE_CWW in types or LIGHT_TYPE_RGB in types:
                    schema_opts[vol.Required(CONF_MIN_BRIGHTNESS, default=opts.get(CONF_MIN_BRIGHTNESS, 3))] = selector.NumberSelector(
                        selector.NumberSelectorConfig(step=1, min=1, max=15, mode=selector.NumberSelectorMode.BOX)
                    )
                    schema_opts[vol.Required(CONF_REFRESH_ON_START, default=opts.get(CONF_REFRESH_ON_START, False))] = bool
                if LIGHT_TYPE_CWW in types:
                    schema_opts[vol.Required(CONF_REVERSED, default=opts.get(CONF_REVERSED, False))] = bool
                if ATTR_EFFECT in feats:
                    effects = list(feats[ATTR_EFFECT])
                    schema_opts[vol.Required(CONF_EFFECTS, default=opts.get(CONF_EFFECTS, effects))] = self._get_multi_selector(CONF_EFFECTS, effects)
                sections[f"{LIGHT_TYPE}_{i}"] = (schema_opts, (i > 0) and CONF_TYPE in opts)

        # Build one section for each Fan supported by the codec
        for i, feats in enumerate(codec.get_supported_features(FAN_TYPE)):
            if ATTR_SUB_TYPE in feats:
                opts = self._data[CONF_FANS][i]
                types = [*feats[ATTR_SUB_TYPE], CONF_TYPE_NONE]
                schema_opts: dict[vol.Schemable, Any] = {
                    vol.Required(CONF_TYPE, default=opts.get(CONF_TYPE, CONF_TYPE_NONE)): self._get_selector(FAN_TYPE, types),
                }
                if ATTR_DIR in feats:
                    schema_opts[vol.Required(CONF_USE_DIR, default=opts.get(CONF_USE_DIR, True))] = bool
                    schema_opts[vol.Required(CONF_REFRESH_DIR_ON_START, default=opts.get(CONF_REFRESH_DIR_ON_START, False))] = bool
                if ATTR_OSC in feats:
                    schema_opts[vol.Required(CONF_USE_OSC, default=opts.get(CONF_USE_OSC, True))] = bool
                    schema_opts[vol.Required(CONF_REFRESH_OSC_ON_START, default=opts.get(CONF_REFRESH_OSC_ON_START, False))] = bool
                if ATTR_PRESET in feats:
                    presets = list(feats[ATTR_PRESET])
                    schema_opts[vol.Required(CONF_PRESETS, default=opts.get(CONF_PRESETS, presets))] = self._get_multi_selector(CONF_PRESETS, presets)
                sections[f"{FAN_TYPE}_{i}"] = (schema_opts, (i > 0) and CONF_TYPE in opts)

        # Finalize schema with all sections
        data_schema = vol.Schema(
            {vol.Required(name): section(vol.Schema(sect), {"collapsed": collapsed}) for name, (sect, collapsed) in sections.items()}
        )

        return self.async_show_form(step_id="config_entities", data_schema=data_schema, errors=errors)

    async def async_step_config_remote(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Configure Remote."""
        self.configs.clear()
        self.selected_config = 0
        self.selected_adapter_id = ""
        self._wait_task = None
        if CONF_REMOTE in self._data and CONF_CODEC_ID in self._data[CONF_REMOTE]:
            return self.async_show_menu(
                step_id="config_remote",
                menu_options=["config_remote_delete", "config_remote_update", "config_remote_new", "configure"],
                description_placeholders=self._remote_conf_placeholders(),
            )
        return await self.async_step_config_remote_new()

    async def async_step_config_remote_delete(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Remove Remote."""
        self._data[CONF_REMOTE].clear()
        return await self.async_step_configure()

    async def async_step_config_remote_new(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Configure New Remote."""
        if not self.configs:
            if self._wait_task is None:
                await self._async_start_listen_to_config()
                self._wait_task = self.hass.async_create_task(self._async_wait_for_config(WAIT_MAX_SECONDS))
            if self._wait_task.done():
                self._wait_task = None
                return self.async_show_progress_done(next_step_id="configure")
            return self.async_show_progress(
                step_id="config_remote_new",
                progress_action="wait_config_remote",
                progress_task=self._wait_task,
                description_placeholders={"max_seconds": str(WAIT_MAX_SECONDS)},
            )
        await self._async_stop_listen_to_config()
        config = self.configs[next(iter(self.configs))][0]  # get the first found adapter/config
        self._data[CONF_REMOTE] = {CONF_CODEC_ID: config.codec_id, CONF_FORCED_ID: config.id, CONF_INDEX: config.index}
        return self.async_show_progress_done(next_step_id="config_remote_update")

    async def async_step_config_remote_update(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Update Remote Options."""
        if user_input is not None:
            return await self.async_step_configure()

        return self.async_show_form(
            step_id="config_remote_update",
            data_schema=vol.Schema({}),
            description_placeholders=self._remote_conf_placeholders(),
        )

    async def async_step_config_technical(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Configure Technical."""
        errors = {}
        if user_input is not None:
            self._data[CONF_TECHNICAL] = user_input
            if len(self._data[CONF_TECHNICAL][CONF_ADAPTER_IDS]) > 0:
                return await self.async_step_configure()
            errors["base"] = "missing_adapter"

        def_tech = self._data[CONF_TECHNICAL]
        avail_adapters = self._coordinator.get_adapter_ids()
        def_adapters = [adapt for adapt in def_tech[CONF_ADAPTER_IDS] if adapt in avail_adapters]
        data_schema = vol.Schema(
            {
                vol.Required(CONF_ADAPTER_IDS, default=def_adapters): self._get_multi_selector(CONF_ADAPTER_IDS, avail_adapters),
                vol.Optional(CONF_DURATION, default=def_tech[CONF_DURATION]): selector.NumberSelector(
                    selector.NumberSelectorConfig(step=50, min=100, max=2000, mode=selector.NumberSelectorMode.SLIDER)
                ),
                vol.Optional(CONF_INTERVAL, default=def_tech[CONF_INTERVAL]): selector.NumberSelector(
                    selector.NumberSelectorConfig(step=10, min=10, max=150, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(CONF_REPEAT, default=def_tech[CONF_REPEAT]): selector.NumberSelector(
                    selector.NumberSelectorConfig(step=1, min=1, max=20, mode=selector.NumberSelectorMode.BOX)
                ),
            }
        )
        return self.async_show_form(step_id="config_technical", data_schema=data_schema, errors=errors)

    async def async_step_finalize(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Finalize Step."""
        if not self._has_one_entity():
            self._finalize_requested = True
            return await self.async_step_config_entities()

        if self.source == SOURCE_RECONFIGURE:
            return self.async_update_reload_and_abort(self._get_reconfigure_entry(), data_updates=self._data)

        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_NAME], data=self._data)

        return self.async_show_form(step_id="finalize", data_schema=vol.Schema({vol.Required(CONF_NAME): str}))

    async def async_step_reconfigure(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Reconfigure Step."""
        self._coordinator = await get_coordinator(self.hass)
        self._data = {**self._get_reconfigure_entry().data}
        return await self.async_step_configure()

    def _convert_to_list(self, ent_type: str, user_input: dict[str, Any]) -> list[Any]:
        """Convert from {'ligth_0':{opts0}, 'ligth_1':{opts1},, ...] to [{opts0}, {opts1}, ...]."""
        return [
            x if x is not None and x.get(CONF_TYPE) != CONF_TYPE_NONE else {}
            for x in [user_input.get(f"{ent_type}_{i}") for i in range(CONF_MAX_ENTITY_NB)]
        ]

    def _get_selector(self, key: str, types: list[str]) -> selector.SelectSelector:
        return selector.SelectSelector(
            selector.SelectSelectorConfig(
                translation_key=key,
                mode=selector.SelectSelectorMode.DROPDOWN,
                options=types,
            )
        )

    def _get_multi_selector(self, key: str, types: list[str]) -> selector.SelectSelector:
        return selector.SelectSelector(
            selector.SelectSelectorConfig(
                translation_key=key,
                mode=selector.SelectSelectorMode.LIST,
                options=types,
                multiple=True,
            )
        )
