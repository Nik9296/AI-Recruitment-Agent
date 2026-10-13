from datetime import UTC
from unittest.mock import MagicMock
from uuid import uuid4

from app.agents.matching_agent import MatchingAgent, SCORE_WEIGHTS
from app.models.candidate import CandidateProfile
from app.models.job import JobProfile, WorkMode
from app.models.match import MatchResult


def _embedder(job_vec=(1.0, 0.0), cand_vec=(1.0, 0.0)) -> MagicMock:
    embedder = MagicMock()
    embedder.embed_documents.return_value = [list(job_vec), list(cand_vec)]
    return embedder


def _job(**overrides) -> JobProfile:
    payload = {
        "job_title": "Senior Backend Engineer",
        "experience_min": 4,
        "experience_max": 8,
        "location": "Bengaluru",
        "work_mode": WorkMode.HYBRID,
        "must_have_skills": ["Python", "FastAPI", "PostgreSQL"],
        "preferred_skills": ["Kubernetes", "AWS"],
        "education": ["Bachelor's in Computer Science"],
        "responsibilities": ["Design APIs"],
        "keywords": ["Python", "API"],
    }
    payload.update(overrides)
    return JobProfile(**payload)


def _candidate(**overrides) -> CandidateProfile:
    payload = {
        "candidate_id": uuid4(),
        "full_name": "Priya Shah",
        "email": "priya.shah@example.com",
        "current_job_title": "Backend Engineer",
        "total_experience_years": 5,
        "location": "Bengaluru, India",
        "technical_skills": ["Python", "FastAPI", "Postgres", "k8s", "AWS"],
        "skills": ["Python", "FastAPI", "PostgreSQL", "Kubernetes", "AWS"],
        "education": [
            {
                "institution": "RV College",
                "degree": "Bachelor's",
                "field": "Computer Science",
            }
        ],
        "previous_roles": [{"title": "Backend Engineer", "company": "Nimbus"}],
        "projects": [
            {
                "name": "Order API",
                "description": "FastAPI services",
                "technologies": ["Python", "PostgreSQL"],
            }
        ],
        "availability": "Immediate",
        "work_authorization": "Indian citizen",
    }
    payload.update(overrides)
    return CandidateProfile(**payload)


def test_strong_match_scores_high() -> None:
    job_id = uuid4()
    candidate = _candidate()
    result = MatchingAgent(embedder=_embedder()).match(
        candidate, _job(), job_id=job_id
    )
    assert isinstance(result, MatchResult)
    assert result.candidate_id == candidate.candidate_id
    assert result.job_id == job_id
    assert result.overall_score >= 0.8
    assert result.required_skill_score == 1.0
    assert result.preferred_skill_score == 1.0
    assert result.experience_score == 1.0
    assert result.location_score == 1.0
    assert result.generated_at.tzinfo is UTC
    assert any("Python" in item for item in result.matched_requirements)
    assert result.missing_requirements == []
    assert "hiring decision" in result.explanation.lower()


def test_missing_required_skills_are_listed_but_not_rejected() -> None:
    result = MatchingAgent(embedder=_embedder()).match(
        _candidate(technical_skills=["Excel"], skills=["Excel"], projects=[]),
        _job(),
    )
    assert result.required_skill_score < 0.4
    assert any("Python" in item for item in result.missing_requirements)
    assert result.overall_score < 0.75
    assert 0 <= result.overall_score <= 1


def test_missing_experience_is_neutral_not_a_reject() -> None:
    result = MatchingAgent(embedder=_embedder()).match(
        _candidate(total_experience_years=None), _job()
    )
    assert result.experience_score == 0.5
    assert result.overall_score > 0
    assert not any("minimum" in item.lower() for item in result.missing_requirements)


def test_under_experience_is_explainable_gap() -> None:
    result = MatchingAgent(embedder=_embedder()).match(
        _candidate(total_experience_years=2), _job(experience_min=5, experience_max=None)
    )
    assert result.experience_score < 0.5
    assert any("Experience" in item for item in result.missing_requirements)


