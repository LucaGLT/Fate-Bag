from uuid import UUID

from src.core.events.event_bus import EventBus
from src.core.events.event_types import TokenCreated, TokenDeleted, TokenUpdated
from src.core.models.token import Token
from src.core.repositories.token_repository import TokenRepository


class TokenService:
    def __init__(self, repository: TokenRepository, event_bus: EventBus) -> None:
        self._repository = repository
        self._event_bus = event_bus

    def create_token(self, token: Token) -> Token:
        self._repository.save(token)
        self._event_bus.publish(TokenCreated(payload={"token_id": str(token.id)}))
        return token

    def update_token(self, token: Token) -> Token:
        self._repository.save(token)
        self._event_bus.publish(TokenUpdated(payload={"token_id": str(token.id)}))
        return token

    def delete_token(self, token_id: UUID) -> None:
        self._repository.delete(token_id)
        self._event_bus.publish(TokenDeleted(payload={"token_id": str(token_id)}))

    def list_tokens(self) -> list[Token]:
        return self._repository.get_all()
