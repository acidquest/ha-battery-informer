"""Constants for the Battery Informer integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "battery_informer"
PLATFORMS: Final[list[str]] = ["sensor"]

CONF_WARNING_THRESHOLD: Final = "warning_threshold"
CONF_CRITICAL_THRESHOLD: Final = "critical_threshold"
CONF_NOTIFY_SERVICE: Final = "notify_service"
CONF_EXCLUDED_ENTITIES: Final = "excluded_entities"
CONF_RESCAN_INTERVAL_MINUTES: Final = "rescan_interval_minutes"
CONF_MONITORING_MODE: Final = "monitoring_mode"
CONF_INCLUDED_ENTITIES: Final = "included_entities"
CONF_WARNING_TEMPLATE: Final = "warning_template"
CONF_CRITICAL_TEMPLATE: Final = "critical_template"
CONF_RECOVERY_TEMPLATE: Final = "recovery_template"

DEFAULT_WARNING_THRESHOLD: Final = 20
DEFAULT_CRITICAL_THRESHOLD: Final = 10
DEFAULT_EXCLUDED_ENTITIES: Final[list[str]] = []
DEFAULT_RESCAN_INTERVAL_MINUTES: Final = 10
DEFAULT_MONITORING_MODE: Final = "all_except_excluded"
DEFAULT_INCLUDED_ENTITIES: Final[list[str]] = []
DEFAULT_WARNING_TEMPLATE: Final = ""
DEFAULT_CRITICAL_TEMPLATE: Final = ""
DEFAULT_RECOVERY_TEMPLATE: Final = ""

LEVEL_NORMAL: Final = "normal"
LEVEL_WARNING: Final = "warning"
LEVEL_CRITICAL: Final = "critical"

ALLOWED_BATTERY_UNIT_VALUES: Final = {"%", ""}

SERVICE_SEND_TEST_NOTIFICATION: Final = "send_test_notification"
ATTR_MESSAGE: Final = "message"
