from fastapi import Header, HTTPException, status

from app.settings import get_settings


def require_trigger_token(x_trigger_token: str | None = Header(default=None, alias="X-Trigger-Token")) -> None:
    settings = get_settings()
    if x_trigger_token != settings.trigger_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid trigger token")
