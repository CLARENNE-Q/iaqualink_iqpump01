import logging
from homeassistant.components.number import NumberEntity
from .const import DOMAIN, rpm_limits
from .entity import IAqualinkPumpEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([PumpSpeedPercentNumber(coordinator)])

class PumpSpeedPercentNumber(IAqualinkPumpEntity, NumberEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        client = coordinator.client
        self._attr_name = "Pump RPM Target Percentage"
        self._attr_unique_id = f"{client.serial}_rpm_percentage"
        self._attr_step = 1
        self._attr_native_min_value = 0
        self._attr_native_max_value = 100
        self._attr_native_unit_of_measurement = "%"

    def _rpm_to_percent(self, rpm):
        rpm_min, rpm_max = rpm_limits(self.coordinator.data)
        if rpm_max == rpm_min:
            return 0
        return int((rpm - rpm_min) / (rpm_max - rpm_min) * 100)

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        try:
            rpm_str = data.get("rpmtarget")
            rpm_min, _ = rpm_limits(data)
            rpm = int(rpm_str) if rpm_str else rpm_min
            percent = self._rpm_to_percent(rpm)
            _LOGGER.debug("[PumpSpeedPercentNumber] rpm=%s -> percent=%s", rpm, percent)
            return percent
        except Exception as e:
            _LOGGER.warning("[PumpSpeedPercentNumber] Failed to read state: %s", e)
            return None

    async def async_set_value(self, value):
        timer_seconds = self.coordinator.custom_speed_timer_seconds()
        await self.coordinator.async_set_custom_speed(value, timer_seconds)
