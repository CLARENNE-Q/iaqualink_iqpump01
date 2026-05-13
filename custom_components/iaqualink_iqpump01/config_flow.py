import logging
from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN
from .api import (
    IAqualinkAuthError,
    IAqualinkClient,
    IAqualinkConnectionError,
    IAqualinkNoDeviceError,
)

_LOGGER = logging.getLogger(__name__)

class AqualinkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            data = dict(user_input)
            data["email"] = data["email"].strip().lower()
            client = IAqualinkClient(data["email"], data["password"])
            try:
                await self.hass.async_add_executor_job(client.login)
                await self.async_set_unique_id(client.serial)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="iAquaLink iQPump01", data=data)
            except IAqualinkAuthError as e:
                _LOGGER.debug("Authentication error: %s", e)
                errors["base"] = "invalid_auth"
            except IAqualinkNoDeviceError as e:
                _LOGGER.debug("No supported device found: %s", e)
                errors["base"] = "no_device"
            except IAqualinkConnectionError as e:
                _LOGGER.debug("Connection error: %s", e)
                errors["base"] = "cannot_connect"
            except Exception as e:
                _LOGGER.debug("Unexpected setup error: %s", e)
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("email"): str,
                vol.Required("password"): str
            }),
            errors=errors
        )
