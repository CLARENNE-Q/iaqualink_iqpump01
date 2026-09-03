import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    IAqualinkAuthError,
    IAqualinkClient,
    IAqualinkCommandError,
    IAqualinkConnectionError,
    IAqualinkError,
)
from .const import (
    CONF_CUSTOM_SPEED_TIMER_SECONDS,
    CONF_FAST_REFRESH_DURATION_SECONDS,
    CONF_FAST_UPDATE_INTERVAL_SECONDS,
    CONF_UPDATE_INTERVAL_SECONDS,
    DEFAULT_CUSTOM_SPEED_TIMER_SECONDS,
    DEFAULT_FAST_REFRESH_DURATION_SECONDS,
    DEFAULT_FAST_UPDATE_INTERVAL_SECONDS,
    DEFAULT_UPDATE_INTERVAL_SECONDS,
    DOMAIN,
    MAX_CUSTOM_SPEED_TIMER_SECONDS,
    OPMODE_SERVICE,
    SERVICE_MODE_REMOTE_CONTROL_ERROR,
    option_int,
    rpm_limits,
)

_LOGGER = logging.getLogger(__name__)

class IAqualinkPumpCoordinator(DataUpdateCoordinator):
    """Coordinate iAquaLink pump polling for all entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: IAqualinkClient,
        config_entry: ConfigEntry,
    ) -> None:
        self.config_entry = config_entry
        self.default_update_interval = timedelta(
            seconds=option_int(
                config_entry.options,
                CONF_UPDATE_INTERVAL_SECONDS,
                DEFAULT_UPDATE_INTERVAL_SECONDS,
            )
        )
        self.fast_update_interval = timedelta(
            seconds=option_int(
                config_entry.options,
                CONF_FAST_UPDATE_INTERVAL_SECONDS,
                DEFAULT_FAST_UPDATE_INTERVAL_SECONDS,
            )
        )
        self.fast_refresh_duration = timedelta(
            seconds=option_int(
                config_entry.options,
                CONF_FAST_REFRESH_DURATION_SECONDS,
                DEFAULT_FAST_REFRESH_DURATION_SECONDS,
            )
        )
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=self.default_update_interval,
        )
        self.client = client
        self._fast_refresh_unsub = None

    async def _async_update_data(self):
        try:
            return await self.hass.async_add_executor_job(self.client.refresh_data)
        except IAqualinkAuthError as err:
            raise ConfigEntryAuthFailed("iAquaLink authentication failed") from err
        except IAqualinkConnectionError as err:
            raise UpdateFailed(f"Network/HTTP error communicating with iAquaLink: {err}") from err
        except IAqualinkCommandError as err:
            raise UpdateFailed(f"Command validation failed: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error communicating with iAquaLink: {err}") from err

    @callback
    def enable_fast_refresh(self) -> None:
        self.update_interval = self.fast_update_interval
        if self._fast_refresh_unsub is not None:
            self._fast_refresh_unsub()
        self._fast_refresh_unsub = async_call_later(
            self.hass,
            self.fast_refresh_duration.total_seconds(),
            self._disable_fast_refresh,
        )
        _LOGGER.debug(
            "[enable_fast_refresh] Using %ss polling for %ss after speed change.",
            int(self.fast_update_interval.total_seconds()),
            int(self.fast_refresh_duration.total_seconds()),
        )

    @callback
    def _disable_fast_refresh(self, *_):
        self.update_interval = self.default_update_interval
        self._fast_refresh_unsub = None
        _LOGGER.debug(
            "[disable_fast_refresh] Restored %ss polling.",
            int(self.default_update_interval.total_seconds()),
        )

    @callback
    def async_shutdown(self) -> None:
        if self._fast_refresh_unsub is not None:
            self._fast_refresh_unsub()
            self._fast_refresh_unsub = None

    @staticmethod
    def async_get_by_device_id(hass: HomeAssistant, device_id: str) -> "IAqualinkPumpCoordinator | None":
        """Resolve a Home Assistant device_id to its IAqualinkPumpCoordinator, if any."""
        device = dr.async_get(hass).async_get(device_id)
        if device is None:
            return None
        domain_entries = hass.data.get(DOMAIN, {})
        entry_id = next(iter(device.config_entries & domain_entries.keys()), None)
        return domain_entries.get(entry_id)

    def custom_speed_timer_seconds(self) -> int:
        return option_int(
            self.config_entry.options,
            CONF_CUSTOM_SPEED_TIMER_SECONDS,
            DEFAULT_CUSTOM_SPEED_TIMER_SECONDS,
        )

    def raise_if_service_mode(self, action) -> None:
        data = self.data or {}
        if str(data.get("opmode")) != OPMODE_SERVICE:
            return
        _LOGGER.warning(
            "%s ignored: pump in service mode (opmode=%s)",
            action,
            OPMODE_SERVICE,
        )
        raise HomeAssistantError(SERVICE_MODE_REMOTE_CONTROL_ERROR)

    async def async_set_custom_speed(self, percentage, duration_seconds) -> None:
        """Set a custom speed via percentage (used by the number entity)."""
        rpm_min, rpm_max = rpm_limits(self.data)
        rpm = int(rpm_min + (percentage / 100) * (rpm_max - rpm_min))
        await self._async_write_custom_speed(rpm, duration_seconds)

    async def async_set_custom_speed_rpm(self, rpm, duration_seconds) -> None:
        """Set a custom speed via raw RPM (used by the set_custom_speed service)."""
        rpm_min, rpm_max = rpm_limits(self.data)
        if not rpm_min <= rpm <= rpm_max:
            raise HomeAssistantError(
                f"RPM must be between {rpm_min} and {rpm_max} for this pump."
            )
        await self._async_write_custom_speed(rpm, duration_seconds)

    async def _async_write_custom_speed(self, rpm, duration_seconds) -> None:
        self.raise_if_service_mode("Set custom speed command")

        if not 1 <= duration_seconds <= MAX_CUSTOM_SPEED_TIMER_SECONDS:
            raise HomeAssistantError(
                "Duration must be between 1 second and "
                f"{MAX_CUSTOM_SPEED_TIMER_SECONDS} seconds (23h59)."
            )

        # The pump only accepts RPM targets in increments of 25.
        rpm = int(round(rpm / 25) * 25)

        _LOGGER.debug(
            "[_async_write_custom_speed] %s RPM for %ss",
            rpm,
            duration_seconds,
        )

        try:
            # The controller ignores custom RPM writes while running in scheduled mode
            # (opmode=0). Switch to manual/custom speed mode before writing the target.
            await self.hass.async_add_executor_job(
                self.client._send_command, "/opmode/write", "value=1"
            )
            await self.hass.async_add_executor_job(
                self.client._send_command, "/customspeedrpm/write", f"value={rpm}"
            )
            await self.hass.async_add_executor_job(
                self.client._send_command,
                "/customspeedtimer/write",
                f"value={duration_seconds}",
            )
        except IAqualinkError as err:
            raise HomeAssistantError(f"Unable to set pump speed: {err}") from err

        self.enable_fast_refresh()
        await self.async_request_refresh()
