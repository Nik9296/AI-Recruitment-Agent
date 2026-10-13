"""Resume Agent: extract a validated CandidateProfile from resume text."""

from __future__ import annotations

import logging
import re
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import ValidationError

from app.models.candidate import CandidateProfile, PreviousRole, Project
from app.prompts.resume_prompt import build_resume_extraction_messages
from app.services.llm import LLMConfigurationError, get_chat_model
from app.utils.jd_text import location_is_supported
from app.utils.resume_text import (
    availability_is_stated,
    experience_is_supported,
    notice_period_is_stated,
    parse_stated_experience_years,
    phone_supported_by_text,
    value_supported_by_text,
    work_authorization_is_stated,
)
from app.utils.skills import SKILL_ALIASES, canonicalize_skill

logger = logging.getLogger(__name__)


class ResumeAgentError(Exception):
    """Base error for resume analysis failures."""


class EmptyResumeTextError(ResumeAgentError):
    """Raised when the resume text is missing or blank."""


class ResumeExtractionError(ResumeAgentError):
    """Raised when the LLM result cannot be turned into a valid CandidateProfile."""


class ResumeAgent:
    """Extract structured candidate data. Independent of FastAPI and storage."""

    def __init__(self, llm: BaseChatModel | None = None) -> None:
        self._llm = llm

    def parse(
        self,
        resume_text: str,
        *,
        resume_source: str | None = None,
        resume_file_name: str | None = None,
    ) -> CandidateProfile:
        text = self._require_resume_text(resume_text)
        logger.info(
            "ResumeAgent.parse started",
            extra={"resume_chars": len(text), "resume_source": resume_source},
        )
        messages = build_resume_extraction_messages(text)
        try:
            raw = self._structured_llm().invoke(messages)
        except (ResumeAgentError, LLMConfigurationError):
            raise
        except Exception as exc:
            logger.warning("ResumeAgent LLM extraction failed")
            raise ResumeExtractionError(f"LLM extraction failed: {exc}") from exc

        try:
            profile = self._to_profile(raw)
        except ValidationError as exc:
            logger.warning("ResumeAgent CandidateProfile validation failed")
            raise ResumeExtractionError(
                f"CandidateProfile validation failed: {exc}"
            ) from exc

        profile = self._normalize_profile(
            profile,
            text,
            resume_source=resume_source,
            resume_file_name=resume_file_name,
        )
        logger.info(
            "ResumeAgent.parse completed",
            extra={
                "has_name": profile.full_name is not None,
                "has_email": profile.email is not None,
                "has_experience": profile.total_experience_years is not None,
                "technical_skill_count": len(profile.technical_skills),
                "soft_skill_count": len(profile.soft_skills),
                "role_count": len(profile.previous_roles),
                "education_count": len(profile.education),
            },
        )
        return profile

    def _structured_llm(self) -> Any:
        llm = self._llm or get_chat_model()
        if self._llm is None and hasattr(llm, "bind"):
            llm = llm.bind(temperature=0)
        if not hasattr(llm, "with_structured_output"):
            raise ResumeExtractionError(
                "Configured LLM does not support structured output"
            )
        return llm.with_structured_output(CandidateProfile)

    @staticmethod
    def _require_resume_text(resume_text: str) -> str:
        if not isinstance(resume_text, str):
            raise EmptyResumeTextError("resume_text must be a non-empty string")
        text = resume_text.strip()
        if not text:
            raise EmptyResumeTextError(
                "resume_text cannot be empty or whitespace-only"
            )
        return text

    @staticmethod
    def _to_profile(raw: Any) -> CandidateProfile:
        if raw is None:
            raise ResumeExtractionError("LLM returned no structured result")
        if isinstance(raw, CandidateProfile):
            return CandidateProfile.model_validate(raw.model_dump())
        if isinstance(raw, dict):
            return CandidateProfile.model_validate(raw)
        raise ResumeExtractionError(
            f"Unexpected LLM output type: {type(raw).__name__}"
        )

    def _normalize_profile(
        self,
        profile: CandidateProfile,
        source: str,
        *,
        resume_source: str | None,
        resume_file_name: str | None,
    ) -> CandidateProfile:
        technical = self._normalize_skill_list(profile.technical_skills, source)
        technical_keys = {item.lower() for item in technical}
        soft = [
            skill
            for skill in self._normalize_skill_list(profile.soft_skills, source)
            if skill.lower() not in technical_keys
        ]
        skills = self._normalize_skill_list(
            [*profile.skills, *technical, *soft], source
        )

        years = profile.total_experience_years
        if years is not None and not experience_is_supported(years, source):
            years = None
        if years is None:
            years = parse_stated_experience_years(source)

        full_name = profile.full_name
        if full_name and not value_supported_by_text(full_name, source):
            full_name = None
        email = profile.email
        if email and email.lower() not in source.lower():
            email = None
        phone = profile.phone
        if phone and not phone_supported_by_text(phone, source):
            phone = None
        location = profile.location
        if location and not location_is_supported(location, source):
            location = None

        current_title = profile.current_job_title
        if current_title and not value_supported_by_text(current_title, source):
            current_title = None

        notice_period = profile.notice_period
        if notice_period and not (
            notice_period_is_stated(source)
            and value_supported_by_text(notice_period, source)
        ):
            notice_period = None
        availability = profile.availability
        if availability and not (
            availability_is_stated(source)
            and value_supported_by_text(availability, source)
        ):
            availability = None
        work_authorization = profile.work_authorization
        if work_authorization and not (
            work_authorization_is_stated(source)
            and value_supported_by_text(work_authorization, source)
        ):
            work_authorization = None

        summary = profile.resume_summary
        if summary and not _summary_is_grounded(summary, source):
            summary = None

        previous_roles = [
            role.model_copy(
                update={"highlights": [h for h in role.highlights if h]}
            )
            for role in profile.previous_roles
            if _role_is_grounded(role, source)
        ]
        if current_title is None:
            current_title = _current_title_from_roles(previous_roles)

        projects = [
            project.model_copy(
                update={
                    "technologies": self._normalize_skill_list(
                        project.technologies, source
                    )
                }
            )
            for project in profile.projects
            if _project_is_grounded(project, source)
        ]
        companies = self._normalize_name_list(
            [*profile.companies, *[role.company for role in previous_roles]]
        )
        achievements = [
            item
            for item in profile.achievements
            if value_supported_by_text(item, source) or _tokens_mostly_present(item, source)
        ]

        return profile.model_copy(
            update={
                "candidate_id": None,
                "full_name": full_name,
                "email": email,
                "phone": phone,
                "location": location,
                "current_job_title": current_title,
                "total_experience_years": years,
                "skills": skills,
                "technical_skills": technical,
                "soft_skills": soft,
                "companies": companies,
                "previous_roles": previous_roles,
                "projects": projects,
                "achievements": achievements,
                "notice_period": notice_period,
                "availability": availability,
                "work_authorization": work_authorization,
                "resume_summary": summary,
                "resume_source": resume_source,
                "resume_file_name": resume_file_name,
            }
        )

    @staticmethod
    def _normalize_skill_list(skills: list[str], source: str) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []
        for skill in skills:
            canonical = canonicalize_skill(skill)
            if not canonical or not _skill_in_resume(canonical, source):
                continue
            key = canonical.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(canonical)
        return normalized

    @staticmethod
    def _normalize_name_list(names: list[str | None]) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []
        for name in names:
            if not name:
                continue
            text = name.strip()
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(text)
        return normalized


