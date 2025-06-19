import logging
from homeassistant.components.number import NumberEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    client = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([PumpSpeedPercentNumber(client)], update_before_add=True)

class PumpSpeedPercentNumber(NumberEntity):
    def __init__(self, client):
        self._client = client
        self._attr_name = "Pump RPM Target Percentage"
        self._attr_unique_id = f"{client.serial}_rpm_percentage"
        self._attr_step = 1
        self._attr_native_min_value = 0
        self._attr_native_max_value = 100
        self._attr_native_unit_of_measurement = "%"
        self._attr_value = None
        self._rpm_min = 1000
        self._rpm_max = 3450

    def _percent_to_rpm(self, percent):
        return int(self._rpm_min + (percent / 100) * (self._rpm_max - self._rpm_min))

    def _rpm_to_percent(self, rpm):
        if self._rpm_max == self._rpm_min:
            return 0
        return int((rpm - self._rpm_min) / (self._rpm_max - self._rpm_min) * 100)

    @property
    def native_value(self):
        return self._attr_value

    async def async_set_value(self, value):
        rpm = self._percent_to_rpm(value)
        rpm = int(round(rpm / 25) * 25)

        _LOGGER.debug("[PumpSpeedPercentNumber] async_set_value %s%% -> %s RPM", value, rpm)

        await self.hass.async_add_executor_job(
            self._client._send_command, "/customspeedrpm/write", f"value={rpm}"
        )
        await self.hass.async_add_executor_job(
            self._client._send_command, "/customspeedtimer/write", "value=1800"
        )

        self._client.last_refresh = 0
        await self.async_update()
    
        self._attr_value = value
        self.async_write_ha_state()

    async def async_update(self):
        data = await self.hass.async_add_executor_job(self._client.refresh_data)
        try:
            self._rpm_min = int(data.get("globalrpmmin", 1000))
            self._rpm_max = int(data.get("globalrpmmax", 3450))

            rpm_str = data.get("rpmtarget")
            rpm = int(rpm_str) if rpm_str else self._rpm_min

            percent = self._rpm_to_percent(rpm)
            self._attr_value = percent
            _LOGGER.debug("[PumpSpeedPercentNumber] Value type = %s", type(self._attr_value))
            _LOGGER.debug("[PumpSpeedPercentNumber] rpm=%s -> percent=%s", rpm, percent)
        except Exception as e:
            _LOGGER.warning("[PumpSpeedPercentNumber] Failed to update state: %s", e)
            self._attr_value = None
