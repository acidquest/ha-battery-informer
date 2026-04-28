"""Tests for Battery Informer runtime monitoring."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_FRIENDLY_NAME, ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import State

from custom_components.battery_informer.const import (
    CONF_CRITICAL_THRESHOLD,
    CONF_EXCLUDED_ENTITIES,
    CONF_INCLUDED_ENTITIES,
    CONF_MONITORING_MODE,
    CONF_NOTIFY_SERVICE,
    CONF_RESCAN_INTERVAL_MINUTES,
    CONF_WARNING_THRESHOLD,
)
from custom_components.battery_informer.manager import BatteryInformerManager


def _build_manager(hass: object) -> BatteryInformerManager:
    return BatteryInformerManager(
        hass,
        "entry-1",
        {
            CONF_WARNING_THRESHOLD: 20,
            CONF_CRITICAL_THRESHOLD: 10,
            CONF_NOTIFY_SERVICE: "service:telegram",
            CONF_RESCAN_INTERVAL_MINUTES: 10,
            CONF_MONITORING_MODE: "all_except_excluded",
            CONF_INCLUDED_ENTITIES: [],
            CONF_EXCLUDED_ENTITIES: [],
        },
    )


@pytest.mark.asyncio
async def test_manager_sends_notification_on_level_change() -> None:
    old_state = State(
        "sensor.front_door_battery",
        "35",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY,
            ATTR_UNIT_OF_MEASUREMENT: "%",
            ATTR_FRIENDLY_NAME: "Front Door Battery",
        },
    )
    new_state = State(
        "sensor.front_door_battery",
        "19",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY,
            ATTR_UNIT_OF_MEASUREMENT: "%",
            ATTR_FRIENDLY_NAME: "Front Door Battery",
        },
    )
    hass = SimpleNamespace(
        services=SimpleNamespace(async_call=AsyncMock()),
        states=SimpleNamespace(async_all=lambda _domain=None: [old_state]),
        async_create_task=lambda coro: coro,
    )
    manager = _build_manager(hass)
    manager._initialize_snapshot()

    event = SimpleNamespace(data={"entity_id": new_state.entity_id, "old_state": old_state, "new_state": new_state})
    await manager._async_process_state_change(event)

    hass.services.async_call.assert_awaited_once()
    hass.services.async_call.assert_awaited_with(
        "notify",
        "telegram",
        {
            "message": "Battery low: Front Door Battery (sensor.front\\_door\\_battery) is at 19%. Warning threshold: 20%.",
        },
        blocking=False,
    )


@pytest.mark.asyncio
async def test_manager_does_not_send_duplicate_notification_within_same_level() -> None:
    old_state = State(
        "sensor.front_door_battery",
        "18",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY,
            ATTR_UNIT_OF_MEASUREMENT: "%",
            ATTR_FRIENDLY_NAME: "Front Door Battery",
        },
    )
    new_state = State(
        "sensor.front_door_battery",
        "17",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY,
            ATTR_UNIT_OF_MEASUREMENT: "%",
            ATTR_FRIENDLY_NAME: "Front Door Battery",
        },
    )
    hass = SimpleNamespace(
        services=SimpleNamespace(async_call=AsyncMock()),
        states=SimpleNamespace(async_all=lambda _domain=None: [old_state]),
        async_create_task=lambda coro: coro,
    )
    manager = _build_manager(hass)
    manager._initialize_snapshot()

    event = SimpleNamespace(data={"entity_id": new_state.entity_id, "old_state": old_state, "new_state": new_state})
    await manager._async_process_state_change(event)

    hass.services.async_call.assert_not_awaited()


@pytest.mark.asyncio
async def test_manager_sends_notification_via_notify_entity() -> None:
    old_state = State(
        "sensor.front_door_battery",
        "35",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY,
            ATTR_UNIT_OF_MEASUREMENT: "%",
            ATTR_FRIENDLY_NAME: "Front Door Battery",
        },
    )
    new_state = State(
        "sensor.front_door_battery",
        "19",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY,
            ATTR_UNIT_OF_MEASUREMENT: "%",
            ATTR_FRIENDLY_NAME: "Front Door Battery",
        },
    )
    hass = SimpleNamespace(
        services=SimpleNamespace(async_call=AsyncMock()),
        states=SimpleNamespace(async_all=lambda _domain=None: [old_state]),
        async_create_task=lambda coro: coro,
    )
    manager = BatteryInformerManager(
        hass,
        "entry-1",
        {
            CONF_WARNING_THRESHOLD: 20,
            CONF_CRITICAL_THRESHOLD: 10,
            CONF_NOTIFY_SERVICE: "entity:notify.mobile_app_pixel",
            CONF_RESCAN_INTERVAL_MINUTES: 10,
            CONF_MONITORING_MODE: "all_except_excluded",
            CONF_INCLUDED_ENTITIES: [],
            CONF_EXCLUDED_ENTITIES: [],
        },
    )
    manager._initialize_snapshot()

    event = SimpleNamespace(data={"entity_id": new_state.entity_id, "old_state": old_state, "new_state": new_state})
    await manager._async_process_state_change(event)

    hass.services.async_call.assert_awaited_once()
    hass.services.async_call.assert_awaited_with(
        "notify",
        "send_message",
        {
            "entity_id": "notify.mobile_app_pixel",
            "message": "Battery low: Front Door Battery (sensor.front_door_battery) is at 19%. Warning threshold: 20%.",
        },
        blocking=False,
    )


@pytest.mark.asyncio
async def test_manager_sends_lowest_battery_notification() -> None:
    state = State(
        "sensor.front_door_battery",
        "19",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY,
            ATTR_UNIT_OF_MEASUREMENT: "%",
            ATTR_FRIENDLY_NAME: "Front Door Battery",
        },
    )
    hass = SimpleNamespace(
        config=SimpleNamespace(language="en"),
        services=SimpleNamespace(async_call=AsyncMock()),
        states=SimpleNamespace(async_all=lambda _domain=None: [state]),
        async_create_task=lambda coro: coro,
    )
    manager = _build_manager(hass)

    result = await manager.async_send_lowest_battery_notification()

    assert result is True
    hass.services.async_call.assert_awaited_once_with(
        "notify",
        "telegram",
        {
            "message": "Lowest tracked battery: Front Door Battery (sensor.front\\_door\\_battery) is at 19%. Current status: warning.",
        },
        blocking=False,
    )


@pytest.mark.asyncio
async def test_manager_does_not_add_telegram_payload_for_non_telegram_target() -> None:
    state = State(
        "sensor.front_door_battery",
        "19",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY,
            ATTR_UNIT_OF_MEASUREMENT: "%",
            ATTR_FRIENDLY_NAME: "Front Door Battery",
        },
    )
    hass = SimpleNamespace(
        config=SimpleNamespace(language="en"),
        services=SimpleNamespace(async_call=AsyncMock()),
        states=SimpleNamespace(async_all=lambda _domain=None: [state]),
        async_create_task=lambda coro: coro,
    )
    manager = BatteryInformerManager(
        hass,
        "entry-1",
        {
            CONF_WARNING_THRESHOLD: 20,
            CONF_CRITICAL_THRESHOLD: 10,
            CONF_NOTIFY_SERVICE: "service:mobile_app_pixel",
            CONF_RESCAN_INTERVAL_MINUTES: 10,
            CONF_MONITORING_MODE: "all_except_excluded",
            CONF_INCLUDED_ENTITIES: [],
            CONF_EXCLUDED_ENTITIES: [],
        },
    )

    result = await manager.async_send_lowest_battery_notification()

    assert result is True
    hass.services.async_call.assert_awaited_once_with(
        "notify",
        "mobile_app_pixel",
        {
            "message": "Lowest tracked battery: Front Door Battery (sensor.front_door_battery) is at 19%. Current status: warning."
        },
        blocking=False,
    )


@pytest.mark.asyncio
async def test_manager_localizes_lowest_battery_notification_message() -> None:
    state = State(
        "sensor.front_door_battery",
        "9",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY,
            ATTR_UNIT_OF_MEASUREMENT: "%",
            ATTR_FRIENDLY_NAME: "Front Door Battery",
        },
    )
    hass = SimpleNamespace(
        config=SimpleNamespace(language="ru"),
        services=SimpleNamespace(async_call=AsyncMock()),
        states=SimpleNamespace(async_all=lambda _domain=None: [state]),
        async_create_task=lambda coro: coro,
    )
    manager = _build_manager(hass)

    result = await manager.async_send_lowest_battery_notification()

    assert result is True
    hass.services.async_call.assert_awaited_once_with(
        "notify",
        "telegram",
        {
            "message": "Самая разряженная батарея: Front Door Battery (sensor.front\\_door\\_battery) имеет 9%. Текущий статус: критический.",
        },
        blocking=False,
    )


@pytest.mark.asyncio
async def test_manager_include_only_mode_ignores_non_included_entity() -> None:
    old_state = State(
        "sensor.front_door_battery",
        "35",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY,
            ATTR_UNIT_OF_MEASUREMENT: "%",
            ATTR_FRIENDLY_NAME: "Front Door Battery",
        },
    )
    new_state = State(
        "sensor.front_door_battery",
        "19",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY,
            ATTR_UNIT_OF_MEASUREMENT: "%",
            ATTR_FRIENDLY_NAME: "Front Door Battery",
        },
    )
    hass = SimpleNamespace(
        services=SimpleNamespace(async_call=AsyncMock()),
        states=SimpleNamespace(async_all=lambda _domain=None: [old_state]),
        async_create_task=lambda coro: coro,
    )
    manager = BatteryInformerManager(
        hass,
        "entry-1",
        {
            CONF_WARNING_THRESHOLD: 20,
            CONF_CRITICAL_THRESHOLD: 10,
            CONF_NOTIFY_SERVICE: "service:telegram",
            CONF_RESCAN_INTERVAL_MINUTES: 10,
            CONF_MONITORING_MODE: "include_only",
            CONF_INCLUDED_ENTITIES: [],
            CONF_EXCLUDED_ENTITIES: [],
        },
    )
    manager._initialize_snapshot()

    event = SimpleNamespace(data={"entity_id": new_state.entity_id, "old_state": old_state, "new_state": new_state})
    await manager._async_process_state_change(event)

    assert manager.get_summary()["tracked_count"] == 0
    hass.services.async_call.assert_not_awaited()


@pytest.mark.asyncio
async def test_manager_uses_custom_message_template() -> None:
    old_state = State(
        "sensor.front_door_battery",
        "35",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY,
            ATTR_UNIT_OF_MEASUREMENT: "%",
            ATTR_FRIENDLY_NAME: "Front Door Battery",
        },
    )
    new_state = State(
        "sensor.front_door_battery",
        "19",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY,
            ATTR_UNIT_OF_MEASUREMENT: "%",
            ATTR_FRIENDLY_NAME: "Front Door Battery",
        },
    )
    hass = SimpleNamespace(
        services=SimpleNamespace(async_call=AsyncMock()),
        states=SimpleNamespace(async_all=lambda _domain=None: [old_state]),
        async_create_task=lambda coro: coro,
    )
    manager = BatteryInformerManager(
        hass,
        "entry-1",
        {
            CONF_WARNING_THRESHOLD: 20,
            CONF_CRITICAL_THRESHOLD: 10,
            CONF_NOTIFY_SERVICE: "service:telegram",
            CONF_RESCAN_INTERVAL_MINUTES: 10,
            CONF_MONITORING_MODE: "all_except_excluded",
            CONF_INCLUDED_ENTITIES: [],
            CONF_EXCLUDED_ENTITIES: [],
            "warning_template": "Warn {name} {level} {status}",
        },
    )
    manager._initialize_snapshot()

    event = SimpleNamespace(data={"entity_id": new_state.entity_id, "old_state": old_state, "new_state": new_state})
    await manager._async_process_state_change(event)

    hass.services.async_call.assert_awaited_once_with(
        "notify",
        "telegram",
        {"message": "Warn Front Door Battery 19% warning"},
        blocking=False,
    )
