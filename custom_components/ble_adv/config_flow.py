"""Config Flow for BLE ADV."""

from __future__ import annotations

import asyncio
import json
import logging
from abc import abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from http import HTTPStatus
from random import randint
from typing import Any, cast

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
    CONF_DEVICE_QUEUE,
    CONF_DURATION,
    CONF_EFFECTS,
    CONF_FANS,
    CONF_FORCE_SEND,
    CONF_FORCED_ID,
    CONF_INDEX,
    CONF_INTERVAL,
    CONF_LAST_VERSION,
    CONF_LIGHTS,
    CONF_MAX_ENTITY_NB,
    CONF_MIN_BRIGHTNESS,
    CONF_PHONE_APP,
    CONF_PRESETS,
    CONF_RAW,
    CONF_REFRESH_DIR_ON_START,
    CONF_REFRESH_ON_START,
    CONF_REFRESH_OSC_ON_START,
    CONF_REMOTE,
    CONF_REPEAT,
    CONF_REPEATS,
    CONF_REVERSED,
    CONF_TECHNICAL,
    CONF_TYPE_NONE,
    CONF_USE_DIR,
    CONF_USE_OSC,
    DOMAIN,
)
from .coordinator import BleAdvBaseDevice, BleAdvCoordinator

_LOGGER = logging.getLogger(__name__)

WAIT_MAX_SECONDS = 10


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
        return hash((self.codec_id, self.id, self.index))


type WebResponseCallback = Callable[[], Awaitable[web.Response]]


class BleAdvConfigView(HomeAssistantView):
    """Config Flow related api view."""

    url: str = f"/api/{DOMAIN}/config_flow/{{flow_id}}"
    name: str = f"api:{DOMAIN}:config_flow"
    requires_auth: bool = False
    NOT_FOUND_RESP: web.Response = web.Response(status=HTTPStatus.NOT_FOUND)

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
            return self.NOT_FOUND_RESP
        self._called_once = True
        return await self._response()


@dataclass
class _ActionResult:
    name: str | None = None
    ph: dict[str, str] | None = None


class BleAdvProgressFlowBase:
    """Base Progress Flow."""

    def __init__(self, flow: BleAdvConfigFlow, step_id: str, ph: dict[str, str]) -> None:
        self._flow: BleAdvConfigFlow = flow
        self._step_id: str = step_id
        self._task: asyncio.Task | None = None
        self._result: _ActionResult = _ActionResult(name=self._step_id, ph=ph)
        self._exit = False

    @abstractmethod
    async def _action_task(self) -> None:
        """Task to be implemented by child. Called in loop, updates _result until the _exit is setup."""

    def _update_action_result(self, result: _ActionResult) -> bool:
        if result.name is not None and self._result.name != result.name:
            self._result.name = result.name
            return True
        if result.ph is not None and self._result.ph != result.ph:
            self._result.ph = result.ph
            return True
        return False

    def next(self) -> ConfigFlowResult | None:
        """Execute next step of the Progress Flow."""
        if self._exit:
            return None
        if self._task is None or self._task.done():
            self._task = self._flow.hass.async_create_task(self._action_task())
        return self._flow.async_show_progress(
            step_id=self._step_id,
            progress_action=self._result.name if self._result.name is not None else self._step_id,
            progress_task=self._task,
            description_placeholders=self._result.ph if self._result.ph is not None else {},
        )


class BleAdvBlinkProgressFlow(BleAdvProgressFlowBase):
    """Progress flow for blink task."""

    async def _action_task(self) -> None:
        await self._flow.async_blink_light()
        self._exit = True


class BleAdvPairProgressFlow(BleAdvProgressFlowBase):
    """Progress flow for pair task."""

    async def _action_task(self) -> None:
        await self._flow.async_pair_all()
        self._exit = True


class BleAdvWaitProgress(BleAdvProgressFlowBase):
    """Base Progress Flow based on wait / update."""

    def __init__(self, flow: BleAdvConfigFlow, step_id: str, max_duration: float) -> None:
        super().__init__(flow, step_id, {})
        self._stop_time: datetime | None = None
        self._max_duration: float = max_duration
        self._setup_stop_time(max_duration)

    def _setup_stop_time(self, max_duration: float | None = None) -> None:
        if max_duration is not None:
            self._stop_time = datetime.now() + timedelta(seconds=max_duration)

    @abstractmethod
    def _evaluate(self) -> _ActionResult:
        """Evaluate the updated name / placeholders. Called every 0.1s to compute the updated _ActionResult."""

    async def _action_task(self) -> None:
        """Task for Evaluation every 0.1s. Return if name / placeholders changed."""
        while self._stop_time is None or datetime.now() < self._stop_time:
            if self._update_action_result(self._evaluate()):
                return
            await asyncio.sleep(0.1)
        self._exit = True


