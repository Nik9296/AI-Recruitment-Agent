import pytest
from pydantic import ValidationError

from app.models.enums import EmploymentType, WorkMode
from app.models.job_description import AnalyzedJobDescription


def _base(**overrides):
    payload = {
        "title": "Backend Engineer",
        "experience": {"min_years": 2, "max_years": 4, "raw": "2-4 years"},
        "location": {"raw": "Pune", "city": "Pune", "is_remote": False},
        "work_mode": WorkMode.ONSITE,
        "employment_type": EmploymentType.FULL_TIME,
        "must_have_skills": ["Python", "python", "  SQL  "],
        "preferred_skills": ["Python", "AWS"],
        "education": ["B.Tech"],
        "responsibilities": ["Ship features"],
        "keywords": ["Python", "API"],
        "confidence": 1.4,
        "extraction_notes": ["", "ok"],
    }
    payload.update(overrides)
    return payload


def test_valid_model_normalizes_lists_and_clamps_confidence() -> None:
    model = AnalyzedJobDescription.model_validate(_base())
    assert model.must_have_skills == ["Python", "SQL"]
    assert model.preferred_skills == ["AWS"]
    assert model.keywords == ["python", "api"]
    assert model.confidence == 1.0
    assert model.extraction_notes == ["ok"]


def test_empty_title_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AnalyzedJobDescription.model_validate(_base(title=" "))


def test_title_too_short_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AnalyzedJobDescription.model_validate(_base(title="A"))


def test_experience_min_greater_than_max_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AnalyzedJobDescription.model_validate(
            _base(experience={"min_years": 8, "max_years": 3, "raw": "8-3"})
        )


def test_experience_out_of_bounds_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AnalyzedJobDescription.model_validate(
            _base(experience={"min_years": 51, "max_years": None, "raw": "51 years"})
        )


def test_missing_title_is_rejected() -> None:
    payload = _base()
    payload.pop("title")
    with pytest.raises(ValidationError):
        AnalyzedJobDescription.model_validate(payload)
