"""Enable newly recommended counters without overriding a user's disabled choice."""
from homeassistant.helpers import entity_registry as er

def enable_important(hass, entry_id, unique_id):
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("sensor", "startech_raid", unique_id)
    if entity_id:
        entity = registry.async_get(entity_id)
        if entity.config_entry_id == entry_id and entity.disabled_by == er.RegistryEntryDisabler.INTEGRATION:
            registry.async_update_entity(entity_id, disabled_by=None)
