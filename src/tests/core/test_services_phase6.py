from uuid import UUID

from src.core.engine.draw_engine import DrawEngine
from src.core.engine.session_engine import SessionEngine
from src.core.engine.shuffle_engine import ShuffleEngine
from src.core.events.event_bus import EventBus
from src.core.events.event_types import EventType
from src.core.models.enums import TokenFrontType, TokenShape
from src.core.models.session import Session
from src.core.models.token import Token
from src.core.repositories.session_repository import SessionRepository
from src.core.repositories.token_repository import TokenRepository
from src.core.services.draw_service import DrawService
from src.core.services.session_service import SessionService
from src.core.services.token_service import TokenService


def _debug_case(title, given, expected, actual):
    print(f"\n[CASE] {title}")
    print(f"  GIVEN    : {given}")
    print(f"  EXPECTED : {expected}")
    print(f"  ACTUAL   : {actual}")


class InMemoryTokenRepository(TokenRepository):
    def __init__(self):
        self._data: dict[UUID, Token] = {}

    def get_all(self) -> list[Token]:
        return list(self._data.values())

    def get_by_id(self, token_id: UUID) -> Token | None:
        return self._data.get(token_id)

    def save(self, token: Token) -> None:
        self._data[token.id] = token

    def delete(self, token_id: UUID) -> None:
        self._data.pop(token_id, None)


class InMemorySessionRepository(SessionRepository):
    def __init__(self):
        self._data: dict[UUID, Session] = {}

    def save(self, session: Session) -> None:
        self._data[session.session_id] = session

    def load(self, session_id: UUID) -> Session | None:
        return self._data.get(session_id)

    def delete(self, session_id: UUID) -> None:
        self._data.pop(session_id, None)


def _build_tokens(tmp_path):
    back = tmp_path / "service_back.png"
    back.write_bytes(b"fake-image")

    def make_token(name, categories, tags, weight, rarity):
        return Token(
            name=name,
            shape=TokenShape.HEXAGON,
            front_type=TokenFrontType.TEXT,
            front_value=name,
            back_value=str(back),
            categories=categories,
            tags=tags,
            weight=weight,
            rarity=rarity,
        )

    return [
        make_token("Blessing", ["holy"], ["light"], 3.0, "common"),
        make_token("Curse", ["shadow"], ["dark"], 1.0, "rare"),
        make_token("Shield", ["holy"], ["defense"], 2.0, "common"),
    ]


def _capture_events(event_bus: EventBus):
    received: list[tuple[str, dict]] = []

    def handler(event):
        received.append((event.event_type, event.payload))

    for event_type in EventType:
        event_bus.register(event_type, handler)
    return received


def test_token_service_orchestrates_repository_and_events(tmp_path):
    token_repo = InMemoryTokenRepository()
    event_bus = EventBus()
    received = _capture_events(event_bus)

    service = TokenService(token_repo, event_bus)
    token = _build_tokens(tmp_path)[0]

    service.create_token(token)
    service.update_token(token)
    service.delete_token(token.id)

    _debug_case(
        "TokenService create/update/delete",
        {"token_id": str(token.id)},
        {
            "events": ["TOKEN_CREATED", "TOKEN_UPDATED", "TOKEN_DELETED"],
            "repo_size": 0,
        },
        {
            "events": [event_type for event_type, _ in received],
            "repo_size": len(token_repo.get_all()),
        },
    )

    assert [event_type for event_type, _ in received] == [
        EventType.TOKEN_CREATED.value,
        EventType.TOKEN_UPDATED.value,
        EventType.TOKEN_DELETED.value,
    ]
    assert token_repo.get_by_id(token.id) is None


def test_session_service_orchestrates_engine_repository_events(tmp_path):
    tokens = _build_tokens(tmp_path)
    session_repo = InMemorySessionRepository()
    event_bus = EventBus()
    received = _capture_events(event_bus)

    service = SessionService(
        session_engine=SessionEngine(tokens),
        shuffle_engine=ShuffleEngine(),
        repository=session_repo,
        event_bus=event_bus,
    )

    session = service.start_session(category="holy", seed=44)
    loaded = service.load_session(session.session_id)
    shuffled = service.shuffle_session(session, seed=99)
    reset = service.reset_session(session)
    service.close_session(session.session_id)

    _debug_case(
        "SessionService lifecycle",
        {"category": "holy", "start_seed": 44, "shuffle_seed": 99},
        {
            "events_present": [
                "SESSION_STARTED",
                "SESSION_LOADED",
                "SESSION_SHUFFLED",
                "SESSION_RESET",
                "SESSION_CLOSED",
            ],
            "session_deleted": True,
        },
        {
            "events": [event_type for event_type, _ in received],
            "started_size": len(session.table_tokens),
            "loaded_id": str(loaded.session_id),
            "shuffled_seed": shuffled.seed,
            "reset_history": len(reset.draw_history),
            "session_deleted": session_repo.load(session.session_id) is None,
        },
    )

    event_names = [event_type for event_type, _ in received]
    assert EventType.SESSION_STARTED.value in event_names
    assert EventType.SESSION_LOADED.value in event_names
    assert EventType.SESSION_SHUFFLED.value in event_names
    assert EventType.SESSION_RESET.value in event_names
    assert EventType.SESSION_CLOSED.value in event_names
    assert session_repo.load(session.session_id) is None


def test_draw_service_orchestrates_draw_reveal_hide_and_events(tmp_path):
    tokens = _build_tokens(tmp_path)
    session_repo = InMemorySessionRepository()
    event_bus = EventBus()
    received = _capture_events(event_bus)

    session_engine = SessionEngine(tokens)
    session = session_engine.use_all_tokens(seed=7)
    session_repo.save(session)

    draw_service = DrawService(
        draw_engine=DrawEngine(tokens),
        session_repository=session_repo,
        event_bus=event_bus,
    )

    uniform = draw_service.draw_uniform(session, count=1, with_replacement=False, seed=3)
    weighted = draw_service.draw_weighted(session, count=1, with_replacement=False, seed=3)
    rarity = draw_service.draw_by_rarity(
        session,
        rarity="common",
        count=1,
        with_replacement=True,
        seed=3,
    )
    revealed = draw_service.reveal_tokens(session)
    hidden = draw_service.hide_tokens(session)

    _debug_case(
        "DrawService draw + reveal/hide",
        {"session_id": str(session.session_id)},
        {
            "draw_events": 3,
            "reveal_event": 1,
            "hide_event": 1,
            "persisted_session": True,
        },
        {
            "uniform": uniform,
            "weighted": weighted,
            "rarity": rarity,
            "revealed_count": len(revealed),
            "hidden_count": len(hidden),
            "events": [event_type for event_type, _ in received],
            "persisted_session": session_repo.load(session.session_id) is not None,
        },
    )

    event_names = [event_type for event_type, _ in received]
    assert event_names.count(EventType.TOKENS_DRAWN.value) == 3
    assert EventType.TOKEN_REVEALED.value in event_names
    assert EventType.TOKEN_HIDDEN.value in event_names
    assert session_repo.load(session.session_id) is not None
