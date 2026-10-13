from app.config.production import (
    ProductionConfigurationError,
    ensure_runtime_settings,
    validate_runtime_settings,
)
from app.config.settings import Settings


def _production(**overrides) -> Settings:
    payload = {
        "app_env": "production",
        "debug": False,
        "database_url": "postgresql+asyncpg://user:pass@db:5432/recruitment",
        "recruiter_username": "recruiter",
        "recruiter_password": "a-strong-password",
        "recruiter_session_secret": "session-secret-16",
        "google_api_key": "from-env-not-hardcoded",
        "email_dry_run": True,
        "calendar_dry_run": True,
    }
    payload.update(overrides)
    return Settings(**payload)


def test_development_does_not_require_secrets() -> None:
    assert validate_runtime_settings(Settings(app_env="development")) == []


def test_production_requires_core_secrets() -> None:
    errors = validate_runtime_settings(
        Settings(
            app_env="production",
            debug=False,
            database_url=None,
            recruiter_username=None,
            recruiter_password=None,
            recruiter_session_secret=None,
            google_api_key=None,
            email_dry_run=True,
            calendar_dry_run=True,
        )
    )
    assert "DATABASE_URL is required" in errors
    assert "RECRUITER_USERNAME is required" in errors
    assert "RECRUITER_SESSION_SECRET is required" in errors
    assert "GOOGLE_API_KEY is required when LLM_PROVIDER=gemini" in errors
    assert all("from-env-not-hardcoded" not in item for item in errors)


def test_production_accepts_complete_dry_run_config() -> None:
    assert validate_runtime_settings(_production()) == []


def test_live_email_and_calendar_requirements() -> None:
    errors = validate_runtime_settings(
        _production(
            email_dry_run=False,
            email_provider="ses",
            email_from_address=None,
            aws_region=None,
            calendar_dry_run=False,
            calendar_provider="none",
            google_calendar_id=None,
            google_calendar_credentials_json=None,
            google_calendar_credentials_file=None,
        )
    )
    assert "EMAIL_FROM_ADDRESS is required when EMAIL_DRY_RUN=false" in errors
    assert "AWS_REGION is required when EMAIL_PROVIDER=ses and live email is on" in errors
    assert "CALENDAR_PROVIDER=google is required when CALENDAR_DRY_RUN=false" in errors


def test_ensure_runtime_settings_raises() -> None:
    try:
        ensure_runtime_settings(Settings(app_env="production", debug=True))
        raise AssertionError("expected ProductionConfigurationError")
    except ProductionConfigurationError as exc:
        assert "DEBUG must be false" in str(exc)
