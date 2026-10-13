"""Sourcing plan and grounded candidate refs. Never invented people."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SourcingQuery(BaseModel):
    job_title: str | None = None
    skills: list[str] = Field(default_factory=list)
    location: str | None = None
    experience_min: float | None = None
    label: str = "primary"

    @field_validator("job_title", "location", "label", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("skills", mode="before")
    @classmethod
    def clean_skills(cls, value: object) -> list[str]:
        if not value:
            return []
        if not isinstance(value, list):
            value = [value]
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in value:
            text = str(item or "").strip()
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(text)
        return cleaned


class SourcedCandidateRef(BaseModel):
    """Pointer to a candidate that already exists. No new personal facts."""

    candidate_id: UUID
    source: str = "internal_ats"
    matched_query_skills: list[str] = Field(default_factory=list)
    title_matched: bool = False


class SourcingResult(BaseModel):
    job_title: str | None = None
    queries: list[SourcingQuery] = Field(default_factory=list)
    candidates: list[SourcedCandidateRef] = Field(default_factory=list)
    invented_candidates: Literal[False] = False
    external_providers_used: list[str] = Field(default_factory=list)
