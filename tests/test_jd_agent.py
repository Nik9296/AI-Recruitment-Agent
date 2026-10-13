from pathlib import Path
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.jd_agent import (
    EmptyJobDescriptionError,
    JDAgent,
    JDExtractionError,
)
from app.models.job import EmploymentType, JobProfile, WorkMode
from app.prompts.jd_prompt import JD_EXTRACTION_SYSTEM, build_jd_extraction_messages


def _agent() -> tuple[JDAgent, MagicMock]:
    llm = MagicMock()
    structured = MagicMock()
    llm.with_structured_output.return_value = structured
    return JDAgent(llm=llm), structured


def test_normal_technical_jd() -> None:
    agent, structured = _agent()
    structured.invoke.return_value = {
        "job_title": "Senior Backend Engineer",
        "experience_min": 5,
        "experience_max": 8,
        "location": "Bengaluru, India",
        "work_mode": "On-site",
        "employment_type": "Full-time",
        "must_have_skills": ["Python", "k8s", "js"],
        "preferred_skills": ["Go"],
        "education": ["Bachelor's in CS"],
        "responsibilities": ["Design APIs"],
        "keywords": ["python", "k8s"],
    }
    jd = (
        "Senior Backend Engineer in Bengaluru. Full-time, on-site. "
        "5-8 years. Must have Python, k8s, JS. Preferred: Go. "
        "Bachelor's in CS. Design APIs."
    )
    profile = agent.analyze(jd)
    assert profile.job_title == "Senior Backend Engineer"
    assert profile.location == "Bengaluru, India"
    assert profile.work_mode is WorkMode.ON_SITE
    assert profile.employment_type is EmploymentType.FULL_TIME
    assert profile.must_have_skills == ["Python", "Kubernetes", "JavaScript"]
    assert profile.preferred_skills == ["Go"]
    assert "Kubernetes" in profile.keywords
    structured.invoke.assert_called_once()


def test_jd_with_missing_location() -> None:
    agent, structured = _agent()
    structured.invoke.return_value = JobProfile(
        job_title="Product Manager",
        experience_min=6,
        location=None,
        work_mode="Hybrid",
        employment_type="Full-time",
        must_have_skills=["SQL"],
    )
    profile = agent.analyze(
        "Product Manager, hybrid, full-time, 6 years. Must have SQL. "
        "Location is not specified."
    )
    assert profile.job_title == "Product Manager"
    assert profile.location is None


def test_jd_with_missing_experience() -> None:
    agent, structured = _agent()
    structured.invoke.return_value = {
        "job_title": "Frontend Engineer",
        "experience_min": None,
        "experience_max": None,
        "location": "Mumbai",
        "must_have_skills": ["React"],
    }
    profile = agent.analyze(
        "Frontend Engineer in Mumbai. Must have React. Experience not listed."
    )
    assert profile.experience_min is None
    assert profile.experience_max is None
    assert profile.must_have_skills == ["React"]


def test_jd_with_two_plus_years() -> None:
    agent, structured = _agent()
    structured.invoke.return_value = {
        "job_title": "Data Engineer",
        "experience_min": 2,
        "experience_max": None,
        "work_mode": "Remote",
        "employment_type": "Contract",
        "must_have_skills": ["SQL"],
    }
    profile = agent.analyze(
        "Data Engineer, remote contract. Experience: 2+ years. Required: SQL."
    )
    assert profile.experience_min == 2
    assert profile.experience_max is None


def test_jd_with_one_to_three_years() -> None:
    agent, structured = _agent()
    structured.invoke.return_value = {
        "job_title": "QA Engineer",
        "experience_min": 1,
        "experience_max": 3,
        "must_have_skills": ["Selenium"],
    }
    profile = agent.analyze("QA Engineer with 1-3 years. Must have Selenium.")
    assert profile.experience_min == 1
    assert profile.experience_max == 3


