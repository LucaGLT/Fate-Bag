import json
from pathlib import Path
from uuid import UUID

from src.core.models.token import Token
from src.core.repositories.token_repository import TokenRepository


class JsonTokenRepository(TokenRepository):
    def __init__(self, file_path: str | Path) -> None:
        self._file_path = Path(file_path)

    def get_all(self) -> list[Token]:
        return [Token.model_validate(item) for item in self._read_all_raw()]

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
        if not self._file_path.exists():
            return []

        content = self._file_path.read_text(encoding="utf-8").strip()
        if not content:
            return []

        data = json.loads(content)
        if not isinstance(data, list):
            raise ValueError("Token repository JSON must contain a list")

        return data

    def _write_all_raw(self, items: list[dict]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(json.dumps(items, indent=2), encoding="utf-8")
