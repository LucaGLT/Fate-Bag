from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.core.models.enums import TokenFrontType, TokenShape


class Token(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: UUID = Field(default_factory=uuid4, frozen=True)
    name: str = Field(min_length=1)
    shape: TokenShape
    front_type: TokenFrontType
    front_value: str = Field(min_length=1)
    back_value: str = Field(min_length=1)
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    weight: float = Field(default=1.0, gt=0.0)
    rarity: str | None = None

    @field_validator("categories", "tags")
    @classmethod
    def _validate_string_lists(cls, values: list[str]) -> list[str]:
        if any(not item.strip() for item in values):
            raise ValueError("List items must be non-empty strings")
        return values

    @field_validator("rarity")
    @classmethod
    def _validate_rarity(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("rarity must be a non-empty string when provided")
        return value

    @field_validator("back_value")
    @classmethod
    def _validate_back_value_path(cls, value: str) -> str:
        path = Path(value)
        if not path.is_file():
            raise ValueError("back_value must point to an existing image file")
        return value

    @model_validator(mode="after")
    def _validate_front_value_for_front_type(self) -> "Token":
        if self.front_type == TokenFrontType.TEXT and not self.front_value.strip():
            raise ValueError("front_value must be non-empty text for TEXT tokens")

        if self.front_type == TokenFrontType.IMAGE:
            front_path = Path(self.front_value)
            if not front_path.is_file():
                raise ValueError("front_value must point to an existing image file for IMAGE tokens")

        return self
