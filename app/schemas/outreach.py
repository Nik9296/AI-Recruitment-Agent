"""API schemas for recruiter-reviewable outreach drafts."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.outreach import REVIEW_PENDING, OutreachTemplateType


class OutreachGenerateRequest(BaseModel):
    template: OutreachTemplateType = OutreachTemplateType.INITIAL


class OutreachDraftResponse(BaseModel):
    candidate_id: UUID
    job_id: UUID
    subject: str
    body: str
    personalization_points: list[str] = Field(default_factory=list)
    generated_at: datetime
    template: str
    review_status: str = REVIEW_PENDING
    email_sent: bool = False
    recruiter_id: str | None = None
    message: str
