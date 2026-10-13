"""Email and calendar integrations. Isolated from recruitment agents."""

from app.integrations.calendar_service import (
    CalendarConfigurationError,
    CalendarError,
    CalendarEventResult,
    CalendarNotImplementedError,
    CalendarService,
    GoogleCalendarProvider,
)
from app.integrations.email_service import (
    DuplicateEmailError,
    EmailConfigurationError,
    EmailProvider,
    EmailSendDeniedError,
    EmailSendRecord,
    EmailService,
    OutboundEmail,
    SESEmailProvider,
    SendGridEmailProvider,
    get_email_provider,
)

__all__ = [
    "CalendarConfigurationError",
    "CalendarError",
    "CalendarEventResult",
    "CalendarNotImplementedError",
    "CalendarService",
    "GoogleCalendarProvider",
    "DuplicateEmailError",
    "EmailConfigurationError",
    "EmailProvider",
    "EmailSendDeniedError",
    "EmailSendRecord",
    "EmailService",
    "OutboundEmail",
    "SESEmailProvider",
    "SendGridEmailProvider",
    "get_email_provider",
]
