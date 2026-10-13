from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1.routes.recruiter import get_recruiter_service, require_recruiter
from app.candidates.availability_filter import OpenToWorkStatus
from app.database.models.job_candidate import (
    REVIEW_APPROVED,
    REVIEW_ON_HOLD,
    REVIEW_PENDING,
)
from app.main import app
from app.models.ranking import RankedCandidate
from app.schemas.recruiter import (
    RecruiterCandidateProfile,
    RecruiterDashboard,
    RecruiterDecisionResponse,
    RecruiterJobSummary,
)
from app.services.recruiter_auth import RecruiterAuth, RecruiterSession, get_recruiter_auth
from app.services.recruiter_service import RecruiterService, _signal_from_candidate


def setup_function() -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[require_recruiter] = lambda: RecruiterSession(
        username="tester", expires_at=4102444800
    )


def teardown_function() -> None:
    app.dependency_overrides.clear()


def _auth() -> RecruiterAuth:
    return RecruiterAuth("recruiter", "review-pass", "session-secret", ttl_seconds=3600)


def _dashboard() -> RecruiterDashboard:
    job_id = uuid4()
    rahul = uuid4()
    return RecruiterDashboard(
        job_id=job_id,
        job_title="AI/ML Engineer",
        location="Hyderabad",
        work_mode="Hybrid",
        employment_type="Full-time",
        matched_count=127,
        open_to_work_count=42,
        pending_review_count=42,
        candidates=[
            {
                "candidate_id": rahul,
                "name": "Rahul Sharma",
                "match_percent": 94,
                "availability_status": "Open to Work",
                "eligible_for_outreach": True,
                "review_status": REVIEW_PENDING,
                "explanation": "Strong Python and TensorFlow match.",
                "matched_requirements": ["Required skill: Python"],
                "missing_requirements": [],
                "confidence": 0.9,
                "current_job_title": "ML Engineer",
                "location": "Hyderabad",
            }
        ],
    )


