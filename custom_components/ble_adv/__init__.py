"ble_adv package."

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE, CONF_NAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig
from homeassistant.helpers.singleton import singleton
from homeassistant.helpers.typing import ConfigType

from .codecs import dyn_codec_params, get_codecs
from .codecs.models import BleAdvConfig
from .const import (
    CONF_ADAPTER_ID,
    CONF_ADAPTER_IDS,
    CONF_APPLE_INC_UUIDS,
    CONF_CODEC_ID,
    CONF_CODEC_ID_OLD,
    CONF_COORDINATOR_ID,
    CONF_DEVICE_QUEUE,
    CONF_DURATION,
    CONF_FANS,
    CONF_FORCED_ID,
    CONF_GOOGLE_LCC_UUIDS,
    CONF_IGN_ADAPTERS,
    CONF_IGN_CIDS,
    CONF_IGN_DURATION,
    CONF_IGN_MACS,
    CONF_INDEX,
    CONF_INTERVAL,
    CONF_LAST_VERSION,
    CONF_LIGHTS,
    CONF_MAX_ENTITY_NB,
    CONF_PARAMS,
    CONF_RAW,
    CONF_REFRESH_DIR_ON_START,
    CONF_REFRESH_ON_START,
    CONF_REFRESH_OSC_ON_START,
    CONF_REMOTE,
    CONF_REPEAT,
    CONF_REPEATS,
    CONF_TECHNICAL,
    CONF_USE_DIR,
    CONF_USE_OSC,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import BleAdvCoordinator
from .device import BleAdvDevice

_LOGGER = logging.getLogger(__name__)

INJECT_RAW_SERVICE_NAME = "inject_raw"
INJECT_RAW_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ADAPTER_ID): str,
        vol.Required(CONF_RAW): str,
        vol.Optional(CONF_INTERVAL, default=20): NumberSelector(NumberSelectorConfig(min=10, max=150)),
        vol.Optional(CONF_REPEAT, default=3): NumberSelector(NumberSelectorConfig(min=1, max=20)),
        vol.Optional(CONF_DEVICE_QUEUE, default="device"): str,
        vol.Optional(CONF_DURATION, default=800): NumberSelector(NumberSelectorConfig(min=100, max=2000)),
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_IGN_ADAPTERS): vol.All(cv.ensure_list, [cv.string]),
                vol.Optional(CONF_IGN_DURATION): vol.All(vol.Coerce(int), vol.Range(min=0, max=60000)),
                vol.Optional(CONF_IGN_CIDS): vol.All(cv.ensure_list, [vol.All(vol.Coerce(int), vol.Range(min=0, max=0xFFFF))]),
                vol.Optional(CONF_IGN_MACS): vol.All(cv.ensure_list, [cv.string]),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


@singleton(f"{DOMAIN}/{CONF_COORDINATOR_ID}")
async def get_coordinator(hass: HomeAssistant) -> BleAdvCoordinator:
    """Get and initiate a coordinator."""
    conf = hass.data.get(DOMAIN, {}).pop(CONF_COORDINATOR_ID, {})
    coordinator = BleAdvCoordinator(
        hass,
        get_codecs(),
        conf.get(CONF_IGN_ADAPTERS, []),
        conf.get(CONF_IGN_DURATION, 60000),
        conf.get(CONF_IGN_CIDS, [*CONF_GOOGLE_LCC_UUIDS, *CONF_APPLE_INC_UUIDS]),
        conf.get(CONF_IGN_MACS, []),
    )
    await coordinator.async_init()
    return coordinator


