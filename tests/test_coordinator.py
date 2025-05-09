"""Coordinator tests."""

# ruff: noqa: S101
from unittest import mock

from ble_adv.adapters import BleAdvQueueItem
from ble_adv.codecs.models import BleAdvAdvertisement, BleAdvCodec, BleAdvConfig, BleAdvEntAttr
from ble_adv.coordinator import (
    CONF_ATTR_NAME,
    CONF_ATTR_PUBLISH_ADV_SVC,
    CONF_ATTR_RAW,
    CONF_ATTR_RECV_EVENT_NAME,
    ESPHOME_BLE_ADV_DISCOVERY_EVENT,
    BleAdvCoordinator,
    MatchingCallback,
)
from homeassistant.core import Event, HomeAssistant


class _Codec(mock.MagicMock):
    decode_adv = mock.MagicMock(return_value=(0x10, BleAdvConfig(1, 0)))


class _MatchingClbk(MatchingCallback):
    async def handle(self, _: str, __: str, ___: BleAdvConfig, ____: list[BleAdvEntAttr]) -> None:
        pass


class _MatchingEx(MatchingCallback):
    async def handle(self, codec_id: str, adapter_id: str, config: BleAdvConfig, ent_attrs: list[BleAdvEntAttr]) -> None:
        await super().handle(codec_id, adapter_id, config, ent_attrs)


async def test_coordinator(hass: HomeAssistant) -> None:
    """Test coordinator."""
    cod1 = _Codec()
    cod2 = _Codec()
    codecs: dict[str, BleAdvCodec] = {"cod1": cod1, "cod2": cod2}
    coord = BleAdvCoordinator(hass, codecs)
    assert list(coord.codecs.keys()) == ["cod1", "cod2"]
    await coord.async_init()
    assert coord.get_adapter_ids() == []
    await coord.on_discovery_event(
        Event(
            ESPHOME_BLE_ADV_DISCOVERY_EVENT,
            {CONF_ATTR_NAME: "esp-test", CONF_ATTR_RECV_EVENT_NAME: "recv-event", CONF_ATTR_PUBLISH_ADV_SVC: "pub-svc"},
        )
    )
    assert coord.get_adapter_ids() == ["esp-test"]
    await coord.register_callback("clbck1", _MatchingClbk())
    adv = BleAdvAdvertisement(0xFF, b"dt", 0x1A)
    qi = BleAdvQueueItem(0x10, 1, 100, 20, bytes(adv.to_raw()))
    await coord.advertise("not-exists", "q1", qi)
    await coord.advertise("esp-test", "q1", qi)
    await coord.handle_raw_adv("esp-test", bytes(adv.to_raw()))
    await coord._esp_bt_adapters["esp-test"]._on_adv_recv_event(Event("recv-event", {CONF_ATTR_RAW: adv.to_raw().hex()}))  # type: ignore [None]  # noqa: SLF001
    adv.ad_flag = 0x1B
    await coord.handle_raw_adv("esp-test", bytes(adv.to_raw()))
    await coord.handle_raw_adv("esp-test", b"invalid_adv")
    await coord.advertise("esp-test", "q1", qi)
    await coord.unregister_callback("clbck1")

    await coord.register_callback("clbck2", _MatchingEx())
    adv2 = BleAdvAdvertisement(0xFF, b"2dt2", 0x1A)
    await coord.handle_raw_adv("esp-test", bytes(adv2.to_raw()))
    await coord.unregister_callback("clbck2")
    assert coord.has_available_adapters()
