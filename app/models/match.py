"""Structured result of CandidateProfile vs JobProfile matching."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MatchResult(BaseModel):
    candidate_id: UUID | None = None
    job_id: UUID | None = None
    overall_score: float = Field(ge=0, le=1)
    required_skill_score: float = Field(ge=0, le=1)
    preferred_skill_score: float = Field(ge=0, le=1)
    experience_score: float = Field(ge=0, le=1)
    title_similarity_score: float = Field(ge=0, le=1)
    education_score: float = Field(ge=0, le=1)
    project_score: float = Field(ge=0, le=1)
    location_score: float = Field(ge=0, le=1)
    semantic_score: float = Field(ge=0, le=1)
    matched_requirements: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    explanation: str
    confidence: float = Field(ge=0, le=1)
    generated_at: datetime
