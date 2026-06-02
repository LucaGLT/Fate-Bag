from pathlib import Path
from uuid import UUID

from src.core.engine.draw_engine import DrawEngine
from src.core.engine.session_engine import SessionEngine
from src.core.engine.shuffle_engine import ShuffleEngine
from src.core.events.event_bus import EventBus
from src.core.models.enums import TokenFrontType, TokenShape
from src.core.models.session import Session
from src.core.models.token import Token
from src.core.services.draw_service import DrawService
from src.core.services.session_service import SessionService
from src.core.services.token_service import TokenService
from src.infrastructure.json.json_session_repository import JsonSessionRepository
from src.infrastructure.json.json_token_repository import JsonTokenRepository


class MainController:
    def __init__(
        self,
        base_dir: str | Path = ".runtime/gui",
        *,
        deterministic_mode: bool = False,
    ) -> None:
        self._base_dir = Path(base_dir)
        self._deterministic_mode = deterministic_mode
        self._seed_counter = 0
        self._token_repo = JsonTokenRepository(self._base_dir / "tokens.json")
        self._session_repo = JsonSessionRepository(self._base_dir / "sessions.json")
        self._event_bus = EventBus()

        self._token_service = TokenService(self._token_repo, self._event_bus)
        self._tokens: list[Token] = []
        self._token_name_by_id: dict[UUID, str] = {}

        self._session_service: SessionService | None = None
        self._draw_service: DrawService | None = None
        self.current_session: Session | None = None

    def load_tokens(self) -> list[Token]:
        self._ensure_runtime_assets()

        tokens = self._token_service.list_tokens()
        if not tokens:
            for token in self._build_default_tokens():
                self._token_service.create_token(token)
            tokens = self._token_service.list_tokens()

        self._tokens = tokens
        self._token_name_by_id = {token.id: token.name for token in tokens}

        session_engine = SessionEngine(tokens)
        self._session_service = SessionService(
            session_engine=session_engine,
            shuffle_engine=ShuffleEngine(),
            repository=self._session_repo,
            event_bus=self._event_bus,
        )
        self._draw_service = DrawService(
            draw_engine=DrawEngine(tokens),
            session_repository=self._session_repo,
            event_bus=self._event_bus,
        )

        return tokens

    def create_session(self) -> Session:
        self._ensure_services_ready()
        seed = 42 if self._deterministic_mode else None
        self.current_session = self._session_service.start_session(seed=seed)
        return self.current_session

    def draw_one(self) -> list[str]:
        self._ensure_session_ready()
        seed = self._next_seed() if self._deterministic_mode else None
        return self._draw_service.draw_uniform(
            self.current_session,
            count=1,
            with_replacement=False,
            seed=seed,
        )

    def draw_many(self, count: int) -> list[str]:
        if count <= 0:
            raise ValueError("count must be greater than zero")
        self._ensure_session_ready()
        seed = self._next_seed() if self._deterministic_mode else None
        return self._draw_service.draw_uniform(
            self.current_session,
            count=count,
            with_replacement=False,
            seed=seed,
        )

    def shuffle(self) -> Session:
        self._ensure_session_ready()
        seed = self._next_seed() if self._deterministic_mode else None
        self.current_session = self._session_service.shuffle_session(self.current_session, seed=seed)
        return self.current_session

    def reveal_all(self) -> list[str]:
        self._ensure_session_ready()
        return self._draw_service.reveal_tokens(self.current_session)

    def hide_all(self) -> list[str]:
        self._ensure_session_ready()
        return self._draw_service.hide_tokens(self.current_session)

    def reset(self) -> Session:
        self._ensure_session_ready()
        self.current_session = self._session_service.reset_session(self.current_session)
        return self.current_session

    def table_rows(self) -> list[str]:
        if self.current_session is None:
            return []

        rows = []
        for table_token in self.current_session.table_tokens:
            token_name = self._token_name_by_id.get(table_token.token_id, str(table_token.token_id))
            rows.append(f"{token_name} | {table_token.state.value}")
        return rows

    def _ensure_runtime_assets(self) -> None:
        assets_dir = self._base_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        back_image = assets_dir / "back.png"
        if not back_image.exists():
            back_image.write_bytes(b"fake-image")

    def _build_default_tokens(self) -> list[Token]:
        back_image = self._base_dir / "assets" / "back.png"
        return [
            Token(
                name="Blessing",
                shape=TokenShape.CIRCLE,
                front_type=TokenFrontType.TEXT,
                front_value="Blessing",
                back_value=str(back_image),
                categories=["holy"],
                tags=["light"],
                weight=2.0,
                rarity="common",
            ),
            Token(
                name="Curse",
                shape=TokenShape.HEXAGON,
                front_type=TokenFrontType.TEXT,
                front_value="Curse",
                back_value=str(back_image),
                categories=["shadow"],
                tags=["dark"],
                weight=1.0,
                rarity="rare",
            ),
            Token(
                name="Shield",
                shape=TokenShape.CIRCLE,
                front_type=TokenFrontType.TEXT,
                front_value="Shield",
                back_value=str(back_image),
                categories=["holy"],
                tags=["defense"],
                weight=3.0,
                rarity="common",
            ),
        ]

    def _ensure_services_ready(self) -> None:
        if self._session_service is None or self._draw_service is None:
            raise ValueError("Load tokens before creating a session")

    def _ensure_session_ready(self) -> None:
        self._ensure_services_ready()
        if self.current_session is None:
            raise ValueError("Create session before draw/reveal/hide/reset")

    def _next_seed(self) -> int:
        self._seed_counter += 1
        return self._seed_counter
