from fastapi import APIRouter, Depends

from app.auth_google import require_google_user
from app.models import ReportRulesRequest, ReportRulesResponse
from app.services.supabase_repo import SupabaseRepo

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/report-rules-mine", response_model=ReportRulesResponse)
def get_my_report_rules(google_user: dict = Depends(require_google_user)) -> ReportRulesResponse:
    repo = SupabaseRepo()
    value = repo.get_user_report_rules(google_user.get("sub"))
    return ReportRulesResponse(text=value)


@router.put("/report-rules-mine", response_model=ReportRulesResponse)
def put_my_report_rules(payload: ReportRulesRequest, google_user: dict = Depends(require_google_user)) -> ReportRulesResponse:
    repo = SupabaseRepo()
    repo.set_user_report_rules(
        owner_sub=google_user.get("sub"),
        owner_email=google_user.get("email"),
        value_text=payload.text,
    )
    return ReportRulesResponse(text=payload.text)
