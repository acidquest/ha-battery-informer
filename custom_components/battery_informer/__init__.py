"""The Battery Informer integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

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
from .manager import BatteryInformerManager


@dataclass(slots=True)
class BatteryInformerRuntimeData:
    """Runtime state for a config entry."""

    manager: BatteryInformerManager


BatteryInformerConfigEntry: TypeAlias = ConfigEntry[BatteryInformerRuntimeData]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration namespace."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: BatteryInformerConfigEntry) -> bool:
    """Set up Battery Informer from a config entry."""
    config = {
        CONF_WARNING_THRESHOLD: entry.options.get(CONF_WARNING_THRESHOLD, entry.data.get(CONF_WARNING_THRESHOLD, DEFAULT_WARNING_THRESHOLD)),
        CONF_CRITICAL_THRESHOLD: entry.options.get(CONF_CRITICAL_THRESHOLD, entry.data.get(CONF_CRITICAL_THRESHOLD, DEFAULT_CRITICAL_THRESHOLD)),
        CONF_NOTIFY_SERVICE: entry.options.get(CONF_NOTIFY_SERVICE, entry.data[CONF_NOTIFY_SERVICE]),
        CONF_EXCLUDED_ENTITIES: entry.options.get(CONF_EXCLUDED_ENTITIES, entry.data.get(CONF_EXCLUDED_ENTITIES, DEFAULT_EXCLUDED_ENTITIES)),
    }

    manager = BatteryInformerManager(hass, entry.entry_id, config)
    await manager.async_start()

    runtime_data = BatteryInformerRuntimeData(manager=manager)
    entry.runtime_data = runtime_data
    hass.data[DOMAIN][entry.entry_id] = runtime_data
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BatteryInformerConfigEntry) -> bool:
    """Unload a config entry."""
    runtime_data = hass.data[DOMAIN].pop(entry.entry_id, None)
    if runtime_data is not None:
        await runtime_data.manager.async_stop()
    return True


async def async_reload_entry(hass: HomeAssistant, entry: BatteryInformerConfigEntry) -> None:
    """Reload a config entry after options update."""
    await hass.config_entries.async_reload(entry.entry_id)