def test_fresher_jd() -> None:
    agent, structured = _agent()
    structured.invoke.return_value = {
        "job_title": "Software Engineering Intern",
        "experience_min": 0,
        "experience_max": 1,
        "employment_type": "Internship",
        "must_have_skills": ["Python"],
    }
    profile = agent.analyze(
        "Software Engineering Intern for freshers. Internship. Python."
    )
    assert profile.experience_min == 0
    assert profile.experience_max == 1
    assert profile.employment_type is EmploymentType.INTERNSHIP


def test_must_have_and_preferred_skills() -> None:
    agent, structured = _agent()
    structured.invoke.return_value = {
        "job_title": "Frontend Engineer",
        "must_have_skills": ["HTML", "CSS", "TypeScript"],
        "preferred_skills": ["Next.js", "GraphQL", "TypeScript"],
    }
    profile = agent.analyze(
        "Frontend Engineer. Required: HTML, CSS, TypeScript. "
        "Preferred: Next.js, GraphQL, TypeScript."
    )
    assert profile.must_have_skills == ["HTML", "CSS", "TypeScript"]
    assert profile.preferred_skills == ["Next.js", "GraphQL"]


def test_empty_jd_is_rejected() -> None:
    agent, structured = _agent()
    with pytest.raises(EmptyJobDescriptionError):
        agent.analyze("")
    with pytest.raises(EmptyJobDescriptionError):
        agent.analyze("   \n\t  ")
    structured.invoke.assert_not_called()


def test_malformed_unexpected_input() -> None:
    agent, structured = _agent()
    with pytest.raises(EmptyJobDescriptionError):
        agent.analyze(None)  # type: ignore[arg-type]
    with pytest.raises(EmptyJobDescriptionError):
        agent.analyze(123)  # type: ignore[arg-type]
    structured.invoke.return_value = "not-a-profile"
    with pytest.raises(JDExtractionError):
        agent.analyze("A job description that is long enough to send to the LLM.")
    structured.invoke.return_value = {"experience_min": 8, "experience_max": 2}
    with pytest.raises(JDExtractionError):
        agent.analyze("Another job description used to trigger validation failure.")
    structured.invoke.side_effect = RuntimeError("provider down")
    with pytest.raises(JDExtractionError, match="LLM extraction failed"):
        agent.analyze("Backend role with Python experience for a production team.")


FIXTURES = Path(__file__).parent / "fixtures" / "jds"

REQUIRED_INSTRUCTIONS = [
    "Never invent",
    "job_title",
    "experience_min",
    "experience_max",
    "2+ years",
    "1-3 years",
    "minimum 3 years",
    "5 years preferred",
    "freshers",
    "must_have_skills",
    "preferred_skills",
    "education",
    "responsibilities",
    "location",
    "work_mode",
    "employment_type",
    "keywords",
    "JobProfile",
]


def test_system_prompt_covers_extraction_rules() -> None:
    prompt = JD_EXTRACTION_SYSTEM.lower()
    for instruction in REQUIRED_INSTRUCTIONS:
        assert instruction.lower() in prompt


def test_build_messages_wraps_job_description() -> None:
    jd = "We need a Python engineer in Pune with 1-3 years experience."
    messages = build_jd_extraction_messages(jd)
    assert len(messages) == 2
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert jd in str(messages[1].content)
    assert "JobProfile" in str(messages[0].content)


def test_example_expected_outputs_are_valid_job_profiles() -> None:
    expected_files = sorted(FIXTURES.glob("*.expected.json"))
    assert expected_files, "expected JD fixture files are missing"
    for path in expected_files:
        profile = JobProfile.model_validate_json(path.read_text(encoding="utf-8"))
        assert isinstance(profile, JobProfile)


def test_example_jd_files_exist_for_each_expected_output() -> None:
    for expected in FIXTURES.glob("*.expected.json"):
        jd_path = expected.with_name(expected.name.replace(".expected.json", ".txt"))
        assert jd_path.exists(), f"missing JD text for {expected.name}"
        assert len(jd_path.read_text(encoding="utf-8").strip()) > 40
