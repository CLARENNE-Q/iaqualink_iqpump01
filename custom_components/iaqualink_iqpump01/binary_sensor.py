import logging

from homeassistant.components.binary_sensor import BinarySensorEntity

from .const import DOMAIN
from .entity import IAqualinkPumpEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([PumpPrimingBinarySensor(coordinator)])


class PumpPrimingBinarySensor(IAqualinkPumpEntity, BinarySensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        client = coordinator.client
        self._attr_name = "Pump Priming"
        self._attr_unique_id = f"{client.serial}_priming"
        self._attr_icon = "mdi:timer-sand"

    @property
    def is_on(self):
        data = self.coordinator.data or {}
        timer = self._coerce_int(data.get("primingtimer"))
        if timer is None:
            return None
        return timer >= 0

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        return {
            "priming_timer": self._coerce_int(data.get("primingtimer")),
            "priming_period": self._coerce_int(data.get("primingperiod")),
            "priming_rpm": self._coerce_int(data.get("primingrpm")),
            "motor_speed": self._coerce_int(data.get("motordata", {}).get("speed")),
            "target_rpm": self._coerce_int(data.get("rpmtarget")),
            "runstate": data.get("runstate"),
            "opmode": data.get("opmode"),
        }

    @staticmethod
    def _coerce_int(value):
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
