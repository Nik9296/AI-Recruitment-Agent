"""Recorded outbound email sends

Revision ID: 006_email_sends
Revises: 005_outreach_drafts
Create Date: 2026-09-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006_email_sends"
down_revision: Union[str, None] = "005_outreach_drafts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_sends",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("message_id", sa.String(length=256), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient", sa.String(length=320), nullable=False),
        sa.Column(
            "template", sa.String(length=64), nullable=False, server_default="initial"
        ),
        sa.Column("delivery_status", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("recruiter_id", sa.String(length=128), nullable=True),
        sa.Column(
            "sent_at",
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
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "job_id",
            "candidate_id",
            "template",
            name="uq_email_sends_job_candidate_template",
        ),
        sa.UniqueConstraint("message_id", name="uq_email_sends_message_id"),
    )
    op.create_index("ix_email_sends_job_id", "email_sends", ["job_id"])
    op.create_index("ix_email_sends_candidate_id", "email_sends", ["candidate_id"])
    op.create_index(
        "ix_email_sends_delivery_status", "email_sends", ["delivery_status"]
    )


def downgrade() -> None:
    op.drop_index("ix_email_sends_delivery_status", table_name="email_sends")
    op.drop_index("ix_email_sends_candidate_id", table_name="email_sends")
    op.drop_index("ix_email_sends_job_id", table_name="email_sends")
    op.drop_table("email_sends")
