"""Shared device identity and cached availability."""
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
from .model import fresh


class StartechEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, key, serial=None):
        super().__init__(coordinator)
        self.serial = serial
        self.key = key
        self.identity_cache = next((d for d in coordinator.data["known_ssds"] if d["serial"] == serial), {})
        root = coordinator.data["instance_id"]
        self._attr_unique_id = f"{root}_{serial or 'controller'}_{key}"

    @property
    def device_info(self):
        data = self.coordinator.data
        root = data["instance_id"]
        if self.serial is None:
            return DeviceInfo(identifiers={(DOMAIN, root)}, name="StarTech RAID", manufacturer="StarTech",
                              model="SM22BU31C3R / ASM1352R", sw_version="161028_B5_30_81")
        identity = next((d for d in data["known_ssds"] if d["serial"] == self.serial), self.identity_cache)
        self.identity_cache = identity
        return DeviceInfo(identifiers={(DOMAIN, f"{root}_{self.serial}")},
                          name=f"StarTech SSD port {identity.get('port', '?')}", model=identity.get("model"),
                          serial_number=self.serial, sw_version=identity.get("firmware"), via_device=(DOMAIN, root))

    @property
    def available(self):
        return super().available and fresh(self.coordinator.data)
