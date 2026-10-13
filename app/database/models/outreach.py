"""Persisted recruiter-reviewable outreach drafts. Email is not sent."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base
from app.models.outreach import REVIEW_PENDING, OutreachTemplateType


class OutreachMessageRecord(Base):
    __tablename__ = "outreach_messages"
    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "candidate_id",
            "template",
            name="uq_outreach_messages_job_candidate_template",
        ),
        Index("ix_outreach_messages_job_id", "job_id"),
        Index("ix_outreach_messages_candidate_id", "candidate_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    template: Mapped[str] = mapped_column(
        String(64), nullable=False, default=OutreachTemplateType.INITIAL.value
    )
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    personalization_points: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )
    recruiter_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    review_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default=REVIEW_PENDING
    )
    email_sent: Mapped[bool] = mapped_column(nullable=False, default=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
