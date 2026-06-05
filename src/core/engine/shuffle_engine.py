import random

from src.core.models.session import Session
from src.core.models.enums import TokenState


class ShuffleEngine:
    def shuffle(self, session: Session, seed: int | None = None) -> Session:
        rng = random.Random(seed)
        
        face_down_tokens = [t for t in session.table_tokens if t.state == TokenState.FACE_DOWN]
        face_down_positions = [
            (table_token.x, table_token.y, table_token.z, table_token.rotation)
            for table_token in face_down_tokens
        ]

        rng.shuffle(face_down_tokens)

        for index, table_token in enumerate(face_down_tokens):
            x, y, z, rotation = face_down_positions[index]
            table_token.x = x
            table_token.y = y
            table_token.z = z
            table_token.rotation = rotation

        session.seed = seed
        return session
