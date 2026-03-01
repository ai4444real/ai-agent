from datetime import datetime, timezone

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
from app.models import ActionResponse, RunResponse
from app.services.llm_openai import OpenAIReportHelper
from app.services.mailer_brevo_smtp import BrevoMailer
from app.services.supabase_repo import SupabaseRepo
from app.settings import get_settings

router = APIRouter(prefix="/actions", tags=["actions"])
mailer = BrevoMailer()


@router.get("/runs/latest", response_model=list[RunResponse], dependencies=[Depends(require_trigger_token)])
def latest_runs(limit: int = Query(default=10, ge=1, le=50)) -> list[RunResponse]:
    repo = SupabaseRepo()
    rows = repo.list_latest_runs(limit=limit)
    return [RunResponse(**row) for row in rows]


@router.post("/weekly-report", response_model=ActionResponse, dependencies=[Depends(require_trigger_token)])
async def weekly_report_action() -> ActionResponse:
    repo = SupabaseRepo()
    settings = get_settings()
    window_days = getattr(settings, "report_window_days", 8)
    llm_helper = OpenAIReportHelper()
    start_utc, end_utc = compute_week_window_utc(window_days=window_days)
    run = repo.create_run(
        action="weekly_report",
        input_summary={"from": start_utc.isoformat(), "to": end_utc.isoformat(), "window_days": window_days},
    )
    run_id = run["id"]

    try:
        rows = repo.list_things(from_ts=start_utc, to_ts=end_utc)
        mood_rows = [row for row in rows if (row.get("type") or "").strip().lower() == "mood"]
        values = extract_mood_values(list(reversed(mood_rows)))
        rules_text = repo.get_config_text("report_rules")
        tracker_summary = summarize_tracker_activity(rows)

        metrics = calculate_metrics(values)
        report_payload = {
            "window_days": window_days,
            "mood_metrics": metrics,
            "tracker_summary": tracker_summary,
        }
        summary, signal, micro_action = deterministic_signal_and_action(metrics)
        try:
            llm_result = llm_helper.generate_signal_and_micro_action(report_payload, rules_text=rules_text)
            if llm_result:
                signal, micro_action = llm_result
        except Exception:
            pass
        body = render_weekly_report(metrics, summary, signal, micro_action)
        body += f"\n\nTracker snapshot ({window_days}d):\n{render_tracker_snapshot(tracker_summary)}"
        if rules_text:
            body += f"\n\nRules context excerpt:\n{rules_text[:300]}"

        subject = f"Weekly mood report - {datetime.now(timezone.utc).date().isoformat()}"
        await mailer.send_plain_text(subject=subject, body=body)

        repo.insert_message(
            channel="email",
            recipient=settings.mail_to,
            subject=subject,
            body=body,
            action="weekly_report",
            run_id=run_id,
        )
        repo.finish_run(run_id=run_id, status="success")
        return ActionResponse(ok=True, action="weekly_report", run_id=run_id)
    except Exception as exc:
        repo.finish_run(run_id=run_id, status="fail", error=str(exc)[:4000])
        alert_subject = "Weekly report failed"
        alert_body = f"Run {run_id} failed with error: {str(exc)[:1000]}"
        try:
            await mailer.send_plain_text(subject=alert_subject, body=alert_body, recipient=settings.mail_to)
            repo.insert_message(
                channel="email",
                recipient=settings.mail_to,
                subject=alert_subject,
                body=alert_body,
                action="weekly_report_fail_alert",
                run_id=run_id,
            )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="weekly_report failed") from exc
