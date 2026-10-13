"""Structured shortlist row produced by the ranking engine."""

from uuid import UUID

from pydantic import BaseModel, Field


class RankedCandidate(BaseModel):
    rank: int = Field(ge=1)
    candidate_id: UUID | None = None
    job_id: UUID | None = None
    overall_score: float = Field(ge=0, le=1)
    matched_requirements: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    explanation: str
    confidence: float = Field(ge=0, le=1)
