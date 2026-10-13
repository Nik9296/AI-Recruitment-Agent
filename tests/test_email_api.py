from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1.routes.outreach import get_email_send_service
from app.api.v1.routes.recruiter import require_recruiter
from app.candidates.availability_filter import OpenToWorkStatus
from app.integrations.email_service import (
    DuplicateEmailError,
    EmailSendDeniedError,
    EmailSendRecord,
    EmailService,
)
from app.main import app
from app.schemas.email import EmailSendResponse
from app.services.email_send_service import EmailSendService
from app.services.recruiter_auth import RecruiterSession
from app.workflow.states import WorkflowState


def setup_function() -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[require_recruiter] = lambda: RecruiterSession(
        username="tester", expires_at=4102444800
    )


def teardown_function() -> None:
    app.dependency_overrides.clear()


def _record(**overrides) -> EmailSendRecord:
    payload = {
        "message_id": "ses-abc-123",
        "candidate_id": uuid4(),
        "job_id": uuid4(),
        "recipient": "rahul@example.com",
        "sent_at": datetime.now(UTC),
        "delivery_status": "accepted",
        "template": "initial",
        "provider": "ses",
        "dry_run": False,
    }
    payload.update(overrides)
    return EmailSendRecord(**payload)


def _response(record: EmailSendRecord) -> EmailSendResponse:
    return EmailSendResponse(
        message_id=record.message_id,
        candidate_id=record.candidate_id,
        job_id=record.job_id,
        recipient=record.recipient,
        sent_at=record.sent_at,
        delivery_status=record.delivery_status,
        template=record.template,
        provider=record.provider,
        dry_run=record.dry_run,
        email_sent=not record.dry_run,
        recruiter_id="tester",
        message="Email accepted by the provider. Recruiter authorized this send.",
    )


def test_openapi_documents_email_send_route() -> None:
    client = TestClient(app)
    paths = client.get("/openapi.json").json()["paths"]
    assert (
        "/api/v1/recruiter/jobs/{job_id}/candidates/{candidate_id}/outreach/send"
        in paths
    )


