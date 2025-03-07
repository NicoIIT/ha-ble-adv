"ble_adv package."

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE,
    CONF_NAME,
)
from homeassistant.core import HomeAssistant

from .codecs import get_codecs
from .codecs.models import BleAdvConfig
from .const import (
    CONF_ADAPTER_ID,
    CONF_CODEC_ID,
    CONF_COORDINATOR_ID,
    CONF_DURATION,
    CONF_FORCED_ID,
    CONF_INDEX,
    CONF_INTERVAL,
    CONF_REPEAT,
    CONF_TECHNICAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import BleAdvCoordinator
from .device import BleAdvDevice

_LOGGER = logging.getLogger(__name__)


async def get_coordinator(hass: HomeAssistant) -> BleAdvCoordinator:
    """Get and initiate a coordinator."""
    hass.data.setdefault(DOMAIN, {})
    if CONF_COORDINATOR_ID not in hass.data[DOMAIN]:
        coordinator = BleAdvCoordinator(hass, _LOGGER, get_codecs())
        hass.data[DOMAIN][CONF_COORDINATOR_ID] = coordinator
        await coordinator.async_init()
    return hass.data[DOMAIN][CONF_COORDINATOR_ID]


async def clean_coordinator(hass: HomeAssistant) -> None:
    """Clean coordinator if alone in the DOMAIN."""
    if (len(hass.data[DOMAIN]) == 1) and (CONF_COORDINATOR_ID in hass.data[DOMAIN]):
        _LOGGER.info("Removing coordinator")
        coordinator = hass.data[DOMAIN].pop(CONF_COORDINATOR_ID)
        await coordinator.async_final()
        hass.data.pop(DOMAIN)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BLE ADV from a config entry."""
    _LOGGER.info(f"BLE ADV: Setting up entry {entry.unique_id} / {entry.data}")

    if entry.unique_id is None:
        _LOGGER.warning("entry ignored as unique_id is None.")
        return False

    hass.data.setdefault(DOMAIN, {})
    device_conf = entry.data[CONF_DEVICE]
    tech_conf = entry.data[CONF_TECHNICAL]
    device = BleAdvDevice(
        hass,
        _LOGGER,
        entry.unique_id,
        device_conf[CONF_NAME],
        device_conf[CONF_CODEC_ID],
        device_conf[CONF_ADAPTER_ID],
        tech_conf[CONF_REPEAT],
        tech_conf[CONF_INTERVAL],
        tech_conf[CONF_DURATION],
        BleAdvConfig(device_conf[CONF_FORCED_ID], device_conf[CONF_INDEX]),
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
