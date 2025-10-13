"""Coordinator tests."""

# ruff: noqa: S101
import asyncio
from unittest import mock

from ble_adv.adapters import BleAdvQueueItem
from ble_adv.codecs.models import BleAdvAdvertisement, BleAdvCodec, BleAdvConfig, BleAdvEncCmd
from ble_adv.const import CONF_ADAPTER_ID, CONF_DEVICE_QUEUE, CONF_DURATION, CONF_INTERVAL, CONF_RAW, CONF_REPEAT
from ble_adv.coordinator import BleAdvBaseDevice, BleAdvCoordinator
from homeassistant.core import HomeAssistant

from tests.conftest import MockEspProxy


class _Codec(mock.MagicMock):
    decode_adv = mock.MagicMock(return_value=(BleAdvEncCmd(0x10), BleAdvConfig(1, 0)))
    encode_advs = mock.MagicMock(return_value=[BleAdvAdvertisement(0xFF, b"bouhbouh")])
    enc_to_ent = mock.MagicMock(return_value=[])
    ign_duration = 2


class _Device(BleAdvBaseDevice):
    def __init__(self, coord: BleAdvCoordinator, name: str, codec_id: str, adapter_ids: list[str]) -> None:
        super().__init__(coord, name, codec_id, adapter_ids, 1, 10, 1000, BleAdvConfig(1, 1))


def _get_codecs() -> dict[str, BleAdvCodec]:
    cod1 = _Codec()
    cod1.codec_id = "cod1"
    cod1.match_id = "cod1"
    cod1.multi_advs = False
    cod2 = _Codec()
    cod2.codec_id = "cod2/a"
    cod2.match_id = "cod2"
    cod2.multi_advs = False
    return {cod1.codec_id: cod1, cod2.codec_id: cod2}


async def test_coordinator(hass: HomeAssistant) -> None:
    """Test coordinator."""
    codecs = _get_codecs()
    coord = BleAdvCoordinator(hass, codecs, ["hci"], 20000, [], [])
    assert list(coord.codecs.keys()) == ["cod1", "cod2/a"]
    await coord.async_init()
    assert coord.get_adapter_ids() == []
    dev1 = _Device(coord, "dev1", "cod1", ["esp-test"])
    coord.add_device(dev1)
    t1 = MockEspProxy(hass, "esp-test")
    await t1.setup()
    assert coord.get_adapter_ids() == ["esp-test"]
    adv = BleAdvAdvertisement(0xFF, b"dtwithminlen", 0x1A)
    qi = BleAdvQueueItem(0x10, 1, 100, 20, [adv.to_raw()], 2)
    await coord.advertise("not-exists", "q1", qi)
    await coord.advertise("esp-test", "q1", qi)
    await coord._esp_bt_manager.adapters["esp-test"].drain()  # noqa: SLF001
    assert t1.get_adv_calls() == [{"raw": adv.to_raw().hex()}]
    await coord.handle_raw_adv("esp-test", "", adv.to_raw())
    await t1.recv(adv.to_raw().hex())
    adv.ad_flag = 0x1B
    await coord.handle_raw_adv("esp-test", "", adv.to_raw())
    await coord.handle_raw_adv("esp-test", "", b"invalid_adv")
    await coord.advertise("esp-test", "q1", qi)
    coord.remove_device(dev1)

    dev2 = _Device(coord, "dev1", "cod1", ["other"])
    coord.add_device(dev2)
    adv2 = BleAdvAdvertisement(0xFF, b"2dt2", 0x1A)
    await coord.handle_raw_adv("esp-test", "", adv2.to_raw())
    coord.remove_device(dev2)
    assert coord.has_available_adapters()
    await coord.async_final()


