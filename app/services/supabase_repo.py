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
        owner_sub: str | None = None,
    ) -> list[dict[str, Any]]:
        query = self._client.table("things").select("*").order("created_at", desc=True)
        if thing_type:
            query = query.eq("type", thing_type)
        if from_ts:
            query = query.gte("created_at", from_ts.isoformat())
        if to_ts:
            query = query.lte("created_at", to_ts.isoformat())
        if owner_sub:
            query = query.eq("owner_sub", owner_sub)
        response = query.execute()
        return response.data or []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
    def create_run(
        self,
        action: str,
        input_summary: dict[str, Any] | None = None,
        owner_sub: str | None = None,
        owner_email: str | None = None,
    ) -> dict[str, Any]:
        response = (
            self._client.table("runs")
            .insert(
                {
                    "owner_sub": owner_sub,
                    "owner_email": owner_email,
                    "action": action,
                    "status": "running",
                    "input_summary": input_summary,
                    "usage": {
                        "requests": 0,
                        "model": None,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_tokens": 0,
                    },
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
    def update_run_input_summary(self, run_id: UUID | str, input_summary: dict[str, Any]) -> dict[str, Any]:
        response = (
            self._client.table("runs")
            .update({"input_summary": input_summary})
            .eq("id", str(run_id))
            .execute()
        )
        return response.data[0]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
    def update_run_usage(self, run_id: UUID | str, usage: dict[str, Any]) -> dict[str, Any]:
        response = (
            self._client.table("runs")
            .update({"usage": usage})
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
        owner_sub: str | None = None,
        owner_email: str | None = None,
    ) -> dict[str, Any]:
        response = (
            self._client.table("messages")
            .insert(
                {
                    "owner_sub": owner_sub,
                    "owner_email": owner_email,
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

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
    def list_latest_runs(self, limit: int = 10) -> list[dict[str, Any]]:
        response = self._client.table("runs").select("*").order("created_at", desc=True).limit(limit).execute()
        return response.data or []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
    def list_latest_runs_by_owner(self, owner_sub: str, limit: int = 10) -> list[dict[str, Any]]:
        response = (
            self._client.table("runs")
            .select("*")
            .eq("owner_sub", owner_sub)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
    def get_run_by_id_owner(self, run_id: UUID | str, owner_sub: str) -> dict[str, Any] | None:
        response = (
            self._client.table("runs")
            .select("*")
            .eq("id", str(run_id))
            .eq("owner_sub", owner_sub)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
    def list_messages_by_run_owner(self, run_id: UUID | str, owner_sub: str) -> list[dict[str, Any]]:
        response = (
            self._client.table("messages")
            .select("*")
            .eq("run_id", str(run_id))
            .eq("owner_sub", owner_sub)
            .order("created_at", desc=False)
            .execute()
        )
        return response.data or []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
    def get_user_report_rules(self, owner_sub: str) -> str | None:
        response = (
            self._client.table("user_report_rules")
            .select("value_text")
            .eq("owner_sub", owner_sub)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            return None
        return rows[0].get("value_text")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
    def set_user_report_rules(self, owner_sub: str, owner_email: str | None, value_text: str) -> dict[str, Any]:
        response = (
            self._client.table("user_report_rules")
            .upsert(
                {
                    "owner_sub": owner_sub,
                    "owner_email": owner_email,
                    "value_text": value_text,
                },
                on_conflict="owner_sub",
            )
            .execute()
        )
        return response.data[0]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
    def get_user_tracker_config(self, owner_sub: str) -> str | None:
        response = (
            self._client.table("user_tracker_configs")
            .select("value_text")
            .eq("owner_sub", owner_sub)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            return None
        return rows[0].get("value_text")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
    def set_user_tracker_config(self, owner_sub: str, owner_email: str | None, value_text: str) -> dict[str, Any]:
        response = (
            self._client.table("user_tracker_configs")
            .upsert(
                {
                    "owner_sub": owner_sub,
                    "owner_email": owner_email,
                    "value_text": value_text,
                },
                on_conflict="owner_sub",
            )
            .execute()
        )
        return response.data[0]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
    def upsert_user(self, owner_sub: str, owner_email: str | None, active: bool = True) -> dict[str, Any]:
        response = (
            self._client.table("users")
            .upsert(
                {
                    "owner_sub": owner_sub,
                    "owner_email": owner_email,
                    "active": active,
                },
                on_conflict="owner_sub",
            )
            .execute()
        )
        return response.data[0]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
    def list_known_owners(self, limit: int = 1000) -> list[dict[str, Any]]:
        owners: dict[str, str | None] = {}

        users_rows = (
            self._client.table("users")
            .select("owner_sub,owner_email,active")
            .eq("active", True)
            .limit(limit)
            .execute()
            .data
            or []
        )
        for row in users_rows:
            owner_sub = row.get("owner_sub")
            if not owner_sub:
                continue
            owners[str(owner_sub)] = row.get("owner_email")

        rules_rows = self._client.table("user_report_rules").select("owner_sub,owner_email").limit(limit).execute().data or []
        for row in rules_rows:
            owner_sub = row.get("owner_sub")
            if not owner_sub:
                continue
            owners[str(owner_sub)] = row.get("owner_email")

        things_rows = self._client.table("things").select("owner_sub,owner_email").limit(limit).execute().data or []
        for row in things_rows:
            owner_sub = row.get("owner_sub")
            if not owner_sub:
                continue
            owner_sub = str(owner_sub)
            if owner_sub not in owners:
                owners[owner_sub] = row.get("owner_email")

        return [{"owner_sub": sub, "owner_email": email} for sub, email in owners.items()]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
    def get_thing_by_id_owner(self, thing_id: str, owner_sub: str) -> dict[str, Any] | None:
        response = (
            self._client.table("things")
            .select("*")
            .eq("id", thing_id)
            .eq("owner_sub", owner_sub)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
    def delete_thing_by_id_owner(self, thing_id: str, owner_sub: str) -> None:
        self._client.table("things").delete().eq("id", thing_id).eq("owner_sub", owner_sub).execute()
