"""Localization helpers for Battery Informer."""

from __future__ import annotations

from typing import Final

from homeassistant.core import HomeAssistant

from .const import (
    DEFAULT_CRITICAL_TEMPLATE,
    DEFAULT_RECOVERY_TEMPLATE,
    DEFAULT_WARNING_TEMPLATE,
    LEVEL_CRITICAL,
    LEVEL_NORMAL,
    LEVEL_WARNING,
)
from .detector import BatteryReading

LANG_EN: Final = "en"
LANG_RU: Final = "ru"


def get_hass_language(hass: HomeAssistant) -> str:
    """Return the active Home Assistant language."""
    config = getattr(hass, "config", None)
    language = getattr(config, "language", LANG_EN) or LANG_EN
    normalized = str(language).strip().lower()
    if normalized.startswith("ru"):
        return LANG_RU
    return LANG_EN


def get_default_message_templates(language: str) -> dict[str, str]:
    """Return localized default message templates."""
    if language == LANG_RU:
        return {
            "warning_template": "Низкий заряд батареи: {name} ({entity_id}) {details_warning}",
            "critical_template": "Критический заряд батареи: {name} ({entity_id}) {details_critical}",
            "recovery_template": "Заряд восстановлен: {name} ({entity_id}) {details_recovery}",
        }
    return {
        "warning_template": DEFAULT_WARNING_TEMPLATE,
        "critical_template": DEFAULT_CRITICAL_TEMPLATE,
        "recovery_template": DEFAULT_RECOVERY_TEMPLATE,
    }


def build_localized_level_message(
    reading: BatteryReading,
    new_level: str,
    warning_threshold: int,
    critical_threshold: int,
    language: str,
    warning_template: str = "",
    critical_template: str = "",
    recovery_template: str = "",
) -> str:
    """Build a user-facing notification in the requested language."""
    if new_level == LEVEL_WARNING and warning_template.strip():
        return _render_message_template(
            warning_template,
            reading,
            new_level,
            warning_threshold,
            critical_threshold,
            language,
        )

    if new_level == LEVEL_CRITICAL and critical_template.strip():
        return _render_message_template(
            critical_template,
            reading,
            new_level,
            warning_threshold,
            critical_threshold,
            language,
        )

    if new_level == LEVEL_NORMAL and recovery_template.strip():
        return _render_message_template(
            recovery_template,
            reading,
            new_level,
            warning_threshold,
            critical_threshold,
            language,
        )

    if language == LANG_RU:
        return _build_russian_level_message(
            reading,
            new_level,
            warning_threshold,
            critical_threshold,
        )

    return _build_english_level_message(
        reading,
        new_level,
        warning_threshold,
        critical_threshold,
    )


def _build_english_level_message(
    reading: BatteryReading,
    new_level: str,
    warning_threshold: int,
    critical_threshold: int,
) -> str:
    if new_level == LEVEL_WARNING:
        if reading.level_percent is None:
            return (
                f"Battery low: {reading.name} ({reading.entity_id}) reports a low-battery condition."
            )
        return (
            f"Battery low: {reading.name} ({reading.entity_id}) is at "
            f"{reading.level_percent}%. Warning threshold: {warning_threshold}%."
        )

    if new_level == LEVEL_CRITICAL:
        if reading.level_percent is None:
            return (
                f"Battery critical: {reading.name} ({reading.entity_id}) reports a low-battery condition. "
                f"Replace or recharge the battery soon."
            )
        return (
            f"Battery critical: {reading.name} ({reading.entity_id}) is at "
            f"{reading.level_percent}%. Replace or recharge the battery soon. "
            f"Critical threshold: {critical_threshold}%."
        )

    if reading.level_percent is None:
        return (
            f"Battery recovered: {reading.name} ({reading.entity_id}) no longer reports a low-battery condition."
        )

    return (
        f"Battery recovered: {reading.name} ({reading.entity_id}) is back to "
        f"{reading.level_percent}% and above the warning threshold."
    )


