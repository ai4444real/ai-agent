from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ThingCreateRequest(BaseModel):
    type: str = Field(min_length=1)
    value_num: Decimal | None = None
    value_text: str | None = None
    tags: list[str] | None = None
    meta: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_mood(self) -> "ThingCreateRequest":
        if self.type == "mood":
            if self.value_num is None:
                raise ValueError("value_num is required for mood")
            if self.value_num != int(self.value_num):
                raise ValueError("value_num must be an integer for mood")
            as_int = int(self.value_num)
            if as_int < 1 or as_int > 5:
                raise ValueError("value_num must be between 1 and 5 for mood")
        return self


class ThingResponse(BaseModel):
    id: UUID
    created_at: datetime
    type: str
    value_num: Decimal | None = None
    value_text: str | None = None
    tags: list[str] | None = None
    meta: dict[str, Any] | None = None


class ActionResponse(BaseModel):
    ok: bool
    action: str
    run_id: UUID


class RunResponse(BaseModel):
    id: UUID
    created_at: datetime
    action: str
    status: str
    input_summary: dict[str, Any] | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    ok: bool
