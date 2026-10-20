"""RAID, SSD identity, temperature, threshold and optional raw attribute sensors."""
from datetime import datetime, timezone
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
from .entity import StartechEntity
from .model import ARRAY_SPECS, DRIVE_SPECS, Spec, current_disk, sensor_value

PARALLEL_UPDATES = 0


class StartechSensor(StartechEntity, SensorEntity):
    def __init__(self, coordinator, spec, serial=None):
        super().__init__(coordinator, spec.key, serial)
        self.spec = spec
        self._attr_name = spec.name
        self._attr_entity_registry_enabled_default = not spec.disabled
        if spec.diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        if spec.kind in ("raid", "smart", "attribute"):
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = {"raid": ["Healthy", "Degraded", "Failed", "Rebuilding", "Unknown"],
                                  "smart": ["Complete", "Incomplete", "Disabled", "Paused after error"],
                                  "attribute": ["Passed", "Failed", "Unknown"]}[spec.kind]
        elif spec.kind == "temperature":
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = "°C"
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_suggested_display_precision = 0
        elif spec.kind == "capacity":
            self._attr_device_class = SensorDeviceClass.DATA_SIZE
            self._attr_native_unit_of_measurement = "GB"
            self._attr_suggested_display_precision = 2
        elif spec.kind == "timestamp":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
        elif spec.kind == "duration":
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_native_unit_of_measurement = "ms"
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        value = sensor_value(self.coordinator.data, self.spec, self.serial)
        if self.spec.kind == "timestamp":
            return datetime.fromtimestamp(value, timezone.utc) if value else None
        return value

    @property
    def available(self):
        return super().available and (self.serial is None or self.native_value is not None)

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        if self.serial is None:
            return {"controller_raw_state": data.get("raid_raw"), "mapping_validation": "static_reverse_engineering",
                    "array_synchronization_verified": False, "error": data.get("error")}
        disk = current_disk(data, self.serial)
        if not disk:
            return None
        if self.spec.kind == "temperature":
            return {"interpretation_verified": False, "smart_attribute": disk.get("temperature_attribute"),
                    "source": disk.get("temperature_source")}
        if self.spec.kind == "capacity":
            return {"capacity_bytes": disk.get("capacity_bytes")}
        if self.spec.key.startswith("raw_"):
            attr = next((a for a in disk.get("attributes", []) if a["id"] == int(self.spec.key[4:])), {})
            return {k: attr.get(k) for k in ("id", "normalized", "worst", "threshold", "flags", "raw_hex")}
        if self.spec.key == "attribute_check":
            return {"attributes_compared": disk.get("attributes_compared"),
                    "failed_prefail_attributes": disk.get("failed_prefail_attributes"), "smart_overall_health": "Unknown"}
        return None


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    seen = set()

    def add_new():
        entities = []
        for spec in ARRAY_SPECS:
            marker = (None, spec.key)
            if marker not in seen:
                seen.add(marker)
                entities.append(StartechSensor(coordinator, spec))
        for identity in coordinator.data["known_ssds"]:
            serial = identity["serial"]
            specs = list(DRIVE_SPECS)
            disk = current_disk(coordinator.data, serial)
            if disk and disk.get("smart_data_valid"):
                specs += [Spec(f"raw_{a['id']}", f"SMART {a['id']} raw", "number", True, True) for a in disk.get("attributes", [])]
            for spec in specs:
                marker = (serial, spec.key)
                if marker not in seen:
                    seen.add(marker)
                    entities.append(StartechSensor(coordinator, spec, serial))
        if entities:
            async_add_entities(entities)

    add_new()
    entry.async_on_unload(coordinator.async_add_listener(add_new))
