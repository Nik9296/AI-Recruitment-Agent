"""API schemas for sourcing and the LangGraph pipeline."""

from uuid import UUID

from pydantic import BaseModel, Field

from app.models.sourcing import SourcedCandidateRef, SourcingQuery


class SourcingResponse(BaseModel):
    job_id: UUID
    job_title: str | None = None
    queries: list[SourcingQuery] = Field(default_factory=list)
    candidates: list[SourcedCandidateRef] = Field(default_factory=list)
    invented_candidates: bool = False
    message: str = (
        "Sourced from the internal candidate store. No new people were invented."
    )


class PipelineRunResponse(BaseModel):
    job_id: UUID
    sourced_count: int = 0
    matched_count: int = 0
    ranked_count: int = 0
    shortlist_recorded: bool = False
    outreach_sent: bool = False
    hired: bool = False
    errors: list[str] = Field(default_factory=list)
    message: str = (
        "Shortlist recorded for recruiter review. No email was sent and no hire was made."
    )
