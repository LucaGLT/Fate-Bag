from enum import Enum

from pydantic import Field

from src.core.events.base_event import BaseEvent


class EventType(str, Enum):
    TOKEN_CREATED = "TOKEN_CREATED"
    TOKEN_UPDATED = "TOKEN_UPDATED"
    TOKEN_DELETED = "TOKEN_DELETED"
    SESSION_STARTED = "SESSION_STARTED"
    SESSION_LOADED = "SESSION_LOADED"
    SESSION_CLOSED = "SESSION_CLOSED"
    TOKENS_DRAWN = "TOKENS_DRAWN"
    TOKEN_REVEALED = "TOKEN_REVEALED"
    TOKEN_HIDDEN = "TOKEN_HIDDEN"
    SESSION_RESET = "SESSION_RESET"
    SESSION_SHUFFLED = "SESSION_SHUFFLED"


class TokenCreated(BaseEvent):
    event_type: str = Field(default=EventType.TOKEN_CREATED.value, frozen=True)


class TokenUpdated(BaseEvent):
    event_type: str = Field(default=EventType.TOKEN_UPDATED.value, frozen=True)


class TokenDeleted(BaseEvent):
    event_type: str = Field(default=EventType.TOKEN_DELETED.value, frozen=True)


class SessionStarted(BaseEvent):
    event_type: str = Field(default=EventType.SESSION_STARTED.value, frozen=True)


class SessionLoaded(BaseEvent):
    event_type: str = Field(default=EventType.SESSION_LOADED.value, frozen=True)


class SessionClosed(BaseEvent):
    event_type: str = Field(default=EventType.SESSION_CLOSED.value, frozen=True)


class TokensDrawn(BaseEvent):
    event_type: str = Field(default=EventType.TOKENS_DRAWN.value, frozen=True)


class TokenRevealed(BaseEvent):
    event_type: str = Field(default=EventType.TOKEN_REVEALED.value, frozen=True)


class TokenHidden(BaseEvent):
    event_type: str = Field(default=EventType.TOKEN_HIDDEN.value, frozen=True)


class SessionReset(BaseEvent):
    event_type: str = Field(default=EventType.SESSION_RESET.value, frozen=True)


class SessionShuffled(BaseEvent):
    event_type: str = Field(default=EventType.SESSION_SHUFFLED.value, frozen=True)


__all__ = [
    "EventType",
    "TokenCreated",
    "TokenUpdated",
    "TokenDeleted",
    "SessionStarted",
    "SessionLoaded",
    "SessionClosed",
    "TokensDrawn",
    "TokenRevealed",
    "TokenHidden",
    "SessionReset",
    "SessionShuffled",
]
