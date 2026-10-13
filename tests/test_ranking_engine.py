from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.matching.ranking_engine import RankingEngine
from app.models.match import MatchResult
from app.models.ranking import RankedCandidate

JOB_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def _match(
    *,
    overall: float | None = 0.8,
    candidate_id: UUID | None = None,
    generated_offset: int = 0,
    explanation: str = "Deterministic match explanation.",
    matched: list[str] | None = None,
    missing: list[str] | None = None,
    confidence: float = 0.9,
    **scores: float,
) -> MatchResult:
    payload = {
        "required_skill_score": 0.8,
        "preferred_skill_score": 0.8,
        "experience_score": 0.8,
        "title_similarity_score": 0.8,
        "education_score": 0.8,
        "project_score": 0.8,
        "location_score": 0.8,
        "semantic_score": 0.8,
    }
    payload.update(scores)
    if overall is None:
        overall_score = 0.5
    else:
        overall_score = overall
    return MatchResult(
        candidate_id=candidate_id,
        job_id=JOB_ID,
        overall_score=overall_score,
        matched_requirements=matched or ["Required skill: Python"],
        missing_requirements=missing or [],
        explanation=explanation,
        confidence=confidence,
        generated_at=datetime(2026, 9, 17, tzinfo=UTC) + timedelta(seconds=generated_offset),
        **payload,
    )


def test_ten_candidates_are_ranked_descending() -> None:
    matches = [
        _match(overall=score, candidate_id=uuid4())
        for score in (0.11, 0.92, 0.44, 0.73, 0.28, 0.86, 0.55, 0.67, 0.39, 0.80)
    ]
    shortlist = RankingEngine().generate_shortlist(JOB_ID, matches)
    assert len(shortlist) == 10
    assert [row.rank for row in shortlist] == list(range(1, 11))
    scores = [row.overall_score for row in shortlist]
    assert scores == sorted(scores, reverse=True)
    assert all(isinstance(row, RankedCandidate) for row in shortlist)
    assert shortlist[0].overall_score == 0.92
    assert shortlist[-1].overall_score == 0.11
    assert all(row.job_id == JOB_ID for row in shortlist)
    assert all(row.explanation == "Deterministic match explanation." for row in shortlist)


def test_equal_scores_are_deterministic() -> None:
    low = UUID("00000000-0000-0000-0000-000000000001")
    high = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
    matches = [
        _match(overall=0.7, candidate_id=high, generated_offset=2),
        _match(overall=0.7, candidate_id=low, generated_offset=1),
    ]
    first = RankingEngine().generate_shortlist(JOB_ID, matches)
    second = RankingEngine().generate_shortlist(JOB_ID, list(reversed(matches)))
    assert [row.candidate_id for row in first] == [low, high]
    assert [row.candidate_id for row in second] == [low, high]
    assert [row.rank for row in first] == [1, 2]


def test_missing_overall_score_is_treated_as_incomplete_not_rejected() -> None:
    present = _match(overall=0.9, candidate_id=uuid4())
    incomplete = MatchResult.model_construct(
        candidate_id=uuid4(),
        job_id=JOB_ID,
        overall_score=None,
        required_skill_score=0.8,
        preferred_skill_score=0.8,
        experience_score=0.8,
        title_similarity_score=0.8,
        education_score=0.8,
        project_score=0.8,
        location_score=0.8,
        semantic_score=0.8,
        matched_requirements=["Required skill: Python"],
        missing_requirements=[],
        explanation="Incomplete overall score.",
        confidence=0.4,
        generated_at=datetime(2026, 9, 17, tzinfo=UTC),
    )
    shortlist = RankingEngine().generate_shortlist(JOB_ID, [present, incomplete])
    assert len(shortlist) == 2
    by_id = {row.candidate_id: row for row in shortlist}
    assert by_id[incomplete.candidate_id].overall_score == 0.5
    assert by_id[present.candidate_id].rank == 1
    assert "reject" not in by_id[incomplete.candidate_id].explanation.lower()


