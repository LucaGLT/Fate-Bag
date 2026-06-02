from uuid import uuid4

from src.core.events.event_bus import EventBus
from src.core.events.event_types import (
    EventType,
    SessionClosed,
    SessionLoaded,
    SessionReset,
    SessionShuffled,
    SessionStarted,
    TokenCreated,
    TokenDeleted,
    TokenHidden,
    TokenRevealed,
    TokensDrawn,
    TokenUpdated,
)


def _debug_case(title, given, expected, actual):
    print(f"\n[CASE] {title}")
    print(f"  GIVEN    : {given}")
    print(f"  EXPECTED : {expected}")
    print(f"  ACTUAL   : {actual}")


def test_event_bus_handler_registration_and_publish():
    bus = EventBus()
    handled_events = []

    def handler(event):
        handled_events.append(event)

    bus.register(EventType.TOKEN_CREATED, handler)

    payload = {"token_id": str(uuid4()), "name": "Blessing"}
    event = TokenCreated(payload=payload)
    bus.publish(event)

    _debug_case(
        "Register one handler and publish one event",
        {"event_type": EventType.TOKEN_CREATED.value, "payload": payload},
        {"handled_count": 1, "handled_event_type": EventType.TOKEN_CREATED.value},
        {
            "handled_count": len(handled_events),
            "handled_event_type": handled_events[0].event_type if handled_events else None,
        },
    )

    assert len(handled_events) == 1
    assert handled_events[0].event_type == EventType.TOKEN_CREATED.value


def test_event_bus_publish_dispatches_payload_to_all_handlers():
    bus = EventBus()
    received_a = []
    received_b = []

    def handler_a(event):
        received_a.append(event.payload)

    def handler_b(event):
        received_b.append(event.payload)

    bus.register(EventType.TOKENS_DRAWN, handler_a)
    bus.register(EventType.TOKENS_DRAWN, handler_b)

    payload = {"session_id": str(uuid4()), "drawn_token_ids": [str(uuid4()), str(uuid4())]}
    event = TokensDrawn(payload=payload)
    bus.publish(event)

    _debug_case(
        "Publish event to multiple handlers",
        {"event_type": EventType.TOKENS_DRAWN.value, "payload": payload},
        {"handler_a_payload": payload, "handler_b_payload": payload},
        {
            "handler_a_payload": received_a[0] if received_a else None,
            "handler_b_payload": received_b[0] if received_b else None,
        },
    )

    assert received_a == [payload]
    assert received_b == [payload]


def test_event_bus_unregister_stops_handler_invocation():
    bus = EventBus()
    call_counter = {"count": 0}

    def handler(_event):
        call_counter["count"] += 1

    bus.register(EventType.SESSION_RESET, handler)
    bus.unregister(EventType.SESSION_RESET, handler)

    bus.publish(SessionReset(payload={"session_id": str(uuid4())}))

    _debug_case(
        "Unregister removes handler",
        {"event_type": EventType.SESSION_RESET.value, "handler_registered_then_removed": True},
        {"count": 0},
        call_counter,
    )

    assert call_counter["count"] == 0


def test_event_classes_have_expected_event_types():
    events = [
        TokenCreated(payload={}),
        TokenUpdated(payload={}),
        TokenDeleted(payload={}),
        SessionStarted(payload={}),
        SessionLoaded(payload={}),
        SessionClosed(payload={}),
        TokensDrawn(payload={}),
        TokenRevealed(payload={}),
        TokenHidden(payload={}),
        SessionReset(payload={}),
        SessionShuffled(payload={}),
    ]

    event_types = [event.event_type for event in events]
    expected = [
        EventType.TOKEN_CREATED.value,
        EventType.TOKEN_UPDATED.value,
        EventType.TOKEN_DELETED.value,
        EventType.SESSION_STARTED.value,
        EventType.SESSION_LOADED.value,
        EventType.SESSION_CLOSED.value,
        EventType.TOKENS_DRAWN.value,
        EventType.TOKEN_REVEALED.value,
        EventType.TOKEN_HIDDEN.value,
        EventType.SESSION_RESET.value,
        EventType.SESSION_SHUFFLED.value,
    ]

    _debug_case(
        "All domain event classes expose the expected event_type",
        {"created_event_instances": len(events)},
        expected,
        event_types,
    )

    assert event_types == expected
