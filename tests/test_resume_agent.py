import logging
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.resume_agent import (
    EmptyResumeTextError,
    ResumeAgent,
    ResumeExtractionError,
)
from app.models.candidate import CandidateProfile
from app.prompts.resume_prompt import (
    RESUME_EXTRACTION_SYSTEM,
    build_resume_extraction_messages,
)
from app.services.llm import LLMConfigurationError

SAMPLE_RESUME = """
Jane Candidate
jane.candidate@example.com
+91 98765 43210
Pune, India

Summary
Backend engineer with 6 years of experience.

Experience
Senior Backend Engineer, Acme Corp
2021 - Present
- Built APIs with Python and FastAPI

Software Engineer, Globex
2018 - 2021

Skills
Technical: Python, k8s, JS, FastAPI
Soft skills: Communication, Leadership

Education
B.Tech in Computer Science, IIT Bombay, 2014-2018

Certifications
AWS Certified Developer, Amazon, 2023

Projects
Hiring Platform - internal ATS using Python

Achievements
Reduced API latency 40%

Notice period: 30 days
Available: Immediate
Work authorization: Indian citizen
"""


def _agent() -> tuple[ResumeAgent, MagicMock]:
    llm = MagicMock()
    structured = MagicMock()
    llm.with_structured_output.return_value = structured
    return ResumeAgent(llm=llm), structured


def test_parse_distinguishes_skills_titles_companies_and_education() -> None:
    agent, structured = _agent()
    structured.invoke.return_value = {
        "full_name": "Jane Candidate",
        "email": "jane.candidate@example.com",
        "phone": "98765 43210",
        "location": "Pune, India",
        "current_job_title": "Senior Backend Engineer",
        "total_experience_years": 6,
        "technical_skills": ["Python", "k8s", "js", "FastAPI"],
        "soft_skills": ["Communication", "Leadership", "Python"],
        "skills": [],
        "education": [
            {
                "institution": "IIT Bombay",
                "degree": "B.Tech",
                "field": "Computer Science",
                "start_year": 2014,
                "end_year": 2018,
            }
        ],
        "certifications": [{"name": "AWS Certified Developer", "issuer": "Amazon", "year": 2023}],
        "companies": ["Acme Corp"],
        "previous_roles": [
            {
                "title": "Senior Backend Engineer",
                "company": "Acme Corp",
                "start_date": "2021",
                "end_date": "Present",
                "highlights": ["Built APIs with Python and FastAPI"],
            },
            {
                "title": "Software Engineer",
                "company": "Globex",
                "start_date": "2018",
                "end_date": "2021",
            },
        ],
        "projects": [{"name": "Hiring Platform", "technologies": ["Python"]}],
        "achievements": ["Reduced API latency 40%"],
        "notice_period": "30 days",
        "availability": "Immediate",
        "work_authorization": "Indian citizen",
    }
    profile = agent.parse(SAMPLE_RESUME)
    assert profile.full_name == "Jane Candidate"
    assert profile.current_job_title == "Senior Backend Engineer"
    assert profile.technical_skills == ["Python", "Kubernetes", "JavaScript", "FastAPI"]
    assert profile.soft_skills == ["Communication", "Leadership"]
    assert "Kubernetes" in profile.skills
    assert profile.companies == ["Acme Corp", "Globex"]
    assert [role.title for role in profile.previous_roles] == [
        "Senior Backend Engineer",
        "Software Engineer",
    ]
    assert profile.education[0].institution == "IIT Bombay"
    assert profile.certifications[0].name == "AWS Certified Developer"
    assert profile.projects[0].name == "Hiring Platform"
    assert profile.achievements == ["Reduced API latency 40%"]
    assert profile.total_experience_years == 6
    assert profile.notice_period == "30 days"
    assert profile.availability == "Immediate"
    assert profile.work_authorization == "Indian citizen"
    assert profile.candidate_id is None
    structured.invoke.assert_called_once()
    assert structured.invoke.call_args.args[0][0].content == RESUME_EXTRACTION_SYSTEM


def test_does_not_invent_identity_or_experience() -> None:
    agent, structured = _agent()
    structured.invoke.return_value = {
        "full_name": "Invented Person",
        "email": "invented@example.com",
        "phone": "1111111111",
        "location": "Atlantis",
        "current_job_title": "CEO",
        "total_experience_years": 10,
        "technical_skills": ["COBOL"],
        "notice_period": "90 days",
        "availability": "next month",
        "work_authorization": "H1B",
        "resume_summary": "World-famous executive with a secret clearance.",
    }
    sparse = "Python developer. Skills: Python, FastAPI."
    profile = agent.parse(sparse)
    assert profile.full_name is None
    assert profile.email is None
    assert profile.phone is None
    assert profile.location is None
    assert profile.current_job_title is None
    assert profile.total_experience_years is None
    assert profile.notice_period is None
    assert profile.availability is None
    assert profile.work_authorization is None
    assert profile.resume_summary is None
    assert "COBOL" not in profile.technical_skills
    assert profile.technical_skills == []