async def async_setup(hass: HomeAssistant, conf: ConfigType) -> bool:
    """Initialize the integration."""
    ble_adv_conf = conf.get(DOMAIN, {})
    _LOGGER.debug(f"BLE ADV: Setting component with conf {ble_adv_conf}")
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][CONF_COORDINATOR_ID] = ble_adv_conf
    coord = await get_coordinator(hass)

    async def inject_raw(call: ServiceCall) -> None:
        if errors := await coord.inject_raw(call.data):
            msg = "/".join([f"Invalid {field} - {reason}" for field, reason in errors.items()])
            raise vol.Invalid(msg)

    hass.services.async_register(DOMAIN, INJECT_RAW_SERVICE_NAME, inject_raw, INJECT_RAW_SCHEMA)
    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""

    new_data = {**config_entry.data}
    update_needed: bool = False
    if CONF_ADAPTER_ID in new_data[CONF_DEVICE]:
        new_data[CONF_TECHNICAL][CONF_ADAPTER_ID] = new_data[CONF_DEVICE].pop(CONF_ADAPTER_ID)
        update_needed = True
    if CONF_NAME in new_data[CONF_DEVICE]:
        new_data[CONF_DEVICE].pop(CONF_NAME)
        update_needed = True
    if CONF_ADAPTER_ID in new_data.get(CONF_REMOTE, []):
        new_data[CONF_REMOTE].pop(CONF_ADAPTER_ID)
        update_needed = True
    if len(new_data[CONF_FANS]) < CONF_MAX_ENTITY_NB:
        new_data[CONF_FANS] += [{}] * (CONF_MAX_ENTITY_NB - len(new_data[CONF_FANS]))
        update_needed = True
    if len(new_data[CONF_LIGHTS]) < CONF_MAX_ENTITY_NB:
        new_data[CONF_LIGHTS] += [{}] * (CONF_MAX_ENTITY_NB - len(new_data[CONF_LIGHTS]))
        update_needed = True
    for fan in new_data[CONF_FANS]:
        if CONF_REFRESH_ON_START in fan:
            refresh_on_start = fan.pop(CONF_REFRESH_ON_START)
            fan[CONF_REFRESH_DIR_ON_START] = refresh_on_start and fan.get(CONF_USE_DIR, False)
            fan[CONF_REFRESH_OSC_ON_START] = refresh_on_start and fan.get(CONF_USE_OSC, False)
            update_needed = True
    if CONF_ADAPTER_ID in new_data[CONF_TECHNICAL]:
        new_data[CONF_TECHNICAL][CONF_ADAPTER_IDS] = [new_data[CONF_TECHNICAL].pop(CONF_ADAPTER_ID)]
        update_needed = True
    if CONF_REPEATS not in new_data[CONF_TECHNICAL] and CONF_REPEAT in new_data[CONF_TECHNICAL]:
        new_data[CONF_TECHNICAL][CONF_REPEATS] = 3 * new_data[CONF_TECHNICAL][CONF_REPEAT]
        update_needed = True
    if CONF_CODEC_ID_OLD in new_data[CONF_DEVICE]:
        new_id, params = dyn_codec_params(new_data[CONF_DEVICE][CONF_CODEC_ID_OLD])
        if new_id != new_data[CONF_DEVICE].get(CONF_CODEC_ID) or params != new_data[CONF_DEVICE].get(CONF_PARAMS):
            new_data[CONF_DEVICE][CONF_CODEC_ID] = new_id
            new_data[CONF_DEVICE][CONF_PARAMS] = params
            update_needed = True
    if CONF_REMOTE in new_data and CONF_CODEC_ID_OLD in new_data[CONF_REMOTE]:
        new_id, params = dyn_codec_params(new_data[CONF_REMOTE][CONF_CODEC_ID_OLD])
        if new_id != new_data[CONF_REMOTE].get(CONF_CODEC_ID) or params != new_data[CONF_REMOTE].get(CONF_PARAMS):
            new_data[CONF_REMOTE][CONF_CODEC_ID] = new_id
            new_data[CONF_REMOTE][CONF_PARAMS] = params
            update_needed = True

    if config_entry.version < 2:
        coordinator = await get_coordinator(hass)
        adapt_ids = coordinator.get_adapter_ids()
        if new_data[CONF_TECHNICAL][CONF_ADAPTER_IDS][0] not in adapt_ids:
            _LOGGER.debug(f"Migrating {config_entry.unique_id} configuration from version {config_entry.version}")
            if len(adapt_ids) == 0:
                _LOGGER.error(f"No adapters detected while migrating entry: adapter {new_data[CONF_TECHNICAL][CONF_ADAPTER_IDS][0]} kept.")
            else:
                new_data[CONF_TECHNICAL][CONF_ADAPTER_IDS] = adapt_ids.copy()
            update_needed = True

    if update_needed:
        hass.config_entries.async_update_entry(config_entry, data=new_data, version=CONF_LAST_VERSION)
        _LOGGER.info(f"Migration of entry {config_entry.unique_id} to configuration version {config_entry.version} successful")

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BLE ADV from a config entry."""
    _LOGGER.debug(f"BLE ADV: Setting up entry {entry.unique_id} / {entry.data}")

    if entry.unique_id is None:
        _LOGGER.warning("entry ignored as unique_id is None.")
        return False

    hass.data.setdefault(DOMAIN, {})
    device_conf = entry.data[CONF_DEVICE]
    tech_conf = entry.data[CONF_TECHNICAL]
    coordinator = await get_coordinator(hass)
    device = BleAdvDevice(
        hass,
        entry.unique_id,
        entry.title,
        device_conf[CONF_CODEC_ID],
        tech_conf[CONF_ADAPTER_IDS],
        tech_conf[CONF_REPEATS],
        tech_conf[CONF_INTERVAL],
        tech_conf[CONF_DURATION],
        BleAdvConfig(device_conf[CONF_FORCED_ID], device_conf[CONF_INDEX], device_conf.get(CONF_PARAMS)),
        coordinator,
    )
    if CONF_REMOTE in entry.data and CONF_CODEC_ID in entry.data[CONF_REMOTE]:
        rconf = entry.data[CONF_REMOTE]
        device.add_listener(rconf[CONF_CODEC_ID], BleAdvConfig(rconf[CONF_FORCED_ID], rconf[CONF_INDEX], rconf.get(CONF_PARAMS)))

    hass.data[DOMAIN][entry.entry_id] = device
    coordinator.add_device(device)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug(f"Unloading entry {entry.unique_id}")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = await get_coordinator(hass)
        coordinator.remove_device(hass.data[DOMAIN].pop(entry.entry_id))
    return unload_ok
