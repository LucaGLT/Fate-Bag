import json
from pathlib import Path
from uuid import UUID

from src.core.models.session import Session
from src.core.repositories.session_repository import SessionRepository


class JsonSessionRepository(SessionRepository):
    def __init__(self, file_path: str | Path) -> None:
        self._file_path = Path(file_path)

    def save(self, session: Session) -> None:
        items = self._read_all_raw()
        serialized = session.model_dump(mode="json")
        session_id = serialized["session_id"]

        for index, item in enumerate(items):
            if item.get("session_id") == session_id:
                items[index] = serialized
                self._write_all_raw(items)
                return

        items.append(serialized)
        self._write_all_raw(items)

    def load(self, session_id: UUID) -> Session | None:
        session_id_str = str(session_id)
        for item in self._read_all_raw():
            if item.get("session_id") == session_id_str:
                return Session.model_validate(item)
        return None

    def delete(self, session_id: UUID) -> None:
        session_id_str = str(session_id)
        items = [item for item in self._read_all_raw() if item.get("session_id") != session_id_str]
        self._write_all_raw(items)

    def _read_all_raw(self) -> list[dict]:
        if not self._file_path.exists():
            return []

        content = self._file_path.read_text(encoding="utf-8").strip()
        if not content:
            return []

        data = json.loads(content)
        if not isinstance(data, list):
            raise ValueError("Session repository JSON must contain a list")

        return data

    def _write_all_raw(self, items: list[dict]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(json.dumps(items, indent=2), encoding="utf-8")
