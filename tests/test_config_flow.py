"""Config flow tests."""

# ruff: noqa: S101
import asyncio
from unittest import mock

import pytest
from aiohttp import web
from ble_adv.codecs.models import BleAdvConfig
from ble_adv.config_flow import (
    BleAdvConfigFlow,
    BleAdvConfigHandler,
    BleAdvConfigView,
    BleAdvPairProgressFlow,
    BleAdvTestFanProgressFlow,
    BleAdvTestLightProgressFlow,
    BleAdvWaitConfigProgress,
    BleAdvWaitRawAdvProgress,
    _CodecConfig,
)
from ble_adv.const import CONF_ADAPTER_ID, CONF_PHONE_APP
from ble_adv.coordinator import BleAdvCoordinator
from homeassistant.core import HomeAssistant


def test_codec_config() -> None:
    """Test codec config."""
    conf = _CodecConfig("codec_id", 12, 1)
    assert repr(conf) == "codec_id - 0xC - 1"
    conf2 = _CodecConfig("codec_id", 12, 2)
    assert conf != conf2
    assert hash(conf) != 0


async def test_api_view() -> None:
    """Test BleAdvConfigView."""
    resp = web.Response(body="toto")

    async def _get_resp() -> web.Response:
        return resp

    av = BleAdvConfigView("flow", _get_resp)
    assert av.full_url == "/api/ble_adv/config_flow/flow"
    assert await av.get(None, "wrong_flow") == av.NOT_FOUND_RESP  # type: ignore[none]
    assert await av.get(None, "flow") == resp  # type: ignore[none]
    assert await av.get(None, "flow") == av.NOT_FOUND_RESP  # type: ignore[none]


async def test_light_progress(hass: HomeAssistant) -> None:
    """Test BleAdvTestLightProgressFlow."""
    flow = BleAdvConfigFlow()
    flow.async_test_light = mock.AsyncMock()
    flow.hass = hass
    mtp = BleAdvTestLightProgressFlow(flow, "step", {})
    mtp.next()
    flow.async_test_light.assert_called_once()
    assert mtp.next() is None


async def test_fan_progress(hass: HomeAssistant) -> None:
    """Test BleAdvTestFanProgressFlow."""
    flow = BleAdvConfigFlow()
    flow.async_test_fan = mock.AsyncMock()
    flow.hass = hass
    mtp = BleAdvTestFanProgressFlow(flow, "step", {})
    mtp.next()
    flow.async_test_fan.assert_called_once()
    assert mtp.next() is None


async def test_pair_progress(hass: HomeAssistant) -> None:
    """Test BleAdvPairProgressFlow."""
    flow = BleAdvConfigFlow()
    flow.async_pair_all = mock.AsyncMock()
    flow.hass = hass
    mtp = BleAdvPairProgressFlow(flow, "step", {})
    mtp.next()
    flow.async_pair_all.assert_called_once()
    assert mtp.next() is None


async def test_wait_config_progress(hass: HomeAssistant) -> None:
    """Test BleAdvWaitConfigProgress."""
    flow = BleAdvConfigFlow()
    flow.hass = hass
    flow.coordinator = mock.Mock(spec=BleAdvCoordinator)
    flow.coordinator.listened_decoded_confs = []
    mtp = BleAdvWaitConfigProgress(flow, "wait_config", 0.3, 0.1)
    cfr = mtp.next()
    assert cfr is not None
    assert dict(cfr)["step_id"] == "wait_config"
    assert dict(cfr)["progress_action"] == "wait_config"
    assert dict(cfr)["description_placeholders"] == {"max_seconds": "0.3"}
    flow.coordinator.listened_decoded_confs = [("aaa", "a", "b", [], BleAdvConfig(0x10, 0))]
    cfr = mtp.next()
    assert cfr is not None
    assert dict(cfr)["progress_action"] == "agg_config"


async def test_wait_raw_adv_progress(hass: HomeAssistant) -> None:
    """Test BleAdvWaitRawAdvProgress."""
    flow = BleAdvConfigFlow()
    flow.hass = hass
    flow.coordinator = mock.Mock(spec=BleAdvCoordinator)
    flow.coordinator.listened_raw_advs = []
    mtp = BleAdvWaitRawAdvProgress(flow, "listen_raw", 0.2)
    cfr = mtp.next()
    assert cfr is not None
    assert dict(cfr)["step_id"] == "listen_raw"
    assert dict(cfr)["progress_action"] == "listen_raw"
    assert dict(cfr)["description_placeholders"] == {"advs": "\n    None"}
    flow.coordinator.listened_raw_advs = [bytes([0x12, 0x34])]
    flow.coordinator.decode_raw = mock.Mock(return_value=["cod1", "1234"])
    cfr = mtp.next()
    assert cfr is not None
    assert dict(cfr)["description_placeholders"] == {"advs": '\n    ("cod1","1234")'}
    assert flow.coordinator.listened_raw_advs == []
    flow.coordinator.listened_raw_advs = [bytes([0x56, 0x78])]
    flow.coordinator.decode_raw = mock.Mock(return_value=["not decoded"])
    cfr = mtp.next()
    assert cfr is not None
    assert dict(cfr)["description_placeholders"] == {"advs": "\n    1234\n    5678"}
    await asyncio.sleep(0.1)
    cfr = mtp.next()
    assert cfr is not None
    await asyncio.sleep(0.3)
    cfr = mtp.next()
    assert cfr is None


async def test_config_handler() -> None:
    """Test BleAdvConfigHandler."""
    ch = BleAdvConfigHandler()
    assert ch.is_empty()
    assert repr(ch) == "{}"
    with pytest.raises(IndexError):
        ch.selected_adapter()
    with pytest.raises(IndexError):
        ch.selected()
    with pytest.raises(IndexError):
        ch.next()
    with pytest.raises(IndexError):
        assert not ch.has_next()
    cf1 = _CodecConfig("b", 0xAA, 1)
    ch = BleAdvConfigHandler({"a": [cf1]})
    assert ch.selected_adapter() == "a"
    assert ch.selected() == cf1
    assert ch.selected_confs() == [cf1]
    assert not ch.has_next()
    with pytest.raises(IndexError):
        ch.next()
    ch.reset_selected()
    assert ch.selected_adapter() == "a"
    cf2 = _CodecConfig("b", 0xBB, 1)
    cf3 = _CodecConfig("b", 0xCC, 1)
    ch = BleAdvConfigHandler({"a": [cf1, cf2], "b": [cf3]})
    assert ch.selected_adapter() == "a"
    assert ch.selected_confs() == [cf1, cf2]
    assert ch.adapters == ["a", "b"]
    ch.set_selected_adapter("c")
    assert ch.selected_adapter() == "a"
    ch.set_selected_adapter("b")
    assert ch.selected_adapter() == "b"
    assert ch.selected_confs() == [cf3]
    assert ch.selected() == cf3
    assert ch.placeholders() == {"nb": "1", "tot": "1", "codec": "b", "id": "0xCC", "index": "1"}


async def test_config_flow(hass: HomeAssistant, coord: BleAdvCoordinator) -> None:
    """Test main config flow."""
    flow = BleAdvConfigFlow()
    flow.hass = hass
    flow.coordinator = coord
    flow.WAIT_TEST_LIGHT = 0.1
    flow.WAIT_TEST_FAN = 0.1
    await flow.async_step_user()
    await flow.async_step_pair({CONF_PHONE_APP: "Fan Lamp Pro", CONF_ADAPTER_ID: "test"})
    await flow.async_test_light()
    await flow.async_test_fan()
