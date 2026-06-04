import json
import math
import re
from pathlib import Path
from uuid import UUID

from src.core.engine.draw_engine import DrawEngine
from src.core.engine.session_engine import SessionEngine
from src.core.engine.shuffle_engine import ShuffleEngine
from src.core.events.event_bus import EventBus
from src.core.models.enums import TokenFrontType, TokenShape, TokenState
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
        self._token_file_settings = self._default_token_file_settings(self._bootstrap_tokens_file)
        self._tokens: list[Token] = []
        self._tokens_by_id: dict[UUID, Token] = {}
        self._token_name_by_id: dict[UUID, str] = {}

        self._session_service: SessionService | None = None
        self._draw_service: DrawService | None = None
        self.current_session: Session | None = None

    @property
    def bootstrap_tokens_file(self) -> Path:
        return self._bootstrap_tokens_file

    @property
    def token_file_settings(self) -> dict:
        return dict(self._token_file_settings)

    def load_tokens(self, tokens_file: str | Path | None = None) -> list[Token]:
        self._ensure_runtime_assets()

        if tokens_file is not None:
            selected_file = Path(tokens_file)
            self._bootstrap_tokens_file = selected_file
            bootstrap_tokens, settings = self._load_tokens_and_settings_from_file(selected_file)
            self._token_file_settings = settings
            self._write_tokens_to_file(selected_file, bootstrap_tokens, settings)
            self._set_active_token_repository(selected_file)
            self._token_repo.update_settings(settings)
            tokens = self._token_service.list_tokens()
            self.current_session = None

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

        bootstrap_tokens, settings = self._load_tokens_and_settings_from_file(self._bootstrap_tokens_file)
        self._token_file_settings = settings
        existing_tokens = self._token_service.list_tokens()
        for token in existing_tokens:
            self._token_service.delete_token(token.id)

        for token in bootstrap_tokens:
            self._token_service.create_token(token)

        tokens = self._token_service.list_tokens()
        self.current_session = None

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
        self._token_repo.update_settings(settings)

        return tokens

    def _set_active_token_repository(self, file_path: Path) -> None:
        self._token_repo = JsonTokenRepository(file_path)
        self._token_service = TokenService(self._token_repo, self._event_bus)

    @staticmethod
    def _write_tokens_to_file(file_path: Path, tokens: list[Token], settings: dict) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = JsonTokenRepository(file_path)._normalize_document_for_write({
            "settings": dict(settings),
            "tokens": [token.model_dump(mode="json") for token in tokens],
        })
        file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

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

    def create_new_token(self) -> Token:
        existing_names = {token.name for token in self._tokens}
        base_name = "Nuovo Token"
        suffix = 1
        candidate = f"{base_name} {suffix}"
        while candidate in existing_names:
            suffix += 1
            candidate = f"{base_name} {suffix}"

        token = Token(
            name=candidate,
            shape=TokenShape.CIRCLE,
            front_type=TokenFrontType.TEXT,
            front_value=candidate,
            back_value=str(self._default_back_image_path()),
            tags=[],
            categories=[],
        )
        created = self._token_service.create_token(token)
        self._tokens.append(created)
        self._tokens_by_id[created.id] = created
        self._token_name_by_id[created.id] = created.name
        return created

    def delete_tokens(self, token_ids: list[UUID]) -> int:
        selected_ids = self._normalize_selected_token_ids(token_ids)
        selected_set = set(selected_ids)

        for token_id in selected_ids:
            token = self._tokens_by_id.get(token_id)
            if token is None:
                raise ValueError(f"Token non trovato: {token_id}")
            self._token_service.delete_token(token_id)

        self._tokens = [token for token in self._tokens if token.id not in selected_set]
        for token_id in selected_set:
            self._tokens_by_id.pop(token_id, None)
            self._token_name_by_id.pop(token_id, None)

        if self.current_session is not None:
            self.current_session.table_tokens = [
                table_token
                for table_token in self.current_session.table_tokens
                if table_token.token_id not in selected_set
            ]
            self._session_repo.save(self.current_session)

        return len(selected_ids)

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

    def draw_all(self) -> list[str]:
        self._ensure_session_ready()
        remaining = sum(
            1
            for table_token in self.current_session.table_tokens
            if table_token.state == TokenState.FACE_DOWN
        )
        if remaining <= 0:
            return []

        seed = self._next_seed() if self._deterministic_mode else None
        return self._draw_service.draw_uniform(
            self.current_session,
            count=remaining,
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

    def clear_bag(self) -> None:
        self._ensure_services_ready()
        if self.current_session is None:
            return

        self._session_service.close_session(self.current_session.session_id)
        self.current_session = None

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
                    "shape": token.shape.value,
                    "tags": list(token.tags),
                    "categories": list(token.categories),
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
        normalized_name = self._extract_name_from_formatted_text(normalized_text)

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

            payload["name"] = normalized_name

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

    def tip_text_for_token(self, token_id: UUID) -> str:
        token = self._tokens_by_id.get(token_id)
        if token is None:
            raise ValueError(f"Token non trovato: {token_id}")
        return str(token.metadata.get("tip_text", "")).strip()

    def token_for_id(self, token_id: UUID) -> Token:
        token = self._tokens_by_id.get(token_id)
        if token is None:
            raise ValueError(f"Token non trovato: {token_id}")
        return token

    def apply_token_metadata_to_tokens(
        self,
        token_ids: list[UUID],
        *,
        text: str,
        tip_text: str | None,
        tags: list[str],
        shape: TokenShape,
        display_mode: str,
    ) -> int:
        selected_ids = self._normalize_selected_token_ids(token_ids)
        normalized_text = text.strip()
        if not normalized_text:
            raise ValueError("Il testo token deve essere non vuoto")

        normalized_name = self._extract_name_from_formatted_text(normalized_text)
        if not normalized_name:
            raise ValueError("Il nome token deve essere non vuoto")

        normalized_tags = [tag.strip() for tag in tags if str(tag).strip()]
        normalized_tip_text = ""
        if isinstance(tip_text, str):
            normalized_tip_text = tip_text.strip()

        updated_count = 0
        for token_id in selected_ids:
            token = self._tokens_by_id.get(token_id)
            if token is None:
                raise ValueError(f"Token non trovato: {token_id}")

            payload = token.model_dump(mode="json")
            payload["name"] = normalized_name
            payload["tags"] = normalized_tags
            payload["shape"] = shape.value
            metadata = dict(payload.get("metadata", {}))
            if normalized_tip_text:
                metadata["tip_text"] = normalized_tip_text
            else:
                metadata.pop("tip_text", None)

            if display_mode == "text_only":
                payload["front_type"] = TokenFrontType.TEXT.value
                payload["front_value"] = normalized_text
                metadata.pop("front_text", None)
                metadata.pop("front_text_color_mode", None)
            elif display_mode == "image_only":
                if token.front_type not in (TokenFrontType.IMAGE, TokenFrontType.TEXT_IMAGE):
                    raise ValueError("Per 'Solo Immagine' serve prima una Front-Img")
                # Preserve full text for hover preview in IMAGE mode.
                metadata["front_text"] = normalized_text
                metadata.pop("front_text_color_mode", None)
                payload["front_type"] = TokenFrontType.IMAGE.value
            elif display_mode in ("image_text_black", "image_text_white", "image_text_auto"):
                if token.front_type not in (TokenFrontType.IMAGE, TokenFrontType.TEXT_IMAGE):
                    raise ValueError("Per 'Imm+Testo' serve prima una Front-Img")
                payload["front_type"] = TokenFrontType.TEXT_IMAGE.value
                metadata["front_text"] = normalized_text
                if display_mode == "image_text_black":
                    metadata["front_text_color_mode"] = "black"
                elif display_mode == "image_text_white":
                    metadata["front_text_color_mode"] = "white"
                else:
                    metadata["front_text_color_mode"] = "auto"
            else:
                raise ValueError(f"Modalita non supportata: {display_mode}")

            payload["metadata"] = metadata

            updated = Token.model_validate(payload)
            self._token_service.update_token(updated)
            self._update_token_cache(updated)
            updated_count += 1

        return updated_count

    def _ensure_runtime_assets(self) -> None:
        assets_dir = self._base_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        back_image = assets_dir / "back.png"
        if not back_image.exists():
            back_image.write_bytes(b"fake-image")

    def _default_back_image_path(self) -> Path:
        self._ensure_runtime_assets()
        return self._base_dir / "assets" / "back.png"

    def _load_tokens_and_settings_from_file(self, source_file: Path) -> tuple[list[Token], dict]:
        if not source_file.exists():
            raise FileNotFoundError(
                f"Bootstrap token file not found: {source_file}"
            )

        data = json.loads(source_file.read_text(encoding="utf-8"))

        if isinstance(data, list):
            raw_tokens = data
            settings = self._default_token_file_settings(source_file)
        elif isinstance(data, dict):
            raw_tokens = data.get("tokens", [])
            if not isinstance(raw_tokens, list):
                raise ValueError("Bootstrap token JSON field 'tokens' must contain a list")
            settings = self._normalize_token_file_settings(data.get("settings", {}), source_file)
        else:
            raise ValueError("Bootstrap token JSON must contain either a list or an object")

        back_image = self._base_dir / "assets" / "back.png"
        assets_root_dir = Path(settings["assets_root_path"])
        source_dir = source_file.parent
        tokens: list[Token] = []
        for item in raw_tokens:
            payload = dict(item)

            front_type_raw = str(payload.get("front_type", "")).strip().upper()
            if front_type_raw in (TokenFrontType.IMAGE.value, TokenFrontType.TEXT_IMAGE.value):
                resolved_front = self._resolve_existing_image_path(
                    payload.get("front_value"),
                    assets_root_dir=assets_root_dir,
                    source_dir=source_dir,
                )
                if resolved_front is not None:
                    payload["front_value"] = resolved_front

            back_value = payload.get("back_value")
            if self._is_runtime_back_placeholder(back_value):
                payload["back_value"] = str(back_image)
            else:
                resolved_back = self._resolve_existing_image_path(
                    back_value,
                    assets_root_dir=assets_root_dir,
                    source_dir=source_dir,
                )
                if resolved_back is not None:
                    payload["back_value"] = resolved_back
                else:
                    payload["back_value"] = str(back_image)

            if isinstance(payload.get("back_value"), str) and not Path(payload["back_value"]).is_file():
                payload["back_value"] = str(back_image)

            self._sanitize_invalid_front_image_payload(payload)
            tokens.append(Token.model_validate(payload))

        return tokens, settings

    def _default_token_file_settings(self, source_file: Path | None) -> dict:
        source = source_file or self._bootstrap_tokens_file
        source_parent = source.parent if source.parent else Path.cwd()
        return {
            "assets_root_path": str(source_parent.resolve()),
            "table_background_file": "",
            "token_radius_px": 42,
            "table_grid_margin_px": 42,
            "hover_preview_enabled": True,
            "front_text_font_px": 7,
            "tip_text_font_px": 8,
            "flip_speed": 60,
            "move_speed": 60,
            "auto_sort_delay_seconds": 0.0,
            "auto_shuffle_after_insert_count": 3,
        }

    def _normalize_token_file_settings(self, raw_settings: object, source_file: Path) -> dict:
        defaults = self._default_token_file_settings(source_file)
        if not isinstance(raw_settings, dict):
            return defaults

        normalized = dict(defaults)

        def _first_present(*keys: str) -> object:
            for key in keys:
                if key in raw_settings:
                    return raw_settings.get(key)
            return None

        raw_assets_root = _first_present("assets_root_path", "root_path", "root-path")
        if isinstance(raw_assets_root, str) and raw_assets_root.strip():
            root_candidate = Path(raw_assets_root.strip())
            if not root_candidate.is_absolute():
                root_candidate = (source_file.parent / root_candidate).resolve()
            normalized["assets_root_path"] = str(root_candidate)

        raw_background = _first_present(
            "table_background_file",
            "table_background",
            "table-background-file",
        )
        resolved_background = self._resolve_existing_image_path(
            raw_background,
            assets_root_dir=Path(normalized["assets_root_path"]),
            source_dir=source_file.parent,
        )
        normalized["table_background_file"] = resolved_background or ""

        raw_radius = _first_present("token_radius_px", "token_radius", "token-radius-px")
        if isinstance(raw_radius, (int, float)):
            normalized["token_radius_px"] = int(max(16, min(180, round(float(raw_radius)))))

        raw_margin = raw_settings.get("table_grid_margin_px")
        if isinstance(raw_margin, (int, float)):
            normalized["table_grid_margin_px"] = int(max(16, min(220, round(float(raw_margin)))))

        raw_hover = raw_settings.get("hover_preview_enabled")
        if isinstance(raw_hover, bool):
            normalized["hover_preview_enabled"] = raw_hover

        raw_front_text_font = _first_present("front_text_font_px", "front_text_font", "front_text_size_px")
        if isinstance(raw_front_text_font, (int, float)):
            normalized["front_text_font_px"] = int(max(5, min(24, round(float(raw_front_text_font)))))

        raw_tip_text_font = _first_present("tip_text_font_px", "tip_text_font", "tip_text_size_px")
        if isinstance(raw_tip_text_font, (int, float)):
            normalized["tip_text_font_px"] = int(max(6, min(28, round(float(raw_tip_text_font)))))

        raw_flip_speed = _first_present("flip_speed", "flip-speed", "flip_speed_percent")
        if isinstance(raw_flip_speed, (int, float)):
            normalized["flip_speed"] = int(max(1, min(100, round(float(raw_flip_speed)))))

        raw_move_speed = _first_present("move_speed", "move-speed", "move_speed_percent")
        if isinstance(raw_move_speed, (int, float)):
            normalized["move_speed"] = int(max(1, min(100, round(float(raw_move_speed)))))

        raw_auto_sort_delay = _first_present(
            "auto_sort_delay_seconds",
            "auto-sort-delay-seconds",
            "auto_sort_delay_s",
        )
        if isinstance(raw_auto_sort_delay, (int, float)):
            normalized["auto_sort_delay_seconds"] = max(0.0, float(raw_auto_sort_delay))

        raw_auto_shuffle_count = _first_present(
            "auto_shuffle_after_insert_count",
            "auto-shuffle-after-insert-count",
            "auto_shuffle_count",
        )
        if isinstance(raw_auto_shuffle_count, (int, float)):
            normalized["auto_shuffle_after_insert_count"] = max(0, int(round(float(raw_auto_shuffle_count))))

        return normalized

    @staticmethod
    def _resolve_existing_image_path(
        raw_path: object,
        *,
        assets_root_dir: Path,
        source_dir: Path,
    ) -> str | None:
        if not isinstance(raw_path, str):
            return None

        candidate = raw_path.strip()
        if not candidate:
            return None

        direct = Path(candidate)
        if direct.is_file():
            return str(direct)

        attempts: list[Path] = []
        if direct.is_absolute():
            attempts.append(direct)
        else:
            attempts.append((assets_root_dir / direct).resolve())
            attempts.append((source_dir / direct).resolve())

        for attempt in attempts:
            if attempt.is_file():
                return str(attempt)

        return None

    @staticmethod
    def _sanitize_invalid_front_image_payload(payload: dict) -> None:
        front_type_raw = str(payload.get("front_type", "")).strip().upper()
        if front_type_raw not in (TokenFrontType.IMAGE.value, TokenFrontType.TEXT_IMAGE.value):
            return

        front_value = payload.get("front_value")
        if isinstance(front_value, str) and Path(front_value).is_file():
            return

        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}

        fallback_text = str(metadata.get("front_text", "")).strip()
        if not fallback_text:
            fallback_text = str(payload.get("name", "Token")).strip() or "Token"

        payload["front_type"] = TokenFrontType.TEXT.value
        payload["front_value"] = fallback_text
        metadata.pop("front_text", None)
        metadata.pop("front_text_color_mode", None)
        payload["metadata"] = metadata

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
    def _is_runtime_back_placeholder(value: object) -> bool:
        if not isinstance(value, str):
            return False
        normalized = value.strip().upper().replace("_", "")
        return normalized == "RUNTIMEBACKIMAGE"

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
        if token.front_type == TokenFrontType.IMAGE:
            text = str(token.metadata.get("front_text", "")).strip()
            if text:
                return text
        if token.front_type == TokenFrontType.TEXT_IMAGE:
            text = str(token.metadata.get("front_text", "")).strip()
            if text:
                return text
        return token.name

    @staticmethod
    def _extract_name_from_formatted_text(full_text: str) -> str:
        match = re.search(r"<\s*([^<>]+?)\s*>", full_text)
        if match:
            candidate = MainController._sanitize_name_text(match.group(1))
            if candidate:
                return candidate
        return MainController._sanitize_name_text(full_text)

    @staticmethod
    def _sanitize_name_text(value: str) -> str:
        cleaned = value.replace("<", "").replace(">", "").strip()
        return cleaned

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
