from uuid import UUID

from pydantic import BaseModel, Field

from src.core.models.enums import TokenState


class TableToken(BaseModel):
    token_id: UUID
    state: TokenState = TokenState.FACE_DOWN
    x: float = Field(ge=0.0, le=100.0)
    y: float = Field(ge=0.0, le=100.0)
    z: float = Field(default=0.0, ge=0.0, le=100.0)
    rotation: float = Field(default=0.0, ge=0.0, le=180.0)
