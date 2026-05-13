import logging
from homeassistant.components.switch import SwitchEntity
from .const import DOMAIN
from .entity import IAqualinkPumpEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([PumpRunSwitch(coordinator)])

class PumpRunSwitch(IAqualinkPumpEntity, SwitchEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        client = coordinator.client
        self._attr_name = "Pump i2d"
        self._attr_unique_id = f"{client.serial}_pump_i2d"

    async def async_turn_on(self, **kwargs):
        await self.hass.async_add_executor_job(self.client._send_command, "/opmode/write", "value=0")
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await self.hass.async_add_executor_job(self.client._send_command, "/opmode/write", "value=2")
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self):
        data = self.coordinator.data or {}
        return data.get("runstate") == "on"

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        return {
            "serial_number": data.get("serialnumber"),
            "local_time": data.get("localtime"),
            "target_rpm": data.get("rpmtarget"),
            "temperature": data.get("motordata", {}).get("temperature"),
            "product_id": data.get("motordata", {}).get("productid"),
            "globalrpmmin": data.get("globalrpmmin"),
            "globalrpmmax": data.get("globalrpmmax"),
            "wifi_ssid": data.get("wifistatus", {}).get("ssid"),
            "wifi_state": data.get("wifistatus", {}).get("state"),
            "fwversion": data.get("fwversion"),
            "primingrpm": data.get("primingrpm"),
            "primingperiod": data.get("primingperiod"),
            "primingtimer": data.get("primingtimer"),
            "speed": data.get("motordata", {}).get("speed"),
        }
