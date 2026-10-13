"""Recruiter-reviewable outreach message drafts

Revision ID: 005_outreach_drafts
Revises: 004_human_approval_workflow
Create Date: 2026-09-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_outreach_drafts"
down_revision: Union[str, None] = "004_human_approval_workflow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "outreach_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "template",
            sa.String(length=64),
            nullable=False,
            server_default="initial",
        ),
        sa.Column("subject", sa.String(length=512), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "personalization_points",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("recruiter_id", sa.String(length=128), nullable=True),
        sa.Column(
            "review_status",
            sa.String(length=64),
            nullable=False,
            server_default="pending_recruiter_review",
        ),
        sa.Column(
            "email_sent", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
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
        sa.UniqueConstraint(
            "job_id",
            "candidate_id",
            "template",
            name="uq_outreach_messages_job_candidate_template",
        ),
    )
    op.create_index("ix_outreach_messages_job_id", "outreach_messages", ["job_id"])
    op.create_index(
        "ix_outreach_messages_candidate_id", "outreach_messages", ["candidate_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_outreach_messages_candidate_id", table_name="outreach_messages"
    )
    op.drop_index("ix_outreach_messages_job_id", table_name="outreach_messages")
    op.drop_table("outreach_messages")
