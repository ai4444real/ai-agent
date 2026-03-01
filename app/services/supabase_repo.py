from datetime import datetime
from typing import Any
from uuid import UUID

from tenacity import retry, stop_after_attempt, wait_exponential

from app.db import get_supabase_client


class SupabaseRepo:
    def __init__(self) -> None:
        self._client = get_supabase_client()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
    def insert_thing(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._client.table("things").insert(payload).execute()
        return response.data[0]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
    def list_things(
        self,
        thing_type: str | None = None,
        from_ts: datetime | None = None,
        to_ts: datetime | None = None,
    ) -> list[dict[str, Any]]:
        query = self._client.table("things").select("*").order("created_at", desc=True)
        if thing_type:
            query = query.eq("type", thing_type)
        if from_ts:
            query = query.gte("created_at", from_ts.isoformat())
        if to_ts:
            query = query.lte("created_at", to_ts.isoformat())
        response = query.execute()
        return response.data or []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
    def create_run(self, action: str, input_summary: dict[str, Any] | None = None) -> dict[str, Any]:
        response = (
            self._client.table("runs")
            .insert(
                {
                    "action": action,
                    "status": "running",
                    "input_summary": input_summary,
                }
            )
            .execute()
        )
        return response.data[0]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
    def finish_run(self, run_id: UUID | str, status: str, error: str | None = None) -> dict[str, Any]:
        response = (
            self._client.table("runs")
            .update({"status": status, "error": error})
            .eq("id", str(run_id))
            .execute()
        )
        return response.data[0]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
    def insert_message(
        self,
        channel: str,
        recipient: str,
        subject: str,
        body: str,
        action: str,
        run_id: UUID | str | None,
    ) -> dict[str, Any]:
        response = (
            self._client.table("messages")
            .insert(
                {
                    "channel": channel,
                    "recipient": recipient,
                    "subject": subject,
                    "body": body,
                    "action": action,
                    "run_id": str(run_id) if run_id else None,
                }
            )
            .execute()
        )
        return response.data[0]
