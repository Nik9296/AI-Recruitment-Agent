from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1.routes.outreach import get_outreach_service
from app.api.v1.routes.recruiter import require_recruiter
from app.candidates.availability_filter import OpenToWorkStatus
from app.main import app
from app.models.outreach import OutreachTemplateType
from app.schemas.outreach import OutreachDraftResponse
from app.services.outreach_service import OutreachService
from app.services.recruiter_auth import RecruiterSession
from app.workflow.outreach_gate import OutreachHandoffDeniedError
from app.workflow.states import WorkflowState


def setup_function() -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[require_recruiter] = lambda: RecruiterSession(
        username="tester", expires_at=4102444800
    )


def teardown_function() -> None:
    app.dependency_overrides.clear()


def _draft(**overrides) -> OutreachDraftResponse:
    job_id = overrides.get("job_id", uuid4())
    candidate_id = overrides.get("candidate_id", uuid4())
    data = {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "subject": "AI/ML Engineer at Northwind",
        "body": "Hello Rahul,\n\nI am reaching out about the AI/ML Engineer role.",
        "personalization_points": ["Current role: ML Engineer", "Skill: Python"],
        "generated_at": datetime.now(UTC),
        "template": OutreachTemplateType.INITIAL.value,
        "review_status": "pending_recruiter_review",
        "email_sent": False,
        "recruiter_id": "tester",
        "message": "Draft saved for recruiter review. No email was sent.",
    }
    data.update(overrides)
    return OutreachDraftResponse(**data)


def test_openapi_documents_outreach_draft_routes() -> None:
    client = TestClient(app)
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/recruiter/jobs/{job_id}/candidates/{candidate_id}/outreach" in paths
    methods = paths["/api/v1/recruiter/jobs/{job_id}/candidates/{candidate_id}/outreach"]
    assert "get" in methods
    assert "post" in methods


def test_generate_draft_is_reviewable_and_not_sent() -> None:
    draft = _draft()
    service = MagicMock()
    service.generate_draft = AsyncMock(return_value=draft)
    app.dependency_overrides[get_outreach_service] = lambda: service
    client = TestClient(app)
    response = client.post(
        f"/api/v1/recruiter/jobs/{draft.job_id}/candidates/{draft.candidate_id}/outreach",
        json={"template": "initial"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email_sent"] is False
    assert body["review_status"] == "pending_recruiter_review"
    assert body["subject"] == draft.subject
    assert "Rahul" in body["body"]
    service.generate_draft.assert_awaited_once()


def test_generate_draft_denied_when_not_open_to_work() -> None:
    service = MagicMock()
    service.generate_draft = AsyncMock(
        side_effect=OutreachHandoffDeniedError(
            "Candidate does not have an explicit eligible open-to-work "
            "status. No email will be sent."
        )
    )
    app.dependency_overrides[get_outreach_service] = lambda: service
    client = TestClient(app)
    response = client.post(
        f"/api/v1/recruiter/jobs/{uuid4()}/candidates/{uuid4()}/outreach",
        json={"template": "initial"},
    )
    assert response.status_code == 400
    assert "open-to-work" in response.json()["detail"]


def test_get_draft_returns_404_when_missing() -> None:
    service = MagicMock()
    service.get_draft = AsyncMock(return_value=None)
    app.dependency_overrides[get_outreach_service] = lambda: service
    client = TestClient(app)
    response = client.get(
        f"/api/v1/recruiter/jobs/{uuid4()}/candidates/{uuid4()}/outreach"
    )
    assert response.status_code == 404


def test_get_draft_returns_saved_review_copy() -> None:
    draft = _draft(message="Draft loaded for recruiter review. No email was sent.")
    service = MagicMock()
    service.get_draft = AsyncMock(return_value=draft)
    app.dependency_overrides[get_outreach_service] = lambda: service
    client = TestClient(app)
    response = client.get(
        f"/api/v1/recruiter/jobs/{draft.job_id}/candidates/{draft.candidate_id}/outreach"
        "?template=initial"
    )
    assert response.status_code == 200
    assert response.json()["email_sent"] is False
    assert response.json()["body"] == draft.body


@pytest.mark.asyncio
async def test_service_requires_open_to_work() -> None:
    job_id = uuid4()
    candidate_id = uuid4()
    match_row = MagicMock()
    match_row.workflow_status = WorkflowState.PENDING_REVIEW.value
    candidate = MagicMock()
    candidate.id = candidate_id
    candidate.open_to_work_status = OpenToWorkStatus.OPEN_TO_WORK
    candidate.open_to_work_source = "candidate_declaration"
    outreach_repo = MagicMock()
    recruiter_repo = MagicMock()
    recruiter_repo.get_job = AsyncMock(return_value=MagicMock())
    recruiter_repo.get_candidate = AsyncMock(return_value=candidate)
    recruiter_repo.get_job_candidate = AsyncMock(return_value=match_row)
    service = OutreachService(outreach_repo, recruiter_repo, agent=MagicMock())
    candidate.open_to_work_source = None
    with pytest.raises(OutreachHandoffDeniedError, match="open-to-work"):
        await service.generate_draft(
            job_id, candidate_id, recruiter_id="tester", use_llm=False
        )
    outreach_repo.upsert_draft.assert_not_called()
