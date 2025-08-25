"""Config flow tests."""

# ruff: noqa: S101
import asyncio
from unittest import mock

from aiohttp import web
from ble_adv.codecs.models import BleAdvConfig
from ble_adv.config_flow import BleAdvConfigView, BleAdvMultiTaskProgress, _CodecConfig, _MatchingAllCallback
from homeassistant.config_entries import ConfigFlow
from homeassistant.core import HomeAssistant


def test_codec_config() -> None:
    """Test codec config."""
    conf = _CodecConfig("codec_id", 12, 1)
    assert repr(conf) == "codec_id - 0xC - 1"


async def test_matching_callback() -> None:
    """Test _MatchingAllCallback."""
    clbk = mock.AsyncMock()
    mc = _MatchingAllCallback(clbk)
    assert await mc.handle("a", "b", "c", BleAdvConfig(1, 1), [])
    clbk.assert_called_once_with("a", "b", "c", BleAdvConfig(1, 1))


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


async def test_multi_task_progress(hass: HomeAssistant) -> None:
    """Test BleAdvMultiTaskProgress."""
    flow = ConfigFlow()
    flow.hass = hass
    mtp = BleAdvMultiTaskProgress(flow, "step")
    mtp.add_task("aaa", asyncio.sleep(0.01), {})
    mtp.add_task("bbb", asyncio.sleep(0.01), {"tt": "tt"})
    cfrd = dict(cfr) if (cfr := mtp.next()) is not None else {}
    assert cfrd["progress_action"] == "aaa"
    assert cfrd["description_placeholders"] == {}
    await asyncio.sleep(0.1)
    cfrd = dict(cfr) if (cfr := mtp.next()) is not None else {}
    assert cfrd["progress_action"] == "bbb"
    assert cfrd["description_placeholders"] == {"tt": "tt"}
    await asyncio.sleep(0.1)
    assert mtp.next() is None
