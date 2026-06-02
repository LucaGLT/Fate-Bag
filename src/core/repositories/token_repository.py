from abc import ABC, abstractmethod
from uuid import UUID

from src.core.models.token import Token


class TokenRepository(ABC):
    @abstractmethod
    def get_all(self) -> list[Token]:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, token_id: UUID) -> Token | None:
        raise NotImplementedError

    @abstractmethod
    def save(self, token: Token) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, token_id: UUID) -> None:
        raise NotImplementedError
