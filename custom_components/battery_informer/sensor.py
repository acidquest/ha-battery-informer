"""Sensor platform for Battery Informer."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BatteryInformerConfigEntry
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Battery Informer sensors for a config entry."""
    config_entry = entry
    async_add_entities(
        [
            BatteryInformerSummarySensor(config_entry),
            BatteryInformerCriticalSensor(config_entry),
        ]
    )


class BatteryInformerBaseSensor(SensorEntity):
    """Base sensor for Battery Informer entities."""

    _attr_has_entity_name = True

    def __init__(self, entry: BatteryInformerConfigEntry, suffix: str) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{suffix}"

    @property
    def available(self) -> bool:
        """Return entity availability."""
        return self._entry.runtime_data is not None

    async def async_added_to_hass(self) -> None:
        """Register update listener when added to hass."""
        if self._entry.runtime_data is None:
            return
        self.async_on_remove(
            self._entry.runtime_data.manager.async_add_listener(self.async_write_ha_state)
        )

    @property
    def device_info(self) -> dict[str, object]:
        """Return device info for grouping under the integration."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "Battery Informer",
            "manufacturer": "Battery Informer",
        }


class BatteryInformerSummarySensor(BatteryInformerBaseSensor):
    """Sensor that summarizes tracked battery sensors."""

    _attr_icon = "mdi:battery-heart-variant"
    _attr_name = "Tracked batteries"

    def __init__(self, entry: BatteryInformerConfigEntry) -> None:
        super().__init__(entry, "tracked_batteries")

    @property
    def state(self) -> int:
        """Return number of tracked batteries."""
        if self._entry.runtime_data is None:
            return 0
        return int(self._entry.runtime_data.manager.get_summary()["tracked_count"])

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return summary details."""
        if self._entry.runtime_data is None:
            return {}
        summary = self._entry.runtime_data.manager.get_summary()
        return {
            "warning_count": summary["warning_count"],
            "critical_count": summary["critical_count"],
            "excluded_entities": summary["excluded_entities"],
            "batteries": summary["batteries"],
        }


class BatteryInformerCriticalSensor(BatteryInformerBaseSensor):
    """Sensor that summarizes critical battery sensors."""

    _attr_icon = "mdi:battery-alert-variant"
    _attr_name = "Critical batteries"

    def __init__(self, entry: BatteryInformerConfigEntry) -> None:
        super().__init__(entry, "critical_batteries")

    @property
    def state(self) -> int:
        """Return number of critical batteries."""
        if self._entry.runtime_data is None:
            return 0
        return int(self._entry.runtime_data.manager.get_summary()["critical_count"])

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return critical battery details."""
        if self._entry.runtime_data is None:
            return {}
        summary = self._entry.runtime_data.manager.get_summary()
        critical_batteries = [
            battery for battery in summary["batteries"] if battery["status"] == "critical"
        ]
        return {
            "critical_count": summary["critical_count"],
            "batteries": critical_batteries,
        }
