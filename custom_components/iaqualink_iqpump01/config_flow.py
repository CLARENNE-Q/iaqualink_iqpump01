from homeassistant.helpers.aiohttp_client import async_get_clientsession
import logging
from homeassistant import config_entries
from homeassistant.data_entry_flow import AbortFlow
from homeassistant.helpers import selector
import voluptuous as vol
from .const import (
    CONF_SERIAL,
    CONF_CUSTOM_SPEED_TIMER_SECONDS,
    CONF_FAST_REFRESH_DURATION_SECONDS,
    CONF_FAST_UPDATE_INTERVAL_SECONDS,
    CONF_UPDATE_INTERVAL_SECONDS,
    CUSTOM_SPEED_TIMER_OPTIONS,
    DEFAULT_CUSTOM_SPEED_TIMER_SECONDS,
    DEFAULT_FAST_REFRESH_DURATION_SECONDS,
    DEFAULT_FAST_UPDATE_INTERVAL_SECONDS,
    DEFAULT_UPDATE_INTERVAL_SECONDS,
    DOMAIN,
    option_int,
)
from .api import (
    IAqualinkAuthError,
    IAqualinkClient,
    IAqualinkConnectionError,
    IAqualinkNoDeviceError,
)

_LOGGER = logging.getLogger(__name__)

OPTION_INT_KEYS = (
    CONF_CUSTOM_SPEED_TIMER_SECONDS,
    CONF_UPDATE_INTERVAL_SECONDS,
    CONF_FAST_UPDATE_INTERVAL_SECONDS,
    CONF_FAST_REFRESH_DURATION_SECONDS,
)


def _options_schema(options):
    return vol.Schema({
        vol.Required(
            CONF_CUSTOM_SPEED_TIMER_SECONDS,
            default=str(option_int(
                options,
                CONF_CUSTOM_SPEED_TIMER_SECONDS,
                DEFAULT_CUSTOM_SPEED_TIMER_SECONDS,
            )),
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value=str(value), label=label)
                    for value, label in CUSTOM_SPEED_TIMER_OPTIONS.items()
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Required(
            CONF_UPDATE_INTERVAL_SECONDS,
            default=option_int(
                options,
                CONF_UPDATE_INTERVAL_SECONDS,
                DEFAULT_UPDATE_INTERVAL_SECONDS,
            ),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=15,
                max=300,
                step=5,
                unit_of_measurement="s",
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Required(
            CONF_FAST_UPDATE_INTERVAL_SECONDS,
            default=option_int(
                options,
                CONF_FAST_UPDATE_INTERVAL_SECONDS,
                DEFAULT_FAST_UPDATE_INTERVAL_SECONDS,
            ),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=5,
                max=60,
                step=5,
                unit_of_measurement="s",
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Required(
            CONF_FAST_REFRESH_DURATION_SECONDS,
            default=option_int(
                options,
                CONF_FAST_REFRESH_DURATION_SECONDS,
                DEFAULT_FAST_REFRESH_DURATION_SECONDS,
            ),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=30,
                max=600,
                step=30,
                unit_of_measurement="s",
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
    })


class AqualinkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._pending_data = None
        self._devices = []

    @staticmethod
    def async_get_options_flow(config_entry):
        return AqualinkOptionsFlow(config_entry)

    @staticmethod
    def _device_serial(device):
        serial = device.get("serial_number")
        return str(serial) if serial is not None else None

    @classmethod
    def _device_label(cls, device):
        serial = cls._device_serial(device)
        name = (
            device.get("name")
            or device.get("device_name")
            or device.get("deviceName")
            or device.get("label")
            or device.get("location_name")
            or device.get("locationName")
        )
        if name and serial:
            return f"{name} ({serial})"
        return serial or "iQPump01"

    def _select_pump_schema(self):
        return vol.Schema({
            vol.Required(CONF_SERIAL): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(
                            value=self._device_serial(device),
                            label=self._device_label(device),
                        )
                        for device in self._devices
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        })

    async def _async_create_pump_entry(self, data, serial):
        data = dict(data)
        data[CONF_SERIAL] = serial
        await self.async_set_unique_id(serial)
        self._abort_if_unique_id_configured()
        device = next(
            (
                candidate
                for candidate in self._devices
                if self._device_serial(candidate) == serial
            ),
            None,
        )
        label = self._device_label(device) if device else serial
        return self.async_create_entry(
            title=f"iAquaLink iQPump01 {label}",
            data=data,
        )

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            data = dict(user_input)
            data["email"] = data["email"].strip().lower()
            client = IAqualinkClient(async_get_clientsession(self.hass), data["email"], data["password"])
            try:
                await client.login()
                self._devices = client.devices
                if len(self._devices) == 1:
                    return await self._async_create_pump_entry(
                        data,
                        self._device_serial(self._devices[0]),
                    )

                self._pending_data = data
                return await self.async_step_select_pump()
            except IAqualinkAuthError as e:
                _LOGGER.debug("Authentication error: %s", e)
                errors["base"] = "invalid_auth"
            except IAqualinkNoDeviceError as e:
                _LOGGER.debug("No supported device found: %s", e)
                errors["base"] = "no_device"
            except IAqualinkConnectionError as e:
                _LOGGER.debug("Connection error: %s", e)
                errors["base"] = "cannot_connect"
            except AbortFlow:
                raise
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

    async def async_step_select_pump(self, user_input=None):
        if self._pending_data is None:
            return await self.async_step_user()

        if user_input is not None:
            return await self._async_create_pump_entry(
                self._pending_data,
                user_input[CONF_SERIAL],
            )

        return self.async_show_form(
            step_id="select_pump",
            data_schema=self._select_pump_schema(),
        )


class AqualinkOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            options = dict(user_input)
            for key in OPTION_INT_KEYS:
                options[key] = int(options[key])
            return self.async_create_entry(title="", data=options)

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(self._config_entry.options),
        )
