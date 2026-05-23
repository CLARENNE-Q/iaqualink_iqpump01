import logging
from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN, OPMODE_SERVICE
from .entity import IAqualinkPumpEntity

_LOGGER = logging.getLogger(__name__)

FIELDS = {
    "speed": {
        "name": "Pump Speed",
        "path": ("motordata", "speed"),
        "unit": "rpm",
        "state_class": "measurement",
    },
    "power": {
        "name": "Pump Power",
        "path": ("motordata", "power"),
        "unit": "W",
        "device_class": "power",
        "state_class": "measurement",
    },
    "opmode": {
        "name": "Pump Operating Mode",
        "path": ("opmode",),
    },
    "rpmtarget": {
        "name": "Pump Target RPM",
        "path": ("rpmtarget",),
        "unit": "rpm",
    },
    "customspeedrpm": {
        "name": "Pump Custom Speed RPM",
        "path": ("customspeedrpm",),
        "unit": "rpm",
    },
    "customspeedtimer": {
        "name": "Pump Custom Speed Timer",
        "path": ("customspeedtimer",),
        "unit": "s",
    },
}
OPMODE_LABELS = {
    "0": "auto",
    "1": "custom",
    "2": "off",
    "3": "quick clean",
    "4": "timed run",
    "5": "timed stop",
    OPMODE_SERVICE: "off",
}

async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    sensors = [PumpSensor(coordinator, key, description) for key, description in FIELDS.items()]
    async_add_entities(sensors)

class PumpSensor(IAqualinkPumpEntity, SensorEntity):
    def __init__(self, coordinator, field, description):
        super().__init__(coordinator)
        self._field = field
        self._description = description
        self._attr_name = description["name"]
        self._attr_unique_id = f"{coordinator.client.serial}_{field}"

        self._attr_native_unit_of_measurement = description.get("unit")
        self._attr_device_class = description.get("device_class")
        self._attr_state_class = description.get("state_class")

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        value = self._value_from_path(data, self._description["path"])
        if self._field == "opmode" and value is not None:
            return OPMODE_LABELS.get(str(value), str(value))
        return self._coerce_number(value)

    @property
    def extra_state_attributes(self):
        if self._field != "opmode":
            return None

        data = self.coordinator.data or {}
        return {
            "opmode": data.get("opmode"),
            "runstate": data.get("runstate"),
            "rpmtarget": data.get("rpmtarget"),
            "customspeedrpm": data.get("customspeedrpm"),
            "customspeedtimer": data.get("customspeedtimer"),
        }

    @staticmethod
    def _value_from_path(data, path):
        value = data
        for key in path:
            if not isinstance(value, dict):
                return None
            value = value.get(key)
        return value

    @staticmethod
    def _coerce_number(value):
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return value
