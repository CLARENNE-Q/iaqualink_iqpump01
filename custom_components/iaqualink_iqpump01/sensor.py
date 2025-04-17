import logging
from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

FIELDS = {
    "speed": "Pump Speed",           # motordata.speed
    "power": "Pump Power"            # motordata.power
}

async def async_setup_entry(hass, config_entry, async_add_entities):
    client = hass.data[DOMAIN][config_entry.entry_id]
    sensors = [PumpSensor(client, key, name) for key, name in FIELDS.items()]
    async_add_entities(sensors, update_before_add=True)

class PumpSensor(SensorEntity):
    def __init__(self, client, field, name):
        self._client = client
        self._field = field
        self._attr_name = name
        self._attr_unique_id = f"{client.serial}_{field}"
        self._state = None

        if field == "power":
            self._attr_native_unit_of_measurement = "W"
            self._attr_device_class = "power"
            self._attr_state_class = "measurement"
        elif field == "speed":
            self._attr_native_unit_of_measurement = "rpm"
            self._attr_device_class = None
            self._attr_state_class = "measurement"

    @property
    def state(self):
        return self._state

    async def async_update(self):
        data = await self.hass.async_add_executor_job(self._client.refresh_data)
        if self._field in ["speed", "power"]:
            self._state = data.get("motordata", {}).get(self._field)