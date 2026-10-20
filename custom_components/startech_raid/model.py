"""Pure entity value/availability model, independent of HA imports."""
from dataclasses import dataclass
import math
import time
from .smart import indicators

LABELS = {1: "Healthy", 2: "Degraded", 3: "Failed", 4: "Rebuilding"}


def validate(data):
    if (not isinstance(data, dict) or data.get("api_version") != 1
            or not isinstance(data.get("instance_id"), str)
            or not isinstance(data.get("service"), dict)
            or not isinstance(data.get("known_ssds"), list)
            or not isinstance(data.get("ssds"), list)
            or type(data.get("query_ok")) is not bool or type(data.get("fresh")) is not bool):
        raise ValueError("Invalid StarTech API response")
    if data["query_ok"] and (type(data.get("raid_raw")) is not int or not 0 <= data["raid_raw"] <= 255 or data.get("raid_status") != LABELS.get(data["raid_raw"], "Unknown")):
        raise ValueError("Inconsistent RAID status")
    stamp = data.get("sample_time_unix")
    ttl = data["service"].get("stale_after_seconds")
    if type(stamp) not in (int, float) or not math.isfinite(stamp) or type(ttl) is not int or not 180 <= ttl <= 10800:
        raise ValueError("Invalid freshness data")
    seen = set()
    for disk in data["ssds"]:
        if not isinstance(disk, dict) or type(disk.get("identity_verified")) is not bool or not isinstance(disk.get("attributes", []), list):
            raise ValueError("Invalid current SSD record")
        for attr in disk.get("attributes", []):
            if not isinstance(attr, dict) or type(attr.get("id")) is not int or not 1 <= attr["id"] <= 255:
                raise ValueError("Invalid current SMART attribute")
    for disk in data["known_ssds"]:
        if not isinstance(disk, dict) or not isinstance(disk.get("serial"), str) or not disk["serial"] or disk["serial"] in seen:
            raise ValueError("Invalid known SSD identities")
        seen.add(disk["serial"])
    return data


def fresh(data, now=None):
    now = time.time() if now is None else now
    return (data.get("fresh", False) and 0 <= now - data.get("sample_time_unix", 0)
            < data.get("service", {}).get("stale_after_seconds", 0))


def current_disk(data, serial):
    if not fresh(data) or not data.get("query_ok") or data.get("duplicate_ssd_identity"):
        return None
    return next((d for d in data.get("ssds", []) if d.get("serial") == serial and d.get("identity_verified")), None)


@dataclass(frozen=True)
class Spec:
    key: str
    name: str
    kind: str = "text"
    diagnostic: bool = False
    disabled: bool = False


ARRAY_SPECS = (
    Spec("raid_status", "RAID status", "raid"), Spec("raid_raw", "Controller state byte", "number", True),
    Spec("sample_time_unix", "Last collection", "timestamp", True),
    Spec("smart_collection", "SSD collection", "smart"),
    Spec("duration_ms", "Collection duration", "duration", True),
    Spec("next_collection_unix", "Next collection", "timestamp", True),
)
DRIVE_SPECS = (
    Spec("temperature_candidate_c", "Temperature candidate", "temperature"),
    Spec("attribute_check", "Pre-fail attribute health", "attribute"),
    Spec("capacity_bytes", "Capacity", "capacity", True), Spec("model", "Model", diagnostic=True),
    Spec("serial", "Serial number", diagnostic=True), Spec("firmware", "Firmware", diagnostic=True),
    Spec("smart_overall_health", "SMART overall health", diagnostic=True),
    Spec("attributes_compared", "Pre-fail attributes compared", "number", True),
    Spec("failed_prefail_attributes", "Failed pre-fail attributes", "number", True),
)


def sensor_value(data, spec, serial=None):
    if serial is None:
        if spec.key in ("duration_ms", "next_collection_unix"):
            return data["service"].get(spec.key)
        if spec.key == "smart_collection":
            if data["service"].get("smart_paused"):
                return "Paused after error"
            if not data["service"].get("smart_enabled"):
                return "Disabled"
            return "Complete" if data.get("smart_complete") else "Incomplete"
        return data.get(spec.key)
    disk = current_disk(data, serial)
    if disk is None:
        return None
    if spec.key.startswith("raw_"):
        attr = next((a for a in disk.get("attributes", []) if a["id"] == int(spec.key[4:])), None)
        return attr.get("raw") if attr and disk.get("smart_data_valid") else None
    if spec.key == "capacity_bytes":
        return disk.get("capacity_bytes") / 1e9 if disk.get("capacity_bytes") else None
    if spec.key == "temperature_candidate_c" and not disk.get("smart_data_valid"):
        return None
    if spec.key in ("attribute_check", "attributes_compared", "failed_prefail_attributes") and not (disk.get("smart_data_valid") and disk.get("smart_thresholds_valid")):
        return None
    return disk.get(spec.key)


def problem(data, key, serial=None):
    if not fresh(data):
        return None
    if serial is None:
        if key == "collection_problem":
            return bool(not data.get("query_ok") or data.get("duplicate_ssd_identity", False) or data["service"].get("persistence_error") or (data["service"].get("smart_enabled") and not data.get("smart_complete")))
        return None if not data.get("query_ok") or data.get("raid_raw") not in LABELS else data["raid_raw"] != 1
    disk = current_disk(data, serial)
    if disk is None:
        return None
    if key in ("media_error_warning", "interface_error_warning", "life_warning"):
        return indicators(disk)[key]
    if key == "temperature_warning":
        temp = disk.get("temperature_candidate_c")
        return temp >= data["service"]["temperature_warning_c"] if type(temp) in (int, float) else None
    return disk["attribute_check"] == "Failed" if disk.get("attribute_check") in ("Passed", "Failed") and disk.get("smart_thresholds_valid") else None
