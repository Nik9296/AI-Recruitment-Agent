"""create job_candidates and explicit open-to-work columns

Revision ID: 003_recruiter_dashboard
Revises: 002_create_candidates
Create Date: 2026-09-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_recruiter_dashboard"
down_revision: Union[str, None] = "002_create_candidates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "candidates",
        sa.Column(
            "open_to_work_status",
            sa.String(length=32),
            nullable=False,
            server_default="UNKNOWN",
        ),
    )
    op.add_column(
        "candidates",
        sa.Column("open_to_work_source", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "candidates",
        sa.Column("open_to_work_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "job_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column(
            "matched_requirements",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "missing_requirements",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "review_status",
            sa.String(length=32),
            nullable=False,
            server_default="pending",
        ),
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
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("job_id", "candidate_id", name="uq_job_candidates_job_candidate"),
    )
    op.create_index("ix_job_candidates_job_id", "job_candidates", ["job_id"])
    op.create_index(
        "ix_job_candidates_review_status", "job_candidates", ["review_status"]
    )


def downgrade() -> None:
    op.drop_index("ix_job_candidates_review_status", table_name="job_candidates")
    op.drop_index("ix_job_candidates_job_id", table_name="job_candidates")
    op.drop_table("job_candidates")
    op.drop_column("candidates", "open_to_work_verified_at")
    op.drop_column("candidates", "open_to_work_source")
    op.drop_column("candidates", "open_to_work_status")
