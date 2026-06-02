import random

from src.core.models.session import Session


class ShuffleEngine:
    def shuffle(self, session: Session, seed: int | None = None) -> Session:
        rng = random.Random(seed)
        rng.shuffle(session.table_tokens)
        session.seed = seed
        return session
