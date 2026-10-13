"""JD Agent: extract a validated JobProfile from raw job-description text."""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import ValidationError

from app.models.job import JobProfile
from app.prompts.jd_prompt import build_jd_extraction_messages
from app.services.llm import LLMConfigurationError, get_chat_model
from app.utils.jd_text import (
    infer_employment_type,
    infer_location,
    infer_work_mode,
    location_is_supported,
    parse_experience,
)
from app.utils.skills import canonicalize_skill


class JDAgentError(Exception):
    """Base error for JD analysis failures."""


class EmptyJobDescriptionError(JDAgentError):
    """Raised when the job description is missing or blank."""


class JDExtractionError(JDAgentError):
    """Raised when the LLM result cannot be turned into a valid JobProfile."""


class JDAgent:
    """Extract structured job requirements. Independent of FastAPI and storage."""

    def __init__(self, llm: BaseChatModel | None = None) -> None:
        self._llm = llm

    def analyze(self, job_description: str) -> JobProfile:
        text = self._require_job_description(job_description)
        messages = build_jd_extraction_messages(text)
        try:
            raw = self._structured_llm().invoke(messages)
        except (JDAgentError, LLMConfigurationError):
            raise
        except Exception as exc:
            raise JDExtractionError(f"LLM extraction failed: {exc}") from exc

        try:
            profile = self._to_profile(raw)
        except ValidationError as exc:
            raise JDExtractionError(
                f"JobProfile validation failed: {exc}"
            ) from exc

        return self._normalize_profile(profile, text)

    def _structured_llm(self) -> Any:
        llm = self._llm or get_chat_model()
        if self._llm is None and hasattr(llm, "bind"):
            llm = llm.bind(temperature=0)
        if not hasattr(llm, "with_structured_output"):
            raise JDExtractionError(
                "Configured LLM does not support structured output"
            )
        return llm.with_structured_output(JobProfile)

    @staticmethod
    def _require_job_description(job_description: str) -> str:
        if not isinstance(job_description, str):
            raise EmptyJobDescriptionError(
                "job_description must be a non-empty string"
            )
        text = job_description.strip()
        if not text:
            raise EmptyJobDescriptionError(
                "job_description cannot be empty or whitespace-only"
            )
        return text

    @staticmethod
    def _to_profile(raw: Any) -> JobProfile:
        if raw is None:
            raise JDExtractionError("LLM returned no structured result")
        if isinstance(raw, JobProfile):
            return JobProfile.model_validate(raw.model_dump())
        if isinstance(raw, dict):
            return JobProfile.model_validate(raw)
        raise JDExtractionError(
            f"Unexpected LLM output type: {type(raw).__name__}"
        )

    def _normalize_profile(self, profile: JobProfile, source: str) -> JobProfile:
        must_have = self._normalize_skill_list(profile.must_have_skills)
        preferred = self._normalize_skill_list(profile.preferred_skills)
        must_keys = {item.lower() for item in must_have}
        preferred = [item for item in preferred if item.lower() not in must_keys]
        keywords = self._normalize_skill_list(
            [*profile.keywords, *must_have, *preferred]
        )

        min_years, max_years = profile.experience_min, profile.experience_max
        if min_years is None and max_years is None:
            min_years, max_years = parse_experience(source)

        work_mode = profile.work_mode or infer_work_mode(source)
        employment_type = profile.employment_type or infer_employment_type(source)

        location = profile.location
        if location and not location_is_supported(location, source):
            location = None
        if location is None:
            location = infer_location(source)

        return profile.model_copy(
            update={
                "experience_min": min_years,
                "experience_max": max_years,
                "location": location,
                "work_mode": work_mode,
                "employment_type": employment_type,
                "must_have_skills": must_have,
                "preferred_skills": preferred,
                "keywords": keywords,
            }
        )

    @staticmethod
    def _normalize_skill_list(skills: list[str]) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []
        for skill in skills:
            canonical = canonicalize_skill(skill)
            if not canonical:
                continue
            key = canonical.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(canonical)
        return normalized
