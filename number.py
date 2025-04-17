import logging
from homeassistant.components.number import NumberEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    client = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([PumpSpeedNumber(client)], update_before_add=True)

class PumpSpeedNumber(NumberEntity):
    def __init__(self, client):
        self._client = client
        self._value = 0
        self._attr_name = "Pump RPM Target"
        self._attr_unique_id = f"{client.serial}_rpmtarget"
        self._attr_native_unit_of_measurement = "rpm"
        self._attr_step = 50
        self._attr_mode = "slider"
        self._attr_min_value = 1000
        self._attr_max_value = 3450

    @property
    def native_value(self) -> int:
        return self._value

    @native_value.setter
    def native_value(self, value: int):
        self._value = value

    async def async_set_native_value(self, value: int):
        _LOGGER.debug("[PumpSpeedNumber] async_set_native_value called with: %s", value)
        # Convertir en RPM si valeur inférieure ou égale à 100 (probablement un pourcentage)
        if value <= 100:
            value = int(self._attr_min_value + (value / 100) * (self._attr_max_value - self._attr_min_value))
            _LOGGER.debug("[PumpSpeedNumber] Converted value (RPM) before rounding: %s", value)
            value = round(value / 25) * 25
            _LOGGER.debug("[PumpSpeedNumber] Rounded to nearest 25: %s", value)

        await self.hass.async_add_executor_job(
            self._client._send_command, "/customspeedrpm/write", f"value={int(value)}"
        )
        await self.hass.async_add_executor_job(
            self._client._send_command, "/customspeedtimer/write", "value=1800"
        )
        self._value = int(value)
        self.async_write_ha_state()

    async def async_update(self):
        data = await self.hass.async_add_executor_job(self._client.refresh_data)
        _LOGGER.debug("[PumpSpeedNumber] Raw API data: %s", data)
        try:
            self._value = int(data.get("rpmtarget", 0))
        except (TypeError, ValueError):
            self._value = 0
            _LOGGER.warning("[PumpSpeedNumber] rpmtarget was not a valid int, defaulting to 0")
        self._attr_min_value = int(data.get("globalrpmmin", 1000))
        self._attr_max_value = int(data.get("globalrpmmax", 3450))