import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    IAqualinkAuthError,
    IAqualinkClient,
    IAqualinkCommandError,
    IAqualinkConnectionError,
)
from .const import (
    CONF_FAST_REFRESH_DURATION_SECONDS,
    CONF_FAST_UPDATE_INTERVAL_SECONDS,
    CONF_UPDATE_INTERVAL_SECONDS,
    DEFAULT_FAST_REFRESH_DURATION_SECONDS,
    DEFAULT_FAST_UPDATE_INTERVAL_SECONDS,
    DEFAULT_UPDATE_INTERVAL_SECONDS,
    DOMAIN,
    option_int,
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
            return await self.client.refresh_data()
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
