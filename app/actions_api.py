from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query

from app.actions.weekly_report import (
    calculate_metrics,
    compute_week_window_utc,
    deterministic_signal_and_action,
    extract_mood_values,
    render_weekly_report,
    render_tracker_snapshot,
    summarize_tracker_activity,
)
from app.auth import require_trigger_token
from app.auth_google import require_google_user
from app.models import ActionResponse, DispatchItemResponse, DispatchResponse, RunResponse, WeeklyReportRequest
from app.services.llm_openai import OpenAIReportHelper
from app.services.mailer_brevo_smtp import BrevoMailer
from app.services.supabase_repo import SupabaseRepo
from app.settings import get_settings

router = APIRouter(prefix="/actions", tags=["actions"])
mailer = BrevoMailer()


async def _run_weekly_report_for_owner(owner_sub: str, owner_email: str | None, smart_mode: bool = False) -> ActionResponse:
    repo = SupabaseRepo()
    settings = get_settings()
    window_days = getattr(settings, "report_window_days", 8)
    llm_helper = OpenAIReportHelper()
    start_utc, end_utc = compute_week_window_utc(window_days=window_days)
    action_name = "weekly_report_smart" if smart_mode else "weekly_report"
    run = repo.create_run(
        action=action_name,
        input_summary={"from": start_utc.isoformat(), "to": end_utc.isoformat(), "window_days": window_days},
        owner_sub=owner_sub,
        owner_email=owner_email or settings.mail_to,
    )
    run_id = run["id"]

    try:
        rows = repo.list_things(from_ts=start_utc, to_ts=end_utc, owner_sub=owner_sub)
        mood_rows = [row for row in rows if (row.get("type") or "").strip().lower() == "mood"]
        values = extract_mood_values(list(reversed(mood_rows)))
        rules_text = repo.get_user_report_rules(owner_sub)
        tracker_summary = summarize_tracker_activity(rows)

        metrics = calculate_metrics(values)
        report_payload = {
            "window_days": window_days,
            "mood_metrics": metrics,
            "tracker_summary": tracker_summary,
        }
        debug_summary = {
            "from": start_utc.isoformat(),
            "to": end_utc.isoformat(),
            "window_days": window_days,
            "owner_sub": owner_sub,
            "report_payload": report_payload,
            "rules_excerpt": (rules_text or "")[:1000],
            "rules_length": len(rules_text or ""),
            "rules_source": "user_only",
        }
        summary, signal, micro_action = deterministic_signal_and_action(metrics)
        body = ""
        if smart_mode:
            local_tz = ZoneInfo(settings.app_timezone)

            def _parse_created_at(value: str | datetime | None) -> datetime | None:
                if value is None:
                    return None
                if isinstance(value, datetime):
                    return value
                try:
                    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                except ValueError:
                    return None

            def _tool_get_window_coverage(days: int) -> dict:
                safe_days = max(1, min(31, int(days)))
                cov_start_utc, cov_end_utc = compute_week_window_utc(window_days=safe_days)
                cov_rows = repo.list_things(from_ts=cov_start_utc, to_ts=cov_end_utc, owner_sub=owner_sub)
                dates_with_data: set[str] = set()
                first_entry_at: datetime | None = None
                last_entry_at: datetime | None = None
                for row in cov_rows:
                    dt = _parse_created_at(row.get("created_at"))
                    if not dt:
                        continue
                    dt_utc = dt.astimezone(timezone.utc)
                    dates_with_data.add(dt_utc.astimezone(local_tz).date().isoformat())
                    if first_entry_at is None or dt_utc < first_entry_at:
                        first_entry_at = dt_utc
                    if last_entry_at is None or dt_utc > last_entry_at:
                        last_entry_at = dt_utc
                return {
                    "days": safe_days,
                    "total_entries": len(cov_rows),
                    "days_with_data": len(dates_with_data),
                    "first_entry_at": first_entry_at.isoformat() if first_entry_at else None,
                    "last_entry_at": last_entry_at.isoformat() if last_entry_at else None,
                    "window_from": cov_start_utc.isoformat(),
                    "window_to": cov_end_utc.isoformat(),
                }

            def _tool_get_daily_counts(days: int, thing_type: str) -> dict:
                safe_days = max(1, min(31, int(days)))
                type_value = (thing_type or "").strip().lower()
                cov_start_utc, cov_end_utc = compute_week_window_utc(window_days=safe_days)
                cov_rows = repo.list_things(
                    thing_type=type_value if type_value else None,
                    from_ts=cov_start_utc,
                    to_ts=cov_end_utc,
                    owner_sub=owner_sub,
                )
                local_now = datetime.now(timezone.utc).astimezone(local_tz)
                counts: dict[str, int] = {}
                for i in range(safe_days, -1, -1):
                    day = (local_now - timedelta(days=i)).date().isoformat()
                    counts[day] = 0
                for row in cov_rows:
                    dt = _parse_created_at(row.get("created_at"))
                    if not dt:
                        continue
                    key = dt.astimezone(local_tz).date().isoformat()
                    if key in counts:
                        counts[key] = counts[key] + 1
                return {
                    "days": safe_days,
                    "type": type_value,
                    "total_entries": len(cov_rows),
                    "daily_counts": counts,
                }

            def _tool_executor(name: str, args: dict) -> dict:
                if name == "get_window_coverage":
                    return _tool_get_window_coverage(days=args.get("days", window_days))
                if name == "get_daily_counts":
                    return _tool_get_daily_counts(days=args.get("days", window_days), thing_type=args.get("type", ""))
                return {"error": f"unknown tool {name}"}

            smart_context = {
                "window_days": window_days,
                "owner_sub": owner_sub,
                "tracker_types_in_window": sorted(set((row.get("type") or "").strip().lower() for row in rows if row.get("type"))),
                "mood_metrics": metrics,
            }
            try:
                smart_body, smart_trace = llm_helper.generate_smart_weekly_report(
                    context_payload=smart_context,
                    rules_text=rules_text,
                    tool_executor=_tool_executor,
                )
                debug_summary["smart_mode"] = True
                debug_summary["smart_tool_trace"] = smart_trace
                if smart_body:
                    body = smart_body.strip()
            except Exception:
                debug_summary["smart_mode"] = True
                debug_summary["smart_tool_trace"] = [{"error": "smart_generation_failed"}]
        else:
            try:
                llm_result = llm_helper.generate_signal_and_micro_action(report_payload, rules_text=rules_text)
                if llm_result:
                    signal, micro_action = llm_result
            except Exception:
                pass

        if not body:
            body = render_weekly_report(metrics, summary, signal, micro_action)
        body += f"\n\nTracker snapshot ({window_days}d):\n{render_tracker_snapshot(tracker_summary)}"
        if rules_text:
            body += f"\n\nRules context excerpt:\n{rules_text[:300]}"
        body += "\n\nRules source: user_only"
        repo.update_run_input_summary(run_id=run_id, input_summary=debug_summary)

        subject = f"Weekly mood report - {datetime.now(timezone.utc).date().isoformat()}"
        report_recipient = owner_email or settings.mail_to
        await mailer.send_plain_text(subject=subject, body=body, recipient=report_recipient)

        repo.insert_message(
            channel="email",
            recipient=report_recipient,
            subject=subject,
            body=body,
            action=action_name,
            run_id=run_id,
            owner_sub=owner_sub,
            owner_email=owner_email or settings.mail_to,
        )
        repo.finish_run(run_id=run_id, status="success")
        return ActionResponse(ok=True, action=action_name, run_id=run_id)
    except Exception as exc:
        repo.finish_run(run_id=run_id, status="fail", error=str(exc)[:4000])
        alert_subject = "Weekly report failed"
        alert_body = f"Run {run_id} failed with error: {str(exc)[:1000]}"
        try:
            alert_recipient = owner_email or settings.mail_to
            await mailer.send_plain_text(subject=alert_subject, body=alert_body, recipient=alert_recipient)
            repo.insert_message(
                channel="email",
                recipient=alert_recipient,
                subject=alert_subject,
                body=alert_body,
                action=f"{action_name}_fail_alert",
                run_id=run_id,
                owner_sub=owner_sub,
                owner_email=owner_email or settings.mail_to,
            )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="weekly_report failed") from exc


