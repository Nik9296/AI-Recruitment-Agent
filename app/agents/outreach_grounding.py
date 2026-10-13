"""Ground outreach text in stated candidate facts. Do not invent or leak scores."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.models.candidate import CandidateProfile
from app.models.job import EmploymentType, JobProfile, WorkMode
from app.models.match import MatchResult
from app.models.outreach import RecruiterCompanyInfo
from app.utils.matching import candidate_skill_pool, skill_covers
from app.utils.skills import canonicalize_skill

_SKILL_PREFIXES = ("Required skill:", "Preferred skill:")
_YEAR_CLAIM = re.compile(r"(\d+(?:\.\d+)?)\s*\+?\s*years", re.I)
_PERCENT_CLAIM = re.compile(r"\b\d{1,3}(?:\.\d+)?\s*%")
_AT_COMPANY = re.compile(
    r"\bat\s+([A-Z][\w.&'-]+(?:\s+(?:and|&|of|the|[A-Z][\w.&'-]+)){0,4})"
)

_SCORE_TERMS = (
    "overall score",
    "overall_score",
    "match score",
    "match percent",
    "matching score",
    "ai ranking",
    "ai rank",
    "ranked #",
    "match ranking",
    "confidence score",
    "semantic score",
    "required-skill",
    "required skill coverage",
    "deterministic",
)

_SENSITIVE_TERMS = (
    "work authorization",
    "visa",
    "citizenship",
    "national origin",
    "gender",
    "religion",
    "race",
    "ethnicity",
    "disability",
    "sexual orientation",
    "notice period",
    "date of birth",
    "ssn",
    "social security",
    "caste",
)


@dataclass(frozen=True)
class AllowedFacts:
    first_name: str | None = None
    full_name: str | None = None
    current_job_title: str | None = None
    companies: tuple[str, ...] = ()
    overlapping_skills: tuple[str, ...] = ()
    project_names: tuple[str, ...] = ()
    education_bits: tuple[str, ...] = ()
    location: str | None = None
    experience_years: float | None = None
    job_title: str | None = None
    job_location: str | None = None
    work_mode: str | None = None
    employment_type: str | None = None
    recruiter_name: str | None = None
    recruiter_title: str | None = None
    recruiter_email: str | None = None
    company_name: str | None = None
    overall_score: float | None = field(default=None, repr=False)

    def phrases(self) -> list[str]:
        values: list[str] = []
        for item in (
            self.first_name,
            self.full_name,
            self.current_job_title,
            self.location,
            self.job_title,
            self.job_location,
            self.work_mode,
            self.employment_type,
            self.recruiter_name,
            self.recruiter_title,
            self.company_name,
            *self.companies,
            *self.overlapping_skills,
            *self.project_names,
            *self.education_bits,
        ):
            if item:
                values.append(item)
        return values

    def first_name_or_generic(self) -> str:
        return self.first_name or ""


def first_name(full_name: str | None) -> str | None:
    if not full_name:
        return None
    token = full_name.strip().split()[0].strip()
    return token or None


def overlapping_skills(
    candidate: CandidateProfile, job: JobProfile, match: MatchResult
) -> list[str]:
    pool = candidate_skill_pool(candidate)
    ordered: list[str] = []
    seen: set[str] = set()

    def add(skill: str) -> None:
        canonical = canonicalize_skill(skill)
        key = canonical.lower()
        if not canonical or key in seen:
            return
        if not skill_covers(skill, pool):
            return
        seen.add(key)
        ordered.append(canonical)

    for skill in [*job.must_have_skills, *job.preferred_skills]:
        add(skill)
    for label in match.matched_requirements:
        for prefix in _SKILL_PREFIXES:
            if label.startswith(prefix):
                add(label.split(":", 1)[1].strip())
    return ordered


def collect_allowed_facts(
    candidate: CandidateProfile,
    job: JobProfile,
    match: MatchResult,
    recruiter: RecruiterCompanyInfo,
) -> AllowedFacts:
    companies = tuple(item for item in candidate.companies if item)
    if not companies:
        companies = tuple(
            role.company for role in candidate.previous_roles if role.company
        )
    education: list[str] = []
    for entry in candidate.education:
        for bit in (entry.degree, entry.field, entry.institution):
            if bit:
                education.append(bit)
    work_mode = None
    if job.work_mode not in (None, WorkMode.UNKNOWN):
        work_mode = job.work_mode.value
    employment = None
    if job.employment_type not in (None, EmploymentType.UNKNOWN):
        employment = job.employment_type.value
    return AllowedFacts(
        first_name=first_name(candidate.full_name),
        full_name=candidate.full_name,
        current_job_title=candidate.current_job_title,
        companies=companies,
        overlapping_skills=tuple(overlapping_skills(candidate, job, match)),
        project_names=tuple(project.name for project in candidate.projects if project.name),
        education_bits=tuple(education),
        location=candidate.location,
        experience_years=candidate.total_experience_years,
        job_title=job.job_title,
        job_location=job.location,
        work_mode=work_mode,
        employment_type=employment,
        recruiter_name=recruiter.recruiter_name,
        recruiter_title=recruiter.recruiter_title,
        recruiter_email=recruiter.recruiter_email,
        company_name=recruiter.company_name,
        overall_score=match.overall_score,
    )


def allowed_facts_for_prompt(facts: AllowedFacts) -> dict[str, object]:
    """Facts the LLM may use. Scores, gaps, and sensitive fields are omitted."""
    payload: dict[str, object] = {}
    if facts.first_name:
        payload["first_name"] = facts.first_name
    if facts.current_job_title:
        payload["current_job_title"] = facts.current_job_title
    if facts.companies:
        payload["companies"] = list(facts.companies)
    if facts.overlapping_skills:
        payload["skills_also_on_the_job"] = list(facts.overlapping_skills)
    if facts.project_names:
        payload["projects"] = list(facts.project_names)
    if facts.education_bits:
        payload["education"] = list(facts.education_bits)
    if facts.location:
        payload["candidate_location"] = facts.location
    if facts.experience_years is not None:
        payload["stated_experience_years"] = facts.experience_years
    if facts.job_title:
        payload["job_title"] = facts.job_title
    if facts.job_location:
        payload["job_location"] = facts.job_location
    if facts.work_mode:
        payload["work_mode"] = facts.work_mode
    if facts.employment_type:
        payload["employment_type"] = facts.employment_type
    if facts.company_name:
        payload["hiring_company"] = facts.company_name
    if facts.recruiter_name:
        payload["recruiter_name"] = facts.recruiter_name
    if facts.recruiter_title:
        payload["recruiter_title"] = facts.recruiter_title
    if facts.recruiter_email:
        payload["recruiter_email"] = facts.recruiter_email
    return payload


def contains_internal_scores(text: str, overall_score: float | None) -> bool:
    lower = text.lower()
    if any(term in lower for term in _SCORE_TERMS):
        return True
    if _PERCENT_CLAIM.search(text):
        return True
    if overall_score is None:
        return False
    percent = int(round(overall_score * 100))
    if re.search(rf"\b{percent}\s*%", text):
        return True
    score_text = f"{overall_score:.4f}".rstrip("0").rstrip(".")
    if "." in score_text and score_text in text:
        return True
    return False


def contains_sensitive_content(text: str, candidate: CandidateProfile) -> bool:
    lower = text.lower()
    if any(term in lower for term in _SENSITIVE_TERMS):
        return True
    if candidate.email and candidate.email.lower() in lower:
        return True
    if candidate.phone:
        digits = re.sub(r"\D", "", candidate.phone)
        compact = re.sub(r"\D", "", text)
        if digits and len(digits) >= 8 and digits in compact:
            return True
    if candidate.work_authorization and candidate.work_authorization.lower() in lower:
        return True
    if candidate.notice_period and candidate.notice_period.lower() in lower:
        return True
    return False


def contains_false_claims(text: str, facts: AllowedFacts, job: JobProfile) -> bool:
    years = facts.experience_years
    for match in _YEAR_CLAIM.finditer(text):
        claimed = float(match.group(1))
        if years is None or abs(claimed - years) > 0.05:
            return True
    pool = {skill.lower() for skill in facts.overlapping_skills}
    candidate_owned = pool
    for skill in [*job.must_have_skills, *job.preferred_skills]:
        canonical = canonicalize_skill(skill)
        if canonical.lower() in candidate_owned:
            continue
        if re.search(rf"\b{re.escape(canonical)}\b", text, re.I):
            return True
    allowed_lower = {item.lower() for item in facts.phrases()}
    for claimed in _AT_COMPANY.findall(text):
        name = claimed.strip().rstrip(".,")
        if not name:
            continue
        if name.lower() in {"this", "the", "our"}:
            continue
        if any(name.lower() == item or name.lower() in item for item in allowed_lower):
            continue
        if facts.job_title and name.lower() in facts.job_title.lower():
            continue
        return True
    return False


def point_is_grounded(point: str, facts: AllowedFacts) -> bool:
    if contains_internal_scores(point, facts.overall_score):
        return False
    lower = point.lower()
    if any(term in lower for term in _SENSITIVE_TERMS):
        return False
    return any(phrase.lower() in lower for phrase in facts.phrases() if phrase)


def draft_is_safe(
    subject: str,
    body: str,
    facts: AllowedFacts,
    candidate: CandidateProfile,
    job: JobProfile,
) -> bool:
    for text in (subject, body):
        if contains_internal_scores(text, facts.overall_score):
            return False
        if contains_sensitive_content(text, candidate):
            return False
        if contains_false_claims(text, facts, job):
            return False
    return bool(subject.strip()) and bool(body.strip())
