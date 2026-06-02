import json
import math
from pathlib import Path
from uuid import UUID

from src.core.engine.draw_engine import DrawEngine
from src.core.engine.session_engine import SessionEngine
from src.core.engine.shuffle_engine import ShuffleEngine
from src.core.events.event_bus import EventBus
from src.core.models.enums import TokenFrontType, TokenState
from src.core.models.session import Session
from src.core.models.table_token import TableToken
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
        bootstrap_tokens_file: str | Path = "config/default_tokens_20.json",
    ) -> None:
        self._base_dir = Path(base_dir)
        self._bootstrap_tokens_file = Path(bootstrap_tokens_file)
        self._deterministic_mode = deterministic_mode
        self._seed_counter = 0
        self._token_repo = JsonTokenRepository(self._base_dir / "tokens.json")
        self._session_repo = JsonSessionRepository(self._base_dir / "sessions.json")
        self._event_bus = EventBus()

        self._token_service = TokenService(self._token_repo, self._event_bus)
        self._tokens: list[Token] = []
        self._tokens_by_id: dict[UUID, Token] = {}
        self._token_name_by_id: dict[UUID, str] = {}

        self._session_service: SessionService | None = None
        self._draw_service: DrawService | None = None
        self.current_session: Session | None = None

    def load_tokens(self) -> list[Token]:
        self._ensure_runtime_assets()

        tokens = self._token_service.list_tokens()
        bootstrap_tokens = self._load_tokens_from_bootstrap_file()
        if not tokens:
            for token in bootstrap_tokens:
                self._token_service.create_token(token)
        else:
            existing_by_name = {token.name: token for token in tokens}
            for bootstrap_token in bootstrap_tokens:
                existing_token = existing_by_name.get(bootstrap_token.name)
                if existing_token is None:
                    self._token_service.create_token(bootstrap_token)
                    continue

                desired_payload = bootstrap_token.model_dump(mode="json")
                desired_payload["id"] = str(existing_token.id)
                # Keep user-uploaded media assets when reloading bootstrap defaults.
                desired_payload["front_type"] = existing_token.front_type.value
                desired_payload["front_value"] = existing_token.front_value
                desired_payload["back_value"] = existing_token.back_value
                desired_payload["metadata"] = dict(existing_token.metadata)
                desired_token = Token.model_validate(desired_payload)

                if existing_token.model_dump(mode="json") != desired_token.model_dump(mode="json"):
                    self._token_service.update_token(desired_token)

        tokens = self._token_service.list_tokens()

        self._tokens = tokens
        self._tokens_by_id = {token.id: token for token in tokens}
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

    def create_session_from_selection(self, token_ids: list[UUID]) -> Session:
        if not token_ids:
            raise ValueError("Seleziona almeno un token")
        self._ensure_services_ready()
        seed = 42 if self._deterministic_mode else None
        self.current_session = self._session_service.start_session(use_token_ids=token_ids, seed=seed)
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

    def sort_face_up_first(self) -> Session:
        self._ensure_session_ready()

        priority = {
            TokenState.FACE_UP: 0,
            TokenState.FACE_DOWN: 1,
        }
        self.current_session.table_tokens.sort(
            key=lambda table_token: (
                priority.get(table_token.state, 2),
                self._token_name_by_id.get(table_token.token_id, ""),
            )
        )

        positions = self._generate_grid_positions(len(self.current_session.table_tokens))
        for index, table_token in enumerate(self.current_session.table_tokens):
            x, y = positions[index]
            table_token.x = x
            table_token.y = y
            table_token.z = 0.0
            table_token.rotation = 0.0

        self._session_repo.save(self.current_session)
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
        entries = self.token_status_entries()
        return [f"{entry['name']} | {entry['status']}" for entry in entries]

    def token_status_entries(self, selected_token_ids: set[UUID] | None = None) -> list[dict]:
        selected = selected_token_ids or set()
        state_by_token_id = {}
        ordered_tokens: list[Token] = []
        if self.current_session is not None:
            state_by_token_id = {
                table_token.token_id: table_token.state.value
                for table_token in self.current_session.table_tokens
            }
            for table_token in self.current_session.table_tokens:
                token = self._tokens_by_id.get(table_token.token_id)
                if token is not None:
                    ordered_tokens.append(token)

            in_session_ids = {table_token.token_id for table_token in self.current_session.table_tokens}
            ordered_tokens.extend(token for token in self._tokens if token.id not in in_session_ids)
        else:
            ordered_tokens = list(self._tokens)

        entries = []
        for token in ordered_tokens:
            if token.id in state_by_token_id:
                status = state_by_token_id[token.id]
                in_session = True
            elif self.current_session is None and token.id in selected:
                status = "Selezionato (pronto)"
                in_session = False
            else:
                status = "Deselezionato"
                in_session = False

            entries.append(
                {
                    "token_id": token.id,
                    "name": token.name,
                    "status": status,
                    "in_session": in_session,
                }
            )

        return entries

    def scene_entries(self) -> list[tuple[Token, TableToken]]:
        if self.current_session is None:
            return []

        entries: list[tuple[Token, TableToken]] = []
        for table_token in self.current_session.table_tokens:
            token = self._tokens_by_id.get(table_token.token_id)
            if token is not None:
                entries.append((token, table_token))
        return entries

    def flip_token(self, token_id: str | UUID) -> str:
        self._ensure_session_ready()
        parsed_id = token_id if isinstance(token_id, UUID) else UUID(str(token_id))

        table_token = next(
            (item for item in self.current_session.table_tokens if item.token_id == parsed_id),
            None,
        )
        if table_token is None:
            raise ValueError(f"Token non trovato in sessione: {parsed_id}")

        if table_token.state == TokenState.FACE_DOWN:
            self._draw_service.reveal_tokens(self.current_session, [str(parsed_id)])
        elif table_token.state == TokenState.FACE_UP:
            self._draw_service.hide_tokens(self.current_session, [str(parsed_id)])

        return table_token.state.value

    def move_token(self, token_id: str | UUID, x: float, y: float) -> None:
        self._ensure_session_ready()
        parsed_id = token_id if isinstance(token_id, UUID) else UUID(str(token_id))

        table_token = next(
            (item for item in self.current_session.table_tokens if item.token_id == parsed_id),
            None,
        )
        if table_token is None:
            raise ValueError(f"Token non trovato in sessione: {parsed_id}")

        table_token.x = max(0.0, min(100.0, float(x)))
        table_token.y = max(0.0, min(100.0, float(y)))
        self._session_repo.save(self.current_session)

    def apply_front_image_to_tokens(self, token_ids: list[UUID], image_path: str | Path) -> int:
        selected_ids = self._normalize_selected_token_ids(token_ids)
        image_file = self._validate_image_file(image_path)

        updated_count = 0
        for token_id in selected_ids:
            token = self._tokens_by_id.get(token_id)
            if token is None:
                raise ValueError(f"Token non trovato: {token_id}")

            payload = token.model_dump(mode="json")
            payload["front_type"] = TokenFrontType.TEXT_IMAGE.value
            payload["front_value"] = str(image_file)
            metadata = dict(payload.get("metadata", {}))
            metadata["front_text"] = self._current_front_text(token)
            payload["metadata"] = metadata

            updated = Token.model_validate(payload)
            self._token_service.update_token(updated)
            self._update_token_cache(updated)
            updated_count += 1

        return updated_count

    def apply_back_image_to_tokens(self, token_ids: list[UUID], image_path: str | Path) -> int:
        selected_ids = self._normalize_selected_token_ids(token_ids)
        image_file = self._validate_image_file(image_path)

        updated_count = 0
        for token_id in selected_ids:
            token = self._tokens_by_id.get(token_id)
            if token is None:
                raise ValueError(f"Token non trovato: {token_id}")

            payload = token.model_dump(mode="json")
            payload["back_value"] = str(image_file)

            updated = Token.model_validate(payload)
            self._token_service.update_token(updated)
            self._update_token_cache(updated)
            updated_count += 1

        return updated_count

    def delete_front_image_from_tokens(self, token_ids: list[UUID]) -> int:
        selected_ids = self._normalize_selected_token_ids(token_ids)

        updated_count = 0
        for token_id in selected_ids:
            token = self._tokens_by_id.get(token_id)
            if token is None:
                raise ValueError(f"Token non trovato: {token_id}")

            payload = token.model_dump(mode="json")
            payload["front_type"] = TokenFrontType.TEXT.value
            payload["front_value"] = self._current_front_text(token)
            metadata = dict(payload.get("metadata", {}))
            metadata.pop("front_text", None)
            payload["metadata"] = metadata

            updated = Token.model_validate(payload)
            self._token_service.update_token(updated)
            self._update_token_cache(updated)
            updated_count += 1

        return updated_count

    def delete_back_image_from_tokens(self, token_ids: list[UUID]) -> int:
        selected_ids = self._normalize_selected_token_ids(token_ids)
        default_back = self._default_back_image_path()

        updated_count = 0
        for token_id in selected_ids:
            token = self._tokens_by_id.get(token_id)
            if token is None:
                raise ValueError(f"Token non trovato: {token_id}")

            payload = token.model_dump(mode="json")
            payload["back_value"] = str(default_back)

            updated = Token.model_validate(payload)
            self._token_service.update_token(updated)
            self._update_token_cache(updated)
            updated_count += 1

        return updated_count

    def apply_front_text_to_tokens(self, token_ids: list[UUID], text: str) -> int:
        selected_ids = self._normalize_selected_token_ids(token_ids)
        normalized_text = text.strip()
        if not normalized_text:
            raise ValueError("Il testo front deve essere non vuoto")

        updated_count = 0
        for token_id in selected_ids:
            token = self._tokens_by_id.get(token_id)
            if token is None:
                raise ValueError(f"Token non trovato: {token_id}")

            payload = token.model_dump(mode="json")
            if token.front_type == TokenFrontType.TEXT:
                payload["front_value"] = normalized_text
            elif token.front_type in (TokenFrontType.IMAGE, TokenFrontType.TEXT_IMAGE):
                payload["front_type"] = TokenFrontType.TEXT_IMAGE.value
                metadata = dict(payload.get("metadata", {}))
                metadata["front_text"] = normalized_text
                payload["metadata"] = metadata
            else:
                payload["front_value"] = normalized_text

            payload["name"] = normalized_text

            updated = Token.model_validate(payload)
            self._token_service.update_token(updated)
            self._update_token_cache(updated)
            updated_count += 1

        return updated_count

    def front_text_for_token(self, token_id: UUID) -> str:
        token = self._tokens_by_id.get(token_id)
        if token is None:
            raise ValueError(f"Token non trovato: {token_id}")
        return self._current_front_text(token)

    def _ensure_runtime_assets(self) -> None:
        assets_dir = self._base_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        back_image = assets_dir / "back.png"
        if not back_image.exists():
            back_image.write_bytes(b"fake-image")

    def _default_back_image_path(self) -> Path:
        self._ensure_runtime_assets()
        return self._base_dir / "assets" / "back.png"

    def _load_tokens_from_bootstrap_file(self) -> list[Token]:
        if not self._bootstrap_tokens_file.exists():
            raise FileNotFoundError(
                f"Bootstrap token file not found: {self._bootstrap_tokens_file}"
            )

        data = json.loads(self._bootstrap_tokens_file.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("Bootstrap token JSON must contain a list")

        back_image = self._base_dir / "assets" / "back.png"
        tokens: list[Token] = []
        for item in data:
            payload = dict(item)
            if payload.get("back_value") == "__RUNTIME_BACK_IMAGE__":
                payload["back_value"] = str(back_image)
            tokens.append(Token.model_validate(payload))

        if len(tokens) < 20:
            raise ValueError(
                "Bootstrap token file must contain at least 20 tokens"
            )

        return tokens

    def _ensure_services_ready(self) -> None:
        if self._session_service is None or self._draw_service is None:
            raise ValueError("Load tokens before creating a session")

    def _ensure_tokens_ready(self) -> None:
        if not self._tokens:
            raise ValueError("Load tokens before uploading images")

    def _normalize_selected_token_ids(self, token_ids: list[UUID]) -> list[UUID]:
        self._ensure_tokens_ready()
        if not token_ids:
            raise ValueError("Seleziona almeno un token")
        return token_ids

    @staticmethod
    def _validate_image_file(image_path: str | Path) -> Path:
        path = Path(image_path)
        if not path.is_file():
            raise ValueError(f"File immagine non trovato: {path}")
        return path

    @staticmethod
    def _current_front_text(token: Token) -> str:
        if token.front_type == TokenFrontType.TEXT:
            return token.front_value
        if token.front_type == TokenFrontType.TEXT_IMAGE:
            text = str(token.metadata.get("front_text", "")).strip()
            if text:
                return text
        return token.name

    def _update_token_cache(self, updated: Token) -> None:
        self._tokens_by_id[updated.id] = updated
        self._token_name_by_id[updated.id] = updated.name

        for index, token in enumerate(self._tokens):
            if token.id == updated.id:
                self._tokens[index] = updated
                break

    def _ensure_session_ready(self) -> None:
        self._ensure_services_ready()
        if self.current_session is None:
            raise ValueError("Create session before draw/reveal/hide/reset")

    def _next_seed(self) -> int:
        self._seed_counter += 1
        return self._seed_counter

    @staticmethod
    def _generate_grid_positions(count: int) -> list[tuple[float, float]]:
        if count <= 0:
            return []

        cols = max(1, math.ceil(math.sqrt(count)))
        rows = max(1, math.ceil(count / cols))

        x_min, x_max = 10.0, 90.0
        y_min, y_max = 10.0, 90.0

        if cols == 1:
            x_values = [50.0]
        else:
            x_values = [x_min + i * ((x_max - x_min) / (cols - 1)) for i in range(cols)]

        if rows == 1:
            y_values = [50.0]
        else:
            y_values = [y_min + i * ((y_max - y_min) / (rows - 1)) for i in range(rows)]

        positions: list[tuple[float, float]] = []
        for row in range(rows):
            for col in range(cols):
                positions.append((round(x_values[col], 3), round(y_values[row], 3)))
                if len(positions) == count:
                    return positions

        return positions
