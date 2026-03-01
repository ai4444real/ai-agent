from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.actions.weekly_report import (
    calculate_metrics,
    compute_week_window_utc,
    deterministic_signal_and_action,
    extract_mood_values,
    render_weekly_report,
)
from app.auth import require_trigger_token
from app.models import ActionResponse
from app.services.llm_openai import OpenAIReportHelper
from app.services.mailer_brevo_smtp import BrevoMailer
from app.services.supabase_repo import SupabaseRepo
from app.settings import get_settings

router = APIRouter(prefix="/actions", tags=["actions"])
mailer = BrevoMailer()


@router.post("/weekly-report", response_model=ActionResponse, dependencies=[Depends(require_trigger_token)])
async def weekly_report_action() -> ActionResponse:
    repo = SupabaseRepo()
    settings = get_settings()
    llm_helper = OpenAIReportHelper()
    start_utc, end_utc = compute_week_window_utc()
    run = repo.create_run(
        action="weekly_report",
        input_summary={"from": start_utc.isoformat(), "to": end_utc.isoformat()},
    )
    run_id = run["id"]

    try:
        rows = repo.list_things(thing_type="mood", from_ts=start_utc, to_ts=end_utc)
        values = extract_mood_values(list(reversed(rows)))

        metrics = calculate_metrics(values)
        summary, signal, micro_action = deterministic_signal_and_action(metrics)
        try:
            llm_result = llm_helper.generate_signal_and_micro_action(metrics)
            if llm_result:
                signal, micro_action = llm_result
        except Exception:
            pass
        body = render_weekly_report(metrics, summary, signal, micro_action)

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
        raise HTTPException(status_code=500, detail="weekly_report failed") from exc