def _skill_in_resume(skill: str, source: str) -> bool:
    haystack = source.lower()
    needles = {skill.lower()}
    for alias, canonical in SKILL_ALIASES.items():
        if canonical.lower() == skill.lower():
            needles.add(alias)
    return any(needle and needle in haystack for needle in needles)


def _current_title_from_roles(roles: list[PreviousRole]) -> str | None:
    for role in roles:
        if role.title:
            return role.title
    return None


def _role_is_grounded(role: PreviousRole, source: str) -> bool:
    if role.company and value_supported_by_text(role.company, source):
        return True
    if role.title and value_supported_by_text(role.title, source):
        return True
    return False


def _project_is_grounded(project: Project, source: str) -> bool:
    if project.name and value_supported_by_text(project.name, source):
        return True
    if project.description and _tokens_mostly_present(project.description, source):
        return True
    return False


def _summary_is_grounded(summary: str, source: str) -> bool:
    if value_supported_by_text(summary, source):
        return True
    return _tokens_mostly_present(summary, source, minimum=0.5)


def _tokens_mostly_present(value: str, source: str, *, minimum: float = 0.6) -> bool:
    tokens = [token for token in re.split(r"[^a-z0-9]+", value.lower()) if len(token) > 3]
    if not tokens:
        return False
    haystack = source.lower()
    hits = sum(1 for token in tokens if token in haystack)
    return (hits / len(tokens)) >= minimum
