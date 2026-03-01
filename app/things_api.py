from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth_google import require_google_user
from app.models import MoodQuickRequest, TextQuickRequest, ThingCreateRequest, ThingResponse
from app.services.supabase_repo import SupabaseRepo

router = APIRouter(prefix="/things", tags=["things"])


@router.post("", response_model=ThingResponse)
def create_thing(payload: ThingCreateRequest) -> ThingResponse:
    repo = SupabaseRepo()
    inserted = repo.insert_thing(payload.model_dump(mode="json", exclude_none=True))
    return ThingResponse(**inserted)


@router.get("", response_model=list[ThingResponse])
def list_things(
    type: str | None = None,
    from_ts: Annotated[datetime | None, Query(alias="from")] = None,
    to_ts: Annotated[datetime | None, Query(alias="to")] = None,
) -> list[ThingResponse]:
    repo = SupabaseRepo()
    rows = repo.list_things(thing_type=type, from_ts=from_ts, to_ts=to_ts)
    return [ThingResponse(**row) for row in rows]


@router.post("/mood-quick", response_model=ThingResponse)
def create_mood_quick(payload: MoodQuickRequest, google_user: dict = Depends(require_google_user)) -> ThingResponse:
    repo = SupabaseRepo()
    inserted = repo.insert_thing(
        {
            "type": "mood",
            "value_num": payload.value_num,
            "meta": {"source": "mood_quick", "google_email": google_user.get("email")},
        }
    )
    return ThingResponse(**inserted)


@router.post("/text-quick", response_model=ThingResponse)
def create_text_quick(payload: TextQuickRequest, google_user: dict = Depends(require_google_user)) -> ThingResponse:
    repo = SupabaseRepo()
    inserted = repo.insert_thing(
        {
            "type": payload.type,
            "value_text": payload.value_text,
            "meta": {"source": "text_quick", "google_email": google_user.get("email")},
        }
    )
    return ThingResponse(**inserted)
