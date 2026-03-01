from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_timezone: str = Field(default="Europe/Zurich", alias="APP_TIMEZONE")
    report_window_days: int = Field(default=8, alias="REPORT_WINDOW_DAYS")

    supabase_url: str = Field(alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(alias="SUPABASE_SERVICE_ROLE_KEY")

    trigger_token: str = Field(alias="TRIGGER_TOKEN")

    smtp_host: str = Field(default="smtp-relay.brevo.com", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(alias="SMTP_USER")
    smtp_pass: str = Field(alias="SMTP_PASS")
    mail_from: str = Field(alias="MAIL_FROM")
    mail_to: str = Field(alias="MAIL_TO")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")
    google_client_id: str | None = Field(default=None, alias="GOOGLE_CLIENT_ID")
    google_allowed_emails: str | None = Field(default=None, alias="GOOGLE_ALLOWED_EMAILS")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
