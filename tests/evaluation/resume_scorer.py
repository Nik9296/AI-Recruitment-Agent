"""Score predicted CandidateProfile fields against labeled expectations."""

from __future__ import annotations

from typing import Any

from app.models.candidate import CandidateProfile, Certification, EducationEntry, Project
from app.utils.skills import canonicalize_skill

CORE_FIELDS = (
    "name",
    "skills",
    "experience",
    "education",
    "job_titles",
    "companies",
    "projects",
    "certifications",
    "location",
    "availability",
)


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def score_optional_text(predicted: str | None, expected: str | None) -> bool:
    if expected is None:
        return predicted is None
    if predicted is None:
        return False
    return _norm(expected) in _norm(predicted) or _norm(predicted) in _norm(expected)


def score_number(predicted: float | None, expected: float | None) -> bool:
    if expected is None:
        return predicted is None
    if predicted is None:
        return False
    return abs(float(predicted) - float(expected)) < 0.51


def score_list(predicted: list[str], expected: list[str]) -> tuple[bool, float]:
    if not expected:
        return True, 1.0
    expected_keys = {canonicalize_skill(item).lower() for item in expected if item}
    predicted_keys = {canonicalize_skill(item).lower() for item in predicted if item}
    if not expected_keys:
        return True, 1.0
    matched = 0
    for item in expected_keys:
        if any(item in pred or pred in item for pred in predicted_keys):
            matched += 1
    recall = matched / len(expected_keys)
    return recall >= 0.6, recall


def _education_terms(items: list[Any]) -> list[str]:
    terms: list[str] = []
    for item in items:
        if isinstance(item, EducationEntry):
            terms.extend([item.institution, item.degree, item.field])
        elif isinstance(item, dict):
            terms.extend(
                [item.get("institution"), item.get("degree"), item.get("field")]
            )
        elif item:
            terms.append(str(item))
    return [term for term in terms if term]


def _names_from(items: list[Any], model_cls: type, key: str) -> list[str]:
    names: list[str] = []
    for item in items:
        if isinstance(item, model_cls):
            names.append(getattr(item, key) or "")
        elif isinstance(item, dict):
            names.append(str(item.get(key) or item))
        else:
            names.append(str(item))
    return [name for name in names if name]


def _job_titles(profile: CandidateProfile) -> list[str]:
    titles: list[str] = []
    if profile.current_job_title:
        titles.append(profile.current_job_title)
    titles.extend(role.title for role in profile.previous_roles if role.title)
    return titles


def _classify_field(*, ok: bool, expected: Any, predicted: Any) -> str:
    expected_missing = expected in (None, [], "")
    predicted_missing = predicted in (None, [], "")
    if ok:
        return "passed"
    if not expected_missing and predicted_missing:
        return "missing"
    return "failed"


def score_profile(
    profile: CandidateProfile, expected: dict[str, Any]
) -> dict[str, Any]:
    predicted_skills = list(
        dict.fromkeys([*profile.technical_skills, *profile.skills])
    )
    predicted_titles = _job_titles(profile)
    predicted_projects = _names_from(profile.projects, Project, "name")
    predicted_certs = _names_from(profile.certifications, Certification, "name")
    predicted_education = _education_terms(profile.education)

    skills_ok, skills_recall = score_list(
        predicted_skills, expected.get("technical_skills") or []
    )
    edu_ok, edu_recall = score_list(
        predicted_education, _education_terms(expected.get("education") or [])
    )
    titles_ok, titles_recall = score_list(
        predicted_titles, expected.get("job_titles") or []
    )
    companies_ok, companies_recall = score_list(
        profile.companies, expected.get("companies") or []
    )
    projects_ok, projects_recall = score_list(
        predicted_projects, expected.get("projects") or []
    )
    certs_ok, certs_recall = score_list(
        predicted_certs, expected.get("certifications") or []
    )

    raw_checks: list[tuple[str, bool, Any, Any, float | None]] = [
        (
            "name",
            score_optional_text(profile.full_name, expected.get("full_name")),
            expected.get("full_name"),
            profile.full_name,
            None,
        ),
        (
            "skills",
            skills_ok,
            expected.get("technical_skills") or [],
            predicted_skills,
            skills_recall,
        ),
        (
            "experience",
            score_number(
                profile.total_experience_years,
                expected.get("total_experience_years"),
            ),
            expected.get("total_experience_years"),
            profile.total_experience_years,
            None,
        ),
        (
            "education",
            edu_ok,
            expected.get("education") or [],
            predicted_education,
            edu_recall,
        ),
        (
            "job_titles",
            titles_ok,
            expected.get("job_titles") or [],
            predicted_titles,
            titles_recall,
        ),
        (
            "companies",
            companies_ok,
            expected.get("companies") or [],
            profile.companies,
            companies_recall,
        ),
        (
            "projects",
            projects_ok,
            expected.get("projects") or [],
            predicted_projects,
            projects_recall,
        ),
        (
            "certifications",
            certs_ok,
            expected.get("certifications") or [],
            predicted_certs,
            certs_recall,
        ),
        (
            "location",
            score_optional_text(profile.location, expected.get("location")),
            expected.get("location"),
            profile.location,
            None,
        ),
        (
            "availability",
            score_optional_text(profile.availability, expected.get("availability")),
            expected.get("availability"),
            profile.availability,
            None,
        ),
    ]
    if "email" in expected:
        raw_checks.append(
            (
                "email",
                score_optional_text(profile.email, expected.get("email")),
                expected.get("email"),
                profile.email,
                None,
            )
        )
    if "phone" in expected:
        raw_checks.append(
            (
                "phone",
                score_optional_text(profile.phone, expected.get("phone")),
                expected.get("phone"),
                profile.phone,
                None,
            )
        )

    field_scores: dict[str, bool] = {}
    field_status: dict[str, str] = {}
    list_recall: dict[str, float] = {}
    passed_fields: list[str] = []
    failed_fields: list[str] = []
    missing_fields: list[str] = []

    for field, ok, expected_value, predicted_value, recall in raw_checks:
        field_scores[field] = ok
        if recall is not None:
            list_recall[field] = recall
        status = _classify_field(
            ok=ok, expected=expected_value, predicted=predicted_value
        )
        field_status[field] = status
        if status == "passed":
            passed_fields.append(field)
        elif status == "missing":
            missing_fields.append(field)
        else:
            failed_fields.append(field)

    passed = sum(1 for ok in field_scores.values() if ok)
    return {
        "field_scores": field_scores,
        "field_status": field_status,
        "passed_fields": passed_fields,
        "failed_fields": failed_fields,
        "missing_fields": missing_fields,
        "list_recall": list_recall,
        "passed_count": passed,
        "total_fields": len(field_scores),
        "case_pass": passed == len(field_scores),
        "accuracy": passed / len(field_scores),
    }