@router.get("/runs/latest", response_model=list[RunResponse], dependencies=[Depends(require_trigger_token)])
def latest_runs(limit: int = Query(default=10, ge=1, le=50)) -> list[RunResponse]:
    repo = SupabaseRepo()
    rows = repo.list_latest_runs(limit=limit)
    return [RunResponse(**row) for row in rows]


@router.post("/weekly-report-mine", response_model=ActionResponse)
async def weekly_report_mine(google_user: dict = Depends(require_google_user)) -> ActionResponse:
    return await _run_weekly_report_for_owner(
        owner_sub=google_user.get("sub"),
        owner_email=google_user.get("email"),
    )


@router.post("/weekly-report-smart-mine", response_model=ActionResponse)
async def weekly_report_smart_mine(google_user: dict = Depends(require_google_user)) -> ActionResponse:
    return await _run_weekly_report_for_owner(
        owner_sub=google_user.get("sub"),
        owner_email=google_user.get("email"),
        smart_mode=True,
    )


@router.post("/weekly-report", response_model=ActionResponse, dependencies=[Depends(require_trigger_token)])
async def weekly_report_action(payload: WeeklyReportRequest) -> ActionResponse:
    return await _run_weekly_report_for_owner(
        owner_sub=payload.owner_sub,
        owner_email=payload.owner_email,
    )


@router.post("/weekly-report-dispatch", response_model=DispatchResponse, dependencies=[Depends(require_trigger_token)])
async def weekly_report_dispatch(limit: int = Query(default=100, ge=1, le=1000)) -> DispatchResponse:
    repo = SupabaseRepo()
    owners = repo.list_known_owners(limit=limit)
    items: list[DispatchItemResponse] = []

    for owner in owners:
        owner_sub = owner.get("owner_sub")
        owner_email = owner.get("owner_email")
        if not owner_sub:
            continue
        try:
            result = await _run_weekly_report_for_owner(owner_sub=owner_sub, owner_email=owner_email)
            items.append(
                DispatchItemResponse(
                    owner_sub=owner_sub,
                    owner_email=owner_email,
                    ok=True,
                    run_id=result.run_id,
                )
            )
        except Exception as exc:
            items.append(
                DispatchItemResponse(
                    owner_sub=owner_sub,
                    owner_email=owner_email,
                    ok=False,
                    error=str(exc)[:1000],
                )
            )

    success = len([i for i in items if i.ok])
    failed = len(items) - success
    return DispatchResponse(ok=failed == 0, total=len(items), success=success, failed=failed, items=items)
