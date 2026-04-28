"""Battery sensor detection helpers."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from homeassistant.components.notify.const import DOMAIN as NOTIFY_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_FRIENDLY_NAME, ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import State

from .const import ALLOWED_BATTERY_UNIT_VALUES, LEVEL_CRITICAL, LEVEL_NORMAL, LEVEL_WARNING

_SERVICE_NAME_RE = re.compile(r"^[a-z0-9_]+$")
_NOTIFY_ENTITY_PREFIX = "entity:"
_NOTIFY_SERVICE_PREFIX = "service:"


@dataclass(slots=True, frozen=True)
class BatteryReading:
    """Normalized battery reading."""

    entity_id: str
    name: str
    level_percent: int


def normalize_notify_service(raw_service: str) -> str:
    """Normalize a notify service name to the service identifier."""
    value = raw_service.strip().lower()
    if value.startswith("notify."):
        value = value.removeprefix("notify.")
    if not value or not _SERVICE_NAME_RE.fullmatch(value):
        raise ValueError("invalid_notify_service")
    return value


def normalize_notify_target(raw_target: str) -> str:
    """Normalize a notify target to an explicit entity or legacy service value."""
    value = raw_target.strip().lower()
    if not value:
        raise ValueError("invalid_notify_service")

    if value.startswith(_NOTIFY_ENTITY_PREFIX):
        entity_id = value.removeprefix(_NOTIFY_ENTITY_PREFIX)
        if entity_id.startswith(f"{NOTIFY_DOMAIN}.") and _SERVICE_NAME_RE.fullmatch(
            entity_id.removeprefix(f"{NOTIFY_DOMAIN}.")
        ):
            return f"{_NOTIFY_ENTITY_PREFIX}{entity_id}"
        raise ValueError("invalid_notify_service")

    if value.startswith(_NOTIFY_SERVICE_PREFIX):
        service = normalize_notify_service(value.removeprefix(_NOTIFY_SERVICE_PREFIX))
        return f"{_NOTIFY_SERVICE_PREFIX}{service}"

    if value.startswith(f"{NOTIFY_DOMAIN}."):
        suffix = value.removeprefix(f"{NOTIFY_DOMAIN}.")
        if _SERVICE_NAME_RE.fullmatch(suffix):
            return f"{_NOTIFY_ENTITY_PREFIX}{value}"

    service = normalize_notify_service(value)
    return f"{_NOTIFY_SERVICE_PREFIX}{service}"


def build_entity_option_label(state: State) -> str:
    """Build a readable label for entity selector options."""
    name = state.attributes.get(ATTR_FRIENDLY_NAME) or state.name or state.entity_id
    return f"{name} ({state.entity_id})"


def get_battery_reading(state: State | None) -> BatteryReading | None:
    """Return a normalized battery reading if the entity is supported."""
    if state is None or state.domain != SENSOR_DOMAIN:
        return None

    if state.attributes.get(ATTR_DEVICE_CLASS) != SensorDeviceClass.BATTERY:
        return None

    raw_value = _parse_percentage(state.state)
    if raw_value is None:
        return None

    raw_unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
    unit = "" if raw_unit is None else str(raw_unit).strip()
    if unit not in ALLOWED_BATTERY_UNIT_VALUES:
        return None

    name = state.attributes.get(ATTR_FRIENDLY_NAME) or state.name or state.entity_id
    return BatteryReading(
        entity_id=state.entity_id,
        name=name,
        level_percent=raw_value,
    )


def classify_battery_level(level_percent: int, warning_threshold: int, critical_threshold: int) -> str:
    """Classify a percentage into normal, warning or critical."""
    if level_percent <= critical_threshold:
        return LEVEL_CRITICAL
    if level_percent <= warning_threshold:
        return LEVEL_WARNING
    return LEVEL_NORMAL


def _parse_percentage(raw_state: Any) -> int | None:
    raw = str(raw_state).strip()
    if raw.lower() in {"unknown", "unavailable", "none"} or raw == "":
        return None

    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None

    if value < 0 or value > 100:
        return None

    return int(round(value))
