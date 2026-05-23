import logging

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, OPMODE_SERVICE, SERVICE_MODE_REMOTE_CONTROL_ERROR

_LOGGER = logging.getLogger(__name__)


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

    @property
    def _is_service_mode(self):
        data = self.coordinator.data or {}
        return str(data.get("opmode")) == OPMODE_SERVICE

    def _raise_if_service_mode(self, action):
        if not self._is_service_mode:
            return

        _LOGGER.warning(
            "%s ignored: pump in service mode (opmode=%s)",
            action,
            OPMODE_SERVICE,
        )
        raise HomeAssistantError(SERVICE_MODE_REMOTE_CONTROL_ERROR)
