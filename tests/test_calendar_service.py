from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app.config.settings import Settings
from app.integrations.calendar_service import (
    CalendarConfigurationError,
    CalendarService,
    GoogleCalendarProvider,
)


def test_dry_run_does_not_book() -> None:
    service = CalendarService.from_settings(
        Settings(calendar_dry_run=True, calendar_provider="google")
    )
    start = datetime(2026, 9, 21, 10, 0, tzinfo=UTC)
    end = datetime(2026, 9, 21, 10, 45, tzinfo=UTC)
    result = service.book(
        title="Interview",
        start_at=start,
        end_at=end,
        attendees=["rahul@example.com"],
    )
    assert result.booked is False
    assert result.dry_run is True
    assert result.provider == "dry_run"
    assert result.event_id.startswith("dry-run-cal-")


def test_live_google_requires_credentials() -> None:
    with pytest.raises(CalendarConfigurationError, match="GOOGLE_CALENDAR"):
        CalendarService.from_settings(
            Settings(
                calendar_dry_run=False,
                calendar_provider="google",
                google_calendar_id="primary",
            )
        )


def test_google_provider_creates_event_via_api() -> None:
    insert = MagicMock()
    insert.execute.return_value = {"id": "evt-123"}
    events = MagicMock()
    events.insert.return_value = insert
    service_api = MagicMock()
    service_api.events.return_value = events
    provider = GoogleCalendarProvider(service_api, calendar_id="primary")
    start = datetime(2026, 9, 21, 10, 0, tzinfo=UTC)
    end = datetime(2026, 9, 21, 10, 45, tzinfo=UTC)
    result = provider.create_event(
        title="Interview",
        start_at=start,
        end_at=end,
        attendees=["rahul@example.com"],
    )
    assert result.booked is True
    assert result.dry_run is False
    assert result.event_id == "evt-123"
    events.insert.assert_called_once()
    kwargs = events.insert.call_args.kwargs
    assert kwargs["calendarId"] == "primary"
    assert kwargs["body"]["attendees"] == [{"email": "rahul@example.com"}]


def test_live_book_uses_injected_google_provider() -> None:
    provider = MagicMock()
    provider.create_event.return_value = MagicMock(
        event_id="evt-9",
        booked=True,
        provider="google",
        dry_run=False,
        start_at=datetime.now(UTC),
        end_at=datetime.now(UTC),
    )
    service = CalendarService(provider, dry_run=False)
    result = service.book(
        title="Interview",
        start_at=datetime.now(UTC),
        end_at=datetime.now(UTC),
        attendees=[],
    )
    assert result.booked is True
    provider.create_event.assert_called_once()