def test_login_issues_token() -> None:
    app.dependency_overrides.pop(require_recruiter, None)
    app.dependency_overrides[get_recruiter_auth] = _auth
    client = TestClient(app)
    response = client.post(
        "/api/v1/recruiter/login",
        json={"username": "recruiter", "password": "review-pass"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "recruiter"
    assert body["token_type"] == "bearer"
    assert "cannot send candidate email" in body["message"]
    me = client.get(
        "/api/v1/recruiter/me", headers={"Authorization": f"Bearer {body['token']}"}
    )
    assert me.status_code == 200
    assert me.json()["username"] == "recruiter"


def test_login_unconfigured() -> None:
    app.dependency_overrides.pop(require_recruiter, None)
    app.dependency_overrides[get_recruiter_auth] = lambda: RecruiterAuth(
        None, None, None
    )
    client = TestClient(app)
    response = client.post(
        "/api/v1/recruiter/login",
        json={"username": "recruiter", "password": "review-pass"},
    )
    assert response.status_code == 503


def test_login_rejects_bad_password() -> None:
    app.dependency_overrides.pop(require_recruiter, None)
    app.dependency_overrides[get_recruiter_auth] = _auth
    client = TestClient(app)
    response = client.post(
        "/api/v1/recruiter/login",
        json={"username": "recruiter", "password": "wrong"},
    )
    assert response.status_code == 401


def test_jobs_require_auth() -> None:
    app.dependency_overrides.pop(require_recruiter, None)
    app.dependency_overrides[get_recruiter_auth] = _auth
    client = TestClient(app)
    response = client.get("/api/v1/recruiter/jobs")
    assert response.status_code == 401


def test_recruiter_dashboard_endpoint() -> None:
    dashboard = _dashboard()
    service = MagicMock()
    service.get_dashboard = AsyncMock(return_value=dashboard)
    app.dependency_overrides[get_recruiter_service] = lambda: service
    client = TestClient(app)
    response = client.get(f"/api/v1/recruiter/jobs/{dashboard.job_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["job_title"] == "AI/ML Engineer"
    assert body["matched_count"] == 127
    assert body["open_to_work_count"] == 42
    assert body["candidates"][0]["name"] == "Rahul Sharma"
    assert body["candidates"][0]["match_percent"] == 94
    assert body["candidates"][0]["availability_status"] == "Open to Work"
    assert (
        body["candidates"][0]["requirement_match_source"]
        == "deterministic_requirement_matching"
    )
    assert body["candidates"][0]["explanation_source"] == "matching_agent"
    assert body["candidates"][0]["review_source"] == "recruiter"


def test_approve_does_not_send_email() -> None:
    job_id = uuid4()
    candidate_id = uuid4()
    service = MagicMock()
    service.decide = AsyncMock(
        return_value=RecruiterDecisionResponse(
            job_id=job_id,
            candidate_id=candidate_id,
            review_status=REVIEW_APPROVED,
            eligible_for_outreach=True,
            communications_sent=False,
            message="Candidate approved for recruiter review. No email was sent.",
        )
    )
    app.dependency_overrides[get_recruiter_service] = lambda: service
    client = TestClient(app)
    response = client.post(
        f"/api/v1/recruiter/jobs/{job_id}/candidates/{candidate_id}/approve"
    )
    assert response.status_code == 200
    assert "No email was sent" in response.json()["message"]
    assert response.json()["communications_sent"] is False
    service.decide.assert_awaited_once()


def test_reject_endpoint() -> None:
    job_id = uuid4()
    candidate_id = uuid4()
    service = MagicMock()
    service.decide = AsyncMock(
        return_value=RecruiterDecisionResponse(
            job_id=job_id,
            candidate_id=candidate_id,
            review_status="rejected",
            eligible_for_outreach=True,
            message="Candidate rejected for recruiter review. No email was sent.",
        )
    )
    app.dependency_overrides[get_recruiter_service] = lambda: service
    client = TestClient(app)
    response = client.post(
        f"/api/v1/recruiter/jobs/{job_id}/candidates/{candidate_id}/reject"
    )
    assert response.status_code == 200
    assert response.json()["review_status"] == "rejected"


def test_hold_endpoint() -> None:
    job_id = uuid4()
    candidate_id = uuid4()
    service = MagicMock()
    service.decide = AsyncMock(
        return_value=RecruiterDecisionResponse(
            job_id=job_id,
            candidate_id=candidate_id,
            review_status=REVIEW_ON_HOLD,
            eligible_for_outreach=True,
            communications_sent=False,
            message="Candidate put on hold for recruiter review. No email was sent.",
        )
    )
    app.dependency_overrides[get_recruiter_service] = lambda: service
    client = TestClient(app)
    response = client.post(
        f"/api/v1/recruiter/jobs/{job_id}/candidates/{candidate_id}/hold"
    )
    assert response.status_code == 200
    assert response.json()["review_status"] == "on_hold"
    assert "No email was sent" in response.json()["message"]


def test_candidate_profile_endpoint() -> None:
    job_id = uuid4()
    candidate_id = uuid4()
    service = MagicMock()
    service.get_candidate_profile = AsyncMock(
        return_value=RecruiterCandidateProfile(
            job_id=job_id,
            job_title="AI/ML Engineer",
            candidate_id=candidate_id,
            name="Rahul Sharma",
            email="rahul.sharma@example.com",
            location="Hyderabad",
            current_job_title="ML Engineer",
            technical_skills=["Python"],
            skills=["Python"],
            availability_status="Open to Work",
            eligible_for_outreach=True,
            match_percent=94,
            matched_requirements=["Required skill: Python"],
            missing_requirements=[],
            explanation="Deterministic match plus semantic signal. Not a hiring decision.",
            confidence=0.9,
            review_status=REVIEW_PENDING,
            communications_sent=False,
        )
    )
    app.dependency_overrides[get_recruiter_service] = lambda: service
    client = TestClient(app)
    response = client.get(
        f"/api/v1/recruiter/jobs/{job_id}/candidates/{candidate_id}"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["requirement_match_source"] == "deterministic_requirement_matching"
    assert body["explanation_source"] == "matching_agent"
    assert body["review_source"] == "recruiter"
    assert body["communications_sent"] is False


def test_dashboard_404() -> None:
    service = MagicMock()
    service.get_dashboard = AsyncMock(return_value=None)
    app.dependency_overrides[get_recruiter_service] = lambda: service
    client = TestClient(app)
    response = client.get(f"/api/v1/recruiter/jobs/{uuid4()}")
    assert response.status_code == 404


def test_list_jobs_endpoint() -> None:
    dashboard = _dashboard()
    service = MagicMock()
    service.list_job_summaries = AsyncMock(
        return_value=[
            RecruiterJobSummary(
                job_id=dashboard.job_id,
                job_title=dashboard.job_title,
                location=dashboard.location,
                matched_count=127,
                open_to_work_count=42,
                pending_review_count=42,
            )
        ]
    )
    app.dependency_overrides[get_recruiter_service] = lambda: service
    client = TestClient(app)
    response = client.get("/api/v1/recruiter/jobs")
    assert response.status_code == 200
    body = response.json()
    assert body[0]["job_title"] == "AI/ML Engineer"
    assert body[0]["matched_count"] == 127
    assert body[0]["open_to_work_count"] == 42


def test_openapi_documents_recruiter_routes() -> None:
    client = TestClient(app)
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/recruiter/login" in paths
    assert "/api/v1/recruiter/jobs" in paths
    assert "/api/v1/recruiter/jobs/{job_id}" in paths
    assert "/api/v1/recruiter/jobs/{job_id}/candidates/{candidate_id}" in paths
    assert "/api/v1/recruiter/jobs/{job_id}/candidates/{candidate_id}/approve" in paths
    assert "/api/v1/recruiter/jobs/{job_id}/candidates/{candidate_id}/reject" in paths
    assert "/api/v1/recruiter/jobs/{job_id}/candidates/{candidate_id}/hold" in paths
    assert "/api/v1/recruiter/jobs/{job_id}/candidates/{candidate_id}/workflow" in paths
    assert (
        "/api/v1/recruiter/jobs/{job_id}/candidates/{candidate_id}/outreach-handoff"
        in paths
    )
    assert "/api/v1/recruiter/jobs/{job_id}/candidates/{candidate_id}/outreach" in paths
    assert (
        "/api/v1/recruiter/jobs/{job_id}/candidates/{candidate_id}/outreach/send"
        in paths
    )


@pytest.mark.asyncio
async def test_service_dashboard_uses_explicit_open_to_work_only() -> None:
    job_id = uuid4()
    open_id = uuid4()
    unknown_id = uuid4()
    job = MagicMock()
    job.id = job_id
    job.job_title = "AI/ML Engineer"
    job.location = "Hyderabad"
    job.work_mode = "Hybrid"
    job.employment_type = "Full-time"
    job.experience_min = 3
    job.experience_max = None
    job.must_have_skills = ["Python"]
    job.preferred_skills = []
    job.education = []
    job.responsibilities = []
    open_row = MagicMock(
        candidate_id=open_id,
        overall_score=0.94,
        review_status=REVIEW_PENDING,
        explanation="Strong match.",
        matched_requirements=["Required skill: Python"],
        missing_requirements=[],
        confidence=0.9,
    )
    unknown_row = MagicMock(
        candidate_id=unknown_id,
        overall_score=0.91,
        review_status=REVIEW_PENDING,
        explanation="Strong match.",
        matched_requirements=[],
        missing_requirements=[],
        confidence=0.8,
    )
    open_candidate = MagicMock(
        id=open_id,
        full_name="Rahul Sharma",
        current_job_title="ML Engineer",
        location="Hyderabad",
        open_to_work_status=OpenToWorkStatus.OPEN_TO_WORK,
        open_to_work_source="candidate_declaration",
        open_to_work_verified_at=datetime.now(UTC),
        resumes=[],
    )
    unknown_candidate = MagicMock(
        id=unknown_id,
        full_name="Hidden Candidate",
        current_job_title="ML Engineer",
        location="Pune",
        open_to_work_status="UNKNOWN",
        open_to_work_source=None,
        open_to_work_verified_at=None,
        resumes=[],
    )
    repo = MagicMock()
    repo.get_job = AsyncMock(return_value=job)
    repo.list_job_candidates = AsyncMock(return_value=[open_row, unknown_row])
    repo.get_candidate = AsyncMock(side_effect=[open_candidate, unknown_candidate])
    dashboard = await RecruiterService(repo).get_dashboard(job_id)
    assert dashboard is not None
    assert dashboard.matched_count == 2
    assert dashboard.open_to_work_count == 1
    assert dashboard.candidates[0].name == "Rahul Sharma"
    assert dashboard.candidates[0].match_percent == 94
    assert dashboard.candidates[0].eligible_for_outreach is True
    assert dashboard.candidates[1].eligible_for_outreach is False


@pytest.mark.asyncio
async def test_service_filters_and_sorts_shortlist() -> None:
    job_id = uuid4()
    job = MagicMock()
    job.id = job_id
    job.job_title = "AI/ML Engineer"
    job.location = "Hyderabad"
    job.work_mode = "Hybrid"
    job.employment_type = "Full-time"
    job.experience_min = 3
    job.experience_max = None
    job.must_have_skills = ["Python"]
    job.preferred_skills = []
    job.education = []
    job.responsibilities = []
    rahul_id = uuid4()
    amit_id = uuid4()
    rows = [
        MagicMock(
            candidate_id=rahul_id,
            overall_score=0.94,
            review_status=REVIEW_PENDING,
            explanation="ok",
            matched_requirements=["Required skill: Python"],
            missing_requirements=[],
            confidence=0.9,
        ),
        MagicMock(
            candidate_id=amit_id,
            overall_score=0.91,
            review_status=REVIEW_ON_HOLD,
            explanation="ok",
            matched_requirements=["Required skill: Python"],
            missing_requirements=["Required skill: TensorFlow"],
            confidence=0.8,
        ),
    ]
    rahul = MagicMock(
        id=rahul_id,
        full_name="Rahul Sharma",
        current_job_title="ML Engineer",
        location="Hyderabad",
        open_to_work_status=OpenToWorkStatus.OPEN_TO_WORK,
        open_to_work_source="candidate_declaration",
        open_to_work_verified_at=datetime.now(UTC),
        resumes=[],
    )
    amit = MagicMock(
        id=amit_id,
        full_name="Amit Patel",
        current_job_title="AI Engineer",
        location="Bengaluru",
        open_to_work_status=OpenToWorkStatus.OPEN_TO_WORK,
        open_to_work_source="candidate_declaration",
        open_to_work_verified_at=datetime.now(UTC),
        resumes=[],
    )
    repo = MagicMock()
    repo.get_job = AsyncMock(return_value=job)
    repo.list_job_candidates = AsyncMock(return_value=rows)
    repo.get_candidate = AsyncMock(side_effect=[rahul, amit, rahul, amit])
    named = await RecruiterService(repo).get_dashboard(job_id, query="amit")
    assert named is not None
    assert [row.name for row in named.candidates] == ["Amit Patel"]
    held = await RecruiterService(repo).get_dashboard(
        job_id, review_status="on_hold", sort="name", sort_dir="asc"
    )
    assert held is not None
    assert [row.name for row in held.candidates] == ["Amit Patel"]


def test_resume_notice_period_is_not_an_open_to_work_signal() -> None:
    candidate = MagicMock(
        open_to_work_status="UNKNOWN",
        open_to_work_source=None,
        open_to_work_verified_at=None,
        availability="Immediate",
        notice_period="30 days",
    )
    assert _signal_from_candidate(candidate) is None


@pytest.mark.asyncio
async def test_record_shortlist_delegates() -> None:
    repo = MagicMock()
    job = MagicMock()
    job.id = uuid4()
    job.job_title = "AI/ML Engineer"
    job.location = None
    job.work_mode = None
    job.employment_type = None
    job.experience_min = None
    job.experience_max = None
    job.must_have_skills = []
    job.preferred_skills = []
    job.education = []
    job.responsibilities = []
    repo.get_job = AsyncMock(return_value=job)
    repo.upsert_shortlist = AsyncMock()
    repo.list_job_candidates = AsyncMock(return_value=[])
    service = RecruiterService(repo)
    job_id = job.id
    ranked = [
        RankedCandidate(
            rank=1,
            candidate_id=uuid4(),
            job_id=job_id,
            overall_score=0.94,
            matched_requirements=[],
            missing_requirements=[],
            explanation="ok",
            confidence=0.9,
        )
    ]
    result = await service.record_shortlist(job_id, ranked)
    assert result is not None
    repo.upsert_shortlist.assert_awaited_once()


@pytest.mark.asyncio
async def test_decide_records_review_and_does_not_send_email() -> None:
    job_id = uuid4()
    candidate_id = uuid4()
    repo = MagicMock()
    repo.set_review_status = AsyncMock(return_value=MagicMock())
    repo.get_candidate = AsyncMock(
        return_value=MagicMock(
            id=candidate_id,
            open_to_work_status=OpenToWorkStatus.OPEN_TO_WORK,
            open_to_work_source="candidate_declaration",
            open_to_work_verified_at=datetime.now(UTC),
        )
    )
    result = await RecruiterService(repo).decide(
        job_id, candidate_id, REVIEW_APPROVED
    )
    assert result is not None
    assert result.review_status == REVIEW_APPROVED
    assert result.eligible_for_outreach is True
    assert result.communications_sent is False
    assert "No email was sent" in result.message
    repo.set_review_status.assert_awaited_once_with(
        job_id, candidate_id, REVIEW_APPROVED
    )
