"""Problems suitable for alerts; never substitutes SMART for RAID state."""
from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from .entity import StartechEntity
from .model import problem

PARALLEL_UPDATES = 0


class StartechProblem(StartechEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator, key, name, serial=None):
        super().__init__(coordinator, key, serial)
        self._attr_name = name

    @property
    def is_on(self):
        return problem(self.coordinator.data, self.key, self.serial)

    @property
    def available(self):
        return super().available and self.is_on is not None

    @property
    def extra_state_attributes(self):
        if self.key == "temperature_warning":
            return {"threshold_c": self.coordinator.data["service"]["temperature_warning_c"],
                    "temperature_interpretation_verified": False, "manufacturer_limit": False}
        return None


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    async_add_entities([StartechProblem(coordinator, "raid_problem", "RAID problem"),
                        StartechProblem(coordinator, "collection_problem", "Collection problem")])
    seen = set()

    def add_new():
        entities = []
        for disk in coordinator.data["known_ssds"]:
            serial = disk["serial"]
            if serial in seen:
                continue
            seen.add(serial)
            entities.extend([StartechProblem(coordinator, "attribute_problem", "Pre-fail attribute problem", serial),
                             StartechProblem(coordinator, "temperature_warning", "Temperature warning", serial)])
        if entities:
            async_add_entities(entities)

    add_new()
    entry.async_on_unload(coordinator.async_add_listener(add_new))
