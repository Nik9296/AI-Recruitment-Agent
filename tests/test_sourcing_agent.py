from uuid import uuid4

import pytest

from app.agents.sourcing_agent import (
    ExternalSourcingNotImplementedError,
    SourcingAgent,
)
from app.models.candidate import CandidateProfile
from app.models.job import JobProfile


def _job(**overrides) -> JobProfile:
    payload = {
        "job_title": "AI/ML Engineer",
        "location": "Hyderabad",
        "must_have_skills": ["Python", "TensorFlow"],
        "preferred_skills": ["PyTorch"],
    }
    payload.update(overrides)
    return JobProfile(**payload)


def _candidate(**overrides) -> CandidateProfile:
    payload = {
        "candidate_id": uuid4(),
        "full_name": "Rahul Sharma",
        "current_job_title": "ML Engineer",
        "technical_skills": ["Python", "TensorFlow"],
        "skills": ["Python", "TensorFlow"],
        "location": "Hyderabad",
    }
    payload.update(overrides)
    return CandidateProfile(**payload)


def test_plan_builds_must_have_and_preferred_queries() -> None:
    queries = SourcingAgent().plan(_job())
    labels = [query.label for query in queries]
    assert "must_have" in labels
    assert "preferred" in labels
    must = next(query for query in queries if query.label == "must_have")
    assert "Python" in must.skills
    assert must.job_title == "AI/ML Engineer"


def test_select_keeps_only_existing_overlapping_profiles() -> None:
    job = _job()
    kept = _candidate()
    skipped = _candidate(
        full_name="Unrelated",
        current_job_title="Accountant",
        technical_skills=["Excel"],
        skills=["Excel"],
    )
    missing_id = _candidate(candidate_id=None, full_name="No id")
    result = SourcingAgent().select(job, [kept, skipped, missing_id])
    assert result.invented_candidates is False
    assert result.external_providers_used == []
    assert [item.candidate_id for item in result.candidates] == [kept.candidate_id]
    assert "Python" in result.candidates[0].matched_query_skills


def test_select_does_not_invent_when_store_is_empty() -> None:
    result = SourcingAgent().select(_job(), [])
    assert result.candidates == []
    assert result.invented_candidates is False


def test_external_search_is_not_wired() -> None:
    with pytest.raises(ExternalSourcingNotImplementedError, match="not wired"):
        SourcingAgent().search_external(_job())
