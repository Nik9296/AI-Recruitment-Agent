from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.config.settings import Settings
from app.integrations.email_service import (
    DuplicateEmailError,
    EmailConfigurationError,
    EmailSendDeniedError,
    EmailService,
    NullEmailProvider,
    OutboundEmail,
    SESEmailProvider,
    SendGridEmailProvider,
    get_email_provider,
)


def _message(**overrides) -> OutboundEmail:
    payload = {
        "candidate_id": uuid4(),
        "job_id": uuid4(),
        "recipient": "rahul@example.com",
        "subject": "AI/ML Engineer at Northwind",
        "body": "Hello Rahul,\n\nI am reaching out about the role.",
        "template": "initial",
    }
    payload.update(overrides)
    return OutboundEmail(**payload)


def _service(provider=None, *, dry_run=False, from_address="jobs@example.com"):
    return EmailService(
        provider or MagicMock(),
        dry_run=dry_run,
        from_address=from_address,
    )


def test_dry_run_does_not_call_provider() -> None:
    provider = MagicMock()
    service = _service(provider, dry_run=True)
    record = service.send(
        _message(),
        workflow_status="PENDING_REVIEW",
        eligible_open_to_work=True,
    )
    provider.send.assert_not_called()
    assert record.dry_run is True
    assert record.delivery_status == "dry_run"
    assert record.provider == "dry_run"
    assert record.message_id.startswith("dry-run-")
    assert record.recipient == "rahul@example.com"
    assert record.sent_at.tzinfo is not None


def test_ses_provider_is_mocked_and_records_message_id() -> None:
    client = MagicMock()
    client.send_email.return_value = {"MessageId": "ses-abc-123"}
    provider = SESEmailProvider(client)
    service = _service(provider, dry_run=False)
    message = _message()
    record = service.send(
        message,
        workflow_status="PENDING_REVIEW",
        eligible_open_to_work=True,
        overall_score=0.99,
    )
    assert record.message_id == "ses-abc-123"
    assert record.delivery_status == "accepted"
    assert record.provider == "ses"
    assert record.dry_run is False
    assert record.candidate_id == message.candidate_id
    assert record.job_id == message.job_id
    kwargs = client.send_email.call_args.kwargs
    assert kwargs["Source"] == "jobs@example.com"
    assert kwargs["Destination"]["ToAddresses"] == ["rahul@example.com"]
    assert kwargs["Message"]["Subject"]["Data"] == message.subject


def test_duplicate_send_is_blocked_before_provider() -> None:
    provider = MagicMock()
    service = _service(provider, dry_run=False)
    with pytest.raises(DuplicateEmailError, match="Duplicate send"):
        service.send(
            _message(),
            workflow_status="PENDING_REVIEW",
            eligible_open_to_work=True,
            already_sent=True,
        )
    provider.send.assert_not_called()


def test_send_allows_any_workflow_status_when_open_to_work() -> None:
    provider = MagicMock()
    service = _service(provider, dry_run=False)
    service.send(
        _message(),
        workflow_status="PENDING_REVIEW",
        eligible_open_to_work=True,
        overall_score=0.99,
    )
    provider.send.assert_called_once()


def test_ineligible_open_to_work_cannot_be_emailed() -> None:
    provider = MagicMock()
    service = _service(provider, dry_run=False)
    with pytest.raises(EmailSendDeniedError, match="open-to-work"):
        service.send(
            _message(),
            workflow_status="MATCHED",
            eligible_open_to_work=False,
        )
    provider.send.assert_not_called()


def test_missing_recipient_cannot_be_emailed() -> None:
    provider = MagicMock()
    service = _service(provider, dry_run=False)
    with pytest.raises(EmailSendDeniedError, match="email is missing"):
        service.send(
            _message(recipient=""),
            workflow_status="NEW",
            eligible_open_to_work=True,
        )
    provider.send.assert_not_called()


def test_live_send_requires_from_address() -> None:
    service = _service(MagicMock(), dry_run=False, from_address=None)
    with pytest.raises(EmailConfigurationError, match="EMAIL_FROM_ADDRESS"):
        service.send(
            _message(),
            workflow_status="NEW",
            eligible_open_to_work=True,
        )


def test_sendgrid_requires_api_key() -> None:
    with pytest.raises(EmailConfigurationError, match="SENDGRID_API_KEY"):
        SendGridEmailProvider("")


def test_sendgrid_send_posts_mail() -> None:
    client = MagicMock()
    response = MagicMock()
    response.status_code = 202
    response.headers = {"X-Message-Id": "sg-message-1"}
    client.post.return_value = response
    provider = SendGridEmailProvider("from-env-sendgrid", client=client)
    result = provider.send(_message(), from_address="jobs@example.com")
    assert result.provider == "sendgrid"
    assert result.message_id == "sg-message-1"
    assert result.delivery_status == "accepted"
    client.post.assert_called_once()
    kwargs = client.post.call_args.kwargs
    assert kwargs["headers"]["Authorization"].startswith("Bearer ")
    assert "from-env-sendgrid" not in str(kwargs["json"])


def test_get_email_provider_uses_null_in_dry_run() -> None:
    settings = Settings(email_dry_run=True, email_provider="ses")
    provider = get_email_provider(settings)
    assert isinstance(provider, NullEmailProvider)


def test_source_does_not_hardcode_provider_secrets() -> None:
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1] / "app" / "integrations" / "email_service.py"
    ).read_text(encoding="utf-8")
    assert "AKIA" not in source
    assert "SG." not in source
    assert "loaded.aws_secret_access_key" in source
    assert "AIza" not in source


def test_ses_from_settings_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_boto3 = MagicMock()
    fake_client = MagicMock()
    fake_boto3.client.return_value = fake_client
    monkeypatch.setitem(__import__("sys").modules, "boto3", fake_boto3)
    settings = Settings(
        email_dry_run=False,
        email_from_address="jobs@example.com",
        aws_region="ap-south-1",
        aws_access_key_id="from-env-key",
        aws_secret_access_key="from-env-secret",
    )
    provider = SESEmailProvider.from_settings(settings)
    fake_boto3.client.assert_called_once_with(
        "ses",
        region_name="ap-south-1",
        aws_access_key_id="from-env-key",
        aws_secret_access_key="from-env-secret",
    )
    assert provider._client is fake_client
