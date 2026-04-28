"""Tests for Battery Informer config flow helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from custom_components.battery_informer.config_flow import (
    _build_options_schema,
    _get_notify_service_options,
    _validate_notify_service,
)


def test_get_notify_service_options_filters_builtin_notify_services() -> None:
    hass = SimpleNamespace(
        services=SimpleNamespace(
            async_services=lambda: {
                "notify": {
                    "notify": object(),
                    "send_message": object(),
                    "persistent_notification": object(),
                    "mobile_app_pixel": object(),
                    "telegram_home": object(),
                }
            }
        )
    )
    entity_registry = SimpleNamespace(
        entities={
            "notify.mobile_app_pixel": SimpleNamespace(
                entity_id="notify.mobile_app_pixel",
                domain="notify",
                disabled_by=None,
                name="Pixel 9",
                original_name=None,
            )
        }
    )

    with patch(
        "custom_components.battery_informer.config_flow.er.async_get",
        return_value=entity_registry,
    ):
        options = _get_notify_service_options(hass, "")

    assert [option["value"] for option in options] == [
        "entity:notify.mobile_app_pixel",
        "service:mobile_app_pixel",
        "service:telegram_home",
    ]
    assert [option["label"] for option in options] == [
        "Pixel 9 (notify.mobile_app_pixel)",
        "Legacy service (notify.mobile_app_pixel)",
        "Legacy service (notify.telegram_home)",
    ]


def test_get_notify_service_options_preserves_current_missing_service() -> None:
    hass = SimpleNamespace(
        services=SimpleNamespace(
            async_services=lambda: {
                "notify": {
                    "telegram_home": object(),
                }
            }
        )
    )
    entity_registry = SimpleNamespace(entities={})

    with patch(
        "custom_components.battery_informer.config_flow.er.async_get",
        return_value=entity_registry,
    ):
        options = _get_notify_service_options(hass, "legacy_telegram")

    assert [option["value"] for option in options] == [
        "service:telegram_home",
        "service:legacy_telegram",
    ]


def test_validate_notify_service_resolves_notify_entity() -> None:
    hass = SimpleNamespace(
        services=SimpleNamespace(has_service=lambda _domain, _service: False),
    )
    entity_registry = SimpleNamespace(async_get=lambda entity_id: object() if entity_id == "notify.mobile_app_pixel" else None)

    with patch(
        "custom_components.battery_informer.config_flow.er.async_get",
        return_value=entity_registry,
    ):
        assert _validate_notify_service(hass, "notify.mobile_app_pixel") == "entity:notify.mobile_app_pixel"


def test_validate_notify_service_resolves_legacy_service() -> None:
    hass = SimpleNamespace(
        services=SimpleNamespace(has_service=lambda domain, service: domain == "notify" and service == "telegram"),
    )
    entity_registry = SimpleNamespace(async_get=lambda _entity_id: None)

    with patch(
        "custom_components.battery_informer.config_flow.er.async_get",
        return_value=entity_registry,
    ):
        assert _validate_notify_service(hass, "notify.telegram") == "service:telegram"


def test_build_options_schema_normalizes_legacy_notify_default() -> None:
    hass = SimpleNamespace(
        states=SimpleNamespace(async_all=lambda _domain=None: []),
        services=SimpleNamespace(
            async_services=lambda: {
                "notify": {
                    "telegram": object(),
                }
            }
        )
    )
    config_entry = SimpleNamespace(
        options={},
        data={
            "warning_threshold": 20,
            "critical_threshold": 10,
            "notify_service": "telegram",
            "rescan_interval_minutes": 10,
            "excluded_entities": [],
        },
    )
    entity_registry = SimpleNamespace(entities={})

    with patch(
        "custom_components.battery_informer.config_flow.er.async_get",
        return_value=entity_registry,
    ):
        schema = _build_options_schema(config_entry, hass)

    notify_marker = next(
        key for key in schema.schema if getattr(key, "schema", None) == "notify_service"
    )
    assert notify_marker.default() == "service:telegram"
    rescan_marker = next(
        key for key in schema.schema if getattr(key, "schema", None) == "rescan_interval_minutes"
    )
    assert rescan_marker.default() == 10
    warning_template_marker = next(
        key for key in schema.schema if getattr(key, "schema", None) == "warning_template"
    )
    assert warning_template_marker.default()
    reset_templates_marker = next(
        key for key in schema.schema if getattr(key, "schema", None) == "reset_templates_to_default"
    )
    assert reset_templates_marker.default() is False
