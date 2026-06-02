from src.core.engine.draw_engine import DrawEngine
from src.core.events.event_bus import EventBus
from src.core.events.event_types import TokenHidden, TokenRevealed, TokensDrawn
from src.core.models.session import Session
from src.core.repositories.session_repository import SessionRepository


class DrawService:
    def __init__(
        self,
        draw_engine: DrawEngine,
        session_repository: SessionRepository,
        event_bus: EventBus,
    ) -> None:
        self._draw_engine = draw_engine
        self._session_repository = session_repository
        self._event_bus = event_bus

    def draw_uniform(
        self,
        session: Session,
        *,
        count: int = 1,
        with_replacement: bool = False,
        seed: int | None = None,
    ) -> list[str]:
        drawn_ids = self._draw_engine.draw_uniform(
            session,
            count=count,
            with_replacement=with_replacement,
            seed=seed,
        )
        self._session_repository.save(session)
        as_str = [str(token_id) for token_id in drawn_ids]
        self._event_bus.publish(
            TokensDrawn(
                payload={
                    "session_id": str(session.session_id),
                    "drawn_token_ids": as_str,
                    "mode": "uniform",
                    "with_replacement": with_replacement,
                }
            )
        )
        return as_str

    def draw_weighted(
        self,
        session: Session,
        *,
        count: int = 1,
        with_replacement: bool = False,
        seed: int | None = None,
    ) -> list[str]:
        drawn_ids = self._draw_engine.draw_weighted(
            session,
            count=count,
            with_replacement=with_replacement,
            seed=seed,
        )
        self._session_repository.save(session)
        as_str = [str(token_id) for token_id in drawn_ids]
        self._event_bus.publish(
            TokensDrawn(
                payload={
                    "session_id": str(session.session_id),
                    "drawn_token_ids": as_str,
                    "mode": "weighted",
                    "with_replacement": with_replacement,
                }
            )
        )
        return as_str

    def draw_by_rarity(
        self,
        session: Session,
        *,
        rarity: str,
        count: int = 1,
        with_replacement: bool = False,
        seed: int | None = None,
    ) -> list[str]:
        drawn_ids = self._draw_engine.draw_by_rarity(
            session,
            rarity=rarity,
            count=count,
            with_replacement=with_replacement,
            seed=seed,
        )
        self._session_repository.save(session)
        as_str = [str(token_id) for token_id in drawn_ids]
        self._event_bus.publish(
            TokensDrawn(
                payload={
                    "session_id": str(session.session_id),
                    "drawn_token_ids": as_str,
                    "mode": "rarity",
                    "rarity": rarity,
                    "with_replacement": with_replacement,
                }
            )
        )
        return as_str

    def reveal_tokens(self, session: Session, token_ids: list[str] | None = None) -> list[str]:
        parsed = None if token_ids is None else [self._parse_uuid(token_id) for token_id in token_ids]
        revealed = self._draw_engine.reveal_tokens(session, parsed)
        self._session_repository.save(session)
        as_str = [str(token_id) for token_id in revealed]
        self._event_bus.publish(
            TokenRevealed(payload={"session_id": str(session.session_id), "token_ids": as_str})
        )
        return as_str

    def hide_tokens(self, session: Session, token_ids: list[str] | None = None) -> list[str]:
        parsed = None if token_ids is None else [self._parse_uuid(token_id) for token_id in token_ids]
        hidden = self._draw_engine.hide_tokens(session, parsed)
        self._session_repository.save(session)
        as_str = [str(token_id) for token_id in hidden]
        self._event_bus.publish(
            TokenHidden(payload={"session_id": str(session.session_id), "token_ids": as_str})
        )
        return as_str

    @staticmethod
    def _parse_uuid(value: str):
        from uuid import UUID

        return UUID(value)
