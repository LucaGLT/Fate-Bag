from abc import ABC, abstractmethod
from uuid import UUID

from src.core.models.session import Session


class SessionRepository(ABC):
    @abstractmethod
    def save(self, session: Session) -> None:
        raise NotImplementedError

    @abstractmethod
    def load(self, session_id: UUID) -> Session | None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, session_id: UUID) -> None:
        raise NotImplementedError
