"""Score predicted JobProfile fields against labeled expectations."""

from __future__ import annotations

from typing import Any

from app.models.job import JobProfile
from app.utils.skills import canonicalize_skill

LIST_FIELDS = (
    "must_have_skills",
    "preferred_skills",
    "education",
    "responsibilities",
    "keywords",
)


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def score_title(predicted: str | None, expected: str | None) -> bool:
    if not expected:
        return True
    if not predicted:
        return False
    return _norm(expected) in _norm(predicted) or _norm(predicted) in _norm(expected)


def score_optional_text(predicted: str | None, expected: str | None) -> bool:
    if expected is None:
        return predicted is None
    if predicted is None:
        return False
    return _norm(expected) in _norm(predicted)


def score_enum(predicted: Any, expected: str | None) -> bool:
    if expected is None:
        return predicted is None
    if predicted is None:
        return False
    return _norm(predicted) == _norm(expected)


def score_number(predicted: float | None, expected: float | None) -> bool:
    if expected is None:
        return predicted is None
    if predicted is None:
        return False
    return float(predicted) == float(expected)


def score_list(predicted: list[str], expected: list[str]) -> tuple[bool, float]:
    if not expected:
        return True, 1.0
    expected_keys = {canonicalize_skill(item).lower() for item in expected}
    predicted_keys = {canonicalize_skill(item).lower() for item in predicted}
    matched = 0
    for item in expected_keys:
        if any(item in pred or pred in item for pred in predicted_keys):
            matched += 1
    recall = matched / len(expected_keys)
    return recall >= 0.6, recall


def score_profile(profile: JobProfile, expected: dict[str, Any]) -> dict[str, Any]:
    field_scores: dict[str, bool] = {
        "title": score_title(profile.job_title, expected.get("job_title")),
        "experience_min": score_number(
            profile.experience_min, expected.get("experience_min")
        ),
        "experience_max": score_number(
            profile.experience_max, expected.get("experience_max")
        ),
        "location": score_optional_text(profile.location, expected.get("location")),
        "work_mode": score_enum(profile.work_mode, expected.get("work_mode")),
        "employment_type": score_enum(
            profile.employment_type, expected.get("employment_type")
        ),
    }
    list_recall: dict[str, float] = {}
    for field in LIST_FIELDS:
        ok, recall = score_list(getattr(profile, field), expected.get(field) or [])
        field_scores[field] = ok
        list_recall[field] = recall
    passed = sum(1 for ok in field_scores.values() if ok)
    return {
        "field_scores": field_scores,
        "list_recall": list_recall,
        "passed_fields": passed,
        "total_fields": len(field_scores),
        "case_pass": passed == len(field_scores),
        "accuracy": passed / len(field_scores),
    }
