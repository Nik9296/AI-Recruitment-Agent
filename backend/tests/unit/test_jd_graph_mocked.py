import pytest

from app.agents.jd_agent.graph import analyze_job_description, compile_jd_graph
from app.core.exceptions import JDAnalysisError
from app.models.enums import EmploymentType, WorkMode

VALID_EXTRACTION = {
    "title": "software engineer",
    "experience": {"min_years": None, "max_years": None, "raw": "3-5 years"},
    "location": {
        "raw": "Bangalore",
        "city": "Bangalore",
        "state": None,
        "country": "India",
        "is_remote": False,
    },
    "work_mode": "hybrid",
    "employment_type": "full time",
    "must_have_skills": ["python", "k8s"],
    "preferred_skills": ["go"],
    "education": ["Bachelor's in CS"],
    "education_level": "bachelors",
    "responsibilities": ["Build APIs"],
    "keywords": ["Python"],
    "confidence": 0.8,
    "extraction_notes": [],
}


async def _valid_extract(_raw_jd: str) -> dict:
    return dict(VALID_EXTRACTION)


async def _empty_title_extract(_raw_jd: str) -> dict:
    payload = dict(VALID_EXTRACTION)
    payload["title"] = ""
    return payload


async def _valid_repair(_raw_jd: str, _previous: dict, _errors: list[str]) -> dict:
    return dict(VALID_EXTRACTION)


async def _bad_repair(_raw_jd: str, _previous: dict, _errors: list[str]) -> dict:
    payload = dict(VALID_EXTRACTION)
    payload["title"] = ""
    return payload


async def test_graph_extract_normalize_validate() -> None:
    graph = compile_jd_graph(extractor=_valid_extract, repairer=_bad_repair)
    result = await graph.ainvoke(
        {
            "raw_jd": "We need a software engineer with 3-5 years...",
            "raw_extraction": None,
            "analyzed_jd": None,
            "errors": [],
            "repair_attempts": 0,
        }
    )
    analyzed = result["analyzed_jd"]
    assert analyzed is not None
    assert analyzed.title == "Software Engineer"
    assert analyzed.experience.min_years == 3
    assert analyzed.experience.max_years == 5
    assert "Kubernetes" in analyzed.must_have_skills
    assert analyzed.work_mode is WorkMode.HYBRID
    assert analyzed.employment_type is EmploymentType.FULL_TIME
    assert result["errors"] == []


async def test_graph_repair_path_recovers_invalid_title() -> None:
    graph = compile_jd_graph(extractor=_empty_title_extract, repairer=_valid_repair)
    result = await graph.ainvoke(
        {
            "raw_jd": "Software Engineer role in Bangalore.",
            "raw_extraction": None,
            "analyzed_jd": None,
            "errors": [],
            "repair_attempts": 0,
        }
    )
    assert result["analyzed_jd"] is not None
    assert result["analyzed_jd"].title == "Software Engineer"
    assert result["repair_attempts"] == 1


async def test_graph_failed_repair_leaves_errors() -> None:
    graph = compile_jd_graph(extractor=_empty_title_extract, repairer=_bad_repair)
    result = await graph.ainvoke(
        {
            "raw_jd": "Unknown role",
            "raw_extraction": None,
            "analyzed_jd": None,
            "errors": [],
            "repair_attempts": 0,
        }
    )
    assert result["analyzed_jd"] is None
    assert result["repair_attempts"] == 1
    assert result["errors"]


async def test_analyze_job_description_raises_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    graph = compile_jd_graph(extractor=_empty_title_extract, repairer=_bad_repair)
    monkeypatch.setattr("app.agents.jd_agent.graph.get_compiled_jd_graph", lambda: graph)
    with pytest.raises(JDAnalysisError):
        await analyze_job_description("This is a job description that cannot be parsed well.")