def test_empty_candidate_list() -> None:
    assert RankingEngine().generate_shortlist(JOB_ID, []) == []
    assert RankingEngine().sort_by_score([]) == []
    assert RankingEngine().apply_minimum_threshold([], 0.5) == []
    assert RankingEngine().get_top_candidates([], 5) == []


def test_threshold_filtering_keeps_explainability() -> None:
    matches = [
        _match(
            overall=0.9,
            candidate_id=uuid4(),
            explanation="Strong Python match.",
            matched=["Required skill: Python"],
            missing=[],
        ),
        _match(
            overall=0.4,
            candidate_id=uuid4(),
            explanation="Gaps: Required skill: Python.",
            matched=[],
            missing=["Required skill: Python"],
        ),
        _match(overall=0.7, candidate_id=uuid4()),
    ]
    engine = RankingEngine()
    filtered = engine.apply_minimum_threshold(matches, 0.7)
    assert {match.overall_score for match in filtered} == {0.9, 0.7}
    shortlist = engine.generate_shortlist(JOB_ID, matches, min_score=0.7)
    assert [row.overall_score for row in shortlist] == [0.9, 0.7]
    assert shortlist[0].explanation == "Strong Python match."
    assert shortlist[0].matched_requirements == ["Required skill: Python"]
    assert shortlist[1].missing_requirements == []


def test_get_top_n_candidates() -> None:
    matches = [
        _match(overall=score, candidate_id=uuid4())
        for score in (0.2, 0.9, 0.5, 0.8, 0.1)
    ]
    engine = RankingEngine()
    top = engine.get_top_candidates(matches, 3)
    assert [match.overall_score for match in top] == [0.9, 0.8, 0.5]
    shortlist = engine.generate_shortlist(JOB_ID, matches, top_n=2)
    assert [row.rank for row in shortlist] == [1, 2]
    assert [row.overall_score for row in shortlist] == [0.9, 0.8]
    assert engine.get_top_candidates(matches, 0) == []
    assert len(engine.get_top_candidates(matches, 50)) == 5


def test_configurable_weights_only_use_existing_match_scores() -> None:
    skills_strong = _match(
        overall=0.4,
        candidate_id=uuid4(),
        required_skill_score=1.0,
        semantic_score=0.0,
    )
    semantic_strong = _match(
        overall=0.4,
        candidate_id=uuid4(),
        required_skill_score=0.0,
        semantic_score=1.0,
    )
    default_order = RankingEngine().generate_shortlist(
        JOB_ID, [skills_strong, semantic_strong]
    )
    assert default_order[0].candidate_id < default_order[1].candidate_id or (
        default_order[0].overall_score == default_order[1].overall_score
    )
    skill_weighted = RankingEngine(
        weights={"required_skill_score": 1.0, "semantic_score": 0.0}
    ).generate_shortlist(JOB_ID, [skills_strong, semantic_strong])
    assert skill_weighted[0].candidate_id == skills_strong.candidate_id
    semantic_weighted = RankingEngine(
        weights={"required_skill_score": 0.0, "semantic_score": 1.0}
    ).generate_shortlist(JOB_ID, [skills_strong, semantic_strong])
    assert semantic_weighted[0].candidate_id == semantic_strong.candidate_id


def test_ranking_does_not_inspect_protected_or_contact_fields() -> None:
    source = RankingEngine.generate_shortlist.__code__.co_names
    blocked = {
        "full_name",
        "email",
        "phone",
        "gender",
        "race",
        "religion",
        "disability",
        "nationality",
        "marital",
        "age",
        "work_authorization",
        "send_email",
        "smtp",
    }
    assert not (blocked & set(source))


def test_sort_by_score_does_not_mutate_input() -> None:
    first = _match(overall=0.2, candidate_id=uuid4())
    second = _match(overall=0.9, candidate_id=uuid4())
    original = [first, second]
    ordered = RankingEngine().sort_by_score(original)
    assert original[0] is first
    assert ordered[0] is second
