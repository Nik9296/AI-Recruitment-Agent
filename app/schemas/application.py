"""Schemas for public candidate job applications."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class JobApplicationRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=512)
    email: str = Field(..., min_length=3, max_length=320)
    phone: str | None = Field(default=None, max_length=64)
    location: str | None = Field(default=None, max_length=512)
    current_job_title: str | None = Field(default=None, max_length=512)
    skills: list[str] = Field(default_factory=list)
    resume_summary: str | None = None
    open_to_work: bool = True

    @field_validator("full_name", "email", mode="before")
    @classmethod
    def _required_strip(cls, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("must not be blank")
        return text

    @field_validator("phone", "location", "current_job_title", "resume_summary", mode="before")
    @classmethod
    def _optional_strip(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("skills", mode="before")
    @classmethod
    def _clean_skills(cls, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            value = [value]
        seen: set[str] = set()
        cleaned: list[str] = []
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


class JobApplicationResponse(BaseModel):
    job_id: UUID
    candidate_id: UUID
    created_candidate: bool
    created_match: bool
    applied_at: datetime
    message: str
