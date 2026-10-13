from app.agents.jd_agent.normalizer import (
    map_employment_type,
    map_work_mode,
    normalize_extraction,
    normalize_title,
    parse_experience,
)
from app.models.enums import EmploymentType, WorkMode


def test_skill_aliases_and_disjoint_preferred() -> None:
    result = normalize_extraction(
        {
            "title": "senior software engineer",
            "must_have_skills": ["python", "k8s", "js"],
            "preferred_skills": ["Python", "go", "react.js"],
            "keywords": ["Backend"],
        }
    )
    assert result["must_have_skills"] == ["Python", "Kubernetes", "JavaScript"]
    assert result["preferred_skills"] == ["Go", "React"]
    assert "python" in result["keywords"]
    assert "kubernetes" in result["keywords"]
    assert "backend" in result["keywords"]


def test_experience_range_from_raw() -> None:
    notes: list[str] = []
    min_years, max_years = parse_experience("3-5 years", None, None, notes)
    assert min_years == 3
    assert max_years == 5


def test_experience_plus_from_raw() -> None:
    notes: list[str] = []
    min_years, max_years = parse_experience("5+ years of experience", None, None, notes)
    assert min_years == 5
    assert max_years is None


def test_experience_from_seniority_term() -> None:
    notes: list[str] = []
    min_years, max_years = parse_experience("Senior engineer", None, None, notes)
    assert min_years == 5
    assert max_years == 8
    assert notes


def test_intern_experience_from_raw() -> None:
    result = normalize_extraction(
        {
            "title": "software intern",
            "experience": {"raw": "Internship for freshers"},
        }
    )
    assert result["experience"]["min_years"] == 0
    assert result["experience"]["max_years"] == 1


def test_work_mode_synonyms() -> None:
    assert map_work_mode("WFH") is WorkMode.REMOTE
    assert map_work_mode("in-office") is WorkMode.ONSITE
    assert map_work_mode("hybrid") is WorkMode.HYBRID
    assert map_employment_type("full time") is EmploymentType.FULL_TIME
    assert map_employment_type("contractor") is EmploymentType.CONTRACT


def test_remote_location_sets_flag_and_mode() -> None:
    result = normalize_extraction(
        {
            "title": "Data Analyst",
            "location": {"raw": "Remote, anywhere"},
            "work_mode": "unknown",
        }
    )
    assert result["location"]["is_remote"] is True
    assert result["work_mode"] is WorkMode.REMOTE


def test_title_case_conservatively() -> None:
    assert normalize_title("senior software engineer") == "Senior Software Engineer"
    assert normalize_title("Senior Software Engineer") == "Senior Software Engineer"
    assert "AI" in normalize_title("ai engineer")
