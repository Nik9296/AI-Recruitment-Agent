from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.agents.outreach_agent import OutreachAgent, OutreachInputError
from app.models.candidate import CandidateProfile
from app.models.job import JobProfile
from app.models.match import MatchResult
from app.models.outreach import OutreachTemplateType, RecruiterCompanyInfo
from app.prompts.outreach_prompt import OUTREACH_SYSTEM, build_outreach_messages


def _recruiter() -> RecruiterCompanyInfo:
    return RecruiterCompanyInfo(
        company_name="Northwind",
        recruiter_name="Ada Recruiter",
        recruiter_title="Technical Recruiter",
        recruiter_email="ada@northwind.example",
    )


def _candidate(**overrides) -> CandidateProfile:
    payload = {
        "candidate_id": uuid4(),
        "full_name": "Rahul Sharma",
        "email": "rahul@example.com",
        "phone": "+91 98765 43210",
        "location": "Hyderabad",
        "current_job_title": "ML Engineer",
        "total_experience_years": 6,
        "technical_skills": ["Python", "TensorFlow"],
        "skills": ["Python", "TensorFlow"],
        "companies": ["Acme Analytics"],
        "previous_roles": [{"title": "ML Engineer", "company": "Acme Analytics"}],
        "work_authorization": "Indian citizen",
        "notice_period": "30 days",
    }
    payload.update(overrides)
    return CandidateProfile(**payload)


def _job(**overrides) -> JobProfile:
    payload = {
        "job_title": "AI/ML Engineer",
        "location": "Hyderabad",
        "work_mode": "Hybrid",
        "employment_type": "Full-time",
        "must_have_skills": ["Python", "TensorFlow", "Kubernetes"],
        "preferred_skills": ["PyTorch"],
    }
    payload.update(overrides)
    return JobProfile(**payload)


def _match(candidate: CandidateProfile, job_id=None, **overrides) -> MatchResult:
    payload = {
        "candidate_id": candidate.candidate_id,
        "job_id": job_id or uuid4(),
        "overall_score": 0.94,
        "required_skill_score": 0.8,
        "preferred_skill_score": 0.5,
        "experience_score": 1.0,
        "title_similarity_score": 0.9,
        "education_score": 0.7,
        "project_score": 0.6,
        "location_score": 1.0,
        "semantic_score": 0.88,
        "matched_requirements": [
            "Required skill: Python",
            "Required skill: TensorFlow",
        ],
        "missing_requirements": ["Required skill: Kubernetes"],
        "explanation": (
            "Overall match score is 94% from deterministic requirement scoring. "
            "This is not a hiring decision."
        ),
        "confidence": 0.91,
        "generated_at": datetime.now(UTC),
    }
    payload.update(overrides)
    return MatchResult(**payload)


def _agent_with_llm(draft: dict) -> tuple[OutreachAgent, MagicMock]:
    llm = MagicMock()
    structured = MagicMock()
    structured.invoke.return_value = draft
    llm.with_structured_output.return_value = structured
    return OutreachAgent(llm=llm), structured


def _visible(message) -> str:
    return " ".join(
        [message.subject, message.body, " ".join(message.personalization_points)]
    )


def test_template_initial_personalizes_only_stated_facts() -> None:
    candidate = _candidate()
    job = _job()
    match = _match(candidate)
    message = OutreachAgent().generate(
        candidate, job, match, _recruiter(), use_llm=False
    )
    assert message.candidate_id == candidate.candidate_id
    assert message.job_id == match.job_id
    assert message.email_sent is False
    assert message.review_status == "pending_recruiter_review"
    assert "Rahul" in message.body
    assert "ML Engineer" in message.body
    assert "Acme Analytics" in message.body
    assert "Python" in message.body
    assert "Northwind" in message.body
    assert any("Python" in point for point in message.personalization_points)
    assert message.generated_at.tzinfo is not None


def test_sparse_profile_does_not_invent_employer_or_name() -> None:
    candidate = _candidate(
        full_name=None,
        current_job_title=None,
        companies=[],
        previous_roles=[],
        technical_skills=["Python"],
        skills=["Python"],
    )
    message = OutreachAgent().generate(
        candidate, _job(), _match(candidate), _recruiter(), use_llm=False
    )
    visible = _visible(message)
    assert "Hello," in message.body
    assert "Rahul" not in visible
    assert "Acme" not in visible
    assert "your experience as" not in message.body.lower()


