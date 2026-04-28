"""Runtime battery monitoring for Battery Informer."""

from __future__ import annotations

from collections.abc import Callable
import logging

from homeassistant.components.notify.const import ATTR_MESSAGE, DOMAIN as NOTIFY_DOMAIN, SERVICE_SEND_MESSAGE
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import Event, HomeAssistant, State, callback

from .const import (
    CONF_CRITICAL_THRESHOLD,
    CONF_EXCLUDED_ENTITIES,
    CONF_NOTIFY_SERVICE,
    CONF_WARNING_THRESHOLD,
    LEVEL_CRITICAL,
    LEVEL_WARNING,
)
from .detector import BatteryReading, classify_battery_level, get_battery_reading
from .i18n import build_localized_level_message, get_hass_language

LOGGER = logging.getLogger(__name__)


class BatteryInformerManager:
    """Monitors Home Assistant battery sensors and sends notifications."""

    def __init__(self, hass: HomeAssistant, entry_id: str, config: dict[str, object]) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.warning_threshold = int(config[CONF_WARNING_THRESHOLD])
        self.critical_threshold = int(config[CONF_CRITICAL_THRESHOLD])
        self.notify_target = str(config[CONF_NOTIFY_SERVICE])
        self.excluded_entities = set(config.get(CONF_EXCLUDED_ENTITIES, []))
        self._entity_levels: dict[str, str] = {}
        self._listeners: list[Callable[[], None]] = []
        self._unsubscribe: Callable[[], None] | None = None

    async def async_start(self) -> None:
        """Initialize state and subscribe to entity changes."""
        self._initialize_snapshot()
        self._unsubscribe = self.hass.bus.async_listen(EVENT_STATE_CHANGED, self._handle_state_change_event)

    async def async_stop(self) -> None:
        """Stop monitoring."""
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        self._listeners.clear()

    def _initialize_snapshot(self) -> None:
        """Build the initial tracked entity state without notifications."""
        self._entity_levels.clear()
        for state in self.hass.states.async_all("sensor"):
            reading = get_battery_reading(state)
            if reading is None or reading.entity_id in self.excluded_entities:
                continue
            self._entity_levels[reading.entity_id] = classify_battery_level(
                reading.level_percent,
                self.warning_threshold,
                self.critical_threshold,
            )
        self._notify_listeners()

    @callback
    def _handle_state_change_event(self, event: Event) -> None:
        """Schedule processing for a state change."""
        self.hass.async_create_task(self._async_process_state_change(event))

    async def _async_process_state_change(self, event: Event) -> None:
        """Process a single entity state change."""
        entity_id = event.data.get("entity_id")
        if not isinstance(entity_id, str):
            return

        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")

        if entity_id in self.excluded_entities:
            self._entity_levels.pop(entity_id, None)
            self._notify_listeners()
            return

        should_inspect = entity_id.startswith("sensor.") or entity_id in self._entity_levels
        if not should_inspect:
            return

        reading = get_battery_reading(new_state if isinstance(new_state, State) else None)
        if reading is None:
            self._entity_levels.pop(entity_id, None)
            self._notify_listeners()
            return

        new_level = classify_battery_level(
            reading.level_percent,
            self.warning_threshold,
            self.critical_threshold,
        )
        previous_level = self._entity_levels.get(entity_id)
        self._entity_levels[entity_id] = new_level
        self._notify_listeners()

        if previous_level is None or previous_level == new_level:
            return

        if self._states_are_equivalent(old_state, new_state):
            return

        await self._async_send_notification(reading, new_level)

    async def _async_send_notification(self, reading: BatteryReading, new_level: str) -> None:
        """Send a notification through the configured notify service."""
        message = build_localized_level_message(
            reading=reading,
            new_level=new_level,
            warning_threshold=self.warning_threshold,
            critical_threshold=self.critical_threshold,
            language=get_hass_language(self.hass),
        )
        LOGGER.debug(
            "Sending battery notification for %s via %s: %s",
            reading.entity_id,
            self.notify_target,
            message,
        )
        await self._async_send_raw_notification(message)

    async def async_send_test_notification(self, message: str | None = None) -> None:
        """Send a test notification through the configured target."""
        await self._async_send_raw_notification(
            message
            or "Battery Informer test notification. The integration is configured and can send messages."
        )

    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a callback invoked when tracked battery data changes."""
        self._listeners.append(listener)

        def _remove_listener() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _remove_listener

    def get_tracked_batteries(self) -> list[dict[str, object]]:
        """Return tracked battery sensors with current levels."""
        batteries: list[dict[str, object]] = []
        for entity_id, current_level in sorted(self._entity_levels.items()):
            state = self.hass.states.get(entity_id)
            reading = get_battery_reading(state if isinstance(state, State) else None)
            if reading is None:
                continue
            batteries.append(
                {
                    "entity_id": reading.entity_id,
                    "name": reading.name,
                    "level_percent": reading.level_percent,
                    "status": current_level,
                }
            )
        return batteries

    def get_summary(self) -> dict[str, object]:
        """Return a summary of tracked battery sensors."""
        batteries = self.get_tracked_batteries()
        return {
            "tracked_count": len(batteries),
            "warning_count": sum(1 for item in batteries if item["status"] == LEVEL_WARNING),
            "critical_count": sum(1 for item in batteries if item["status"] == LEVEL_CRITICAL),
            "excluded_entities": sorted(self.excluded_entities),
            "batteries": batteries,
        }

    async def _async_send_raw_notification(self, message: str) -> None:
        """Deliver a raw notification through the configured target."""
        if self.notify_target.startswith("entity:"):
            await self.hass.services.async_call(
                NOTIFY_DOMAIN,
                SERVICE_SEND_MESSAGE,
                {
                    "entity_id": self.notify_target.removeprefix("entity:"),
                    ATTR_MESSAGE: message,
                },
                blocking=False,
            )
            return

        await self.hass.services.async_call(
            NOTIFY_DOMAIN,
            self.notify_target.removeprefix("service:"),
            {ATTR_MESSAGE: message},
            blocking=False,
        )

    def _notify_listeners(self) -> None:
        """Notify listeners that tracked battery data changed."""
        for listener in tuple(self._listeners):
            listener()

    @staticmethod
    def _states_are_equivalent(old_state: object, new_state: object) -> bool:
        """Avoid notifications for duplicate state_changed events."""
        if not isinstance(old_state, State) or not isinstance(new_state, State):
            return False
        return old_state.state == new_state.state and old_state.attributes == new_state.attributes
