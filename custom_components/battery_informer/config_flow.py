"""Config flow for Battery Informer."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.notify.const import (
    DOMAIN as NOTIFY_DOMAIN,
    SERVICE_NOTIFY,
    SERVICE_PERSISTENT_NOTIFICATION,
    SERVICE_SEND_MESSAGE,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    BooleanSelector,
    BooleanSelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    CONF_CRITICAL_THRESHOLD,
    CONF_CRITICAL_TEMPLATE,
    CONF_EXCLUDED_ENTITIES,
    CONF_INCLUDED_ENTITIES,
    CONF_MONITORING_MODE,
    CONF_NOTIFY_SERVICE,
    CONF_RESCAN_INTERVAL_MINUTES,
    CONF_RESET_TEMPLATES_TO_DEFAULT,
    CONF_RECOVERY_TEMPLATE,
    CONF_SEND_LOWEST_BATTERY_NOTIFICATION,
    CONF_WARNING_THRESHOLD,
    CONF_WARNING_TEMPLATE,
    DEFAULT_CRITICAL_THRESHOLD,
    DEFAULT_CRITICAL_TEMPLATE,
    DEFAULT_EXCLUDED_ENTITIES,
    DEFAULT_INCLUDED_ENTITIES,
    DEFAULT_MONITORING_MODE,
    DEFAULT_RECOVERY_TEMPLATE,
    DEFAULT_RESCAN_INTERVAL_MINUTES,
    DEFAULT_WARNING_THRESHOLD,
    DEFAULT_WARNING_TEMPLATE,
    DOMAIN,
)
from .detector import (
    build_entity_option_label,
    get_battery_reading,
    normalize_notify_service,
    normalize_notify_target,
)
from .i18n import (
    get_default_message_templates,
    get_hass_language,
    get_legacy_notify_service_label,
    normalize_builtin_template,
)

LOGGER = logging.getLogger(__name__)


def _get_notify_service_options(
    hass: HomeAssistant,
    current_target: str,
) -> list[SelectOptionDict]:
    language = get_hass_language(hass)
    try:
        normalized_current_target = normalize_notify_target(current_target)
    except ValueError:
        normalized_current_target = current_target

    options: list[SelectOptionDict] = []
    entity_registry = er.async_get(hass)

    options.extend(
        SelectOptionDict(
            value=f"entity:{entry.entity_id}",
            label=f"{entry.name or entry.original_name or entry.entity_id} ({entry.entity_id})",
        )
        for entry in sorted(
            (
                entry
                for entry in entity_registry.entities.values()
                if entry.domain == NOTIFY_DOMAIN and entry.disabled_by is None
            ),
            key=lambda item: item.name or item.original_name or item.entity_id,
        )
    )

    options.extend(
        SelectOptionDict(
            value=f"service:{service_name}",
            label=get_legacy_notify_service_label(language, service_name),
        )
        for service_name in sorted(hass.services.async_services().get(NOTIFY_DOMAIN, {}))
        if service_name
        not in {SERVICE_NOTIFY, SERVICE_SEND_MESSAGE, SERVICE_PERSISTENT_NOTIFICATION}
    )

    if normalized_current_target and normalized_current_target not in {
        option["value"] for option in options
    }:
        if normalized_current_target.startswith("entity:"):
            entity_id = normalized_current_target.removeprefix("entity:")
            options.append(
                SelectOptionDict(
                    value=normalized_current_target,
                    label=f"{entity_id} ({entity_id})",
                )
            )
        elif normalized_current_target.startswith("service:"):
            service_name = normalized_current_target.removeprefix("service:")
            options.append(
                SelectOptionDict(
                    value=normalized_current_target,
                    label=get_legacy_notify_service_label(language, service_name),
                )
            )

    return options


def _build_notify_service_selector(
    hass: HomeAssistant,
    current_target: str,
) -> SelectSelector:
    try:
        normalized_current_target = normalize_notify_target(current_target)
    except ValueError:
        normalized_current_target = current_target

    options = _get_notify_service_options(hass, normalized_current_target)
    return SelectSelector(
        SelectSelectorConfig(
            options=options,
            custom_value=not options,
            mode="dropdown",
            sort=True,
        )
    )


def _get_battery_entity_options(
    hass: HomeAssistant,
    selected_entities: list[str],
) -> list[SelectOptionDict]:
    options: list[SelectOptionDict] = []
    for state in hass.states.async_all():
        reading = get_battery_reading(state)
        if reading is None:
            continue
        options.append(
            SelectOptionDict(
                value=state.entity_id,
                label=build_entity_option_label(state),
            )
        )

    for entity_id in sorted(set(selected_entities) - {option["value"] for option in options}):
        options.append(SelectOptionDict(value=entity_id, label=entity_id))

    options.sort(key=lambda option: option["label"])
    return options


def _build_battery_entity_selector(
    hass: HomeAssistant,
    selected_entities: list[str],
) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=_get_battery_entity_options(hass, selected_entities),
            multiple=True,
            mode="dropdown",
        )
    )


def _build_monitoring_mode_selector(current_mode: str) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=["all_except_excluded", "include_only"],
            mode="dropdown",
            translation_key="monitoring_mode",
        )
    )


def _build_template_selector() -> TextSelector:
    return TextSelector(TextSelectorConfig(multiline=True))


def _build_reset_templates_selector() -> BooleanSelector:
    return BooleanSelector(BooleanSelectorConfig())


def _build_send_lowest_battery_notification_selector() -> BooleanSelector:
    return BooleanSelector(BooleanSelectorConfig())


def _get_localized_default_templates(hass: HomeAssistant) -> dict[str, str]:
    """Return localized default templates for the current HA language."""
    return get_default_message_templates(get_hass_language(hass))


def _normalize_notify_target_for_form(current_target: str) -> str:
    """Normalize stored notify target for selector defaults."""
    try:
        return normalize_notify_target(current_target)
    except ValueError:
        return current_target


def _build_common_schema(
    hass: HomeAssistant,
    *,
    warning_threshold: int,
    critical_threshold: int,
    notify_service: str,
    rescan_interval_minutes: int,
    monitoring_mode: str,
    warning_template: str,
    critical_template: str,
    recovery_template: str,
) -> vol.Schema:
    normalized_notify_service = _normalize_notify_target_for_form(notify_service)
    default_templates = _get_localized_default_templates(hass)
    current_language = get_hass_language(hass)
    return vol.Schema(
        {
            vol.Required(CONF_WARNING_THRESHOLD, default=warning_threshold): NumberSelector(
                NumberSelectorConfig(min=1, max=100, mode="box")
            ),
            vol.Required(CONF_CRITICAL_THRESHOLD, default=critical_threshold): NumberSelector(
                NumberSelectorConfig(min=1, max=100, mode="box")
            ),
            vol.Required(CONF_NOTIFY_SERVICE, default=normalized_notify_service): _build_notify_service_selector(
                hass,
                normalized_notify_service,
            ),
            vol.Required(
                CONF_RESCAN_INTERVAL_MINUTES,
                default=rescan_interval_minutes,
            ): NumberSelector(NumberSelectorConfig(min=1, max=1440, mode="box")),
            vol.Required(
                CONF_MONITORING_MODE,
                default=monitoring_mode,
            ): _build_monitoring_mode_selector(monitoring_mode),
            vol.Optional(
                CONF_WARNING_TEMPLATE,
                default=normalize_builtin_template(
                    warning_template or default_templates["warning_template"],
                    "warning_template",
                    current_language,
                ),
            ): _build_template_selector(),
            vol.Optional(
                CONF_CRITICAL_TEMPLATE,
                default=normalize_builtin_template(
                    critical_template or default_templates["critical_template"],
                    "critical_template",
                    current_language,
                ),
            ): _build_template_selector(),
            vol.Optional(
                CONF_RECOVERY_TEMPLATE,
                default=normalize_builtin_template(
                    recovery_template or default_templates["recovery_template"],
                    "recovery_template",
                    current_language,
                ),
            ): _build_template_selector(),
        }
    )


def _build_excluded_entities_selector(
    hass: HomeAssistant,
    selected_entities: list[str],
) -> SelectSelector:
    return _build_battery_entity_selector(hass, selected_entities)


def _build_options_schema(config_entry: config_entries.ConfigEntry, hass: HomeAssistant) -> vol.Schema:
    monitoring_mode = str(
        config_entry.options.get(
            CONF_MONITORING_MODE,
            config_entry.data.get(CONF_MONITORING_MODE, DEFAULT_MONITORING_MODE),
        )
    )
    selected_entities = list(
        config_entry.options.get(
            CONF_EXCLUDED_ENTITIES,
            config_entry.data.get(CONF_EXCLUDED_ENTITIES, []),
        )
    )
    included_entities = list(
        config_entry.options.get(
            CONF_INCLUDED_ENTITIES,
            config_entry.data.get(CONF_INCLUDED_ENTITIES, DEFAULT_INCLUDED_ENTITIES),
        )
    )
    notify_service = str(
        config_entry.options.get(
            CONF_NOTIFY_SERVICE,
            config_entry.data.get(CONF_NOTIFY_SERVICE, ""),
        )
    )
    normalized_notify_service = _normalize_notify_target_for_form(notify_service)
    default_templates = _get_localized_default_templates(hass)
    current_language = get_hass_language(hass)
    return vol.Schema(
        {
            vol.Required(
                CONF_WARNING_THRESHOLD,
                default=config_entry.options.get(
                    CONF_WARNING_THRESHOLD,
                    config_entry.data.get(
                        CONF_WARNING_THRESHOLD, DEFAULT_WARNING_THRESHOLD
                    ),
                ),
            ): NumberSelector(NumberSelectorConfig(min=1, max=100, mode="box")),
            vol.Required(
                CONF_CRITICAL_THRESHOLD,
                default=config_entry.options.get(
                    CONF_CRITICAL_THRESHOLD,
                    config_entry.data.get(
                        CONF_CRITICAL_THRESHOLD, DEFAULT_CRITICAL_THRESHOLD
                    ),
                ),
            ): NumberSelector(NumberSelectorConfig(min=1, max=100, mode="box")),
            vol.Required(
                CONF_NOTIFY_SERVICE,
                default=normalized_notify_service,
            ): _build_notify_service_selector(hass, normalized_notify_service),
            vol.Required(
                CONF_RESCAN_INTERVAL_MINUTES,
                default=config_entry.options.get(
                    CONF_RESCAN_INTERVAL_MINUTES,
                    config_entry.data.get(
                        CONF_RESCAN_INTERVAL_MINUTES, DEFAULT_RESCAN_INTERVAL_MINUTES
                    ),
                ),
            ): NumberSelector(NumberSelectorConfig(min=1, max=1440, mode="box")),
            vol.Required(
                CONF_MONITORING_MODE,
                default=monitoring_mode,
            ): _build_monitoring_mode_selector(monitoring_mode),
            vol.Required(CONF_EXCLUDED_ENTITIES, default=selected_entities): _build_excluded_entities_selector(
                hass,
                selected_entities,
            ),
            vol.Required(CONF_INCLUDED_ENTITIES, default=included_entities): _build_battery_entity_selector(
                hass,
                included_entities,
            ),
            vol.Optional(
                CONF_WARNING_TEMPLATE,
                default=str(
                    normalize_builtin_template(
                        str(
                            config_entry.options.get(
                                CONF_WARNING_TEMPLATE,
                                config_entry.data.get(
                                    CONF_WARNING_TEMPLATE,
                                    default_templates["warning_template"],
                                ),
                            )
                        )
                        or default_templates["warning_template"],
                        "warning_template",
                        current_language,
                    )
                ),
            ): _build_template_selector(),
            vol.Optional(
                CONF_CRITICAL_TEMPLATE,
                default=str(
                    normalize_builtin_template(
                        str(
                            config_entry.options.get(
                                CONF_CRITICAL_TEMPLATE,
                                config_entry.data.get(
                                    CONF_CRITICAL_TEMPLATE,
                                    default_templates["critical_template"],
                                ),
                            )
                        )
                        or default_templates["critical_template"],
                        "critical_template",
                        current_language,
                    )
                ),
            ): _build_template_selector(),
            vol.Optional(
                CONF_RECOVERY_TEMPLATE,
                default=str(
                    normalize_builtin_template(
                        str(
                            config_entry.options.get(
                                CONF_RECOVERY_TEMPLATE,
                                config_entry.data.get(
                                    CONF_RECOVERY_TEMPLATE,
                                    default_templates["recovery_template"],
                                ),
                            )
                        )
                        or default_templates["recovery_template"],
                        "recovery_template",
                        current_language,
                    )
                ),
            ): _build_template_selector(),
            vol.Optional(
                CONF_RESET_TEMPLATES_TO_DEFAULT,
                default=False,
            ): _build_reset_templates_selector(),
            vol.Optional(
                CONF_SEND_LOWEST_BATTERY_NOTIFICATION,
                default=False,
            ): _build_send_lowest_battery_notification_selector(),
        }
    )


def _validate_thresholds(user_input: dict[str, Any]) -> None:
    warning_threshold = int(user_input[CONF_WARNING_THRESHOLD])
    critical_threshold = int(user_input[CONF_CRITICAL_THRESHOLD])
    if critical_threshold >= warning_threshold:
        raise ValueError("invalid_thresholds")


def _validate_notify_service(hass: HomeAssistant, raw_service: str) -> str:
    value = raw_service.strip().lower()

    if value.startswith("entity:") or value.startswith("service:"):
        target = normalize_notify_target(value)
    elif value.startswith(f"{NOTIFY_DOMAIN}."):
        if er.async_get(hass).async_get(value) is not None:
            target = f"entity:{value}"
        else:
            target = f"service:{normalize_notify_service(value)}"
    else:
        target = normalize_notify_target(value)

    if target.startswith("entity:"):
        entity_id = target.removeprefix("entity:")
        if er.async_get(hass).async_get(entity_id) is None:
            raise ValueError("notify_service_not_found")
        return target

    service = normalize_notify_service(target.removeprefix("service:"))
    if not hass.services.has_service(NOTIFY_DOMAIN, service):
        raise ValueError("notify_service_not_found")
    return f"service:{service}"


class BatteryInformerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Battery Informer."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Return the options flow handler."""
        return BatteryInformerOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            try:
                _validate_thresholds(user_input)
                notify_service = _validate_notify_service(self.hass, user_input[CONF_NOTIFY_SERVICE])
            except ValueError as err:
                errors["base"] = str(err)
            else:
                default_templates = _get_localized_default_templates(self.hass)
                return self.async_create_entry(
                    title="Battery Informer",
                    data={
                        CONF_WARNING_THRESHOLD: int(user_input[CONF_WARNING_THRESHOLD]),
                        CONF_CRITICAL_THRESHOLD: int(user_input[CONF_CRITICAL_THRESHOLD]),
                        CONF_NOTIFY_SERVICE: notify_service,
                        CONF_RESCAN_INTERVAL_MINUTES: int(user_input[CONF_RESCAN_INTERVAL_MINUTES]),
                        CONF_MONITORING_MODE: str(user_input[CONF_MONITORING_MODE]),
                        CONF_EXCLUDED_ENTITIES: DEFAULT_EXCLUDED_ENTITIES,
                        CONF_INCLUDED_ENTITIES: DEFAULT_INCLUDED_ENTITIES,
                        CONF_WARNING_TEMPLATE: str(user_input.get(CONF_WARNING_TEMPLATE, "")).strip()
                        or default_templates["warning_template"],
                        CONF_CRITICAL_TEMPLATE: str(user_input.get(CONF_CRITICAL_TEMPLATE, "")).strip()
                        or default_templates["critical_template"],
                        CONF_RECOVERY_TEMPLATE: str(user_input.get(CONF_RECOVERY_TEMPLATE, "")).strip()
                        or default_templates["recovery_template"],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_build_common_schema(
                self.hass,
                warning_threshold=DEFAULT_WARNING_THRESHOLD,
                critical_threshold=DEFAULT_CRITICAL_THRESHOLD,
                notify_service=next(
                    iter(
                        option["value"]
                        for option in _get_notify_service_options(self.hass, "")
                    ),
                    "",
                ),
                rescan_interval_minutes=DEFAULT_RESCAN_INTERVAL_MINUTES,
                monitoring_mode=DEFAULT_MONITORING_MODE,
                warning_template=DEFAULT_WARNING_TEMPLATE,
                critical_template=DEFAULT_CRITICAL_TEMPLATE,
                recovery_template=DEFAULT_RECOVERY_TEMPLATE,
            ),
            errors=errors,
        )


class BatteryInformerOptionsFlow(config_entries.OptionsFlow):
    """Manage Battery Informer options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                _validate_thresholds(user_input)
                notify_service = _validate_notify_service(self.hass, user_input[CONF_NOTIFY_SERVICE])
            except ValueError as err:
                errors["base"] = str(err)
            else:
                default_templates = _get_localized_default_templates(self.hass)
                reset_templates = bool(user_input.get(CONF_RESET_TEMPLATES_TO_DEFAULT))
                options_data = {
                    CONF_WARNING_THRESHOLD: int(user_input[CONF_WARNING_THRESHOLD]),
                    CONF_CRITICAL_THRESHOLD: int(user_input[CONF_CRITICAL_THRESHOLD]),
                    CONF_NOTIFY_SERVICE: notify_service,
                    CONF_RESCAN_INTERVAL_MINUTES: int(user_input[CONF_RESCAN_INTERVAL_MINUTES]),
                    CONF_MONITORING_MODE: str(user_input[CONF_MONITORING_MODE]),
                    CONF_EXCLUDED_ENTITIES: sorted(set(user_input.get(CONF_EXCLUDED_ENTITIES, []))),
                    CONF_INCLUDED_ENTITIES: sorted(set(user_input.get(CONF_INCLUDED_ENTITIES, []))),
                    CONF_WARNING_TEMPLATE: (
                        default_templates["warning_template"]
                        if reset_templates
                        else str(user_input.get(CONF_WARNING_TEMPLATE, "")).strip()
                        or default_templates["warning_template"]
                    ),
                    CONF_CRITICAL_TEMPLATE: (
                        default_templates["critical_template"]
                        if reset_templates
                        else str(user_input.get(CONF_CRITICAL_TEMPLATE, "")).strip()
                        or default_templates["critical_template"]
                    ),
                    CONF_RECOVERY_TEMPLATE: (
                        default_templates["recovery_template"]
                        if reset_templates
                        else str(user_input.get(CONF_RECOVERY_TEMPLATE, "")).strip()
                        or default_templates["recovery_template"]
                    ),
                }
                if bool(user_input.get(CONF_SEND_LOWEST_BATTERY_NOTIFICATION)):
                    from .manager import BatteryInformerManager

                    preview_manager = BatteryInformerManager(
                        self.hass,
                        self._config_entry.entry_id,
                        options_data,
                    )
                    try:
                        if not await preview_manager.async_send_lowest_battery_notification():
                            errors["base"] = "no_batteries_found"
                        else:
                            return self.async_create_entry(title="", data=options_data)
                    except Exception:  # pragma: no cover - defensive path for HA runtime failures
                        LOGGER.exception(
                            "Failed to send lowest-battery preview notification for entry %s",
                            self._config_entry.entry_id,
                        )
                        errors["base"] = "send_preview_failed"
                else:
                    return self.async_create_entry(title="", data=options_data)

        return self.async_show_form(
            step_id="init",
            data_schema=_build_options_schema(self._config_entry, self.hass),
            errors=errors,
        )
