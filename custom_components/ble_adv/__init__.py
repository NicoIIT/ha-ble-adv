"ble_adv package."

import contextlib
import logging

with contextlib.suppress(Exception):
    from homeassistant.components.bluetooth.api import _get_manager as get_bt_manager
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
)
from homeassistant.core import HomeAssistant

from .adapters import get_adapter
from .codecs import get_codecs
from .codecs.models import BleAdvConfig
from .const import CONF_ADAPTER_ID, CONF_CODEC_ID, CONF_COORDINATOR_ID, CONF_FORCED_ID, CONF_INDEX, DOMAIN, PLATFORMS
from .coordinator import BleAdvCoordinator
from .device import BleAdvDevice

_LOGGER = logging.getLogger(__name__)


async def get_coordinator(hass: HomeAssistant) -> BleAdvCoordinator:
    """Get and initiate a coordinator."""
    hass.data.setdefault(DOMAIN, {})
    if CONF_COORDINATOR_ID not in hass.data[DOMAIN]:
        hass.data[DOMAIN][CONF_COORDINATOR_ID] = BleAdvCoordinator(hass, _LOGGER, get_codecs())
        bt_adapters = await get_bt_manager(hass).async_get_bluetooth_adapters()
        _LOGGER.debug(f"BT Adapters: {bt_adapters}")
        for adapter_id in bt_adapters:
            try:
                adapter = get_adapter(adapter_id)
                await adapter.async_init()
                await hass.data[DOMAIN][CONF_COORDINATOR_ID].add_adapter(adapter)
            except OSError as exc:
                _LOGGER.warning(f"Failed to init adapter {adapter.name}:{type(exc)}:{exc}, ignoring it")
                await adapter.close()
    return hass.data[DOMAIN][CONF_COORDINATOR_ID]


async def clean_coordinator(hass: HomeAssistant) -> None:
    """Clean coordinator if alone in the DOMAIN."""
    if (len(hass.data[DOMAIN]) == 1) and (CONF_COORDINATOR_ID in hass.data[DOMAIN]):
        _LOGGER.info("Removing coordinator")
        coordinator = hass.data[DOMAIN].pop(CONF_COORDINATOR_ID)
        for adapter in coordinator.adapters.values():
            await adapter.async_final()
        hass.data.pop(DOMAIN)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BLE ADV from a config entry."""
    _LOGGER.info(f"BLE ADV: Setting up entry {entry.unique_id} / {entry.data}")

    if entry.unique_id is None:
        _LOGGER.warning("entry ignored as unique_id is None.")
        return False

    hass.data.setdefault(DOMAIN, {})

    device = BleAdvDevice(
        hass,
        _LOGGER,
        entry.unique_id,
        entry.data[CONF_NAME],
        entry.data[CONF_CODEC_ID],
        entry.data[CONF_ADAPTER_ID],
        entry.data["technical"]["repeat"],
        entry.data["technical"]["interval"],
        BleAdvConfig(entry.data[CONF_FORCED_ID], entry.data[CONF_INDEX]),
        await get_coordinator(hass),
    )

    hass.data[DOMAIN][entry.entry_id] = device
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await device.async_start()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info(f"Unloading entry {entry.unique_id}")
    await hass.data[DOMAIN][entry.entry_id].async_stop()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove a config entry."""
    _LOGGER.info(f"BLE ADV: Removing entry {entry.unique_id} / {entry.data}")
    await clean_coordinator(hass)
