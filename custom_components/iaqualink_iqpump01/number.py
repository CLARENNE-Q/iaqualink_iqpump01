import logging
from homeassistant.components.number import NumberEntity
from homeassistant.exceptions import HomeAssistantError
from .api import IAqualinkError
from .const import (
    CONF_CUSTOM_SPEED_TIMER_SECONDS,
    DEFAULT_CUSTOM_SPEED_TIMER_SECONDS,
    DOMAIN,
    option_int,
)
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
        self._attr_native_step = 1
        self._attr_native_min_value = 0
        self._attr_native_max_value = 100
        self._attr_native_unit_of_measurement = "%"

    def _rpm_limits(self):
        data = self.coordinator.data or {}
        return (
            int(data.get("globalrpmmin", 1000)),
            int(data.get("globalrpmmax", 3450)),
        )

    def _percent_to_rpm(self, percent):
        rpm_min, rpm_max = self._rpm_limits()
        return int(rpm_min + (percent / 100) * (rpm_max - rpm_min))

    def _rpm_to_percent(self, rpm):
        rpm_min, rpm_max = self._rpm_limits()
        if rpm_max == rpm_min:
            return 0
        return int((rpm - rpm_min) / (rpm_max - rpm_min) * 100)

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        try:
            rpm_str = data.get("rpmtarget")
            rpm_min, _ = self._rpm_limits()
            rpm = int(rpm_str) if rpm_str else rpm_min
            percent = self._rpm_to_percent(rpm)
            _LOGGER.debug("[PumpSpeedPercentNumber] rpm=%s -> percent=%s", rpm, percent)
            return percent
        except Exception as e:
            _LOGGER.warning("[PumpSpeedPercentNumber] Failed to read state: %s", e)
            return None

    def _custom_speed_timer_seconds(self):
        return option_int(
            self.coordinator.config_entry.options,
            CONF_CUSTOM_SPEED_TIMER_SECONDS,
            DEFAULT_CUSTOM_SPEED_TIMER_SECONDS,
        )

    async def async_set_native_value(self, value: float) -> None:
        self._raise_if_service_mode("Set speed command")
        rpm = self._percent_to_rpm(value)
        rpm = int(round(rpm / 25) * 25)
        timer_seconds = self._custom_speed_timer_seconds()

        _LOGGER.debug(
            "[PumpSpeedPercentNumber] async_set_value %s%% -> %s RPM for %ss",
            value,
            rpm,
            timer_seconds,
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
                f"value={timer_seconds}",
            )
        except IAqualinkError as err:
            raise HomeAssistantError(f"Unable to set pump speed: {err}") from err

        self.coordinator.enable_fast_refresh()
        await self.coordinator.async_request_refresh()
