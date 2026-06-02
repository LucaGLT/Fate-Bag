from uuid import UUID

from src.core.engine.session_engine import SessionEngine
from src.core.engine.shuffle_engine import ShuffleEngine
from src.core.events.event_bus import EventBus
from src.core.events.event_types import SessionClosed, SessionLoaded, SessionReset, SessionShuffled, SessionStarted
from src.core.models.session import Session
from src.core.repositories.session_repository import SessionRepository


class SessionService:
    def __init__(
        self,
        session_engine: SessionEngine,
        shuffle_engine: ShuffleEngine,
        repository: SessionRepository,
        event_bus: EventBus,
    ) -> None:
        self._session_engine = session_engine
        self._shuffle_engine = shuffle_engine
        self._repository = repository
        self._event_bus = event_bus

    def start_session(
        self,
        *,
        use_token_ids: list[UUID] | None = None,
        exclude_token_ids: list[UUID] | None = None,
        category: str | None = None,
        tag: str | None = None,
        random_subset_size: int | None = None,
        seed: int | None = None,
    ) -> Session:
        session = self._session_engine.create_session(
            use_token_ids=use_token_ids,
            exclude_token_ids=exclude_token_ids,
            category=category,
            tag=tag,
            random_subset_size=random_subset_size,
            seed=seed,
        )
        self._repository.save(session)
        self._event_bus.publish(
            SessionStarted(
                payload={
                    "session_id": str(session.session_id),
                    "seed": seed,
                    "table_size": len(session.table_tokens),
                }
            )
        )
        return session

    def load_session(self, session_id: UUID) -> Session:
        session = self._repository.load(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        self._event_bus.publish(SessionLoaded(payload={"session_id": str(session_id)}))
        return session

    def close_session(self, session_id: UUID) -> None:
        self._repository.delete(session_id)
        self._event_bus.publish(SessionClosed(payload={"session_id": str(session_id)}))

    def shuffle_session(self, session: Session, seed: int | None = None) -> Session:
        updated = self._shuffle_engine.shuffle(session, seed=seed)
        self._repository.save(updated)
        self._event_bus.publish(
            SessionShuffled(
                payload={
                    "session_id": str(updated.session_id),
                    "seed": seed,
                }
            )
        )
        return updated

    def reset_session(self, session: Session) -> Session:
        updated = self._session_engine.reset_session(session)
        self._repository.save(updated)
        self._event_bus.publish(SessionReset(payload={"session_id": str(updated.session_id)}))
        return updated
