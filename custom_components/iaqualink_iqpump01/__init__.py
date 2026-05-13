import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from .const import DOMAIN
from .api import (
    IAqualinkAuthError,
    IAqualinkClient,
    IAqualinkConnectionError,
    IAqualinkNoDeviceError,
)
from .coordinator import IAqualinkPumpCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["switch", "number", "sensor"]

async def async_setup(hass: HomeAssistant, config: dict):
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    client = IAqualinkClient(entry.data["email"], entry.data["password"])
    try:
        await hass.async_add_executor_job(client.login)
    except IAqualinkAuthError as err:
        raise ConfigEntryAuthFailed("iAquaLink authentication failed") from err
    except IAqualinkNoDeviceError as err:
        raise ConfigEntryNotReady("No iQPump01 controller found in iAquaLink account") from err
    except IAqualinkConnectionError as err:
        raise ConfigEntryNotReady("Unable to connect to iAquaLink") from err

    if entry.unique_id is None:
        hass.config_entries.async_update_entry(entry, unique_id=client.serial)

    coordinator = IAqualinkPumpCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id, None)
        if coordinator is not None:
            coordinator.async_shutdown()
    return unload_ok
