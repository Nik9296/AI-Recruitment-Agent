"""workflow_status, transition history, and outreach handoff queue

Revision ID: 004_human_approval_workflow
Revises: 003_recruiter_dashboard
Create Date: 2026-09-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_human_approval_workflow"
down_revision: Union[str, None] = "003_recruiter_dashboard"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "job_candidates",
        sa.Column(
            "workflow_status",
            sa.String(length=32),
            nullable=False,
            server_default="PENDING_REVIEW",
        ),
    )
    op.add_column(
        "job_candidates",
        sa.Column("outreach_handed_off_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_job_candidates_workflow_status", "job_candidates", ["workflow_status"]
    )
    op.execute(
        """
        UPDATE job_candidates
        SET workflow_status = CASE review_status
            WHEN 'approved' THEN 'APPROVED_FOR_OUTREACH'
            WHEN 'rejected' THEN 'REJECTED'
            WHEN 'on_hold' THEN 'ON_HOLD'
            ELSE 'PENDING_REVIEW'
        END
        """
    )
    op.create_table(
        "job_candidate_transitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("recruiter_id", sa.String(length=128), nullable=True),
        sa.Column("actor", sa.String(length=32), nullable=False, server_default="system"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_candidate_id"], ["job_candidates.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_job_candidate_transitions_job_candidate_id",
        "job_candidate_transitions",
        ["job_candidate_id"],
    )
    op.create_index(
        "ix_job_candidate_transitions_job_id", "job_candidate_transitions", ["job_id"]
    )
    op.create_index(
        "ix_job_candidate_transitions_created_at",
        "job_candidate_transitions",
        ["created_at"],
    )
    op.create_table(
        "outreach_handoffs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recruiter_id", sa.String(length=128), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("email_sent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("job_id", "candidate_id", name="uq_outreach_handoffs_job_candidate"),
    )
    op.create_index("ix_outreach_handoffs_job_id", "outreach_handoffs", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_outreach_handoffs_job_id", table_name="outreach_handoffs")
    op.drop_table("outreach_handoffs")
    op.drop_index(
        "ix_job_candidate_transitions_created_at", table_name="job_candidate_transitions"
    )
    op.drop_index(
        "ix_job_candidate_transitions_job_id", table_name="job_candidate_transitions"
    )
    op.drop_index(
        "ix_job_candidate_transitions_job_candidate_id",
        table_name="job_candidate_transitions",
    )
    op.drop_table("job_candidate_transitions")
    op.drop_index("ix_job_candidates_workflow_status", table_name="job_candidates")
    op.drop_column("job_candidates", "outreach_handed_off_at")
    op.drop_column("job_candidates", "workflow_status")
