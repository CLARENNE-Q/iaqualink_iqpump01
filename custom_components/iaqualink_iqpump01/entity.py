from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class IAqualinkPumpEntity(CoordinatorEntity):
    """Base entity for iAquaLink iQPump01."""

    def __init__(self, coordinator):
        super().__init__(coordinator)
        client = coordinator.client
        device_label = self._device_label(client)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, client.serial)},
            "name": f"iAquaLink iQPump01 {device_label}",
            "manufacturer": "Zodiac",
            "model": "iQPump01",
        }

    @staticmethod
    def _device_label(client):
        device = client.device or {}
        return (
            device.get("name")
            or device.get("device_name")
            or device.get("deviceName")
            or device.get("label")
            or device.get("location_name")
            or device.get("locationName")
            or client.serial
        )

    @property
    def client(self):
        return self.coordinator.client

    def _raise_if_service_mode(self, action):
        self.coordinator.raise_if_service_mode(action)
