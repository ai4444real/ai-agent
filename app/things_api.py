from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from app.models import ThingCreateRequest, ThingResponse
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
