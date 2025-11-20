"""Coordinator tests."""

# ruff: noqa: S101
import asyncio
from unittest import mock

from ble_adv.adapters import BleAdvQueueItem
from ble_adv.codecs.models import BleAdvAdvertisement, BleAdvCodec, BleAdvConfig, BleAdvEncCmd
from ble_adv.const import CONF_ADAPTER_ID, CONF_DEVICE_QUEUE, CONF_DURATION, CONF_INTERVAL, CONF_RAW, CONF_REPEAT
from ble_adv.coordinator import BleAdvBaseDevice, BleAdvCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.loader import Manifest

from tests.conftest import MockEspProxy


class _Codec(mock.MagicMock):
    decode_adv = mock.MagicMock(return_value=(BleAdvEncCmd(0x10), BleAdvConfig(1, 0)))
    encode_advs = mock.MagicMock(return_value=[BleAdvAdvertisement(0xFF, b"bouhbouh")])
    enc_to_ent = mock.MagicMock(return_value=[])
    ign_duration = 2
    consolidate = mock.MagicMock(return_value=BleAdvEncCmd(0x20))


class _Device(BleAdvBaseDevice):
    def __init__(self, coord: BleAdvCoordinator, name: str, codec_id: str, adapter_ids: list[str]) -> None:
        super().__init__(coord, name, codec_id, adapter_ids, 1, 10, 1000, BleAdvConfig(1, 1))


def _get_codecs() -> dict[str, BleAdvCodec]:
    cod1 = _Codec()
    cod1.codec_id = "cod1"
    cod1.match_id = "cod1"
    cod2 = _Codec()
    cod2.codec_id = "cod2/a"
    cod2.match_id = "cod2"
    return {cod1.codec_id: cod1, cod2.codec_id: cod2}


async def test_coordinator(hass: HomeAssistant, coord: BleAdvCoordinator) -> None:
    """Test coordinator."""
    coord.codecs = _get_codecs()
    assert list(coord.codecs.keys()) == ["cod1", "cod2/a"]
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
    await coord._esp_bt_manager.adapters["esp-test"].drain()  # noqa: SLF001
    coord.remove_device(dev1)

    dev2 = _Device(coord, "dev1", "cod1", ["other"])
    coord.add_device(dev2)
    adv2 = BleAdvAdvertisement(0xFF, b"2dt2", 0x1A)
    await coord.handle_raw_adv("esp-test", "", adv2.to_raw())
    coord.remove_device(dev2)
    assert coord.has_available_adapters()


async def test_device_pub(hass: HomeAssistant, coord: BleAdvCoordinator) -> None:
    """Test device publication."""
    codecs = _get_codecs()
    cod1: BleAdvCodec = codecs["cod1"]
    coord.codecs = _get_codecs()
    dev1 = _Device(coord, "dev1", "cod1", ["esp-test"])
    dev1.add_listener("cod1", BleAdvConfig(1, 0))
    assert dev1.config.prev_cmd is None
    coord.add_device(dev1)
    t1 = MockEspProxy(hass, "esp-test")
    await t1.setup()
    base_adv1 = b"base_adv_nb1"
    adv1 = BleAdvAdvertisement(0xFF, base_adv1, 0x1A)
    await coord.handle_raw_adv("esp-test", "", bytes(adv1.to_raw()))
    cod1.consolidate.assert_called_once_with(BleAdvEncCmd(0x10), None)  # type: ignore[mock]
    cod1.consolidate.reset_mock()  # type: ignore[mock]
    recv1 = coord._dec_last_advs.get(base_adv1)  # noqa: SLF001
    assert recv1 is not None
    assert recv1.pub_devices == {"dev1"}
    assert recv1.enc_cmd.cmd == 0x10
    assert dev1.config.prev_cmd == BleAdvEncCmd(0x10)
    dev1.config.prev_cmd = BleAdvEncCmd(0x20)
    base_adv2 = b"base_adv_nb2"
    adv2 = BleAdvAdvertisement(0xFF, base_adv2, 0x1A)
    await coord.handle_raw_adv("esp-test", "", bytes(adv2.to_raw()))
    cod1.consolidate.assert_called_once_with(BleAdvEncCmd(0x10), BleAdvEncCmd(0x20))  # type: ignore[mock]
    recv2 = coord._dec_last_advs.get(base_adv2)  # noqa: SLF001
    assert recv2 is not None
    assert dev1.config.prev_cmd == BleAdvEncCmd(0x10)


async def test_listening(coord: BleAdvCoordinator) -> None:
    """Test listening mode."""
    coord.codecs = _get_codecs()
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


async def test_ign_cid(coord: BleAdvCoordinator) -> None:
    """Test Ignored Company IDs."""
    coord.ign_cids = {0x3412}
    coord.start_listening(0.1)
    raw_adv = bytes([0x03, 0xFF, 0x12, 0x34, 0x12, 0x34, 0x12, 0x34])
    await coord.handle_raw_adv("aaa", "mac1", raw_adv)
    assert coord.listened_raw_advs == []


async def test_ign_mac(coord: BleAdvCoordinator) -> None:
    """Test Ignored Macs."""
    coord.ign_macs = {"mac1"}
    coord.start_listening(0.1)
    raw_adv = bytes([0x03, 0xFF, 0x12, 0x34, 0x12, 0x34, 0x12, 0x34])
    await coord.handle_raw_adv("aaa", "mac1", raw_adv)
    assert coord.listened_raw_advs == []


async def test_inject_raw(hass: HomeAssistant, coord: BleAdvCoordinator) -> None:
    """Test Raw Injection."""
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


async def test_decode_raw(coord: BleAdvCoordinator) -> None:
    """Test Raw Decoding."""
    coord.codecs = {"cod1": _Codec()}
    res = coord.decode_raw("123")
    assert res == ["Cannot convert to bytes"]
    res = coord.decode_raw("1234")
    assert res == ["cod1", "1234", "cmd: 0x10, param: 0x00, args: [0,0,0]", "id: 0x00000001, index: 0, tx: 0, seed: 0x0000", ""]
    coord.codecs.clear()
    res = coord.decode_raw("1234")
    assert res == ["Could not be decoded by any known codec"]


async def test_full_diagnostics(coord: BleAdvCoordinator) -> None:
    """Test Full Diagnostics."""

    class _MockIntegration:
        manifest = Manifest({"domain": "ble_adv", "version": "1.0"})

    async def _mock_async_get_integration(_: HomeAssistant, __: str) -> _MockIntegration:
        return _MockIntegration()

    with mock.patch("ble_adv.coordinator.async_get_integration", side_effect=_mock_async_get_integration):
        diag = await coord.full_diagnostic_dump()
        assert len(diag["coordinator"]) > 0
