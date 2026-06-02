import random
from collections import Counter

from src.infrastructure.deck_adapter.exceptions import (
    DeckEmptyError,
    DuplicateTokenIdError,
    InvalidDrawCountError,
)


class TokenDeck:
    """Deterministic in-memory token deck adapter.

    The adapter only handles low-level deck operations over token IDs.
    Domain rules stay in core engine/services.
    """

    def __init__(self, token_ids: list[str], seed: int | None = None) -> None:
        self._validate_token_ids(token_ids)
        self._seed = seed
        self._rng = random.Random(seed)
        self._initial_token_ids = list(token_ids)
        self._deck = list(token_ids)
        self.shuffle()

    @staticmethod
    def _validate_token_ids(token_ids: list[str]) -> None:
        duplicates = [token_id for token_id, count in Counter(token_ids).items() if count > 1]
        if duplicates:
            raise DuplicateTokenIdError(f"Duplicate token IDs are not allowed: {duplicates}")

    def shuffle(self) -> None:
        self._rng.shuffle(self._deck)

    def draw_one(self) -> str:
        if self.is_empty():
            raise DeckEmptyError("Cannot draw from an empty deck")
        return self._deck.pop(0)

    def draw_many(self, k: int) -> list[str]:
        if k <= 0:
            raise InvalidDrawCountError("k must be greater than zero")
        if k > self.remaining_count():
            raise DeckEmptyError(
                f"Cannot draw {k} tokens from deck with {self.remaining_count()} remaining"
            )
        return [self.draw_one() for _ in range(k)]

    def remaining_count(self) -> int:
        return len(self._deck)

    def is_empty(self) -> bool:
        return self.remaining_count() == 0

    def reset(self, token_ids: list[str] | None = None) -> None:
        if token_ids is not None:
            self._validate_token_ids(token_ids)
            self._initial_token_ids = list(token_ids)
        self._deck = list(self._initial_token_ids)
        self._rng = random.Random(self._seed)
        self.shuffle()

    def peek_all(self) -> list[str]:
        return list(self._deck)

    def remove(self, token_id: str) -> None:
        if token_id in self._deck:
            self._deck.remove(token_id)

    def contains(self, token_id: str) -> bool:
        return token_id in self._deck