class BleAdvWaitConfigProgress(BleAdvWaitProgress):
    """Listen to configurations."""

    def __init__(self, flow: BleAdvConfigFlow, step_id: str, max_duration: float, wait_agg: float = 0) -> None:
        super().__init__(flow, step_id, max_duration)
        self._wait_agg = wait_agg
        self._agg_mode: bool = False
        self.configs: dict[str, list[_CodecConfig]] = {}
        self._flow.coordinator.start_listening(max_duration + wait_agg)

    def _add_config(self, adapter_id: str, conf: _CodecConfig) -> None:
        confs = self.configs.setdefault(adapter_id, [])
        if conf not in confs:
            confs.append(conf)

    def _evaluate(self) -> _ActionResult:
        coord = self._flow.coordinator
        for adapter_id, codec_id, match_id, config in coord.listened_decoded_confs:
            self._add_config(adapter_id, _CodecConfig(match_id, config.id, config.index))
            self._add_config(adapter_id, _CodecConfig(codec_id, config.id, config.index))
        coord.listened_decoded_confs.clear()

        if not self.configs:
            return _ActionResult(ph={"max_seconds": str(self._max_duration)})
        if not self._agg_mode:
            self._agg_mode = True
            self._setup_stop_time(self._wait_agg)
        return _ActionResult(name="agg_config", ph={})


def _format_advs(raw_advs: list[bytes]) -> str:
    return "\n    " + "\n    ".join([x.hex().upper() for x in raw_advs]) if raw_advs else "\n    None"


class BleAdvWaitRawAdvProgress(BleAdvWaitProgress):
    """Listen to raw ADVs."""

    def __init__(self, flow: BleAdvConfigFlow, step_id: str, max_duration: float) -> None:
        super().__init__(flow, step_id, max_duration)
        self.raw_advs: list[bytes] = []
        self._flow.coordinator.start_listening(max_duration)

    def _evaluate(self) -> _ActionResult:
        coord = self._flow.coordinator
        for raw_adv in coord.listened_raw_advs:
            if raw_adv not in self.raw_advs:
                self.raw_advs.append(raw_adv)
        coord.listened_raw_advs.clear()
        return _ActionResult(ph={"advs": _format_advs(self.raw_advs)})


class BleAdvConfigHandler:
    """Handle configs."""

    def __init__(self, configs: dict[str, list[_CodecConfig]] | None = None) -> None:
        self._configs: dict[str, list[_CodecConfig]] = {} if configs is None else configs
        self._selected_adapter_id: str | None = None
        self._selected_config: int = 0

    def __repr__(self) -> str:
        return repr(self._configs)

    def reset_selected(self) -> None:
        """Clear selection."""
        self._selected_config = 0
        self._selected_adapter_id = None

    @property
    def adapters(self) -> list[str]:
        """Return the list of adapter_id."""
        return list(self._configs.keys())

    def selected_adapter(self) -> str:
        """Return the selected adapter if any, else the first one. Can only be called if 'has_confs' is True."""
        if self._selected_adapter_id in self._configs:
            return self._selected_adapter_id
        return self.adapters[0]

    def is_empty(self) -> bool:
        """Return True if no conf."""
        return not bool(self._configs)

    def has_next(self) -> bool:
        """Return True if there are still conf in selected."""
        return (self._selected_config + 1) < len(self.selected_confs())

    def next(self) -> _CodecConfig:
        """Return the next conf if any."""
        self._selected_config += 1
        return self.selected_confs()[self._selected_config]

    def set_selected_adapter(self, adapter_id: str) -> None:
        """Set adapter as selected."""
        self._selected_adapter_id = adapter_id
        self._selected_config = 0

    def selected_confs(self) -> list[_CodecConfig]:
        """Return the confs filtered by selected_adapter_id."""
        return self._configs[self.selected_adapter()]

    def selected(self) -> _CodecConfig:
        """Return the selected conf."""
        return self.selected_confs()[self._selected_config]

    def placeholders(self) -> dict[str, str]:
        """Return the Placeholders for the selected conf."""
        conf = self.selected()
        nb: str = str(self._selected_config + 1)
        tot: str = str(len(self.selected_confs()))
        return {"nb": nb, "tot": tot, "codec": conf.codec_id, "id": f"0x{conf.id:X}", "index": str(conf.index)}


class BleAdvConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BLE ADV."""

    VERSION = CONF_LAST_VERSION

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._confs: BleAdvConfigHandler = BleAdvConfigHandler()
        self._progress: BleAdvProgressFlowBase | None = None

        self._data: dict[str, Any] = {}
        self._finalize_requested: bool = False
        self._last_inject: dict[str, Any] = {CONF_RAW: "", CONF_INTERVAL: 20, CONF_REPEATS: 9}

        self._diags: list[str] = []
        self._return_step_after_diag: str = ""

    def _add_diag(self, msg: str, log_level: int = logging.DEBUG) -> None:
        _LOGGER.log(log_level, msg)
        self._diags.append(f"{datetime.now()} - {msg}")

    async def _diagnostic_dump(self) -> dict[str, Any]:
        """Diagnostic dump."""
        return {**await self.coordinator.full_diagnostic_dump(), "flow": self._diags}

    def _remote_conf_placeholders(self) -> dict[str, str]:
        conf = self._data[CONF_REMOTE]
        return {"codec": conf[CONF_CODEC_ID], "id": f"0x{conf[CONF_FORCED_ID]:X}", "index": str(conf[CONF_INDEX])}

    def async_update_progress(self, progress: float) -> None:
        """Backward compatibility to avoid the need for user to upgrade their HA, as this feature is a Nice to Have."""
        if hasattr(ConfigFlow, "async_update_progress"):
            super().async_update_progress(progress)  # type: ignore[none]

    def _get_device(self, name: str, adapter_id: str, config: _CodecConfig, duration: int | None = None) -> BleAdvBaseDevice:
        codec: BleAdvCodec = self.coordinator.codecs[config.codec_id]
        duration = duration if duration is not None else codec.duration
        return BleAdvBaseDevice(self.coordinator, name, config.codec_id, [adapter_id], codec.repeat, codec.interval, duration, config)

    async def async_blink_light(self) -> None:
        """Blink."""
        self._add_diag(f"Start blink - {self._confs.selected_adapter()} / {self._confs.selected()}.")
        tmp_device: BleAdvBaseDevice = self._get_device("cf", self._confs.selected_adapter(), self._confs.selected())
        on_cmd = BleAdvEntAttr([ATTR_ON], {ATTR_ON: True}, LIGHT_TYPE, 0)
        off_cmd = BleAdvEntAttr([ATTR_ON], {ATTR_ON: False}, LIGHT_TYPE, 0)
        self.async_update_progress(0)
        await tmp_device.advertise(on_cmd)
        await asyncio.sleep(1)
        self.async_update_progress(0.25)
        await tmp_device.advertise(off_cmd)
        await asyncio.sleep(1)
        self.async_update_progress(0.50)
        await tmp_device.advertise(on_cmd)
        await asyncio.sleep(1)
        self.async_update_progress(0.75)
        await tmp_device.advertise(off_cmd)
        await asyncio.sleep(1)
        self.async_update_progress(1)
        self._add_diag("Stop blink.")

    async def async_pair_all(self) -> None:
        """Pair."""
        self._add_diag(f"Start pair - {self._confs.selected_adapter()} / {self._confs.selected_confs()}.")
        pair_cmd = BleAdvEntAttr([ATTR_CMD], {ATTR_CMD: ATTR_CMD_PAIR}, DEVICE_TYPE, 0)
        adapter_id = self._confs.selected_adapter()
        for i, config in enumerate(self._confs.selected_confs()):
            tmp_device: BleAdvBaseDevice = self._get_device(f"cf{i}", adapter_id, config, 300)
            await tmp_device.advertise(pair_cmd)
            await asyncio.sleep(0.3)
        await asyncio.sleep(2)
        self._add_diag("Stop pair.")

    def _create_api_view(self, response: web.Response) -> str:
        async def api_resp() -> web.Response:
            await self.hass.config_entries.flow.async_configure(flow_id=self.flow_id, user_input={})
            return response

        api_view = BleAdvConfigView(self.flow_id, api_resp)
        self.hass.http.register_view(api_view)
        return api_view.full_url

    def _create_api_json_view(self, name: str, data: dict[str, Any]) -> str:
        return self._create_api_view(
            web.Response(
                body=json.dumps(data, indent=2, cls=ExtendedJSONEncoder),
                content_type="application/json",
                headers={"Content-Disposition": f'attachment; filename="{name}.json"'},
            )
        )

    async def async_step_user(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the user step to setup a device."""
        self._add_diag("Config flow 'user' started.")
        self.coordinator: BleAdvCoordinator = await get_coordinator(self.hass)
        if not self.coordinator.has_available_adapters():
            return self.async_abort(reason="no_adapters")
        return self.async_show_menu(step_id="user", menu_options=["wait_config", "manual", "pair", "tools"])

    async def async_step_tools(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Tooling Step."""
        self._return_step_after_diag = "tools"
        return self.async_show_menu(step_id="tools", menu_options=["diag", "inject", "listen_raw", "decode_raw"])

    async def async_step_diag(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Diagnostic step."""
        if user_input is not None:
            return self.async_external_step_done(next_step_id=self._return_step_after_diag)
        return self.async_external_step(url=self._create_api_json_view("ble_adv_diag", await self._diagnostic_dump()))

    async def async_step_inject(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manual injection step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._last_inject = user_input
            if not (errors := await self.coordinator.inject_raw({**user_input, CONF_DURATION: 800, CONF_DEVICE_QUEUE: "man"})):
                return await self.async_step_inject_res()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ADAPTER_ID, default=self._last_inject.get(CONF_ADAPTER_ID, None)): vol.In(self.coordinator.get_adapter_ids()),
                vol.Required(CONF_RAW, default=self._last_inject[CONF_RAW]): selector.TextSelector(selector.TextSelectorConfig()),
                vol.Optional(CONF_INTERVAL, default=self._last_inject[CONF_INTERVAL]): selector.NumberSelector(
                    selector.NumberSelectorConfig(step=10, min=10, max=150, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(CONF_REPEAT, default=self._last_inject[CONF_REPEAT]): selector.NumberSelector(
                    selector.NumberSelectorConfig(step=1, min=1, max=20, mode=selector.NumberSelectorMode.BOX)
                ),
            }
        )

        return self.async_show_form(step_id="inject", data_schema=data_schema, errors=errors)

    async def async_step_inject_res(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manual injection result step."""
        return self.async_show_menu(step_id="inject_res", menu_options=["inject", "tools"])

    async def async_step_listen_raw(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Listen to all BLE ADV messages."""
        if self._progress is None:
            self._progress = BleAdvWaitRawAdvProgress(self, "listen_raw", WAIT_MAX_SECONDS)
        if (flow_res := self._progress.next()) is not None:
            return flow_res
        self._raw_advs = cast("BleAdvWaitRawAdvProgress", self._progress).raw_advs
        self._progress = None
        return self.async_show_progress_done(next_step_id="listen_raw_res")

    async def async_step_listen_raw_res(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Listen to all BLE ADV messages result step."""
        return self.async_show_menu(
            step_id="listen_raw_res", menu_options=["listen_raw", "tools"], description_placeholders={"advs": _format_advs(self._raw_advs)}
        )

    async def async_step_decode_raw(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Decode Raw BLE ADV messages."""
        if user_input is not None:
            self._decode_res = await self.coordinator.decode_raw(user_input[CONF_RAW])
            return await self.async_step_decode_raw_res()
        data_schema = vol.Schema({vol.Required(CONF_RAW, default=self._last_inject[CONF_RAW]): selector.TextSelector(selector.TextSelectorConfig())})
        return self.async_show_form(step_id="decode_raw", data_schema=data_schema)

    async def async_step_decode_raw_res(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Decode BLE ADV messages result step."""
        conf = '\n    ("' + '",\n    "'.join(self._decode_res) + '")'
        return self.async_show_menu(step_id="decode_raw_res", menu_options=["decode_raw", "tools"], description_placeholders={"conf": conf})

    async def async_step_manual(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manual input step."""
        if user_input is not None:
            codec = _CodecConfig(user_input[CONF_CODEC_ID], int(f"0x{user_input[CONF_FORCED_ID]}", 16), int(user_input[CONF_INDEX]))
            self._confs = BleAdvConfigHandler({user_input[CONF_ADAPTER_ID]: [codec]})
            self._add_diag(f"Step Manual - confs: {self._confs}")
            return await self.async_step_blink()

        self._add_diag("Step Manual")
        data_schema = vol.Schema(
            {
                vol.Required(CONF_ADAPTER_ID): vol.In(self.coordinator.get_adapter_ids()),
                vol.Required(CONF_CODEC_ID): vol.In(list(self.coordinator.codecs.keys())),
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
            codecs = [_CodecConfig(codec_id, gen_id, 1) for codec_id in PHONE_APPS[user_input[CONF_PHONE_APP]]]
            self._confs = BleAdvConfigHandler({user_input[CONF_ADAPTER_ID]: codecs})
            self._add_diag(f"Step Pair - confs: {self._confs}")
            return await self.async_step_wait_pair()

        self._add_diag("Step Pair")
        data_schema = vol.Schema(
            {
                vol.Required(CONF_ADAPTER_ID): vol.In(self.coordinator.get_adapter_ids()),
                vol.Required(CONF_PHONE_APP): vol.In(list(PHONE_APPS.keys())),
            }
        )
        return self.async_show_form(step_id="pair", data_schema=data_schema)

    async def async_step_wait_pair(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Effective Pair Step."""
        if self._progress is None:
            self._progress = BleAdvPairProgressFlow(self, "wait_pair", {})
        if (flow_res := self._progress.next()) is not None:
            return flow_res
        self._progress = None
        return self.async_show_progress_done(next_step_id="confirm_pair")

    async def async_step_confirm_pair(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the confirm that pair worked OK."""
        return self.async_show_menu(step_id="confirm_pair", menu_options=["pair", "confirm_no_abort", "blink"])

    async def async_step_wait_config(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Wait for listened config Step."""
        if self._progress is None:
            self._progress = BleAdvWaitConfigProgress(self, "wait_config", WAIT_MAX_SECONDS, 3)
        if (flow_res := self._progress.next()) is not None:
            return flow_res
        self._confs = BleAdvConfigHandler(cast("BleAdvWaitConfigProgress", self._progress).configs)
        self._add_diag(f"Wait Config - Raw advs: {[x.hex().upper() for x in self.coordinator.listened_raw_advs]}")
        self._add_diag(f"Wait Config - Confs: {self._confs}")
        self._progress = None
        return self.async_show_progress_done(next_step_id="no_config" if self._confs.is_empty() else "choose_adapter")

    async def async_step_no_config(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """No Config found, abort or retry."""
        return self.async_show_menu(step_id="no_config", menu_options=["wait_config", "abort_config", "open_issue"])

    async def async_step_abort_config(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """No Config found, abort."""
        return self.async_abort(reason="no_config")

    async def async_step_choose_adapter(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Choose adapter."""
        if len(self._confs.adapters) != 1:
            if user_input is not None:
                self._confs.set_selected_adapter(user_input[CONF_ADAPTER_ID])
                return await self.async_step_blink()

            self._add_diag("Selecting adapter.")
            data_schema = vol.Schema({vol.Required(CONF_ADAPTER_ID): vol.In(self._confs.adapters)})
            return self.async_show_form(step_id="choose_adapter", data_schema=data_schema)

        return await self.async_step_blink()

    async def async_step_blink(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Blink Step."""
        if self._progress is None:
            self._progress = BleAdvBlinkProgressFlow(self, "blink", self._confs.placeholders())
        if (flow_res := self._progress.next()) is not None:
            return flow_res
        self._progress = None
        return self.async_show_progress_done(next_step_id="confirm")

    async def async_step_confirm(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Confirm choice Step."""
        varying_choices = ["confirm_no_another"] if self._confs.has_next() else ["confirm_no_abort", "open_issue"]
        opts = ["confirm_yes", *varying_choices, "confirm_retry_last", "confirm_retry_all"]
        return self.async_show_menu(step_id="confirm", menu_options=opts, description_placeholders=self._confs.placeholders())

    async def async_step_open_issue(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Open issue Step."""
        self._return_step_after_diag = "open_issue"
        return self.async_show_menu(step_id="open_issue", menu_options=["diag"])

    async def async_step_confirm_yes(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Confirm YES Step."""
        conf = self._confs.selected()
        await self.async_set_unique_id(f"{conf.codec_id}##0x{conf.id:X}##{conf.index:d}", raise_on_progress=False)
        self._abort_if_unique_id_configured()
        codec: BleAdvCodec = self.coordinator.codecs[conf.codec_id]
        self._data = {
            CONF_DEVICE: {CONF_CODEC_ID: conf.codec_id, CONF_FORCED_ID: conf.id, CONF_INDEX: conf.index},
            CONF_LIGHTS: [{}] * CONF_MAX_ENTITY_NB,
            CONF_FANS: [{}] * CONF_MAX_ENTITY_NB,
            CONF_TECHNICAL: {
                CONF_ADAPTER_IDS: [self._confs.selected_adapter()],
                CONF_DURATION: codec.duration,
                CONF_INTERVAL: codec.interval,
                CONF_REPEATS: codec.repeat,
                CONF_FORCE_SEND: False,
            },
        }
        return await self.async_step_configure()

    async def async_step_confirm_no_another(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Confirm NO, try another Step."""
        self._confs.next()
        return await self.async_step_blink()

    async def async_step_confirm_no_abort(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Confirm NO, abort Step."""
        return self.async_abort(reason="no_config")

    async def async_step_confirm_retry_last(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Confirm Retry Step."""
        return await self.async_step_blink()

    async def async_step_confirm_retry_all(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Confirm Retry ALL Step."""
        self._confs.reset_selected()
        return await self.async_step_choose_adapter()

    async def async_step_configure(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Configure choice Step."""
        opts = ["config_entities", "config_remote", "config_technical", "finalize"]
        return self.async_show_menu(step_id="configure", menu_options=opts)

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

        codec: BleAdvCodec = self.coordinator.codecs[self._data[CONF_DEVICE][CONF_CODEC_ID]]
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
        self._progress = None
        if CONF_REMOTE in self._data and CONF_CODEC_ID in self._data[CONF_REMOTE]:
            return self.async_show_menu(
                step_id="config_remote",
                menu_options=["config_remote_delete", "config_remote_update", "wait_config_remote", "configure"],
                description_placeholders=self._remote_conf_placeholders(),
            )
        return await self.async_step_wait_config_remote()

    async def async_step_config_remote_delete(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Remove Remote."""
        self._data[CONF_REMOTE] = {}
        return await self.async_step_configure()

    async def async_step_wait_config_remote(self, _: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Configure New Remote."""
        if self._progress is None:
            self._progress = BleAdvWaitConfigProgress(self, "wait_config_remote", WAIT_MAX_SECONDS)
        if (flow_res := self._progress.next()) is not None:
            return flow_res
        self._confs = BleAdvConfigHandler(cast("BleAdvWaitConfigProgress", self._progress).configs)
        self._progress = None
        if self._confs.is_empty():
            return self.async_show_progress_done(next_step_id="configure")
        config = self._confs.selected()  # get the first found adapter/config
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
        avail_adapters = self.coordinator.get_adapter_ids()
        def_adapters = [adapt for adapt in def_tech[CONF_ADAPTER_IDS] if adapt in avail_adapters]
        data_schema = vol.Schema(
            {
                vol.Required(CONF_ADAPTER_IDS, default=def_adapters): self._get_multi_selector(CONF_ADAPTER_IDS, avail_adapters),
                vol.Optional(CONF_DURATION, default=def_tech[CONF_DURATION]): selector.NumberSelector(
                    selector.NumberSelectorConfig(step=50, min=100, max=2000, mode=selector.NumberSelectorMode.SLIDER)
                ),
                vol.Optional(CONF_FORCE_SEND, default=def_tech[CONF_FORCE_SEND]): bool,
                vol.Optional(CONF_INTERVAL, default=def_tech[CONF_INTERVAL]): selector.NumberSelector(
                    selector.NumberSelectorConfig(step=10, min=10, max=150, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(CONF_REPEATS, default=def_tech[CONF_REPEATS]): selector.NumberSelector(
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
        self._add_diag("'Reconfigure' flow started")
        self.coordinator = await get_coordinator(self.hass)
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