def test_does_not_expose_internal_scores_or_gaps() -> None:
    candidate = _candidate()
    message = OutreachAgent().generate(
        candidate, _job(), _match(candidate), _recruiter(), use_llm=False
    )
    visible = _visible(message).lower()
    assert "94%" not in visible
    assert "0.94" not in visible
    assert "overall score" not in visible
    assert "confidence" not in visible
    assert "kubernetes" not in visible
    assert "hiring decision" not in visible
    assert message.email_sent is False


def test_does_not_mention_sensitive_or_protected_fields() -> None:
    candidate = _candidate()
    visible = _visible(
        OutreachAgent().generate(
            candidate, _job(), _match(candidate), _recruiter(), use_llm=False
        )
    ).lower()
    assert "indian citizen" not in visible
    assert "work authorization" not in visible
    assert "30 days" not in visible
    assert "98765" not in visible
    assert "rahul@example.com" not in visible


def test_templates_differ_for_initial_interview_and_follow_up() -> None:
    candidate = _candidate()
    job = _job()
    match = _match(candidate)
    recruiter = _recruiter()
    agent = OutreachAgent()
    initial = agent.generate(
        candidate,
        job,
        match,
        recruiter,
        template=OutreachTemplateType.INITIAL,
        use_llm=False,
    )
    interview = agent.generate(
        candidate,
        job,
        match,
        recruiter,
        template=OutreachTemplateType.INTERVIEW_INVITATION,
        use_llm=False,
    )
    follow_up = agent.generate(
        candidate,
        job,
        match,
        recruiter,
        template=OutreachTemplateType.FOLLOW_UP,
        use_llm=False,
    )
    assert initial.template is OutreachTemplateType.INITIAL
    assert "Interview invitation" in interview.subject
    assert "invite you to interview" in interview.body.lower()
    assert "Following up" in follow_up.subject
    assert "follow up" in follow_up.body.lower()
    assert initial.subject != interview.subject
    assert interview.subject != follow_up.subject
    assert "scheduled" in interview.body.lower()


def test_unsafe_llm_draft_falls_back_to_template() -> None:
    candidate = _candidate()
    agent, structured = _agent_with_llm(
        {
            "subject": "You scored 94% — top AI ranking",
            "body": (
                "Hello Rahul, you are our #1 Kubernetes expert from Google "
                "with visa-ready work authorization and 12 years of experience."
            ),
            "personalization_points": ["AI ranking 94%", "Employer: Google"],
        }
    )
    message = agent.generate(candidate, _job(), _match(candidate), _recruiter())
    structured.invoke.assert_called_once()
    visible = _visible(message).lower()
    assert "94%" not in visible
    assert "google" not in visible
    assert "kubernetes" not in visible
    assert "visa" not in visible
    assert "12 years" not in visible
    assert message.email_sent is False
    assert "Rahul" in message.body


def test_safe_llm_draft_is_kept_and_points_are_grounded() -> None:
    candidate = _candidate()
    agent, _structured = _agent_with_llm(
        {
            "subject": "AI/ML Engineer at Northwind",
            "body": (
                "Hello Rahul,\n\n"
                "I am reaching out about the AI/ML Engineer role at Northwind. "
                "Your experience as ML Engineer at Acme Analytics and your "
                "background with Python are relevant.\n\n"
                "Best regards,\nAda Recruiter\nNorthwind"
            ),
            "personalization_points": [
                "Current role: ML Engineer",
                "Employer: Acme Analytics",
                "Skill: Python",
                "Invented: Google",
            ],
        }
    )
    message = agent.generate(candidate, _job(), _match(candidate), _recruiter())
    assert message.subject == "AI/ML Engineer at Northwind"
    assert "Acme Analytics" in message.body
    assert any(point == "Skill: Python" for point in message.personalization_points)
    assert not any("Google" in point for point in message.personalization_points)


def test_missing_ids_raise() -> None:
    candidate = _candidate(candidate_id=None)
    match = _match(candidate, job_id=None)
    match.candidate_id = None
    with pytest.raises(OutreachInputError, match="candidate_id and job_id"):
        OutreachAgent().generate(
            candidate, _job(), match, _recruiter(), use_llm=False
        )


def test_agent_has_no_send_capability() -> None:
    assert not hasattr(OutreachAgent, "send")
    assert not hasattr(OutreachAgent, "send_email")


def test_prompt_forbids_scores_and_false_claims() -> None:
    assert "Do not mention internal AI scores" in OUTREACH_SYSTEM
    assert "Never invent" in OUTREACH_SYSTEM
    messages = build_outreach_messages(
        template=OutreachTemplateType.INITIAL,
        allowed_facts={"first_name": "Rahul"},
    )
    assert "ALLOWED FACTS" in messages[1].content
    assert "94%" not in messages[1].content
