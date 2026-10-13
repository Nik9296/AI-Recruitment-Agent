from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1.routes.recruiter import require_recruiter
from app.api.v1.routes.scheduling import get_scheduling_service
from app.main import app
from app.schemas.scheduling import InterviewRecordResponse
from app.schemas.workflow import WorkflowHistoryResponse
from app.services.recruiter_auth import RecruiterSession
from app.services.scheduling_service import SchedulingServiceError
from app.workflow.states import WorkflowState


def setup_function() -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[require_recruiter] = lambda: RecruiterSession(
        username="tester", expires_at=4102444800
    )


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_openapi_documents_interview_routes() -> None:
    client = TestClient(app)
    paths = client.get("/openapi.json").json()["paths"]
    assert (
        "/api/v1/recruiter/jobs/{job_id}/candidates/{candidate_id}/interview/invite"
        in paths
    )
    assert (
        "/api/v1/recruiter/jobs/{job_id}/candidates/{candidate_id}/interview/confirm"
        in paths
    )


def test_invite_endpoint_returns_history() -> None:
    job_id = uuid4()
    candidate_id = uuid4()
    service = MagicMock()
    service.invite = AsyncMock(
        return_value=WorkflowHistoryResponse(
            job_id=job_id,
            candidate_id=candidate_id,
            workflow_status=WorkflowState.INTERVIEW_INVITED.value,
            review_status="approved",
            outreach_handed_off=True,
            transitions=[],
        )
    )
    app.dependency_overrides[get_scheduling_service] = lambda: service
    client = TestClient(app)
    response = client.post(
        f"/api/v1/recruiter/jobs/{job_id}/candidates/{candidate_id}/interview/invite"
    )
    assert response.status_code == 200
    assert response.json()["workflow_status"] == WorkflowState.INTERVIEW_INVITED.value


def test_confirm_endpoint_rejects_unproposed_slot() -> None:
    service = MagicMock()
    service.confirm = AsyncMock(
        side_effect=SchedulingServiceError(
            "Confirm a slot from the proposed list. No calendar event was created."
        )
    )
    app.dependency_overrides[get_scheduling_service] = lambda: service
    client = TestClient(app)
    response = client.post(
        f"/api/v1/recruiter/jobs/{uuid4()}/candidates/{uuid4()}/interview/confirm",
        json={
            "start_at": datetime(2026, 9, 21, 10, 0, tzinfo=UTC).isoformat(),
            "end_at": datetime(2026, 9, 21, 10, 45, tzinfo=UTC).isoformat(),
        },
    )
    assert response.status_code == 409
    assert "proposed list" in response.json()["detail"]


def test_propose_endpoint_returns_unbooked_slots() -> None:
    job_id = uuid4()
    candidate_id = uuid4()
    service = MagicMock()
    service.propose = AsyncMock(
        return_value=InterviewRecordResponse(
            job_id=job_id,
            candidate_id=candidate_id,
            status="proposed",
            timezone="Asia/Kolkata",
            duration_minutes=45,
            proposed_slots=[{"start_at": "2026-09-21T10:00:00+05:30"}],
            calendar_booked=False,
            message="Interview times proposed for recruiter review. Calendar is not booked yet.",
        )
    )
    app.dependency_overrides[get_scheduling_service] = lambda: service
    client = TestClient(app)
    response = client.post(
        f"/api/v1/recruiter/jobs/{job_id}/candidates/{candidate_id}/interview/proposals"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["calendar_booked"] is False
    assert body["status"] == "proposed"
