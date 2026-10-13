from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.graphs.recruitment import RecruitmentPipeline
from app.models.match import MatchResult
from app.models.ranking import RankedCandidate
from app.models.sourcing import SourcedCandidateRef, SourcingResult


def _match(job_id, candidate_id) -> MatchResult:
    return MatchResult(
        candidate_id=candidate_id,
        job_id=job_id,
        overall_score=0.8,
        required_skill_score=0.8,
        preferred_skill_score=0.5,
        experience_score=1.0,
        title_similarity_score=0.9,
        education_score=0.7,
        project_score=0.6,
        location_score=1.0,
        semantic_score=0.5,
        matched_requirements=["Required skill: Python"],
        missing_requirements=[],
        explanation="Deterministic match. This is not a hiring decision.",
        confidence=0.8,
        generated_at=datetime.now(UTC),
    )


def _candidate_row(candidate_id):
    row = MagicMock()
    row.id = candidate_id
    row.full_name = "Rahul Sharma"
    row.email = "rahul@example.com"
    row.phone = None
    row.location = "Hyderabad"
    row.current_job_title = "ML Engineer"
    row.total_experience_years = 6
    row.skills = ["Python"]
    row.technical_skills = ["Python"]
    row.soft_skills = []
    row.education = []
    row.certifications = []
    row.companies = []
    row.previous_roles = []
    row.projects = []
    row.achievements = []
    row.industries = []
    row.notice_period = None
    row.availability = None
    row.work_authorization = None
    row.resume_summary = None
    return row


def _job_row():
    row = MagicMock()
    row.job_title = "AI/ML Engineer"
    row.experience_min = 3
    row.experience_max = 8
    row.location = "Hyderabad"
    row.work_mode = "Hybrid"
    row.employment_type = "Full-time"
    row.must_have_skills = ["Python"]
    row.preferred_skills = []
    row.education = []
    row.responsibilities = []
    row.keywords = []
    return row


@pytest.mark.asyncio
async def test_pipeline_records_shortlist_and_stops_before_outreach() -> None:
    job_id = uuid4()
    candidate_id = uuid4()
    sourcing = MagicMock()
    sourcing.source_job = AsyncMock(
        return_value=SourcingResult(
            job_title="AI/ML Engineer",
            candidates=[SourcedCandidateRef(candidate_id=candidate_id)],
            invented_candidates=False,
        )
    )
    recruiter = MagicMock()
    recruiter.record_shortlist = AsyncMock(return_value=MagicMock())
    candidates = MagicMock()
    candidates.get_by_id = AsyncMock(return_value=_candidate_row(candidate_id))
    jobs = MagicMock()
    jobs.get_job = AsyncMock(return_value=_job_row())
    matching = MagicMock()
    matching.match.return_value = _match(job_id, candidate_id)
    pipeline = RecruitmentPipeline(
        sourcing,
        recruiter,
        candidates,
        jobs,
        matching_agent=matching,
    )
    state = await pipeline.run(job_id)
    assert state["sourced_count"] == 1
    assert state["matched_count"] == 1
    assert state["ranked_count"] == 1
    assert state["shortlist_recorded"] is True
    assert state["outreach_sent"] is False
    assert state["hired"] is False
    recruiter.record_shortlist.assert_awaited_once()
    ranked = recruiter.record_shortlist.await_args.args[1]
    assert isinstance(ranked[0], RankedCandidate)


@pytest.mark.asyncio
async def test_pipeline_missing_job_does_not_hire_or_email() -> None:
    job_id = uuid4()
    sourcing = MagicMock()
    sourcing.source_job = AsyncMock(return_value=None)
    recruiter = MagicMock()
    recruiter.record_shortlist = AsyncMock()
    pipeline = RecruitmentPipeline(
        sourcing, recruiter, MagicMock(), MagicMock()
    )
    state = await pipeline.run(job_id)
    assert "Job not found" in state["errors"]
    assert state["outreach_sent"] is False
    assert state["hired"] is False
    recruiter.record_shortlist.assert_not_called()
