from fastapi import APIRouter

from app.auth_google import verify_google_token
from app.models import GoogleClientIdResponse, GoogleUserResponse, GoogleVerifyRequest
from app.settings import get_settings

router = APIRouter(prefix="/auth/google", tags=["auth"])


@router.get("/client-id", response_model=GoogleClientIdResponse)
def google_client_id() -> GoogleClientIdResponse:
    settings = get_settings()
    if not settings.google_client_id:
        return GoogleClientIdResponse(client_id="")
    return GoogleClientIdResponse(client_id=settings.google_client_id)


@router.post("/verify", response_model=GoogleUserResponse)
def verify_google(payload: GoogleVerifyRequest) -> GoogleUserResponse:
    claims = verify_google_token(payload.id_token)
    return GoogleUserResponse(sub=claims["sub"], email=claims["email"], name=claims.get("name"))
