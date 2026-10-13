"""Deterministic outreach templates. Candidate-facing; never sent automatically."""

from __future__ import annotations

from app.agents.outreach_grounding import AllowedFacts
from app.models.outreach import OutreachDraft, OutreachTemplateType


def render_template(template: OutreachTemplateType, facts: AllowedFacts) -> OutreachDraft:
    if template is OutreachTemplateType.INTERVIEW_INVITATION:
        return _interview(facts)
    if template is OutreachTemplateType.FOLLOW_UP:
        return _follow_up(facts)
    return _initial(facts)


def _greeting(facts: AllowedFacts) -> str:
    if facts.first_name:
        return f"Hello {facts.first_name},"
    return "Hello,"


def _role_phrase(facts: AllowedFacts) -> str:
    title = facts.job_title or "this role"
    if facts.company_name:
        return f"the {title} role at {facts.company_name}"
    return f"the {title} role"


def _signature(facts: AllowedFacts) -> str:
    lines = ["Best regards,"]
    if facts.recruiter_name:
        lines.append(facts.recruiter_name)
        if facts.recruiter_title:
            lines.append(facts.recruiter_title)
    else:
        lines.append("Recruiting team")
    if facts.company_name:
        lines.append(facts.company_name)
    if facts.recruiter_email:
        lines.append(facts.recruiter_email)
    return "\n".join(lines)


def _background_sentence(facts: AllowedFacts) -> str | None:
    title = facts.current_job_title
    company = facts.companies[0] if facts.companies else None
    if title and company:
        return (
            f"Your experience as {title} at {company} is relevant to what we "
            "are hiring for."
        )
    if title:
        return f"Your experience as {title} is relevant to what we are hiring for."
    if company:
        return f"Your work at {company} is relevant to what we are hiring for."
    return None


def _skills_sentence(facts: AllowedFacts) -> str | None:
    skills = list(facts.overlapping_skills[:3])
    if not skills:
        return None
    if len(skills) == 1:
        listed = skills[0]
    elif len(skills) == 2:
        listed = f"{skills[0]} and {skills[1]}"
    else:
        listed = f"{skills[0]}, {skills[1]}, and {skills[2]}"
    return f"In particular, your background with {listed} aligns with this opening."


def _job_detail_sentence(facts: AllowedFacts) -> str | None:
    bits: list[str] = []
    if facts.employment_type:
        bits.append(facts.employment_type)
    if facts.work_mode:
        bits.append(facts.work_mode)
    if facts.job_location:
        bits.append(facts.job_location)
    if not bits:
        return None
    return "The role is " + ", ".join(bits) + "."


def _personalization_points(facts: AllowedFacts) -> list[str]:
    points: list[str] = []
    if facts.current_job_title:
        points.append(f"Current role: {facts.current_job_title}")
    if facts.companies:
        points.append(f"Employer: {facts.companies[0]}")
    for skill in facts.overlapping_skills[:3]:
        points.append(f"Skill: {skill}")
    if facts.job_title:
        points.append(f"Job: {facts.job_title}")
    if facts.company_name:
        points.append(f"Hiring company: {facts.company_name}")
    return points


def _join(*sections: str | None) -> str:
    parts: list[str] = []
    for section in sections:
        if section:
            parts.extend(["", section] if parts else [section])
    return "\n".join(parts)


def _initial(facts: AllowedFacts) -> OutreachDraft:
    role = _role_phrase(facts)
    subject_role = facts.job_title or "an open role"
    if facts.company_name:
        subject = f"{subject_role} at {facts.company_name}"
    else:
        subject = f"Opportunity: {subject_role}"
    body = _join(
        _greeting(facts),
        f"I am reaching out about {role}.",
        _background_sentence(facts),
        _skills_sentence(facts),
        _job_detail_sentence(facts),
        "If you are open to a conversation, I would be glad to share more about the role.",
        _signature(facts),
    )
    return OutreachDraft(
        subject=subject,
        body=body,
        personalization_points=_personalization_points(facts),
    )


def _interview(facts: AllowedFacts) -> OutreachDraft:
    role = _role_phrase(facts)
    subject_role = facts.job_title or "our opening"
    body = _join(
        _greeting(facts),
        f"I would like to invite you to interview for {role}.",
        _background_sentence(facts),
        _skills_sentence(facts),
        (
            "If you are interested, reply with times that work for you and we will "
            "coordinate next steps. No interview time has been scheduled yet."
        ),
        _signature(facts),
    )
    return OutreachDraft(
        subject=f"Interview invitation: {subject_role}",
        body=body,
        personalization_points=_personalization_points(facts),
    )


def _follow_up(facts: AllowedFacts) -> OutreachDraft:
    role = _role_phrase(facts)
    subject_role = facts.job_title or "the role we discussed"
    body = _join(
        _greeting(facts),
        f"I wanted to follow up regarding {role}.",
        _background_sentence(facts),
        (
            "If this is still of interest, I would be glad to share more about the "
            "opportunity or answer questions."
        ),
        _signature(facts),
    )
    return OutreachDraft(
        subject=f"Following up: {subject_role}",
        body=body,
        personalization_points=_personalization_points(facts),
    )
