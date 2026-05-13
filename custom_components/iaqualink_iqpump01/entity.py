from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class IAqualinkPumpEntity(CoordinatorEntity):
    """Base entity for iAquaLink iQPump01."""

    def __init__(self, coordinator):
        super().__init__(coordinator)
        client = coordinator.client
        self._attr_device_info = {
            "identifiers": {(DOMAIN, client.serial)},
            "name": "iAquaLink iQPump01",
            "manufacturer": "Zodiac",
            "model": "iQPump01",
        }

    @property
    def client(self):
        return self.coordinator.client
