from collections import defaultdict
from typing import Callable

from src.core.events.base_event import BaseEvent
from src.core.events.event_types import EventType

EventHandler = Callable[[BaseEvent], None]


class EventBus:
    """In-memory synchronous event dispatcher for domain events."""

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[EventHandler]] = defaultdict(list)

    def register(self, event_type: EventType, handler: EventHandler) -> None:
        handlers = self._handlers[event_type]
        if handler not in handlers:
            handlers.append(handler)

    def unregister(self, event_type: EventType, handler: EventHandler) -> None:
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def clear(self) -> None:
        self._handlers.clear()

    def publish(self, event: BaseEvent) -> None:
        event_type = EventType(event.event_type)
        for handler in list(self._handlers.get(event_type, [])):
            handler(event)

    def get_handlers(self, event_type: EventType) -> tuple[EventHandler, ...]:
        return tuple(self._handlers.get(event_type, []))
