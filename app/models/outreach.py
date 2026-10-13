"""Structured outreach draft. Email is never sent from this model."""

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class OutreachTemplateType(StrEnum):
    INITIAL = "initial"
    INTERVIEW_INVITATION = "interview_invitation"
    FOLLOW_UP = "follow_up"


REVIEW_PENDING = "pending_recruiter_review"


class RecruiterCompanyInfo(BaseModel):
    """Public recruiter/company details used in a candidate-facing draft."""

    company_name: str | None = Field(
        default=None,
        description="Hiring company name. Null if not configured; do not invent one.",
    )
    recruiter_name: str | None = Field(
        default=None,
        description="Recruiter display name for the signature. Null if unknown.",
    )
    recruiter_title: str | None = Field(
        default=None,
        description="Recruiter title if known, such as Technical Recruiter.",
    )
    recruiter_email: str | None = Field(
        default=None,
        description="Public reply-to shown in the draft signature. Not used to send.",
    )


class OutreachDraft(BaseModel):
    """LLM-shaped fields only. Identifiers and timestamps are set by the agent."""

    subject: str = Field(description="Professional email subject. No scores or rankings.")
    body: str = Field(
        description="Candidate-facing email body using only allowed facts."
    )
    personalization_points: list[str] = Field(
        default_factory=list,
        description="Short facts actually used in the draft, each grounded in the profile.",
    )

    @field_validator("subject", "body", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> str:
        return str(value or "").strip()

    @field_validator("personalization_points", mode="before")
    @classmethod
    def clean_points(cls, value: object) -> list[str]:
        if value is None:
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


class OutreachMessage(BaseModel):
    """Reviewable recruitment invitation. Never auto-sent."""

    candidate_id: UUID
    job_id: UUID
    subject: str
    body: str
    personalization_points: list[str] = Field(default_factory=list)
    generated_at: datetime
    template: OutreachTemplateType = OutreachTemplateType.INITIAL
    review_status: Literal["pending_recruiter_review"] = REVIEW_PENDING
    email_sent: Literal[False] = False
