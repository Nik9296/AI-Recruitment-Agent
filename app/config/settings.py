"""Environment-based application settings. API keys are never hardcoded."""

from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Recruitment Agent"
    debug: bool = False

    llm_provider: Literal["gemini", "openai", "anthropic"] = "gemini"
    llm_model: str = "gemini-2.0-flash"
    llm_temperature: float = 0.0
    google_api_key: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    database_url: str | None = None
    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173"
    )
    recruiter_username: str | None = None
    recruiter_password: str | None = None
    recruiter_session_secret: str | None = None
    company_name: str | None = None
    recruiter_display_name: str | None = None
    recruiter_title: str | None = None
    recruiter_contact_email: str | None = None
    email_provider: Literal["ses", "sendgrid"] = "ses"
    email_dry_run: bool = True
    email_from_address: str | None = None
    email_reply_to: str | None = None
    aws_region: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    ses_configuration_set: str | None = None
    sendgrid_api_key: str | None = None
    interview_timezone: str = "Asia/Kolkata"
    interview_duration_minutes: int = 45
    calendar_dry_run: bool = True
    calendar_provider: Literal["none", "google"] = "none"
    google_calendar_id: str | None = None
    google_calendar_credentials_json: str | None = None
    google_calendar_credentials_file: str | None = None
    google_calendar_subject: str | None = None
    embedding_model: str = "models/text-embedding-004"
    app_env: Literal["development", "production"] = "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
