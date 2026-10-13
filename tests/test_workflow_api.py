from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1.routes.recruiter import get_workflow_service, require_recruiter
from app.candidates.availability_filter import OpenToWorkStatus
from app.main import app
from app.schemas.workflow import OutreachHandoffResponse, WorkflowHistoryResponse
from app.services.recruiter_auth import RecruiterSession
from app.services.workflow_service import WorkflowService
from app.workflow.outreach_gate import DuplicateOutreachError, OutreachHandoffDeniedError
from app.workflow.states import WorkflowState
from app.workflow.transitions import InvalidWorkflowTransitionError


def setup_function() -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[require_recruiter] = lambda: RecruiterSession(
        username="tester", expires_at=4102444800
    )


def teardown_function() -> None:
    app.dependency_overrides.clear()


def _history(**overrides) -> WorkflowHistoryResponse:
    job_id = overrides.get("job_id", uuid4())
    candidate_id = overrides.get("candidate_id", uuid4())
    data = {
        "job_id": job_id,
        "candidate_id": candidate_id,
        "workflow_status": WorkflowState.APPROVED_FOR_OUTREACH.value,
        "review_status": "approved",
        "outreach_handed_off": False,
        "transitions": [
            {
                "id": uuid4(),
                "from_status": WorkflowState.PENDING_REVIEW.value,
                "to_status": WorkflowState.APPROVED_FOR_OUTREACH.value,
                "recruiter_id": "tester",
                "actor": "recruiter",
                "reason": "Ready for outreach",
                "created_at": datetime.now(UTC),
            }
        ],
    }
    data.update(overrides)
    return WorkflowHistoryResponse(**data)


def test_openapi_documents_workflow_routes() -> None:
    client = TestClient(app)
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/recruiter/jobs/{job_id}/candidates/{candidate_id}/workflow" in paths
    assert (
        "/api/v1/recruiter/jobs/{job_id}/candidates/{candidate_id}/outreach-handoff"
        in paths
    )


