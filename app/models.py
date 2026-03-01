from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
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


class WeeklyReportRequest(BaseModel):
    owner_sub: str
    owner_email: str | None = None


class DispatchItemResponse(BaseModel):
    owner_sub: str
    owner_email: str | None = None
    ok: bool
    run_id: UUID | None = None
    error: str | None = None


class DispatchResponse(BaseModel):
    ok: bool
    total: int
    success: int
    failed: int
    items: list[DispatchItemResponse]


class RunResponse(BaseModel):
    id: UUID
    created_at: datetime
    action: str
    status: str
    input_summary: dict[str, Any] | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    ok: bool


class MoodQuickRequest(BaseModel):
    value_num: int = Field(ge=1, le=5)


class TextQuickRequest(BaseModel):
    type: str = Field(min_length=1)
    value_text: str = Field(min_length=1)


class ChoiceQuickRequest(BaseModel):
    type: str = Field(min_length=1)
    value_kind: Literal["num", "text"]
    value_num: Decimal | None = None
    value_text: str | None = None
    use_yesterday: bool = False
    choice_label: str | None = None
    choice_icon: str | None = None
    choice_image: str | None = None

    @model_validator(mode="after")
    def validate_choice_payload(self) -> "ChoiceQuickRequest":
        if self.value_kind == "num":
            if self.value_num is None:
                raise ValueError("value_num is required when value_kind is num")
        if self.value_kind == "text":
            if not self.value_text:
                raise ValueError("value_text is required when value_kind is text")
        return self


class GoogleVerifyRequest(BaseModel):
    id_token: str = Field(min_length=10)


class GoogleUserResponse(BaseModel):
    sub: str
    email: str
    name: str | None = None


class GoogleClientIdResponse(BaseModel):
    client_id: str


class ReportRulesRequest(BaseModel):
    text: str = Field(min_length=1)


class ReportRulesResponse(BaseModel):
    text: str | None = None


class TrackerConfigRequest(BaseModel):
    text: str = Field(min_length=1)


class TrackerConfigResponse(BaseModel):
    text: str | None = None
