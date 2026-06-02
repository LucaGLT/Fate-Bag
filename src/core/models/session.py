from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from src.core.models.table_token import TableToken


class Session(BaseModel):
    session_id: UUID = Field(default_factory=uuid4)
    seed: int | None = None
    table_tokens: list[TableToken] = Field(default_factory=list)
    draw_history: list[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("table_tokens")
    @classmethod
    def _validate_unique_table_tokens(cls, values: list[TableToken]) -> list[TableToken]:
        token_ids = [table_token.token_id for table_token in values]
        if len(token_ids) != len(set(token_ids)):
            raise ValueError("table_tokens must contain unique token_id values")
        return values
