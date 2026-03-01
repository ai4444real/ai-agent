from fastapi import APIRouter, Depends

from app.auth import require_trigger_token
from app.models import ReportRulesRequest, ReportRulesResponse
from app.services.supabase_repo import SupabaseRepo

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/report-rules", response_model=ReportRulesResponse, dependencies=[Depends(require_trigger_token)])
def get_report_rules() -> ReportRulesResponse:
    repo = SupabaseRepo()
    value = repo.get_config_text("report_rules")
    return ReportRulesResponse(text=value)


@router.put("/report-rules", response_model=ReportRulesResponse, dependencies=[Depends(require_trigger_token)])
def put_report_rules(payload: ReportRulesRequest) -> ReportRulesResponse:
    repo = SupabaseRepo()
    repo.set_config_text("report_rules", payload.text)
    return ReportRulesResponse(text=payload.text)