def test_missing_education_is_not_scored_zero() -> None:
    result = MatchingAgent(embedder=_embedder()).match(
        _candidate(education=[]), _job()
    )
    assert result.education_score == 0.5
    assert result.overall_score > 0


def test_remote_job_does_not_penalize_different_city() -> None:
    result = MatchingAgent(embedder=_embedder()).match(
        _candidate(location="Pune"),
        _job(work_mode=WorkMode.REMOTE, location="Bengaluru"),
    )
    assert result.location_score == 1.0


def test_empty_job_requirements_do_not_fail_required_skills() -> None:
    result = MatchingAgent(embedder=_embedder()).match(
        _candidate(),
        _job(must_have_skills=[], preferred_skills=[], education=[]),
    )
    assert result.required_skill_score == 1.0
    assert result.preferred_skill_score == 1.0
    assert result.education_score == 1.0


def test_semantic_signal_cannot_override_required_skill_gaps() -> None:
    aligned = MatchingAgent(embedder=_embedder((1, 0), (1, 0))).match(
        _candidate(technical_skills=["Excel"], skills=["Excel"], projects=[]),
        _job(),
    )
    assert aligned.semantic_score == 1.0
    assert aligned.required_skill_score < 0.4
    assert aligned.overall_score < 0.75
    assert aligned.overall_score != aligned.semantic_score


def test_unavailable_embeddings_are_neutral() -> None:
    embedder = MagicMock()
    embedder.embed_documents.side_effect = RuntimeError("no embeddings")
    result = MatchingAgent(embedder=embedder).match(_candidate(), _job())
    assert result.semantic_score == 0.5
    assert "neutral" in result.explanation.lower() or "unused" in result.explanation.lower()


def test_title_similarity_for_related_titles() -> None:
    result = MatchingAgent(embedder=_embedder()).match(
        _candidate(current_job_title="Backend Engineer"),
        _job(job_title="Senior Backend Engineer"),
    )
    assert result.title_similarity_score >= 0.5


def test_work_authorization_and_name_are_not_ranking_signals() -> None:
    agent = MatchingAgent(embedder=_embedder())
    first = agent.match(_candidate(work_authorization="Indian citizen"), _job())
    second = agent.match(
        _candidate(
            full_name="Alex Example",
            work_authorization="US citizen",
            email="alex@example.com",
        ),
        _job(),
    )
    assert first.overall_score == second.overall_score
    assert first.required_skill_score == second.required_skill_score
    combined = first.explanation + second.explanation
    assert "Priya" not in combined
    assert "Alex" not in combined
    assert "citizen" not in combined.lower()
    assert "gender" not in combined.lower()
    assert "nationality" not in combined.lower()
    job_text = " ".join(call.args[0][0] for call in agent._embedder.embed_documents.call_args_list)
    cand_text = " ".join(call.args[0][1] for call in agent._embedder.embed_documents.call_args_list)
    assert "Priya" not in cand_text
    assert "citizen" not in cand_text.lower()
    assert "shah@example.com" not in cand_text


def test_preferred_skills_do_not_count_as_missing_requirements() -> None:
    result = MatchingAgent(embedder=_embedder()).match(
        _candidate(
            technical_skills=["Python", "FastAPI", "PostgreSQL"],
            skills=["Python", "FastAPI", "PostgreSQL"],
        ),
        _job(),
    )
    assert result.preferred_skill_score < 1.0
    assert not any("Preferred" in item for item in result.missing_requirements)


def test_project_relevance_uses_technologies() -> None:
    with_projects = MatchingAgent(embedder=_embedder()).match(_candidate(), _job())
    without_projects = MatchingAgent(embedder=_embedder()).match(
        _candidate(projects=[]), _job()
    )
    assert with_projects.project_score > without_projects.project_score
    assert without_projects.project_score == 0.5


def test_weights_are_deterministic_and_sum_to_one() -> None:
    assert abs(sum(SCORE_WEIGHTS.values()) - 1.0) < 1e-9
    assert SCORE_WEIGHTS["required_skill_score"] > SCORE_WEIGHTS["semantic_score"]
