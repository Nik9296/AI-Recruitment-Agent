"""Schemas for human-approval workflow and outreach handoff."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowChangeRequest(BaseModel):
    to_status: str = Field(min_length=1)
    reason: str | None = None


class RecruiterDecisionRequest(BaseModel):
    reason: str | None = None


class WorkflowTransitionRecord(BaseModel):
    id: UUID
    from_status: str | None
    to_status: str
    recruiter_id: str | None
    actor: str
    reason: str | None
    created_at: datetime


class WorkflowHistoryResponse(BaseModel):
    job_id: UUID
    candidate_id: UUID
    workflow_status: str
    review_status: str
    outreach_handed_off: bool
    outreach_handed_off_at: datetime | None = None
    transitions: list[WorkflowTransitionRecord]


class OutreachHandoffRequest(BaseModel):
    reason: str | None = None


class OutreachHandoffResponse(BaseModel):
    job_id: UUID
    candidate_id: UUID
    workflow_status: str
    recruiter_id: str
    handed_off_at: datetime | None = None
    email_sent: bool = False
    queued_for_outreach_agent: bool
    message: str