def _build_russian_level_message(
    reading: BatteryReading,
    new_level: str,
    warning_threshold: int,
    critical_threshold: int,
) -> str:
    if new_level == LEVEL_WARNING:
        if reading.level_percent is None:
            return (
                f"Низкий заряд батареи: {reading.name} ({reading.entity_id}) сообщает о низком заряде батареи."
            )
        return (
            f"Низкий заряд батареи: {reading.name} ({reading.entity_id}) имеет "
            f"{reading.level_percent}%. Порог предупреждения: {warning_threshold}%."
        )

    if new_level == LEVEL_CRITICAL:
        if reading.level_percent is None:
            return (
                f"Критический заряд батареи: {reading.name} ({reading.entity_id}) сообщает о низком заряде батареи. "
                f"Замените батарею или зарядите устройство как можно скорее."
            )
        return (
            f"Критический заряд батареи: {reading.name} ({reading.entity_id}) имеет "
            f"{reading.level_percent}%. Замените батарею или зарядите устройство как можно скорее. "
            f"Критический порог: {critical_threshold}%."
        )

    if new_level == LEVEL_NORMAL:
        if reading.level_percent is None:
            return (
                f"Заряд восстановлен: {reading.name} ({reading.entity_id}) больше не сообщает о низком заряде батареи."
            )
        return (
            f"Заряд восстановлен: {reading.name} ({reading.entity_id}) снова имеет "
            f"{reading.level_percent}% и находится выше порога предупреждения."
        )

    return _build_english_level_message(
        reading,
        new_level,
        warning_threshold,
        critical_threshold,
    )


def _render_message_template(
    template: str,
    reading: BatteryReading,
    new_level: str,
    warning_threshold: int,
    critical_threshold: int,
    language: str,
) -> str:
    context = _SafeFormatDict(
        entity_id=reading.entity_id,
        name=reading.name,
        level_percent="" if reading.level_percent is None else reading.level_percent,
        level="" if reading.level_percent is None else f"{reading.level_percent}%",
        warning_threshold=warning_threshold,
        critical_threshold=critical_threshold,
        status=new_level,
        is_binary=str(reading.is_binary).lower(),
        details_warning=_build_details_warning(reading, warning_threshold, language),
        details_critical=_build_details_critical(reading, critical_threshold, language),
        details_recovery=_build_details_recovery(reading, language),
    )
    return template.format_map(context)


def _build_details_warning(
    reading: BatteryReading,
    warning_threshold: int,
    language: str,
) -> str:
    if language == LANG_RU:
        if reading.level_percent is None:
            return "сообщает о низком заряде батареи."
        return f"имеет {reading.level_percent}%. Порог предупреждения: {warning_threshold}%."

    if reading.level_percent is None:
        return "reports a low-battery condition."
    return f"is at {reading.level_percent}%. Warning threshold: {warning_threshold}%."


def _build_details_critical(
    reading: BatteryReading,
    critical_threshold: int,
    language: str,
) -> str:
    if language == LANG_RU:
        if reading.level_percent is None:
            return "сообщает о низком заряде батареи. Замените батарею или зарядите устройство как можно скорее."
        return (
            f"имеет {reading.level_percent}%. Замените батарею или зарядите устройство как можно скорее. "
            f"Критический порог: {critical_threshold}%."
        )

    if reading.level_percent is None:
        return "reports a low-battery condition. Replace or recharge the battery soon."
    return (
        f"is at {reading.level_percent}%. Replace or recharge the battery soon. "
        f"Critical threshold: {critical_threshold}%."
    )


def _build_details_recovery(reading: BatteryReading, language: str) -> str:
    if language == LANG_RU:
        if reading.level_percent is None:
            return "больше не сообщает о низком заряде батареи."
        return f"снова имеет {reading.level_percent}% и находится выше порога предупреждения."

    if reading.level_percent is None:
        return "no longer reports a low-battery condition."
    return f"is back to {reading.level_percent}% and above the warning threshold."


class _SafeFormatDict(dict[str, object]):
    """A format context that leaves unknown placeholders unchanged."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"
