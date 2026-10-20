"""Redacted diagnostics and a dashboard using actual registered entity IDs."""
from homeassistant.helpers import entity_registry as er


async def async_get_config_entry_diagnostics(hass, entry):
    coordinator = entry.runtime_data
    data = coordinator.data
    registry = er.async_get(hass)
    entities = [e for e in er.async_entries_for_config_entry(registry, entry.entry_id) if not e.disabled_by]
    temperature_ids = [e.entity_id for e in entities if e.unique_id.endswith("_temperature_candidate_c")]
    overview_ids = [e.entity_id for e in entities if any(e.unique_id.endswith("_" + key) for key in ("raid_status", "raid_problem", "collection_problem", "sample_time_unix", "smart_collection"))]
    cards = [{"type": "entities", "title": "StarTech RAID health", "entities": overview_ids}]
    if temperature_ids:
        cards.append({"type": "history-graph", "title": "SSD temperature candidates", "hours_to_show": 48, "entities": temperature_ids})
    return {"app_version": data.get("app_version"), "backend_version": data.get("tool_version"),
            "fresh": data.get("fresh"), "query_ok": data.get("query_ok"),
            "raid_raw": data.get("raid_raw"), "raid_status": data.get("raid_status"),
            "smart_complete": data.get("smart_complete"), "service": data.get("service"),
            "ssd_summary": [{"port": d.get("port"), "identity_verified": d.get("identity_verified"),
                             "smart_data_valid": d.get("smart_data_valid"), "smart_thresholds_valid": d.get("smart_thresholds_valid"),
                             "attribute_check": d.get("attribute_check"), "attribute_count": len(d.get("attributes", [])),
                             "temperature_candidate_c": d.get("temperature_candidate_c")} for d in data.get("ssds", [])],
            "dashboard": {"title": "StarTech RAID", "views": [{"title": "Health", "path": "health", "cards": cards}]},
            "privacy": "Credentials, instance UUID, serials and raw sectors are omitted; dashboard contains actual HA entity IDs."}
