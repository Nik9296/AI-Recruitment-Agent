"""Fail closed in production when required environment values are missing.

Never include secret values in error text.
"""

from __future__ import annotations

from app.config.settings import Settings


class ProductionConfigurationError(RuntimeError):
    """Raised when production settings are incomplete."""


def validate_runtime_settings(settings: Settings) -> list[str]:
    """Return human-readable problems. Empty means the process may start."""
    errors: list[str] = []
    if not settings.is_production:
        return errors
    if settings.debug:
        errors.append("DEBUG must be false when APP_ENV=production")
    if not (settings.database_url or "").strip():
        errors.append("DATABASE_URL is required")
    if not (settings.recruiter_username or "").strip():
        errors.append("RECRUITER_USERNAME is required")
    if not (settings.recruiter_password or "").strip():
        errors.append("RECRUITER_PASSWORD is required")
    secret = (settings.recruiter_session_secret or "").strip()
    if not secret:
        errors.append("RECRUITER_SESSION_SECRET is required")
    elif len(secret) < 16:
        errors.append("RECRUITER_SESSION_SECRET must be at least 16 characters")
    if settings.llm_provider == "gemini" and not (settings.google_api_key or "").strip():
        errors.append("GOOGLE_API_KEY is required when LLM_PROVIDER=gemini")
    if settings.llm_provider == "openai" and not (settings.openai_api_key or "").strip():
        errors.append("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
    if settings.llm_provider == "anthropic" and not (
        settings.anthropic_api_key or ""
    ).strip():
        errors.append("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")
    if not settings.email_dry_run:
        if not (settings.email_from_address or "").strip():
            errors.append("EMAIL_FROM_ADDRESS is required when EMAIL_DRY_RUN=false")
        if settings.email_provider == "ses" and not (settings.aws_region or "").strip():
            errors.append("AWS_REGION is required when EMAIL_PROVIDER=ses and live email is on")
        if settings.email_provider == "sendgrid" and not (
            settings.sendgrid_api_key or ""
        ).strip():
            errors.append("SENDGRID_API_KEY is required when EMAIL_PROVIDER=sendgrid")
    if not settings.calendar_dry_run:
        if (settings.calendar_provider or "none").strip().lower() != "google":
            errors.append("CALENDAR_PROVIDER=google is required when CALENDAR_DRY_RUN=false")
        if not (settings.google_calendar_id or "").strip():
            errors.append("GOOGLE_CALENDAR_ID is required when CALENDAR_DRY_RUN=false")
        has_json = bool((settings.google_calendar_credentials_json or "").strip())
        has_file = bool((settings.google_calendar_credentials_file or "").strip())
        if not has_json and not has_file:
            errors.append(
                "GOOGLE_CALENDAR_CREDENTIALS_JSON or GOOGLE_CALENDAR_CREDENTIALS_FILE "
                "is required when CALENDAR_DRY_RUN=false"
            )
    return errors


def ensure_runtime_settings(settings: Settings) -> None:
    errors = validate_runtime_settings(settings)
    if errors:
        raise ProductionConfigurationError(
            "Production configuration is incomplete:\n- " + "\n- ".join(errors)
        )


if __name__ == "__main__":
    from app.config.settings import get_settings

    loaded = get_settings()
    problems = validate_runtime_settings(loaded)
    if problems:
        print(f"Not ready for APP_ENV={loaded.app_env}:")
        for item in problems:
            print(f"- {item}")
        raise SystemExit(1)
    print(f"Runtime settings are valid for APP_ENV={loaded.app_env}")
