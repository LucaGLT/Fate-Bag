import random
import math
from uuid import UUID

from src.core.models.enums import TokenState
from src.core.models.session import Session
from src.core.models.table_token import TableToken
from src.core.models.token import Token


class SessionEngine:
    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = {token.id: token for token in tokens}

    def use_all_tokens(self, *, seed: int | None = None) -> Session:
        return self.create_session(seed=seed)

    def use_token_ids(self, token_ids: list[UUID], *, seed: int | None = None) -> Session:
        return self.create_session(use_token_ids=token_ids, seed=seed)

    def exclude_token_ids(self, token_ids: list[UUID], *, seed: int | None = None) -> Session:
        return self.create_session(exclude_token_ids=token_ids, seed=seed)

    def use_category(self, category: str, *, seed: int | None = None) -> Session:
        return self.create_session(category=category, seed=seed)

    def use_random_subset(self, subset_size: int, *, seed: int | None = None) -> Session:
        return self.create_session(random_subset_size=subset_size, seed=seed)

    def create_session(
        self,
        *,
        use_token_ids: list[UUID] | None = None,
        exclude_token_ids: list[UUID] | None = None,
        category: str | None = None,
        tag: str | None = None,
        random_subset_size: int | None = None,
        seed: int | None = None,
    ) -> Session:
        selected_tokens = list(self._tokens.values())

        if use_token_ids is not None:
            self._ensure_unique_ids(use_token_ids)
            self.ensure_existing_ids(use_token_ids)
            selected_tokens = [self._tokens[token_id] for token_id in use_token_ids]

        if exclude_token_ids:
            self._ensure_unique_ids(exclude_token_ids)
            self.ensure_existing_ids(exclude_token_ids)
            excluded = set(exclude_token_ids)
            selected_tokens = [token for token in selected_tokens if token.id not in excluded]

        if category is not None:
            selected_tokens = [token for token in selected_tokens if category in token.categories]

        if tag is not None:
            selected_tokens = [token for token in selected_tokens if tag in token.tags]

        if random_subset_size is not None:
            if random_subset_size <= 0:
                raise ValueError("random_subset_size must be greater than zero")
            if random_subset_size > len(selected_tokens):
                raise ValueError("random_subset_size cannot exceed selected tokens")
            rng = random.Random(seed)
            selected_tokens = rng.sample(selected_tokens, random_subset_size)

        positions = self._generate_grid_positions(len(selected_tokens))
        table_tokens = [
            TableToken(
                token_id=token.id,
                state=TokenState.FACE_DOWN,
                x=positions[index][0],
                y=positions[index][1],
                z=0.0,
                rotation=0.0,
            )
            for index, token in enumerate(selected_tokens)
        ]

        return Session(seed=seed, table_tokens=table_tokens)

    def reset_session(self, session: Session) -> Session:
        for table_token in session.table_tokens:
            table_token.state = TokenState.FACE_DOWN
        session.draw_history.clear()
        return session

    @staticmethod
    def _ensure_unique_ids(token_ids: list[UUID]) -> None:
        if len(set(token_ids)) != len(token_ids):
            raise ValueError("Token IDs must be unique")

    def ensure_existing_ids(self, token_ids: list[UUID]) -> None:
        unknown = [token_id for token_id in token_ids if token_id not in self._tokens]
        if unknown:
            raise ValueError(f"Unknown token IDs: {unknown}")

    def token_by_id(self, token_id: UUID) -> Token:
        token = self._tokens.get(token_id)
        if token is None:
            raise ValueError(f"Unknown token ID: {token_id}")
        return token

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
