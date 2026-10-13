"""Calendar booking abstraction. Dry-run by default; Google Calendar from env."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from pydantic import BaseModel

from app.config.settings import Settings, get_settings


class CalendarError(Exception):
    """Base calendar integration error."""


class CalendarConfigurationError(CalendarError):
    """Raised when live calendar settings are incomplete."""


class CalendarNotImplementedError(CalendarError):
    """Reserved provider is not wired."""


class CalendarEventResult(BaseModel):
    event_id: str
    booked: bool
    provider: str
    dry_run: bool
    start_at: datetime
    end_at: datetime


class CalendarProvider(Protocol):
    name: str

    def create_event(
        self,
        *,
        title: str,
        start_at: datetime,
        end_at: datetime,
        attendees: list[str],
    ) -> CalendarEventResult: ...


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _rfc3339(value: datetime) -> tuple[str, str]:
    aware = _aware(value)
    zone = getattr(aware.tzinfo, "key", None) or "UTC"
    return aware.isoformat(), zone


class GoogleCalendarProvider:
    name = "google"

    def __init__(self, service: object, *, calendar_id: str) -> None:
        self._service = service
        self._calendar_id = calendar_id

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> GoogleCalendarProvider:
        loaded = settings or get_settings()
        calendar_id = (loaded.google_calendar_id or "").strip()
        if not calendar_id:
            raise CalendarConfigurationError(
                "GOOGLE_CALENDAR_ID is required when CALENDAR_DRY_RUN=false"
            )
        info = _credentials_info(loaded)
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise CalendarConfigurationError(
                "google-api-python-client and google-auth are required for live Google Calendar"
            ) from exc
        credentials = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/calendar"],
        )
        subject = (loaded.google_calendar_subject or "").strip()
        if subject:
            credentials = credentials.with_subject(subject)
        service = build(
            "calendar", "v3", credentials=credentials, cache_discovery=False
        )
        return cls(service, calendar_id=calendar_id)

    def create_event(
        self,
        *,
        title: str,
        start_at: datetime,
        end_at: datetime,
        attendees: list[str],
    ) -> CalendarEventResult:
        start_iso, start_zone = _rfc3339(start_at)
        end_iso, end_zone = _rfc3339(end_at)
        body = {
            "summary": title,
            "start": {"dateTime": start_iso, "timeZone": start_zone},
            "end": {"dateTime": end_iso, "timeZone": end_zone},
            "attendees": [
                {"email": email} for email in attendees if (email or "").strip()
            ],
        }
        created = (
            self._service.events()
            .insert(calendarId=self._calendar_id, body=body, sendUpdates="all")
            .execute()
        )
        event_id = str((created or {}).get("id") or "").strip()
        if not event_id:
            raise CalendarError("Google Calendar did not return an event id")
        return CalendarEventResult(
            event_id=event_id,
            booked=True,
            provider=self.name,
            dry_run=False,
            start_at=_aware(start_at),
            end_at=_aware(end_at),
        )


def _credentials_info(settings: Settings) -> dict:
    raw = (settings.google_calendar_credentials_json or "").strip()
    path = (settings.google_calendar_credentials_file or "").strip()
    if raw:
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CalendarConfigurationError(
                "GOOGLE_CALENDAR_CREDENTIALS_JSON is not valid JSON"
            ) from exc
    elif path:
        try:
            loaded = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CalendarConfigurationError(
                "GOOGLE_CALENDAR_CREDENTIALS_FILE could not be read as JSON"
            ) from exc
    else:
        raise CalendarConfigurationError(
            "GOOGLE_CALENDAR_CREDENTIALS_JSON or GOOGLE_CALENDAR_CREDENTIALS_FILE "
            "is required when CALENDAR_DRY_RUN=false"
        )
    if not isinstance(loaded, dict) or not loaded:
        raise CalendarConfigurationError(
            "Google Calendar credentials JSON must be an object"
        )
    return loaded


class CalendarService:
    def __init__(
        self,
        provider: CalendarProvider | None = None,
        *,
        dry_run: bool = True,
    ) -> None:
        self._provider = provider
        self._dry_run = bool(dry_run)

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> CalendarService:
        loaded = settings or get_settings()
        if loaded.calendar_dry_run:
            return cls(None, dry_run=True)
        name = (loaded.calendar_provider or "none").strip().lower()
        if name == "google":
            return cls(GoogleCalendarProvider.from_settings(loaded), dry_run=False)
        raise CalendarConfigurationError(
            "Set CALENDAR_PROVIDER=google when CALENDAR_DRY_RUN=false"
        )

    def book(
        self,
        *,
        title: str,
        start_at: datetime,
        end_at: datetime,
        attendees: list[str],
    ) -> CalendarEventResult:
        if self._dry_run or self._provider is None:
            return CalendarEventResult(
                event_id=f"dry-run-cal-{uuid4()}",
                booked=False,
                provider="dry_run",
                dry_run=True,
                start_at=start_at,
                end_at=end_at,
            )
        return self._provider.create_event(
            title=title,
            start_at=start_at,
            end_at=end_at,
            attendees=attendees,
        )