async def test_listening(hass: HomeAssistant) -> None:
    """Test listening mode."""
    coord = BleAdvCoordinator(hass, _get_codecs(), ["hci"], 20000, [], [])
    coord.start_listening(0.1)
    assert coord.is_listening()
    raw_adv = bytes([0x03, 0xFF, 0x12, 0x34, 0x12, 0x34, 0x12, 0x34])
    await coord.handle_raw_adv("aaa", "mac", raw_adv)
    await coord.handle_raw_adv("bbb", "mac", raw_adv)
    await coord.handle_raw_adv("aaa", "mac", raw_adv)
    assert coord.listened_raw_advs == [raw_adv]
    assert coord.listened_decoded_confs == [("aaa", "cod1", "cod1", BleAdvConfig(1, 0)), ("aaa", "cod2/a", "cod2", BleAdvConfig(1, 0))]
    await asyncio.sleep(0.2)
    assert not coord.is_listening()


async def test_ign_cid(hass: HomeAssistant) -> None:
    """Test Ignored Company IDs."""
    coord = BleAdvCoordinator(hass, {}, ["hci"], 20000, [0x3412], [])
    coord.start_listening(0.1)
    raw_adv = bytes([0x03, 0xFF, 0x12, 0x34])
    await coord.handle_raw_adv("aaa", "mac1", raw_adv)
    assert coord.listened_raw_advs == []


async def test_ign_mac(hass: HomeAssistant) -> None:
    """Test Ignored Macs."""
    coord = BleAdvCoordinator(hass, {}, ["hci"], 20000, [], ["mac1"])
    coord.start_listening(0.1)
    raw_adv = bytes([0x03, 0xFF, 0x12, 0x34])
    await coord.handle_raw_adv("aaa", "mac1", raw_adv)
    assert coord.listened_raw_advs == []


async def test_inject_raw(hass: HomeAssistant) -> None:
    """Test Raw Injection."""
    coord = BleAdvCoordinator(hass, {}, ["hci"], 20000, [], [])
    await coord.async_init()
    coord.advertise = mock.AsyncMock()
    t1 = MockEspProxy(hass, "esp-test")
    await t1.setup()
    assert coord.get_adapter_ids() == ["esp-test"]
    params = {CONF_DURATION: 100, CONF_REPEAT: 1, CONF_INTERVAL: 10, CONF_DEVICE_QUEUE: "test"}
    errors = await coord.inject_raw({CONF_RAW: "1234", CONF_ADAPTER_ID: "esp-test", **params})
    assert errors == {}
    coord.advertise.assert_awaited_once_with("esp-test", "test", BleAdvQueueItem(None, 1, 100, 10, [bytes([0x12, 0x34])], 2))
    errors = await coord.inject_raw({CONF_RAW: "123", CONF_ADAPTER_ID: "esp-test", **params})
    assert errors == {CONF_RAW: "Cannot convert to bytes"}
    errors = await coord.inject_raw({CONF_RAW: "123a", CONF_ADAPTER_ID: "not exists", **params})
    assert errors == {CONF_ADAPTER_ID: "Should be in ['esp-test']"}
    await coord.async_final()


async def test_decode_raw(hass: HomeAssistant) -> None:
    """Test Raw Decoding."""
    coord = BleAdvCoordinator(hass, {"cod1": _Codec()}, ["hci"], 20000, [], [])
    res = coord.decode_raw("123")
    assert res == ["Cannot convert to bytes"]
    res = coord.decode_raw("1234")
    assert res == ["cod1", "1234", "cmd: 0x10, param: 0x00, args: [0,0,0]", "id: 0x00000001, index: 0, tx: 0, seed: 0x0000", ""]
    coord.codecs.clear()
    res = coord.decode_raw("1234")
    assert res == ["Could not be decoded by any known codec"]


async def test_full_diagnostics(hass: HomeAssistant) -> None:
    """Test Full Diagnostics."""
    coord = BleAdvCoordinator(hass, {}, ["hci"], 20000, [], [])
    diag = await coord.full_diagnostic_dump()
    assert len(diag["coordinator"]) > 0
