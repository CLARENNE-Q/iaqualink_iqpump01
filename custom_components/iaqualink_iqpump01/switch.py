import logging
from homeassistant.components.switch import SwitchEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    client = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([PumpRunSwitch(client)], update_before_add=True)

class PumpRunSwitch(SwitchEntity):
    def __init__(self, client):
        self._client = client
        self._attr_name = "Pump i2d"
        self._attr_unique_id = f"{client.serial}_pump_i2d"
        self._state = False
        self._attr_device_info = {
            "identifiers": {(DOMAIN, client.serial)},
            "name": "iAquaLink iQPump01",
            "manufacturer": "Zodiac",
            "model": "iQPump01",
        }

    async def async_turn_on(self, **kwargs):
        await self.hass.async_add_executor_job(self._client._send_command, "/opmode/write", "value=0")
        self._state = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self.hass.async_add_executor_job(self._client._send_command, "/opmode/write", "value=2")
        self._state = False
        self.async_write_ha_state()

    @property
    def is_on(self):
        return self._state

    async def async_update(self):
        data = await self.hass.async_add_executor_job(self._client.refresh_data)
        self._state = data.get("runstate") == "on"
        self._attr_extra_state_attributes = {
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