from homeassistant.helpers.aiohttp_client import async_get_clientsession
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from .const import CONF_SERIAL, DOMAIN
from .api import (
    IAqualinkAuthError,
    IAqualinkClient,
    IAqualinkConnectionError,
    IAqualinkNoDeviceError,
)
from .coordinator import IAqualinkPumpCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["switch", "number", "sensor", "button", "binary_sensor"]

async def async_setup(hass: HomeAssistant, config: dict):
    return True

async def async_options_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    session = async_get_clientsession(hass)
    client = IAqualinkClient(
        session,
        entry.data["email"],
        entry.data["password"],
        entry.data.get(CONF_SERIAL),
    )
    try:
        await client.login()
    except IAqualinkAuthError as err:
        raise ConfigEntryAuthFailed("iAquaLink authentication failed") from err
    except IAqualinkNoDeviceError as err:
        raise ConfigEntryNotReady("No iQPump01 controller found in iAquaLink account") from err
    except IAqualinkConnectionError as err:
        raise ConfigEntryNotReady("Unable to connect to iAquaLink") from err

    update_kwargs = {}
    if entry.unique_id is None:
        update_kwargs["unique_id"] = client.serial
    if entry.data.get(CONF_SERIAL) != client.serial:
        data = dict(entry.data)
        data[CONF_SERIAL] = client.serial
        update_kwargs["data"] = data
    if update_kwargs:
        hass.config_entries.async_update_entry(entry, **update_kwargs)

    coordinator = IAqualinkPumpCoordinator(hass, client, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(async_options_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id, None)
        if coordinator is not None:
            coordinator.async_shutdown()
    return unload_ok