def test_send_endpoint_returns_recorded_delivery() -> None:
    record = _record()
    service = MagicMock()
    service.send_draft = AsyncMock(return_value=_response(record))
    app.dependency_overrides[get_email_send_service] = lambda: service
    client = TestClient(app)
    response = client.post(
        f"/api/v1/recruiter/jobs/{record.job_id}/candidates/{record.candidate_id}/outreach/send",
        json={"template": "initial"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["message_id"] == "ses-abc-123"
    assert body["recipient"] == "rahul@example.com"
    assert body["delivery_status"] == "accepted"
    assert body["email_sent"] is True


def test_send_endpoint_rejects_non_open_to_work_candidate() -> None:
    service = MagicMock()
    service.send_draft = AsyncMock(
        side_effect=EmailSendDeniedError(
            "Candidate does not have an explicit eligible open-to-work "
            "status. No email will be sent."
        )
    )
    app.dependency_overrides[get_email_send_service] = lambda: service
    client = TestClient(app)
    response = client.post(
        f"/api/v1/recruiter/jobs/{uuid4()}/candidates/{uuid4()}/outreach/send",
        json={"template": "initial"},
    )
    assert response.status_code == 400
    assert "open-to-work" in response.json()["detail"]


def test_send_endpoint_rejects_duplicate() -> None:
    service = MagicMock()
    service.send_draft = AsyncMock(
        side_effect=DuplicateEmailError(
            "Duplicate send is not allowed for this job and candidate."
        )
    )
    app.dependency_overrides[get_email_send_service] = lambda: service
    client = TestClient(app)
    response = client.post(
        f"/api/v1/recruiter/jobs/{uuid4()}/candidates/{uuid4()}/outreach/send",
        json={"template": "initial"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_dispatch_requires_draft_and_open_to_work() -> None:
    job_id = uuid4()
    candidate_id = uuid4()
    match_row = MagicMock()
    match_row.workflow_status = WorkflowState.APPROVED_FOR_OUTREACH.value
    match_row.overall_score = 0.99
    match_row.job_id = job_id
    match_row.candidate_id = candidate_id
    candidate = MagicMock()
    candidate.id = candidate_id
    candidate.email = "rahul@example.com"
    candidate.open_to_work_status = OpenToWorkStatus.OPEN_TO_WORK
    candidate.open_to_work_source = "candidate_declaration"
    draft = MagicMock()
    draft.subject = "Hello"
    draft.body = "Body"
    email_service = MagicMock(spec=EmailService)
    email_repo = MagicMock()
    email_repo.has_blocking_send = AsyncMock(return_value=False)
    email_repo.save = AsyncMock(return_value=MagicMock(recruiter_id="tester"))
    email_repo.commit = AsyncMock()
    outreach_repo = MagicMock()
    outreach_repo.get_draft = AsyncMock(return_value=None)
    recruiter_repo = MagicMock()
    recruiter_repo.get_job_candidate = AsyncMock(return_value=match_row)
    recruiter_repo.get_candidate = AsyncMock(return_value=candidate)
    workflow_repo = MagicMock()
    service = EmailSendService(
        email_service,
        email_repo,
        outreach_repo,
        recruiter_repo,
        workflow_repo,
    )
    with pytest.raises(EmailSendDeniedError, match="draft"):
        await service.send_draft(job_id, candidate_id, recruiter_id="tester")
    email_service.send.assert_not_called()

    outreach_repo.get_draft = AsyncMock(return_value=draft)
    record = _record(job_id=job_id, candidate_id=candidate_id, dry_run=True)
    email_service.send.return_value = record
    result = await service.send_draft(job_id, candidate_id, recruiter_id="tester")
    assert result.dry_run is True
    assert result.email_sent is False
    outreach_repo.mark_sent.assert_not_called()
    workflow_repo.add_transition.assert_not_called()
    email_repo.save.assert_awaited()


@pytest.mark.asyncio
async def test_live_dispatch_marks_draft_sent_and_contacted() -> None:
    job_id = uuid4()
    candidate_id = uuid4()
    match_row = MagicMock()
    match_row.id = uuid4()
    match_row.workflow_status = WorkflowState.APPROVED_FOR_OUTREACH.value
    match_row.overall_score = 0.12
    match_row.job_id = job_id
    match_row.candidate_id = candidate_id
    candidate = MagicMock()
    candidate.id = candidate_id
    candidate.email = "rahul@example.com"
    candidate.open_to_work_status = OpenToWorkStatus.OPEN_TO_WORK
    candidate.open_to_work_source = "recruiter_recorded"
    draft = MagicMock()
    draft.subject = "Hello"
    draft.body = "Body"
    record = _record(job_id=job_id, candidate_id=candidate_id, dry_run=False)
    email_service = MagicMock(spec=EmailService)
    email_service.send.return_value = record
    email_repo = MagicMock()
    email_repo.has_blocking_send = AsyncMock(return_value=False)
    email_repo.save = AsyncMock(return_value=MagicMock(recruiter_id="tester"))
    email_repo.commit = AsyncMock()
    outreach_repo = MagicMock()
    outreach_repo.get_draft = AsyncMock(return_value=draft)
    outreach_repo.mark_sent = AsyncMock()
    recruiter_repo = MagicMock()
    recruiter_repo.get_job_candidate = AsyncMock(return_value=match_row)
    recruiter_repo.get_candidate = AsyncMock(return_value=candidate)
    workflow_repo = MagicMock()
    workflow_repo.add_transition = AsyncMock()
    workflow_repo.get_handoff = AsyncMock(return_value=None)
    service = EmailSendService(
        email_service,
        email_repo,
        outreach_repo,
        recruiter_repo,
        workflow_repo,
    )
    result = await service.send_draft(job_id, candidate_id, recruiter_id="tester")
    assert result.email_sent is True
    outreach_repo.mark_sent.assert_awaited_once()
    workflow_repo.add_transition.assert_awaited()
    kwargs = email_service.send.call_args.kwargs
    assert kwargs["workflow_status"] == WorkflowState.APPROVED_FOR_OUTREACH.value
    assert kwargs["eligible_open_to_work"] is True
    assert kwargs["already_sent"] is False
