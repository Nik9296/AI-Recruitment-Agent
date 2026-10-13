"""API schemas for interviews."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class InterviewConfirmRequest(BaseModel):
    start_at: datetime
    end_at: datetime


class InterviewRecordResponse(BaseModel):
    job_id: UUID
    candidate_id: UUID
    status: str
    timezone: str
    duration_minutes: int
    proposed_slots: list[dict] = Field(default_factory=list)
    start_at: datetime | None = None
    end_at: datetime | None = None
    calendar_event_id: str | None = None
    calendar_booked: bool = False
    recruiter_id: str | None = None
    message: str
