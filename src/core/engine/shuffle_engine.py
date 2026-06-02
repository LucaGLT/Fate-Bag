import random

from src.core.models.session import Session


class ShuffleEngine:
    def shuffle(self, session: Session, seed: int | None = None) -> Session:
        rng = random.Random(seed)
        original_positions = [
            (table_token.x, table_token.y, table_token.z, table_token.rotation)
            for table_token in session.table_tokens
        ]

        rng.shuffle(session.table_tokens)

        for index, table_token in enumerate(session.table_tokens):
            x, y, z, rotation = original_positions[index]
            table_token.x = x
            table_token.y = y
            table_token.z = z
            table_token.rotation = rotation

        session.seed = seed
        return session
