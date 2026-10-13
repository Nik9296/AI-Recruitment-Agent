from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1.routes.pipeline import get_pipeline, get_sourcing_service
from app.api.v1.routes.recruiter import require_recruiter
from app.main import app
from app.models.sourcing import SourcedCandidateRef, SourcingQuery, SourcingResult
from app.services.recruiter_auth import RecruiterSession


def setup_function() -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[require_recruiter] = lambda: RecruiterSession(
        username="tester", expires_at=4102444800
    )


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_openapi_documents_source_and_pipeline_routes() -> None:
    client = TestClient(app)
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/recruiter/jobs/{job_id}/source" in paths
    assert "/api/v1/recruiter/jobs/{job_id}/pipeline/run" in paths


def test_source_endpoint_returns_existing_candidates_only() -> None:
    job_id = uuid4()
    candidate_id = uuid4()
    service = MagicMock()
    service.source_job = AsyncMock(
        return_value=SourcingResult(
            job_title="AI/ML Engineer",
            queries=[
                SourcingQuery(
                    job_title="AI/ML Engineer",
                    skills=["Python"],
                    label="must_have",
                )
            ],
            candidates=[SourcedCandidateRef(candidate_id=candidate_id)],
            invented_candidates=False,
        )
    )
    app.dependency_overrides[get_sourcing_service] = lambda: service
    client = TestClient(app)
    response = client.post(f"/api/v1/recruiter/jobs/{job_id}/source")
    assert response.status_code == 200
    body = response.json()
    assert body["invented_candidates"] is False
    assert body["candidates"][0]["candidate_id"] == str(candidate_id)


def test_pipeline_run_never_marks_hired_or_sent() -> None:
    job_id = uuid4()
    pipeline = MagicMock()
    pipeline.run = AsyncMock(
        return_value={
            "job_id": str(job_id),
            "sourced_count": 2,
            "matched_count": 2,
            "ranked_count": 2,
            "shortlist_recorded": True,
            "outreach_sent": True,
            "hired": True,
            "errors": [],
        }
    )
    app.dependency_overrides[get_pipeline] = lambda: pipeline
    client = TestClient(app)
    response = client.post(f"/api/v1/recruiter/jobs/{job_id}/pipeline/run")
    assert response.status_code == 200
    body = response.json()
    assert body["shortlist_recorded"] is True
    assert body["outreach_sent"] is False
    assert body["hired"] is False
    assert body["sourced_count"] == 2
    assert "No email was sent" in body["message"]
