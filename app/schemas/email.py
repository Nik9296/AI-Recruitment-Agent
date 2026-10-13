"""API schemas for recruiter-authorized email sends."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.outreach import OutreachTemplateType


class EmailSendRequest(BaseModel):
    template: OutreachTemplateType = OutreachTemplateType.INITIAL


class EmailSendResponse(BaseModel):
    message_id: str
    candidate_id: UUID
    job_id: UUID
    recipient: str
    sent_at: datetime
    delivery_status: str
    template: str
    provider: str
    dry_run: bool
    email_sent: bool
    recruiter_id: str | None = None
    message: str
