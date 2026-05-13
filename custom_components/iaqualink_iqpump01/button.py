import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.exceptions import HomeAssistantError

from .api import IAqualinkError
from .const import DOMAIN
from .entity import IAqualinkPumpEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([PumpReturnToProgramButton(coordinator)])


class PumpReturnToProgramButton(IAqualinkPumpEntity, ButtonEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        client = coordinator.client
        self._attr_name = "Pump Return to Program"
        self._attr_unique_id = f"{client.serial}_return_to_program"
        self._attr_icon = "mdi:calendar-clock"

    async def async_press(self):
        _LOGGER.debug("[PumpReturnToProgramButton] Returning pump to program mode.")
        try:
            await self.client._send_command("/opmode/write", "value=0")
        except IAqualinkError as err:
            raise HomeAssistantError(
                f"Unable to return pump to program mode: {err}"
            ) from err

        self.coordinator.enable_fast_refresh()
        await self.coordinator.async_request_refresh()
