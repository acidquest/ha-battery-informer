"""Config flow for Battery Informer."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig, SelectOptionDict, SelectSelector, SelectSelectorConfig, TextSelector

from .const import (
    CONF_CRITICAL_THRESHOLD,
    CONF_EXCLUDED_ENTITIES,
    CONF_NOTIFY_SERVICE,
    CONF_WARNING_THRESHOLD,
    DEFAULT_CRITICAL_THRESHOLD,
    DEFAULT_EXCLUDED_ENTITIES,
    DEFAULT_WARNING_THRESHOLD,
    DOMAIN,
)
from .detector import build_entity_option_label, get_battery_reading, normalize_notify_service


def _build_common_schema(
    *,
    warning_threshold: int,
    critical_threshold: int,
    notify_service: str,
) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_WARNING_THRESHOLD, default=warning_threshold): NumberSelector(
                NumberSelectorConfig(min=1, max=100, mode="box")
            ),
            vol.Required(CONF_CRITICAL_THRESHOLD, default=critical_threshold): NumberSelector(
                NumberSelectorConfig(min=1, max=100, mode="box")
            ),
            vol.Required(CONF_NOTIFY_SERVICE, default=notify_service): TextSelector(),
        }
    )


def _build_excluded_entities_selector(
    hass: HomeAssistant,
    selected_entities: list[str],
) -> SelectSelector:
    options: list[SelectOptionDict] = []
    for state in hass.states.async_all("sensor"):
        reading = get_battery_reading(state)
        if reading is None:
            continue
        options.append(SelectOptionDict(value=state.entity_id, label=build_entity_option_label(state)))

    for entity_id in sorted(set(selected_entities) - {option["value"] for option in options}):
        options.append(SelectOptionDict(value=entity_id, label=entity_id))

    options.sort(key=lambda option: option["label"])
    return SelectSelector(SelectSelectorConfig(options=options, multiple=True, mode="dropdown"))


def _build_options_schema(config_entry: config_entries.ConfigEntry, hass: HomeAssistant) -> vol.Schema:
    selected_entities = list(config_entry.options.get(CONF_EXCLUDED_ENTITIES, config_entry.data.get(CONF_EXCLUDED_ENTITIES, [])))
    return vol.Schema(
        {
            vol.Required(
                CONF_WARNING_THRESHOLD,
                default=config_entry.options.get(CONF_WARNING_THRESHOLD, config_entry.data.get(CONF_WARNING_THRESHOLD, DEFAULT_WARNING_THRESHOLD)),
            ): NumberSelector(NumberSelectorConfig(min=1, max=100, mode="box")),
            vol.Required(
                CONF_CRITICAL_THRESHOLD,
                default=config_entry.options.get(CONF_CRITICAL_THRESHOLD, config_entry.data.get(CONF_CRITICAL_THRESHOLD, DEFAULT_CRITICAL_THRESHOLD)),
            ): NumberSelector(NumberSelectorConfig(min=1, max=100, mode="box")),
            vol.Required(
                CONF_NOTIFY_SERVICE,
                default=config_entry.options.get(CONF_NOTIFY_SERVICE, config_entry.data.get(CONF_NOTIFY_SERVICE, "")),
            ): TextSelector(),
            vol.Required(CONF_EXCLUDED_ENTITIES, default=selected_entities): _build_excluded_entities_selector(
                hass,
                selected_entities,
            ),
        }
    )


def _validate_thresholds(user_input: dict[str, Any]) -> None:
    warning_threshold = int(user_input[CONF_WARNING_THRESHOLD])
    critical_threshold = int(user_input[CONF_CRITICAL_THRESHOLD])
    if critical_threshold >= warning_threshold:
        raise ValueError("invalid_thresholds")


def _validate_notify_service(hass: HomeAssistant, raw_service: str) -> str:
    service = normalize_notify_service(raw_service)
    if not hass.services.has_service("notify", service):
        raise ValueError("notify_service_not_found")
    return service


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
                return self.async_create_entry(
                    title="Battery Informer",
                    data={
                        CONF_WARNING_THRESHOLD: int(user_input[CONF_WARNING_THRESHOLD]),
                        CONF_CRITICAL_THRESHOLD: int(user_input[CONF_CRITICAL_THRESHOLD]),
                        CONF_NOTIFY_SERVICE: notify_service,
                        CONF_EXCLUDED_ENTITIES: DEFAULT_EXCLUDED_ENTITIES,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_build_common_schema(
                warning_threshold=DEFAULT_WARNING_THRESHOLD,
                critical_threshold=DEFAULT_CRITICAL_THRESHOLD,
                notify_service="telegram",
            ),
            errors=errors,
        )


class BatteryInformerOptionsFlow(config_entries.OptionsFlow):
    """Manage Battery Informer options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                _validate_thresholds(user_input)
                notify_service = _validate_notify_service(self.hass, user_input[CONF_NOTIFY_SERVICE])
            except ValueError as err:
                errors["base"] = str(err)
            else:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_WARNING_THRESHOLD: int(user_input[CONF_WARNING_THRESHOLD]),
                        CONF_CRITICAL_THRESHOLD: int(user_input[CONF_CRITICAL_THRESHOLD]),
                        CONF_NOTIFY_SERVICE: notify_service,
                        CONF_EXCLUDED_ENTITIES: sorted(set(user_input.get(CONF_EXCLUDED_ENTITIES, []))),
                    },
                )

        return self.async_show_form(
            step_id="init",
            data_schema=_build_options_schema(self.config_entry, self.hass),
            errors=errors,
        )
