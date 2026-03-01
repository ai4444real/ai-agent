from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from zoneinfo import ZoneInfo

from app.actions.weekly_report import compute_week_window_utc
from app.auth_google import require_google_user
from app.models import ChoiceQuickRequest, MoodQuickRequest, TextQuickRequest, ThingResponse
from app.services.supabase_repo import SupabaseRepo
from app.settings import get_settings

router = APIRouter(prefix="/things", tags=["things"])


def _resolve_created_at(use_yesterday: bool) -> str | None:
    if not use_yesterday:
        return None
    settings = get_settings()
    local_tz = ZoneInfo(settings.app_timezone)
    local_dt = datetime.now(local_tz) - timedelta(hours=24)
    return local_dt.astimezone(timezone.utc).isoformat()


def _owner_fields(google_user: dict) -> dict:
    return {
        "owner_sub": google_user.get("sub"),
        "owner_email": google_user.get("email"),
    }


@router.get("-mine", response_model=list[ThingResponse])
def list_my_things(
    type: str | None = None,
    from_ts: Annotated[datetime | None, Query(alias="from")] = None,
    to_ts: Annotated[datetime | None, Query(alias="to")] = None,
    google_user: dict = Depends(require_google_user),
) -> list[ThingResponse]:
    repo = SupabaseRepo()
    rows = repo.list_things(
        thing_type=type,
        from_ts=from_ts,
        to_ts=to_ts,
        owner_sub=google_user.get("sub"),
    )
    return [ThingResponse(**row) for row in rows]


@router.delete("-mine/{thing_id}")
def delete_my_thing(thing_id: UUID, google_user: dict = Depends(require_google_user)) -> dict:
    repo = SupabaseRepo()
    owner_sub = google_user.get("sub")
    existing = repo.get_thing_by_id_owner(str(thing_id), owner_sub)
    if not existing:
        raise HTTPException(status_code=404, detail="Thing not found")
    repo.delete_thing_by_id_owner(str(thing_id), owner_sub)
    return {"ok": True, "deleted_id": str(thing_id)}


@router.post("/mood-quick", response_model=ThingResponse)
def create_mood_quick(payload: MoodQuickRequest, google_user: dict = Depends(require_google_user)) -> ThingResponse:
    repo = SupabaseRepo()
    inserted = repo.insert_thing(
        {
            **_owner_fields(google_user),
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
            **_owner_fields(google_user),
            "type": payload.type,
            "value_text": payload.value_text,
            "meta": {"source": "text_quick", "google_email": google_user.get("email")},
        }
    )
    return ThingResponse(**inserted)


@router.post("/choice-quick", response_model=ThingResponse)
def create_choice_quick(payload: ChoiceQuickRequest, google_user: dict = Depends(require_google_user)) -> ThingResponse:
    repo = SupabaseRepo()
    record: dict = {
        **_owner_fields(google_user),
        "type": payload.type,
        "meta": {
            "source": "choice_quick",
            "google_email": google_user.get("email"),
            "value_kind": payload.value_kind,
            "choice_label": payload.choice_label,
            "choice_icon": payload.choice_icon,
            "choice_image": payload.choice_image,
            "use_yesterday": payload.use_yesterday,
        },
    }
    created_at = _resolve_created_at(payload.use_yesterday)
    if created_at:
        record["created_at"] = created_at
    if payload.value_kind == "num":
        if payload.value_num is not None and payload.value_num == int(payload.value_num):
            record["value_num"] = int(payload.value_num)
        else:
            record["value_num"] = float(payload.value_num) if payload.value_num is not None else None
    else:
        record["value_text"] = payload.value_text

    inserted = repo.insert_thing(record)
    return ThingResponse(**inserted)


@router.get("/summary-window")
def summary_window(days: int = Query(default=8, ge=1, le=31), google_user: dict = Depends(require_google_user)) -> dict:
    settings = get_settings()
    repo = SupabaseRepo()
    start_utc, end_utc = compute_week_window_utc(window_days=days)
    rows = repo.list_things(from_ts=start_utc, to_ts=end_utc, owner_sub=google_user.get("sub"))

    local_tz = ZoneInfo(settings.app_timezone)
    local_today = datetime.now(local_tz).date()

    by_type: dict[str, int] = {}
    today_by_type: dict[str, int] = {}
    by_type_values: dict[str, dict[str, dict[str, int]]] = {}
    recent_entries: list[dict] = []

    def _parse_created_at(value: str | datetime | None) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None

    for row in rows:
        row_type = str(row.get("type") or "unknown").strip().lower()
        by_type[row_type] = by_type.get(row_type, 0) + 1

        created_at = _parse_created_at(row.get("created_at"))
        if created_at:
            created_local_date = created_at.astimezone(local_tz).date()
            if created_local_date == local_today:
                today_by_type[row_type] = today_by_type.get(row_type, 0) + 1

        slot = by_type_values.setdefault(row_type, {"num": {}, "text": {}})
        value_num = row.get("value_num")
        value_text = row.get("value_text")
        if value_num is not None:
            key = str(value_num)
            slot["num"][key] = slot["num"].get(key, 0) + 1
        if value_text:
            key = str(value_text).strip().lower()
            slot["text"][key] = slot["text"].get(key, 0) + 1

        recent_entries.append(
            {
                "created_at": row.get("created_at"),
                "type": row.get("type"),
                "value_num": row.get("value_num"),
                "value_text": row.get("value_text"),
            }
        )

    recent_entries = sorted(recent_entries, key=lambda r: str(r.get("created_at") or ""), reverse=True)[:100]

    return {
        "window_days": days,
        "from": start_utc.isoformat(),
        "to": end_utc.isoformat(),
        "total_entries": len(rows),
        "by_type": by_type,
        "today_by_type": today_by_type,
        "by_type_values": by_type_values,
        "coffee_today": today_by_type.get("caffe", 0),
        "recent_entries": recent_entries,
    }