def test_experience_null_when_not_explicitly_stated() -> None:
    agent, structured = _agent()
    structured.invoke.return_value = {
        "full_name": "Jane Candidate",
        "total_experience_years": 8,
        "previous_roles": [
            {"title": "Engineer", "company": "Acme Corp", "start_date": "2018", "end_date": "2024"}
        ],
    }
    resume = (
        "Jane Candidate\nEngineer at Acme Corp, 2018-2024. Skills: Python.\n"
        "Dates are listed but total years of experience are not stated."
    )
    profile = agent.parse(resume)
    assert profile.total_experience_years is None


def test_fills_experience_from_explicit_statement_when_llm_omits_it() -> None:
    agent, structured = _agent()
    structured.invoke.return_value = {
        "full_name": "Jane Candidate",
        "total_experience_years": None,
        "technical_skills": ["Python"],
    }
    profile = agent.parse(
        "Jane Candidate\nBackend engineer with 6 years of experience. Python."
    )
    assert profile.total_experience_years == 6


def test_empty_resume_is_rejected() -> None:
    agent, structured = _agent()
    with pytest.raises(EmptyResumeTextError):
        agent.parse("")
    with pytest.raises(EmptyResumeTextError):
        agent.parse("   \n\t  ")
    with pytest.raises(EmptyResumeTextError):
        agent.parse(None)  # type: ignore[arg-type]
    structured.invoke.assert_not_called()


def test_malformed_llm_output_raises() -> None:
    agent, structured = _agent()
    structured.invoke.return_value = "not-a-profile"
    with pytest.raises(ResumeExtractionError):
        agent.parse(SAMPLE_RESUME)
    structured.invoke.return_value = {"email": "not-an-email"}
    with pytest.raises(ResumeExtractionError):
        agent.parse(SAMPLE_RESUME)
    structured.invoke.side_effect = RuntimeError("provider down")
    with pytest.raises(ResumeExtractionError, match="LLM extraction failed"):
        agent.parse(SAMPLE_RESUME)


def test_llm_configuration_error_is_reraised() -> None:
    agent, structured = _agent()
    structured.invoke.side_effect = LLMConfigurationError("GOOGLE_API_KEY is required")
    with pytest.raises(LLMConfigurationError):
        agent.parse(SAMPLE_RESUME)


def test_uses_structured_output_with_candidate_profile() -> None:
    agent, structured = _agent()
    structured.invoke.return_value = CandidateProfile(technical_skills=["Python"])
    agent.parse("Skills: Python")
    llm = agent._llm
    llm.with_structured_output.assert_called_once_with(CandidateProfile)


def test_does_not_log_sensitive_resume_contents(caplog: pytest.LogCaptureFixture) -> None:
    agent, structured = _agent()
    structured.invoke.return_value = {
        "full_name": "Jane Candidate",
        "email": "jane.candidate@example.com",
        "phone": "9876543210",
        "technical_skills": ["Python"],
    }
    with caplog.at_level(logging.INFO, logger="app.agents.resume_agent"):
        agent.parse(SAMPLE_RESUME)
    combined = " ".join(record.getMessage() for record in caplog.records)
    extra_blob = " ".join(str(getattr(record, "resume_chars", "")) for record in caplog.records)
    assert "jane.candidate@example.com" not in combined
    assert "98765" not in combined
    assert "Jane Candidate" not in combined
    assert SAMPLE_RESUME not in combined
    assert extra_blob  # char count may be logged, not body


def test_metadata_comes_from_caller_not_llm() -> None:
    agent, structured = _agent()
    structured.invoke.return_value = {
        "resume_source": "linkedin-scrape",
        "resume_file_name": "stolen.pdf",
        "technical_skills": ["Python"],
    }
    profile = agent.parse(
        "Skills: Python",
        resume_source="upload",
        resume_file_name="jane.pdf",
    )
    assert profile.resume_source == "upload"
    assert profile.resume_file_name == "jane.pdf"


REQUIRED_INSTRUCTIONS = [
    "Never invent",
    "technical skills",
    "soft skills",
    "previous_roles",
    "companies",
    "education",
    "certifications",
    "projects",
    "achievements",
    "total_experience_years",
    "notice_period",
    "availability",
    "work_authorization",
    "CandidateProfile",
]


def test_system_prompt_covers_extraction_rules() -> None:
    prompt = RESUME_EXTRACTION_SYSTEM.lower()
    for instruction in REQUIRED_INSTRUCTIONS:
        assert instruction.lower() in prompt


def test_build_messages_wraps_resume_text() -> None:
    messages = build_resume_extraction_messages(SAMPLE_RESUME)
    assert len(messages) == 2
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert SAMPLE_RESUME.strip() in str(messages[1].content)
    assert "CandidateProfile" in str(messages[0].content)
