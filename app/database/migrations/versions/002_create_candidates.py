"""create candidate tables

Revision ID: 002_create_candidates
Revises: 001_create_jobs
Create Date: 2026-09-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_create_candidates"
down_revision: Union[str, None] = "001_create_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("full_name", sa.String(length=512), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("email_normalized", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("phone_digits", sa.String(length=32), nullable=True),
        sa.Column("location", sa.String(length=512), nullable=True),
        sa.Column("current_job_title", sa.String(length=512), nullable=True),
        sa.Column("total_experience_years", sa.Float(), nullable=True),
        sa.Column("notice_period", sa.String(length=128), nullable=True),
        sa.Column("availability", sa.String(length=256), nullable=True),
        sa.Column("work_authorization", sa.String(length=256), nullable=True),
        sa.Column("resume_summary", sa.Text(), nullable=True),
        sa.Column("education", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("certifications", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("companies", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("previous_roles", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("projects", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("achievements", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("industries", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("technical_skills", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("soft_skills", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("skills", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="parsed"),
        sa.Column("embedding", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("embedding_model", sa.String(length=128), nullable=True),
        sa.Column("embedding_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "uq_candidates_email_normalized",
        "candidates",
        ["email_normalized"],
        unique=True,
        postgresql_where=sa.text("email_normalized IS NOT NULL"),
    )
    op.create_index(
        "uq_candidates_phone_digits",
        "candidates",
        ["phone_digits"],
        unique=True,
        postgresql_where=sa.text("phone_digits IS NOT NULL"),
    )
    op.create_index("ix_candidates_status", "candidates", ["status"])
    op.create_index("ix_candidates_location", "candidates", ["location"])
    op.create_index(
        "ix_candidates_current_job_title", "candidates", ["current_job_title"]
    )

    op.create_table(
        "candidate_skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skill_name", sa.String(length=256), nullable=False),
        sa.Column("canonical_name", sa.String(length=256), nullable=False),
        sa.Column("skill_kind", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "uq_candidate_skills_canonical",
        "candidate_skills",
        ["candidate_id", "canonical_name", "skill_kind"],
        unique=True,
    )
    op.create_index(
        "ix_candidate_skills_canonical_name",
        "candidate_skills",
        ["canonical_name"],
    )

    op.create_table(
        "candidate_resumes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_name", sa.String(length=512), nullable=True),
        sa.Column("file_path", sa.String(length=1024), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("byte_size", sa.Integer(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "candidate_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_candidate_events_candidate_id", "candidate_events", ["candidate_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_candidate_events_candidate_id", table_name="candidate_events")
    op.drop_table("candidate_events")
    op.drop_table("candidate_resumes")
    op.drop_index("ix_candidate_skills_canonical_name", table_name="candidate_skills")
    op.drop_index("uq_candidate_skills_canonical", table_name="candidate_skills")
    op.drop_table("candidate_skills")
    op.drop_index("ix_candidates_current_job_title", table_name="candidates")
    op.drop_index("ix_candidates_location", table_name="candidates")
    op.drop_index("ix_candidates_status", table_name="candidates")
    op.drop_index("uq_candidates_phone_digits", table_name="candidates")
    op.drop_index("uq_candidates_email_normalized", table_name="candidates")
    op.drop_table("candidates")
