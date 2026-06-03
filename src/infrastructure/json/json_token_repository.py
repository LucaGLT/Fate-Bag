import json
from pathlib import Path
from uuid import UUID

from src.core.models.token import Token
from src.core.repositories.token_repository import TokenRepository


class JsonTokenRepository(TokenRepository):
    def __init__(self, file_path: str | Path) -> None:
        self._file_path = Path(file_path)

    def get_settings(self) -> dict:
        document = self._read_document_raw()
        settings = document.get("settings", {})
        return dict(settings) if isinstance(settings, dict) else {}

    def update_settings(self, settings: dict) -> None:
        document = self._read_document_raw()
        document["settings"] = dict(settings)
        self._write_document_raw(document)

    def get_all(self) -> list[Token]:
        settings = self.get_settings()
        assets_root = self._normalized_assets_root(settings.get("assets_root_path"))
        source_dir = self._file_path.parent.resolve()
        return [
            Token.model_validate(self._resolve_token_paths_for_read(item, assets_root, source_dir))
            for item in self._read_all_raw()
        ]

    def get_by_id(self, token_id: UUID) -> Token | None:
        for token in self.get_all():
            if token.id == token_id:
                return token
        return None

    def save(self, token: Token) -> None:
        items = self._read_all_raw()
        serialized = token.model_dump(mode="json")
        token_id = serialized["id"]

        for index, item in enumerate(items):
            if item.get("id") == token_id:
                items[index] = serialized
                self._write_all_raw(items)
                return

        items.append(serialized)
        self._write_all_raw(items)

    def delete(self, token_id: UUID) -> None:
        token_id_str = str(token_id)
        items = [item for item in self._read_all_raw() if item.get("id") != token_id_str]
        self._write_all_raw(items)

    def _read_all_raw(self) -> list[dict]:
        document = self._read_document_raw()
        tokens = document.get("tokens", [])
        if not isinstance(tokens, list):
            raise ValueError("Token repository JSON field 'tokens' must contain a list")
        return tokens

    def _read_document_raw(self) -> dict:
        if not self._file_path.exists():
            return {"settings": {}, "tokens": []}

        content = self._file_path.read_text(encoding="utf-8").strip()
        if not content:
            return {"settings": {}, "tokens": []}

        data = json.loads(content)
        if isinstance(data, list):
            return {"settings": {}, "tokens": data}
        if isinstance(data, dict):
            tokens = data.get("tokens", [])
            settings = data.get("settings", {})
            if not isinstance(tokens, list):
                raise ValueError("Token repository JSON field 'tokens' must contain a list")
            if not isinstance(settings, dict):
                raise ValueError("Token repository JSON field 'settings' must contain an object")
            return {
                "settings": settings,
                "tokens": tokens,
            }
        raise ValueError("Token repository JSON must contain either a list or an object")

    def _write_document_raw(self, document: dict) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = self._normalize_document_for_write(document)
        self._file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _write_all_raw(self, items: list[dict]) -> None:
        document = self._read_document_raw()
        document["tokens"] = items
        self._write_document_raw(document)

    def _normalize_document_for_write(self, document: dict) -> dict:
        settings = dict(document.get("settings", {}))
        tokens = list(document.get("tokens", []))

        assets_root = self._normalized_assets_root(settings.get("assets_root_path"))

        table_background = settings.get("table_background_file")
        if isinstance(table_background, str):
            settings["table_background_file"] = self._path_relative_to_root_if_possible(
                table_background,
                assets_root,
            )

        normalized_tokens: list[dict] = []
        for item in tokens:
            payload = dict(item)
            front_value = payload.get("front_value")
            back_value = payload.get("back_value")
            if isinstance(front_value, str):
                payload["front_value"] = self._path_relative_to_root_if_possible(front_value, assets_root)
            if isinstance(back_value, str):
                payload["back_value"] = self._path_relative_to_root_if_possible(back_value, assets_root)
            normalized_tokens.append(payload)

        return {
            "settings": settings,
            "tokens": normalized_tokens,
        }

    @staticmethod
    def _normalized_assets_root(raw_path: object) -> Path | None:
        if not isinstance(raw_path, str) or not raw_path.strip():
            return None
        return Path(raw_path).resolve()

    @staticmethod
    def _path_relative_to_root_if_possible(raw_path: str, assets_root: Path | None) -> str:
        if assets_root is None:
            return raw_path

        candidate = raw_path.strip()
        if not candidate:
            return raw_path

        path = Path(candidate)
        if not path.is_absolute():
            return raw_path

        try:
            return str(path.resolve().relative_to(assets_root))
        except ValueError:
            return raw_path

    @staticmethod
    def _resolve_token_paths_for_read(item: dict, assets_root: Path | None, source_dir: Path) -> dict:
        payload = dict(item)
        for field_name in ("front_value", "back_value"):
            raw_value = payload.get(field_name)
            if not isinstance(raw_value, str):
                continue

            candidate = raw_value.strip()
            if not candidate:
                continue

            path = Path(candidate)
            if path.is_absolute():
                continue

            attempts: list[Path] = []
            if assets_root is not None:
                attempts.append((assets_root / path).resolve())
            attempts.append((source_dir / path).resolve())

            for attempt in attempts:
                if attempt.is_file():
                    payload[field_name] = str(attempt)
                    break

        return payload
