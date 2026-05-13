import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import IAqualinkAuthError, IAqualinkClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DEFAULT_UPDATE_INTERVAL = timedelta(seconds=60)
FAST_UPDATE_INTERVAL = timedelta(seconds=10)
FAST_REFRESH_DURATION = timedelta(minutes=3)


class IAqualinkPumpCoordinator(DataUpdateCoordinator):
    """Coordinate iAquaLink pump polling for all entities."""

    def __init__(self, hass: HomeAssistant, client: IAqualinkClient) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_UPDATE_INTERVAL,
        )
        self.client = client
        self._fast_refresh_unsub = None

    async def _async_update_data(self):
        try:
            return await self.hass.async_add_executor_job(self.client.refresh_data)
        except IAqualinkAuthError as err:
            raise ConfigEntryAuthFailed("iAquaLink authentication failed") from err
        except Exception as err:
            raise UpdateFailed(f"Error communicating with iAquaLink: {err}") from err

    @callback
    def enable_fast_refresh(self) -> None:
        self.update_interval = FAST_UPDATE_INTERVAL
        if self._fast_refresh_unsub is not None:
            self._fast_refresh_unsub()
        self._fast_refresh_unsub = async_call_later(
            self.hass,
            FAST_REFRESH_DURATION.total_seconds(),
            self._disable_fast_refresh,
        )
        _LOGGER.debug(
            "[enable_fast_refresh] Using %ss polling for %ss after speed change.",
            int(FAST_UPDATE_INTERVAL.total_seconds()),
            int(FAST_REFRESH_DURATION.total_seconds()),
        )

    @callback
    def _disable_fast_refresh(self, *_):
        self.update_interval = DEFAULT_UPDATE_INTERVAL
        self._fast_refresh_unsub = None
        _LOGGER.debug(
            "[disable_fast_refresh] Restored %ss polling.",
            int(DEFAULT_UPDATE_INTERVAL.total_seconds()),
        )

    @callback
    def async_shutdown(self) -> None:
        if self._fast_refresh_unsub is not None:
            self._fast_refresh_unsub()
            self._fast_refresh_unsub = None
