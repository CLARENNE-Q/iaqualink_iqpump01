import logging
from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN
from .entity import IAqualinkPumpEntity

_LOGGER = logging.getLogger(__name__)

FIELDS = {
    "speed": "Pump Speed",           # motordata.speed
    "power": "Pump Power"            # motordata.power
}

async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    sensors = [PumpSensor(coordinator, key, name) for key, name in FIELDS.items()]
    async_add_entities(sensors)

class PumpSensor(IAqualinkPumpEntity, SensorEntity):
    def __init__(self, coordinator, field, name):
        super().__init__(coordinator)
        self._field = field
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.client.serial}_{field}"

        if field == "power":
            self._attr_native_unit_of_measurement = "W"
            self._attr_device_class = "power"
            self._attr_state_class = "measurement"
        elif field == "speed":
            self._attr_native_unit_of_measurement = "rpm"
            self._attr_device_class = None
            self._attr_state_class = "measurement"

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        if self._field in ["speed", "power"]:
            return data.get("motordata", {}).get(self._field)
        return None
