"""Tests for Battery Informer detection helpers."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_FRIENDLY_NAME, ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import State

from custom_components.battery_informer.const import LEVEL_CRITICAL, LEVEL_NORMAL, LEVEL_WARNING
from custom_components.battery_informer.detector import (
    classify_battery_level,
    get_battery_reading,
    normalize_notify_service,
    normalize_notify_target,
)
from custom_components.battery_informer.i18n import build_localized_level_message


def test_normalize_notify_service_accepts_domain_prefix() -> None:
    assert normalize_notify_service("notify.telegram") == "telegram"


def test_normalize_notify_service_rejects_invalid_name() -> None:
    try:
        normalize_notify_service("notify.bad-service")
    except ValueError as err:
        assert str(err) == "invalid_notify_service"
    else:
        raise AssertionError("ValueError was not raised")


def test_normalize_notify_target_accepts_legacy_service() -> None:
    assert normalize_notify_target("telegram") == "service:telegram"


def test_normalize_notify_target_accepts_notify_entity() -> None:
    assert normalize_notify_target("entity:notify.mobile_app_phone") == "entity:notify.mobile_app_phone"


def test_get_battery_reading_accepts_valid_battery_sensor() -> None:
    state = State(
        "sensor.window_remote_battery",
        "17",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY,
            ATTR_UNIT_OF_MEASUREMENT: "%",
            ATTR_FRIENDLY_NAME: "Window Remote Battery",
        },
    )

    reading = get_battery_reading(state)

    assert reading is not None
    assert reading.level_percent == 17
    assert reading.name == "Window Remote Battery"


def test_get_battery_reading_rejects_non_percentage_unit() -> None:
    state = State(
        "sensor.window_remote_battery",
        "17",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY,
            ATTR_UNIT_OF_MEASUREMENT: "V",
        },
    )

    assert get_battery_reading(state) is None


def test_classify_battery_level_uses_warning_and_critical_boundaries() -> None:
    assert classify_battery_level(50, 20, 10) == LEVEL_NORMAL
    assert classify_battery_level(20, 20, 10) == LEVEL_WARNING
    assert classify_battery_level(10, 20, 10) == LEVEL_CRITICAL


def test_build_english_level_message_contains_recovery_text() -> None:
    state = State(
        "sensor.window_remote_battery",
        "55",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY,
            ATTR_UNIT_OF_MEASUREMENT: "%",
            ATTR_FRIENDLY_NAME: "Window Remote Battery",
        },
    )
    reading = get_battery_reading(state)

    assert reading is not None
    message = build_localized_level_message(reading, LEVEL_NORMAL, 20, 10, "en")

    assert "Battery recovered" in message


def test_build_russian_level_message_contains_russian_text() -> None:
    state = State(
        "sensor.window_remote_battery",
        "8",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY,
            ATTR_UNIT_OF_MEASUREMENT: "%",
            ATTR_FRIENDLY_NAME: "Window Remote Battery",
        },
    )
    reading = get_battery_reading(state)

    assert reading is not None
    message = build_localized_level_message(reading, LEVEL_CRITICAL, 20, 10, "ru")

    assert "Критический заряд батареи" in message
