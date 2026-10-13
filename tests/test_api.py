from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.agents.jd_agent import EmptyJobDescriptionError, JDExtractionError
from app.api.v1.routes.jobs import (
    get_jd_agent,
    get_job_application_service,
    get_job_service,
)
from app.database.repositories.job_repository import JobRepository
from app.main import app
from app.models.job import EmploymentType, JobProfile, WorkMode
from app.services.job_service import JobService
from app.services.llm import LLMConfigurationError

SAMPLE_JD = (
    "QA Engineer in Pune. Hybrid, full-time. 1-3 years. "
    "Must have Selenium. Preferred: Cypress."
)

SAMPLE_BODY = {
    "job_title": "QA Engineer",
    "experience_min": 1,
    "experience_max": 3,
    "location": "Pune",
    "work_mode": "Hybrid",
    "employment_type": "Full-time",
    "must_have_skills": ["Selenium"],
    "preferred_skills": ["Cypress"],
    "education": [],
    "responsibilities": ["Write tests"],
    "keywords": ["Selenium"],
    "raw_job_description": (
        "QA Engineer in Pune. Hybrid, full-time. 1-3 years. Must have Selenium."
    ),
}


def setup_function() -> None:
    app.dependency_overrides.clear()


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers.get("x-content-type-options") == "nosniff"


def test_ready_does_not_expose_secrets() -> None:
    client = TestClient(app)
    response = client.get("/ready")
    assert response.status_code in {200, 503}
    body = response.json()
    assert "email_dry_run" in body
    assert "calendar_dry_run" in body
    assert "database" in body
    dumped = str(body).lower()
    assert "password" not in dumped
    assert "secret" not in dumped
    assert "api_key" not in dumped
    assert "aiza" not in dumped



def _override_agent(analyze_return=None, side_effect=None) -> MagicMock:
    agent = MagicMock()
    if side_effect is not None:
        agent.analyze.side_effect = side_effect
    else:
        agent.analyze.return_value = analyze_return
    app.dependency_overrides[get_jd_agent] = lambda: agent
    return agent


