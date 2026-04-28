"""Tests for Battery Informer config flow helpers."""

from __future__ import annotations

from types import SimpleNamespace

from custom_components.battery_informer.config_flow import _get_notify_service_options


def test_get_notify_service_options_filters_builtin_notify_services() -> None:
    hass = SimpleNamespace(
        services=SimpleNamespace(
            async_services=lambda: {
                "notify": {
                    "notify": object(),
                    "send_message": object(),
                    "mobile_app_pixel": object(),
                    "telegram_home": object(),
                }
            }
        )
    )

    options = _get_notify_service_options(hass, "")

    assert [option["value"] for option in options] == ["mobile_app_pixel", "telegram_home"]
    assert [option["label"] for option in options] == ["notify.mobile_app_pixel", "notify.telegram_home"]


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

    options = _get_notify_service_options(hass, "legacy_telegram")

    assert [option["value"] for option in options] == ["telegram_home", "legacy_telegram"]