def test_workflow_change_endpoint_stores_recruiter() -> None:
    history = _history()
    service = MagicMock()
    service.change_status = AsyncMock(return_value=history)
    app.dependency_overrides[get_workflow_service] = lambda: service
    client = TestClient(app)
    response = client.post(
        f"/api/v1/recruiter/jobs/{history.job_id}/candidates/{history.candidate_id}/workflow",
        json={"to_status": "APPROVED_FOR_OUTREACH", "reason": "Ready for outreach"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["workflow_status"] == "APPROVED_FOR_OUTREACH"
    assert body["transitions"][0]["recruiter_id"] == "tester"
    assert body["transitions"][0]["reason"] == "Ready for outreach"
    service.change_status.assert_awaited_once()
    kwargs = service.change_status.await_args.kwargs
    assert kwargs["recruiter_id"] == "tester"
    assert kwargs["reason"] == "Ready for outreach"


def test_invalid_transition_returns_409() -> None:
    service = MagicMock()
    service.change_status = AsyncMock(
        side_effect=InvalidWorkflowTransitionError(
            "Cannot transition from MATCHED to APPROVED_FOR_OUTREACH as recruiter. "
            "High match scores do not authorize outreach."
        )
    )
    app.dependency_overrides[get_workflow_service] = lambda: service
    client = TestClient(app)
    response = client.post(
        f"/api/v1/recruiter/jobs/{uuid4()}/candidates/{uuid4()}/workflow",
        json={"to_status": "APPROVED_FOR_OUTREACH"},
    )
    assert response.status_code == 409
    assert "High match scores" in response.json()["detail"]


def test_outreach_handoff_does_not_send_email() -> None:
    job_id = uuid4()
    candidate_id = uuid4()
    service = MagicMock()
    service.handoff_to_outreach = AsyncMock(
        return_value=OutreachHandoffResponse(
            job_id=job_id,
            candidate_id=candidate_id,
            workflow_status=WorkflowState.APPROVED_FOR_OUTREACH.value,
            recruiter_id="tester",
            handed_off_at=datetime.now(UTC),
            email_sent=False,
            queued_for_outreach_agent=True,
            message="Queued for the Outreach Agent. Email is not sent from this step.",
        )
    )
    app.dependency_overrides[get_workflow_service] = lambda: service
    client = TestClient(app)
    response = client.post(
        f"/api/v1/recruiter/jobs/{job_id}/candidates/{candidate_id}/outreach-handoff"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email_sent"] is False
    assert body["queued_for_outreach_agent"] is True
    service.handoff_to_outreach.assert_awaited_once()
    assert service.handoff_to_outreach.await_args.kwargs["recruiter_id"] == "tester"


def test_duplicate_outreach_returns_409() -> None:
    service = MagicMock()
    service.handoff_to_outreach = AsyncMock(
        side_effect=DuplicateOutreachError(
            "Duplicate outreach is not allowed. No email will be sent."
        )
    )
    app.dependency_overrides[get_workflow_service] = lambda: service
    client = TestClient(app)
    response = client.post(
        f"/api/v1/recruiter/jobs/{uuid4()}/candidates/{uuid4()}/outreach-handoff"
    )
    assert response.status_code == 409
    assert "Duplicate outreach" in response.json()["detail"]


def test_handoff_denied_returns_400() -> None:
    service = MagicMock()
    service.handoff_to_outreach = AsyncMock(
        side_effect=OutreachHandoffDeniedError(
            "Candidate does not have an explicit eligible open-to-work "
            "status. No email will be sent."
        )
    )
    app.dependency_overrides[get_workflow_service] = lambda: service
    client = TestClient(app)
    response = client.post(
        f"/api/v1/recruiter/jobs/{uuid4()}/candidates/{uuid4()}/outreach-handoff"
    )
    assert response.status_code == 400
    assert "open-to-work" in response.json()["detail"]


@pytest.mark.asyncio
async def test_service_handoff_allows_pending_review_when_open_to_work() -> None:
    job_id = uuid4()
    candidate_id = uuid4()
    row = MagicMock(
        workflow_status=WorkflowState.PENDING_REVIEW.value,
        overall_score=0.99,
    )
    candidate = MagicMock(
        id=candidate_id,
        open_to_work_status=OpenToWorkStatus.OPEN_TO_WORK,
        open_to_work_source="candidate_declaration",
        open_to_work_verified_at=datetime.now(UTC),
    )
    workflow_repo = MagicMock()
    workflow_repo.get_job_candidate = AsyncMock(return_value=row)
    workflow_repo.get_handoff = AsyncMock(return_value=None)
    workflow_repo.add_handoff = AsyncMock(return_value=MagicMock(created_at=datetime.now(UTC)))
    workflow_repo.commit = AsyncMock()
    recruiter_repo = MagicMock()
    recruiter_repo.get_candidate = AsyncMock(return_value=candidate)
    service = WorkflowService(workflow_repo, recruiter_repo)
    response = await service.handoff_to_outreach(job_id, candidate_id, recruiter_id="tester")
    assert response is not None
    assert response.queued_for_outreach_agent is True
    workflow_repo.add_handoff.assert_awaited_once()


@pytest.mark.asyncio
async def test_service_handoff_blocks_duplicate() -> None:
    job_id = uuid4()
    candidate_id = uuid4()
    row = MagicMock(
        workflow_status=WorkflowState.APPROVED_FOR_OUTREACH.value,
        overall_score=0.91,
    )
    candidate = MagicMock(
        id=candidate_id,
        open_to_work_status=OpenToWorkStatus.OPEN_TO_WORK,
        open_to_work_source="candidate_declaration",
        open_to_work_verified_at=datetime.now(UTC),
    )
    workflow_repo = MagicMock()
    workflow_repo.get_job_candidate = AsyncMock(return_value=row)
    workflow_repo.get_handoff = AsyncMock(return_value=MagicMock())
    recruiter_repo = MagicMock()
    recruiter_repo.get_candidate = AsyncMock(return_value=candidate)
    service = WorkflowService(workflow_repo, recruiter_repo)
    with pytest.raises(DuplicateOutreachError):
        await service.handoff_to_outreach(
            job_id, candidate_id, recruiter_id="tester"
        )
    workflow_repo.add_handoff.assert_not_called()


@pytest.mark.asyncio
async def test_change_status_records_transition() -> None:
    job_id = uuid4()
    candidate_id = uuid4()
    row = MagicMock(
        id=uuid4(),
        job_id=job_id,
        candidate_id=candidate_id,
        workflow_status=WorkflowState.PENDING_REVIEW.value,
        review_status="pending",
        outreach_handed_off_at=None,
    )
    workflow_repo = MagicMock()
    workflow_repo.get_job_candidate = AsyncMock(return_value=row)
    async def _add(job_row, **kwargs):
        job_row.workflow_status = kwargs["to_status"]
        job_row.review_status = "approved"

    workflow_repo.add_transition = AsyncMock(side_effect=_add)
    workflow_repo.commit = AsyncMock()
    workflow_repo.list_transitions = AsyncMock(
        return_value=[
            MagicMock(
                id=uuid4(),
                from_status="PENDING_REVIEW",
                to_status="APPROVED_FOR_OUTREACH",
                recruiter_id="tester",
                actor="recruiter",
                reason="Approved after review",
                created_at=datetime.now(UTC),
            )
        ]
    )
    workflow_repo.get_handoff = AsyncMock(return_value=None)
    service = WorkflowService(workflow_repo, MagicMock())
    history = await service.change_status(
        job_id,
        candidate_id,
        "APPROVED_FOR_OUTREACH",
        recruiter_id="tester",
        reason="Approved after review",
    )
    assert history is not None
    assert history.workflow_status == "APPROVED_FOR_OUTREACH"
    workflow_repo.add_transition.assert_awaited_once()
    kwargs = workflow_repo.add_transition.await_args.kwargs
    assert kwargs["recruiter_id"] == "tester"
    assert kwargs["reason"] == "Approved after review"
    assert kwargs["to_status"] == "APPROVED_FOR_OUTREACH"


@pytest.mark.asyncio
async def test_apply_review_action_is_idempotent_for_same_state() -> None:
    job_id = uuid4()
    candidate_id = uuid4()
    row = MagicMock(
        id=uuid4(),
        job_id=job_id,
        candidate_id=candidate_id,
        workflow_status=WorkflowState.REJECTED.value,
        review_status="rejected",
        outreach_handed_off_at=None,
    )
    workflow_repo = MagicMock()
    workflow_repo.get_job_candidate = AsyncMock(return_value=row)
    workflow_repo.add_transition = AsyncMock()
    workflow_repo.commit = AsyncMock()
    workflow_repo.list_transitions = AsyncMock(return_value=[])
    workflow_repo.get_handoff = AsyncMock(return_value=None)
    service = WorkflowService(workflow_repo, MagicMock())
    history = await service.apply_review_action(
        job_id, candidate_id, "rejected", recruiter_id="tester"
    )
    assert history is not None
    assert history.workflow_status == WorkflowState.REJECTED.value
    workflow_repo.add_transition.assert_not_called()