def test_analyze_success() -> None:
    profile = JobProfile(
        job_title="QA Engineer",
        experience_min=1,
        experience_max=3,
        location="Pune",
        work_mode=WorkMode.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        must_have_skills=["Selenium"],
        preferred_skills=["Cypress"],
        education=[],
        responsibilities=[],
        keywords=["Selenium", "Cypress"],
    )
    agent = _override_agent(analyze_return=profile)
    client = TestClient(app)
    response = client.post(
        "/api/v1/jobs/analyze",
        json={"job_description": SAMPLE_JD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["job_title"] == "QA Engineer"
    assert body["experience_min"] == 1
    assert body["experience_max"] == 3
    assert body["location"] == "Pune"
    assert body["work_mode"] == "Hybrid"
    assert body["employment_type"] == "Full-time"
    assert body["must_have_skills"] == ["Selenium"]
    assert body["preferred_skills"] == ["Cypress"]
    agent.analyze.assert_called_once_with(SAMPLE_JD)


def test_analyze_rejects_missing_field() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/jobs/analyze", json={})
    assert response.status_code == 422


def test_analyze_rejects_whitespace_jd() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/jobs/analyze",
        json={"job_description": "   "},
    )
    assert response.status_code == 422


def test_analyze_maps_empty_jd_error() -> None:
    _override_agent(side_effect=EmptyJobDescriptionError("blank"))
    client = TestClient(app)
    response = client.post(
        "/api/v1/jobs/analyze",
        json={"job_description": SAMPLE_JD},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "blank"


def test_analyze_maps_extraction_error() -> None:
    _override_agent(side_effect=JDExtractionError("invalid profile"))
    client = TestClient(app)
    response = client.post(
        "/api/v1/jobs/analyze",
        json={"job_description": SAMPLE_JD},
    )
    assert response.status_code == 422
    assert "invalid profile" in response.json()["detail"]


def test_analyze_maps_llm_config_error() -> None:
    _override_agent(side_effect=LLMConfigurationError("GOOGLE_API_KEY is required"))
    client = TestClient(app)
    response = client.post(
        "/api/v1/jobs/analyze",
        json={"job_description": SAMPLE_JD},
    )
    assert response.status_code == 503


def test_openapi_documents_analyze_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/jobs/analyze" in paths
    assert "post" in paths["/api/v1/jobs/analyze"]


def _job():
    now = datetime.now(UTC)
    job = MagicMock()
    job.id = uuid4()
    job.job_title = "QA Engineer"
    job.experience_min = 1.0
    job.experience_max = 3.0
    job.location = "Pune"
    job.work_mode = WorkMode.HYBRID
    job.employment_type = EmploymentType.FULL_TIME
    job.must_have_skills = ["Selenium"]
    job.preferred_skills = ["Cypress"]
    job.education = []
    job.responsibilities = ["Write tests"]
    job.keywords = ["Selenium"]
    job.raw_job_description = SAMPLE_BODY["raw_job_description"]
    job.created_at = now
    job.updated_at = now
    return job


def test_save_analyzed_job() -> None:
    job = _job()
    service = MagicMock()
    service.save_analyzed_job = AsyncMock(return_value=job)
    app.dependency_overrides[get_job_service] = lambda: service
    client = TestClient(app)
    response = client.post("/api/v1/jobs", json=SAMPLE_BODY)
    assert response.status_code == 201
    body = response.json()
    assert body["job_title"] == "QA Engineer"
    assert body["location"] == "Pune"
    assert body["id"] == str(job.id)
    assert body["raw_job_description"] == SAMPLE_BODY["raw_job_description"]
    service.save_analyzed_job.assert_awaited_once()


def test_save_rejects_blank_raw_description() -> None:
    app.dependency_overrides[get_job_service] = lambda: MagicMock()
    client = TestClient(app)
    payload = dict(SAMPLE_BODY)
    payload["raw_job_description"] = "   "
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422


def test_save_without_database_returns_503() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/jobs", json=SAMPLE_BODY)
    assert response.status_code == 503


def test_get_saved_job() -> None:
    job = _job()
    service = MagicMock()
    service.get_job = AsyncMock(return_value=job)
    app.dependency_overrides[get_job_service] = lambda: service
    client = TestClient(app)
    response = client.get(f"/api/v1/jobs/{job.id}")
    assert response.status_code == 200
    assert response.json()["id"] == str(job.id)


def test_get_saved_job_not_found() -> None:
    service = MagicMock()
    service.get_job = AsyncMock(return_value=None)
    app.dependency_overrides[get_job_service] = lambda: service
    client = TestClient(app)
    response = client.get(f"/api/v1/jobs/{uuid4()}")
    assert response.status_code == 404


def test_openapi_documents_save_endpoint() -> None:
    client = TestClient(app)
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/jobs" in paths
    assert "post" in paths["/api/v1/jobs"]
    assert "/api/v1/jobs/{job_id}/apply" in paths


def test_apply_to_job_creates_candidate_application() -> None:
    service = MagicMock()
    now = datetime.now(UTC)
    candidate_id = uuid4()
    job_id = uuid4()
    service.apply = AsyncMock(
        return_value={
            "job_id": str(job_id),
            "candidate_id": str(candidate_id),
            "created_candidate": True,
            "created_match": True,
            "applied_at": now.isoformat(),
            "message": "Application submitted successfully. Recruiter will review your profile.",
        }
    )
    app.dependency_overrides[get_job_application_service] = lambda: service
    client = TestClient(app)
    response = client.post(
        f"/api/v1/jobs/{job_id}/apply",
        json={
            "full_name": "Anita Rao",
            "email": "anita@example.com",
            "skills": ["Python", "FastAPI"],
            "open_to_work": True,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["candidate_id"] == str(candidate_id)
    assert body["created_match"] is True
    service.apply.assert_awaited_once()


def test_apply_to_job_returns_404_for_unknown_job() -> None:
    service = MagicMock()
    service.apply = AsyncMock(return_value=None)
    app.dependency_overrides[get_job_application_service] = lambda: service
    client = TestClient(app)
    response = client.post(
        f"/api/v1/jobs/{uuid4()}/apply",
        json={
            "full_name": "Anita Rao",
            "email": "anita@example.com",
        },
    )
    assert response.status_code == 404


def _profile() -> JobProfile:
    return JobProfile(
        job_title="QA Engineer",
        experience_min=1,
        experience_max=3,
        location="Pune",
        work_mode=WorkMode.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        must_have_skills=["Selenium"],
        preferred_skills=["Cypress"],
        education=[],
        responsibilities=["Write tests"],
        keywords=["Selenium", "Cypress"],
    )


@pytest.mark.asyncio
async def test_repository_save_persists_profile_fields() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    repo = JobRepository(session)
    profile = _profile()
    job = await repo.save(profile, "raw JD text")
    session.add.assert_called_once()
    saved = session.add.call_args.args[0]
    assert saved is job
    assert job.job_title == "QA Engineer"
    assert job.location == "Pune"
    assert job.work_mode == "Hybrid"
    assert job.raw_job_description == "raw JD text"
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(job)


@pytest.mark.asyncio
async def test_service_save_delegates_to_repository() -> None:
    repo = MagicMock()
    expected = MagicMock()
    repo.save = AsyncMock(return_value=expected)
    service = JobService(repo)
    profile = _profile()
    result = await service.save_analyzed_job(profile, "raw")
    assert result is expected
    repo.save.assert_awaited_once_with(profile, "raw")


@pytest.mark.asyncio
async def test_service_get_job() -> None:
    repo = MagicMock()
    job_id = uuid4()
    repo.get_by_id = AsyncMock(return_value=None)
    service = JobService(repo)
    assert await service.get_job(job_id) is None
    repo.get_by_id.assert_awaited_once_with(job_id)
