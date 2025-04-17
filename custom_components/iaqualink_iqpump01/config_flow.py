import logging
from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN
from .api import IAqualinkClient

_LOGGER = logging.getLogger(__name__)

class AqualinkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            client = IAqualinkClient(user_input["email"], user_input["password"])
            try:
                await self.hass.async_add_executor_job(client.login)
                return self.async_create_entry(title="iAquaLink Pump", data=user_input)
            except Exception as e:
                _LOGGER.debug("Login error: %s", e)
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("email"): str,
                vol.Required("password"): str
            }),
            errors=errors
        )