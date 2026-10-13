"""Candidate persistence models. Isolated from the Resume Agent."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base

CANDIDATE_STATUS_PARSED = "parsed"


class Candidate(Base):
    """Stored candidate profile. Resume bytes live outside PostgreSQL."""

    __tablename__ = "candidates"
    __table_args__ = (
        Index(
            "uq_candidates_email_normalized",
            "email_normalized",
            unique=True,
            postgresql_where=text("email_normalized IS NOT NULL"),
        ),
        Index(
            "uq_candidates_phone_digits",
            "phone_digits",
            unique=True,
            postgresql_where=text("phone_digits IS NOT NULL"),
        ),
        Index("ix_candidates_status", "status"),
        Index("ix_candidates_location", "location"),
        Index("ix_candidates_current_job_title", "current_job_title"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    full_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    email_normalized: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone_digits: Mapped[str | None] = mapped_column(String(32), nullable=True)
    location: Mapped[str | None] = mapped_column(String(512), nullable=True)
    current_job_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    total_experience_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    notice_period: Mapped[str | None] = mapped_column(String(128), nullable=True)
    availability: Mapped[str | None] = mapped_column(String(256), nullable=True)
    work_authorization: Mapped[str | None] = mapped_column(String(256), nullable=True)
    resume_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    education: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    certifications: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    companies: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    previous_roles: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    projects: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    achievements: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    industries: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    technical_skills: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    soft_skills: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    skills: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=CANDIDATE_STATUS_PARSED
    )
    embedding: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    embedding_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    open_to_work_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="UNKNOWN"
    )
    open_to_work_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    open_to_work_verified_at: Mapped[datetime | None] = mapped_column(
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

    skill_rows: Mapped[list[CandidateSkill]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
    )
    resumes: Mapped[list[CandidateResume]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="CandidateResume.created_at",
    )
    events: Mapped[list[CandidateEvent]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="CandidateEvent.created_at",
    )


class CandidateSkill(Base):
    """Normalized skills for search and later JD matching."""

    __tablename__ = "candidate_skills"
    __table_args__ = (
        Index(
            "uq_candidate_skills_canonical",
            "candidate_id",
            "canonical_name",
            "skill_kind",
            unique=True,
        ),
        Index("ix_candidate_skills_canonical_name", "canonical_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_name: Mapped[str] = mapped_column(String(256), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(256), nullable=False)
    skill_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    candidate: Mapped[Candidate] = relationship(back_populates="skill_rows")


class CandidateResume(Base):
    """Resume file metadata. The binary is stored outside the database."""

    __tablename__ = "candidate_resumes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    byte_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    candidate: Mapped[Candidate] = relationship(back_populates="resumes")


class CandidateEvent(Base):
    """Append-only audit events for review, outreach, and scheduling later."""

    __tablename__ = "candidate_events"
    __table_args__ = (Index("ix_candidate_events_candidate_id", "candidate_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    candidate: Mapped[Candidate] = relationship(back_populates="events")
