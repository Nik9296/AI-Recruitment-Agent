"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.config.production import (
    ProductionConfigurationError,
    ensure_runtime_settings,
)
from app.config.settings import get_settings
from app.database import database as db
from app.database.database import (
    DatabaseNotConfiguredError,
    close_engine,
    init_engine,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    ensure_runtime_settings(settings)
    if settings.database_url:
        init_engine(settings.database_url)
    yield
    await close_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    origins = [
        origin.strip()
        for origin in settings.cors_origins.split(",")
        if origin.strip()
    ]
    docs_enabled = not settings.is_production or settings.debug
    application = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "AI Recruitment API. JD analysis, sourcing, matching, ranking, "
            "recruiter review, outreach drafts, and interview proposals. "
            "Outreach is not sent and interviews are not booked without a recruiter."
        ),
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    @application.get("/health", tags=["health"], summary="Liveness check")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/ready", tags=["health"], summary="Readiness check")
    async def ready():
        settings = get_settings()
        database = "unconfigured"
        http_status = status.HTTP_200_OK
        if db.engine is None:
            if settings.database_url:
                database = "unavailable"
                http_status = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            try:
                async with db.engine.connect() as connection:
                    await connection.execute(text("SELECT 1"))
                database = "ok"
            except Exception:
                database = "unavailable"
                http_status = status.HTTP_503_SERVICE_UNAVAILABLE
        body = {
            "status": "ok" if http_status == status.HTTP_200_OK else "unavailable",
            "app_env": settings.app_env,
            "database": database,
            "email_dry_run": settings.email_dry_run,
            "calendar_dry_run": settings.calendar_dry_run,
            "live_email_configured": _live_email_configured(settings),
            "live_calendar_configured": _live_calendar_configured(settings),
        }
        return JSONResponse(status_code=http_status, content=body)

    @application.exception_handler(DatabaseNotConfiguredError)
    async def database_not_configured(_request, exc: DatabaseNotConfiguredError):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": str(exc)},
        )

    @application.exception_handler(ProductionConfigurationError)
    async def production_not_configured(_request, exc: ProductionConfigurationError):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": str(exc)},
        )

    application.include_router(api_router, prefix="/api/v1")
    return application


def _live_email_configured(settings) -> bool:
    if settings.email_dry_run or not (settings.email_from_address or "").strip():
        return False
    if settings.email_provider == "sendgrid":
        return bool((settings.sendgrid_api_key or "").strip())
    return bool((settings.aws_region or "").strip())


def _live_calendar_configured(settings) -> bool:
    if settings.calendar_dry_run:
        return False
    has_creds = bool(
        (settings.google_calendar_credentials_json or "").strip()
        or (settings.google_calendar_credentials_file or "").strip()
    )
    return (
        (settings.calendar_provider or "").strip().lower() == "google"
        and bool((settings.google_calendar_id or "").strip())
        and has_creds
    )


app = create_app()
