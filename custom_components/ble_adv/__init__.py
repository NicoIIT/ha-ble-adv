"ble_adv package."

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE,
    CONF_NAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.singleton import singleton

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
    CONF_REMOTE,
    CONF_REPEAT,
    CONF_TECHNICAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import BleAdvCoordinator
from .device import BleAdvDevice, BleAdvRemote

_LOGGER = logging.getLogger(__name__)


@singleton(f"{DOMAIN}/{CONF_COORDINATOR_ID}")
async def get_coordinator(hass: HomeAssistant) -> BleAdvCoordinator:
    """Get and initiate a coordinator."""
    coordinator = BleAdvCoordinator(hass, _LOGGER, get_codecs())
    await coordinator.async_init()
    return coordinator


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""

    if config_entry.version < 2:
        coordinator = await get_coordinator(hass)
        adapt_ids = coordinator.get_adapter_ids()
        if config_entry.data[CONF_DEVICE][CONF_ADAPTER_ID] not in adapt_ids:
            _LOGGER.debug("Migrating configuration from version %s", config_entry.version)
            if len(adapt_ids) != 1:
                _LOGGER.error(
                    "Automatic migration of your integration cannot be done as you do not have exactly one bluetooth adapter, please re create it."
                )
                return False
            new_data = {**config_entry.data}
            new_data[CONF_DEVICE][CONF_ADAPTER_ID] = adapt_ids[0]
            hass.config_entries.async_update_entry(config_entry, data=new_data, version=2)
            _LOGGER.debug("Migration to configuration version %s successful", config_entry.version)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BLE ADV from a config entry."""
    _LOGGER.info(f"BLE ADV: Setting up entry {entry.unique_id} / {entry.data}")

    if entry.unique_id is None:
        _LOGGER.warning("entry ignored as unique_id is None.")
        return False

    hass.data.setdefault(DOMAIN, {})
    device_conf = entry.data[CONF_DEVICE]
    tech_conf = entry.data[CONF_TECHNICAL]
    coordinator = await get_coordinator(hass)
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
        coordinator,
    )
    if CONF_REMOTE in entry.data and CONF_CODEC_ID in entry.data[CONF_REMOTE]:
        remote_conf = entry.data[CONF_REMOTE]
        remote = BleAdvRemote(
            f"{entry.unique_id}_remote",
            remote_conf[CONF_CODEC_ID],
            remote_conf[CONF_ADAPTER_ID],
            BleAdvConfig(remote_conf[CONF_FORCED_ID], remote_conf[CONF_INDEX]),
            coordinator,
        )
        device.link_remote(remote)

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
