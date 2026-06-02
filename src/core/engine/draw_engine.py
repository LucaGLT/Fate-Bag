import random
from uuid import UUID

from src.core.models.enums import TokenState
from src.core.models.session import Session
from src.core.models.token import Token


class DrawEngine:
    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = {token.id: token for token in tokens}

    def draw_uniform(
        self,
        session: Session,
        *,
        count: int = 1,
        with_replacement: bool = False,
        seed: int | None = None,
    ) -> list[UUID]:
        candidates = self._eligible_token_ids(session)
        return self._draw_from_candidates(
            session,
            candidates=candidates,
            count=count,
            with_replacement=with_replacement,
            seed=seed,
        )

    def draw_weighted(
        self,
        session: Session,
        *,
        count: int = 1,
        with_replacement: bool = False,
        seed: int | None = None,
    ) -> list[UUID]:
        candidates = self._eligible_token_ids(session)
        weights = [self._tokens[token_id].weight for token_id in candidates]
        return self._draw_from_candidates(
            session,
            candidates=candidates,
            count=count,
            with_replacement=with_replacement,
            seed=seed,
            weights=weights,
        )

    def draw_by_rarity(
        self,
        session: Session,
        *,
        rarity: str,
        count: int = 1,
        with_replacement: bool = False,
        seed: int | None = None,
    ) -> list[UUID]:
        candidates = [
            token_id
            for token_id in self._eligible_token_ids(session)
            if self._tokens[token_id].rarity == rarity
        ]
        if not candidates:
            raise ValueError(f"No eligible tokens with rarity '{rarity}'")
        return self._draw_from_candidates(
            session,
            candidates=candidates,
            count=count,
            with_replacement=with_replacement,
            seed=seed,
        )

    def reveal_tokens(self, session: Session, token_ids: list[UUID] | None = None) -> list[UUID]:
        selected = self._target_tokens(session, token_ids)
        for token in selected:
            token.state = TokenState.FACE_UP
        return [token.token_id for token in selected]

    def hide_tokens(self, session: Session, token_ids: list[UUID] | None = None) -> list[UUID]:
        selected = self._target_tokens(session, token_ids)
        for token in selected:
            token.state = TokenState.FACE_DOWN
        return [token.token_id for token in selected]

    def _draw_from_candidates(
        self,
        session: Session,
        *,
        candidates: list[UUID],
        count: int,
        with_replacement: bool,
        seed: int | None,
        weights: list[float] | None = None,
    ) -> list[UUID]:
        if count <= 0:
            raise ValueError("count must be greater than zero")
        if not candidates:
            raise ValueError("No eligible tokens available for draw")
        if not with_replacement and count > len(candidates):
            raise ValueError("count cannot exceed eligible tokens without replacement")

        rng = random.Random(seed)
        if with_replacement:
            drawn_ids = rng.choices(candidates, weights=weights, k=count)
        else:
            pool = list(candidates)
            local_weights = list(weights) if weights is not None else None
            drawn_ids: list[UUID] = []
            for _ in range(count):
                if local_weights is None:
                    chosen = rng.choice(pool)
                else:
                    chosen = rng.choices(pool, weights=local_weights, k=1)[0]
                chosen_index = pool.index(chosen)
                drawn_ids.append(chosen)
                pool.pop(chosen_index)
                if local_weights is not None:
                    local_weights.pop(chosen_index)

        table_index = {table_token.token_id: table_token for table_token in session.table_tokens}
        for token_id in set(drawn_ids):
            table_index[token_id].state = TokenState.SELECTED
        session.draw_history.extend(drawn_ids)

        return drawn_ids

    def _eligible_token_ids(self, session: Session) -> list[UUID]:
        eligible_states = {TokenState.FACE_DOWN, TokenState.FACE_UP}
        return [
            table_token.token_id
            for table_token in session.table_tokens
            if table_token.state in eligible_states
        ]

    def _target_tokens(self, session: Session, token_ids: list[UUID] | None) -> list:
        if token_ids is None:
            return session.table_tokens

        token_set = set(token_ids)
        selected = [table_token for table_token in session.table_tokens if table_token.token_id in token_set]
        if len(selected) != len(token_set):
            selected_ids = {table_token.token_id for table_token in selected}
            missing = list(token_set - selected_ids)
            raise ValueError(f"Token IDs not found in session: {missing}")
        return selected
