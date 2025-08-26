"""Coordinator tests."""

# ruff: noqa: S101
import asyncio
from unittest import mock

from ble_adv.adapters import BleAdvQueueItem
from ble_adv.codecs.models import BleAdvAdvertisement, BleAdvCodec, BleAdvConfig, BleAdvEntAttr
from ble_adv.coordinator import (
    BleAdvCoordinator,
    MatchingCallback,
)
from homeassistant.core import HomeAssistant

from tests.conftest import MockEspProxy


class _Codec(mock.MagicMock):
    decode_adv = mock.MagicMock(return_value=(0x10, BleAdvConfig(1, 0)))


class _MatchingClbk(MatchingCallback):
    async def handle(self, _: str, __: str, ___: BleAdvConfig, ____: list[BleAdvEntAttr]) -> None:
        pass


class _MatchingEx(MatchingCallback):
    async def handle(self, codec_id: str, adapter_id: str, config: BleAdvConfig, ent_attrs: list[BleAdvEntAttr]) -> None:
        await super().handle(codec_id, adapter_id, adapter_id, config, ent_attrs)


async def test_coordinator(hass: HomeAssistant) -> None:
    """Test coordinator."""
    cod1 = _Codec()
    cod2 = _Codec()
    codecs: dict[str, BleAdvCodec] = {"cod1": cod1, "cod2": cod2}
    coord = BleAdvCoordinator(hass, codecs, ["hci"], 20000, [], [])
    assert list(coord.codecs.keys()) == ["cod1", "cod2"]
    await coord.async_init()
    assert coord.get_adapter_ids() == []
    t1 = MockEspProxy(hass, "esp-test")
    await t1.setup()
    assert coord.get_adapter_ids() == ["esp-test"]
    await coord.register_callback("clbck1", _MatchingClbk())
    adv = BleAdvAdvertisement(0xFF, b"dt", 0x1A)
    qi = BleAdvQueueItem(0x10, 1, 100, 20, adv.to_raw())
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
    await coord.unregister_callback("clbck1")

    await coord.register_callback("clbck2", _MatchingEx())
    adv2 = BleAdvAdvertisement(0xFF, b"2dt2", 0x1A)
    await coord.handle_raw_adv("esp-test", "", adv2.to_raw())
    await coord.unregister_callback("clbck2")
    assert coord.has_available_adapters()
    await coord.async_final()


async def test_listening(hass: HomeAssistant) -> None:
    """Test listening mode."""
    coord = BleAdvCoordinator(hass, {}, ["hci"], 20000, [], [])
    coord.start_listening(0.1)
    assert coord.is_listening()
    raw_adv = bytes([0x03, 0xFF, 0x12, 0x34])
    await coord.handle_raw_adv("aaa", "mac", raw_adv)
    await coord.handle_raw_adv("bbb", "mac", raw_adv)
    await coord.handle_raw_adv("aaa", "mac", raw_adv)
    assert coord.listened_raw_advs == [raw_adv, raw_adv]
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


async def test_full_diagnostics(hass: HomeAssistant) -> None:
    """Test Full Diagnostics."""
    coord = BleAdvCoordinator(hass, {}, ["hci"], 20000, [], [])
    diag = await coord.full_diagnostic_dump()
    assert len(diag["coordinator"]) > 0
