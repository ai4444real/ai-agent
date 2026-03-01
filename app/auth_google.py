from __future__ import annotations

from fastapi import Header, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.settings import get_settings


def _allowed_emails() -> set[str]:
    settings = get_settings()
    raw = settings.google_allowed_emails or ""
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def verify_google_token(raw_id_token: str) -> dict:
    settings = get_settings()
    if not settings.google_client_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="GOOGLE_CLIENT_ID not configured")

    try:
        payload = google_id_token.verify_oauth2_token(
            raw_id_token,
            google_requests.Request(),
            settings.google_client_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token") from exc

    email = (payload.get("email") or "").lower()
    email_verified = bool(payload.get("email_verified"))
    if not email or not email_verified:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google account email not verified")

    allowed = _allowed_emails()
    if allowed and email not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Google user not allowed")

    return payload


def require_google_user(authorization: str | None = Header(default=None, alias="Authorization")) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Google bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Google bearer token")
    return verify_google_token(token)
