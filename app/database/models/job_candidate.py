"""Job-candidate match snapshot and recruiter review. Isolated from agents."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base

from app.workflow.states import WorkflowState

REVIEW_PENDING = "pending"
REVIEW_APPROVED = "approved"
REVIEW_REJECTED = "rejected"
REVIEW_ON_HOLD = "on_hold"


class JobCandidate(Base):
    __tablename__ = "job_candidates"
    __table_args__ = (
        UniqueConstraint("job_id", "candidate_id", name="uq_job_candidates_job_candidate"),
        Index("ix_job_candidates_job_id", "job_id"),
        Index("ix_job_candidates_review_status", "review_status"),
        Index("ix_job_candidates_workflow_status", "workflow_status"),
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
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    matched_requirements: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    missing_requirements: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    review_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=REVIEW_PENDING
    )
    workflow_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=WorkflowState.PENDING_REVIEW.value
    )
    outreach_handed_off_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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
    transitions: Mapped[list["JobCandidateTransition"]] = relationship(
        back_populates="job_candidate",
        cascade="all, delete-orphan",
        order_by="JobCandidateTransition.created_at",
    )
