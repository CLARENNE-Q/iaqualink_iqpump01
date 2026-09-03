import asyncio
import logging
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from .const import CONF_SERIAL, DOMAIN, SERVICE_SET_CUSTOM_SPEED
from .api import (
    IAqualinkAuthError,
    IAqualinkClient,
    IAqualinkConnectionError,
    IAqualinkNoDeviceError,
)
from .coordinator import IAqualinkPumpCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["switch", "number", "sensor", "button", "binary_sensor"]

SET_CUSTOM_SPEED_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Required("rpm"): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Required("duration"): vol.All(cv.time_period, cv.positive_timedelta),
    }
)

async def async_setup(hass: HomeAssistant, config: dict):
    async def async_handle_set_custom_speed(call: ServiceCall):
        duration_seconds = int(call.data["duration"].total_seconds())
        coordinators = []
        for device_id in call.data[ATTR_DEVICE_ID]:
            coordinator = IAqualinkPumpCoordinator.async_get_by_device_id(hass, device_id)
            if coordinator is None:
                raise HomeAssistantError(
                    f"Device {device_id} is not an iAquaLink iQPump01 pump"
                )
            coordinators.append(coordinator)

        await asyncio.gather(
            *(
                coordinator.async_set_custom_speed_rpm(call.data["rpm"], duration_seconds)
                for coordinator in coordinators
            )
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_CUSTOM_SPEED,
        async_handle_set_custom_speed,
        schema=SET_CUSTOM_SPEED_SCHEMA,
    )
    return True

async def async_options_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    client = IAqualinkClient(
        entry.data["email"],
        entry.data["password"],
        entry.data.get(CONF_SERIAL),
    )
    try:
        await hass.async_add_executor_job(client.login)
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
