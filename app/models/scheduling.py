"""Interview slot proposals. Calendar booking is a separate integration."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class InterviewSlot(BaseModel):
    start_at: datetime
    end_at: datetime
    timezone: str = "Asia/Kolkata"


class SchedulingProposal(BaseModel):
    candidate_id: UUID
    job_id: UUID
    slots: list[InterviewSlot] = Field(default_factory=list)
    duration_minutes: int = 45
    calendar_booked: Literal[False] = False
    generated_at: datetime
