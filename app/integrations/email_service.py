"""Email provider abstraction and SES-backed EmailService.

Does not live in the Outreach Agent. API keys come from environment settings.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Literal, Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.config.settings import Settings, get_settings

logger = logging.getLogger("app.integrations.email")

BLOCKING_DELIVERY_STATUSES = frozenset({"queued", "accepted", "sent", "delivered"})
DeliveryStatus = Literal["dry_run", "queued", "accepted", "sent", "delivered", "failed"]


class EmailServiceError(Exception):
    """Base error for outbound email."""


class EmailConfigurationError(EmailServiceError):
    """Raised when the email provider cannot be constructed from settings."""


class EmailProviderNotImplementedError(EmailConfigurationError):
    """Raised when a reserved provider (SendGrid) is selected but not wired."""


class EmailSendDeniedError(EmailServiceError, ValueError):
    """Raised when a message must not be sent."""


class DuplicateEmailError(EmailSendDeniedError):
    """Raised when this job/candidate/template was already sent."""


class OutboundEmail(BaseModel):
    """Candidate-facing payload. Recipient must already exist on the profile."""

    candidate_id: UUID
    job_id: UUID
    recipient: str
    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)
    template: str = "initial"
    reply_to: str | None = None


class ProviderSendResult(BaseModel):
    message_id: str
    delivery_status: DeliveryStatus
    provider: str


class EmailSendRecord(BaseModel):
    message_id: str
    candidate_id: UUID
    job_id: UUID
    recipient: str
    sent_at: datetime
    delivery_status: DeliveryStatus
    template: str = "initial"
    provider: str
    dry_run: bool = False


class EmailProvider(Protocol):
    """Outbound provider. SendGrid can implement the same contract later."""

    name: str

    def send(self, message: OutboundEmail, *, from_address: str) -> ProviderSendResult:
        """Hand the message to the vendor. Must not read secrets from source."""
        ...


class SESEmailProvider:
    """AWS Simple Email Service. Credentials come from env or the IAM role."""

    name = "ses"

    def __init__(self, client: object, *, configuration_set: str | None = None) -> None:
        self._client = client
        self._configuration_set = (configuration_set or "").strip() or None

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> SESEmailProvider:
        loaded = settings or get_settings()
        try:
            import boto3
        except ImportError as exc:
            raise EmailConfigurationError(
                "boto3 is required for EMAIL_PROVIDER=ses"
            ) from exc
        kwargs: dict[str, str] = {}
        region = (loaded.aws_region or "").strip()
        if region:
            kwargs["region_name"] = region
        access_key = (loaded.aws_access_key_id or "").strip()
        secret_key = (loaded.aws_secret_access_key or "").strip()
        if access_key and secret_key:
            kwargs["aws_access_key_id"] = access_key
            kwargs["aws_secret_access_key"] = secret_key
        elif access_key or secret_key:
            raise EmailConfigurationError(
                "Set both AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY, or neither"
            )
        client = boto3.client("ses", **kwargs)
        return cls(client, configuration_set=loaded.ses_configuration_set)

    def send(self, message: OutboundEmail, *, from_address: str) -> ProviderSendResult:
        params: dict = {
            "Source": from_address,
            "Destination": {"ToAddresses": [message.recipient]},
            "Message": {
                "Subject": {"Data": message.subject, "Charset": "UTF-8"},
                "Body": {"Text": {"Data": message.body, "Charset": "UTF-8"}},
            },
        }
        if message.reply_to:
            params["ReplyToAddresses"] = [message.reply_to]
        if self._configuration_set:
            params["ConfigurationSetName"] = self._configuration_set
        response = self._client.send_email(**params)
        message_id = str((response or {}).get("MessageId") or "").strip()
        if not message_id:
            raise EmailServiceError("SES did not return a MessageId")
        return ProviderSendResult(
            message_id=message_id,
            delivery_status="accepted",
            provider=self.name,
        )


class NullEmailProvider:
    """Used in dry-run so SES/SendGrid are not constructed."""

    name = "none"

    def send(self, message: OutboundEmail, *, from_address: str) -> ProviderSendResult:
        del message, from_address
        raise EmailServiceError("Email provider must not be called in dry-run mode")


class SendGridEmailProvider:
    """SendGrid v3 mail send. The API key comes from SENDGRID_API_KEY."""

    name = "sendgrid"

    def __init__(self, api_key: str, *, client=None) -> None:
        key = (api_key or "").strip()
        if not key:
            raise EmailConfigurationError(
                "SENDGRID_API_KEY is required when EMAIL_PROVIDER=sendgrid"
            )
        self._api_key = key
        self._client = client

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> SendGridEmailProvider:
        loaded = settings or get_settings()
        return cls(loaded.sendgrid_api_key or "")

    def send(self, message: OutboundEmail, *, from_address: str) -> ProviderSendResult:
        import httpx

        payload = {
            "personalizations": [{"to": [{"email": message.recipient}]}],
            "from": {"email": from_address},
            "subject": message.subject,
            "content": [{"type": "text/plain", "value": message.body}],
        }
        if message.reply_to:
            payload["reply_to"] = {"email": message.reply_to}
        client = self._client or httpx.Client(timeout=20.0)
        owned = self._client is None
        try:
            response = client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        finally:
            if owned:
                client.close()
        if response.status_code >= 400:
            raise EmailServiceError("SendGrid rejected the message")
        message_id = str(response.headers.get("X-Message-Id") or "").strip() or str(
            uuid4()
        )
        return ProviderSendResult(
            message_id=message_id,
            delivery_status="accepted",
            provider=self.name,
        )


class EmailService:
    """Send a reviewed outreach message through a provider. Never auto-sends."""

    def __init__(
        self,
        provider: EmailProvider,
        *,
        dry_run: bool = True,
        from_address: str | None = None,
    ) -> None:
        self._provider = provider
        self._dry_run = bool(dry_run)
        self._from_address = (from_address or "").strip() or None

    @classmethod
    def from_settings(
        cls,
        settings: Settings | None = None,
        *,
        provider: EmailProvider | None = None,
    ) -> EmailService:
        loaded = settings or get_settings()
        return cls(
            provider or get_email_provider(loaded),
            dry_run=loaded.email_dry_run,
            from_address=loaded.email_from_address,
        )

    def send(
        self,
        message: OutboundEmail,
        *,
        workflow_status: str,
        eligible_open_to_work: bool,
        already_sent: bool = False,
        overall_score: float | None = None,
    ) -> EmailSendRecord:
        """Send only when recipient and open-to-work checks pass.

        ``overall_score`` is ignored so ranking cannot authorize a send.
        """
        del overall_score
        del workflow_status
        self._require_open_to_work(eligible_open_to_work)
        recipient = self._require_recipient(message.recipient)
        if already_sent:
            raise DuplicateEmailError(
                "Duplicate send is not allowed for this job and candidate."
            )
        payload = message.model_copy(update={"recipient": recipient})
        sent_at = datetime.now(UTC)
        if self._dry_run:
            record = EmailSendRecord(
                message_id=f"dry-run-{uuid4()}",
                candidate_id=payload.candidate_id,
                job_id=payload.job_id,
                recipient=recipient,
                sent_at=sent_at,
                delivery_status="dry_run",
                template=payload.template,
                provider="dry_run",
                dry_run=True,
            )
            self._audit(record)
            return record
        from_address = self._require_from_address()
        result = self._provider.send(payload, from_address=from_address)
        record = EmailSendRecord(
            message_id=result.message_id,
            candidate_id=payload.candidate_id,
            job_id=payload.job_id,
            recipient=recipient,
            sent_at=sent_at,
            delivery_status=result.delivery_status,
            template=payload.template,
            provider=result.provider,
            dry_run=False,
        )
        self._audit(record)
        return record

    @staticmethod
    def _require_open_to_work(eligible_open_to_work: bool) -> None:
        if not eligible_open_to_work:
            raise EmailSendDeniedError(
                "Candidate does not have an explicit eligible open-to-work "
                "status. No email will be sent."
            )

    @staticmethod
    def _require_recipient(recipient: str) -> str:
        text = (recipient or "").strip().lower()
        local, sep, domain = text.partition("@")
        if (
            not sep
            or not local
            or not domain
            or " " in text
            or domain.startswith(".")
            or domain.endswith(".")
            or "." not in domain
        ):
            raise EmailSendDeniedError(
                "Candidate email is missing or invalid. No email will be sent."
            )
        return text

    def _require_from_address(self) -> str:
        if not self._from_address:
            raise EmailConfigurationError(
                "EMAIL_FROM_ADDRESS is required when EMAIL_DRY_RUN is false"
            )
        return self._from_address

    @staticmethod
    def _audit(record: EmailSendRecord) -> None:
        logger.info(
            "email_send",
            extra={
                "event": "email_send",
                "job_id": str(record.job_id),
                "candidate_id": str(record.candidate_id),
                "message_id": record.message_id,
                "delivery_status": record.delivery_status,
                "provider": record.provider,
                "dry_run": record.dry_run,
                "template": record.template,
                "has_recipient": True,
            },
        )


def get_email_provider(settings: Settings | None = None) -> EmailProvider:
    loaded = settings or get_settings()
    if loaded.email_dry_run:
        return NullEmailProvider()
    provider = (loaded.email_provider or "ses").strip().lower()
    if provider == "sendgrid":
        return SendGridEmailProvider.from_settings(loaded)
    if provider == "ses":
        return SESEmailProvider.from_settings(loaded)
    raise EmailConfigurationError(
        f"Unknown EMAIL_PROVIDER '{provider}'. Use ses or sendgrid."
    )


def is_blocking_status(delivery_status: str) -> bool:
    return delivery_status in BLOCKING_DELIVERY_STATUSES
