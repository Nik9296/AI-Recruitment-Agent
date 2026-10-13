"""create jobs table

Revision ID: 001_create_jobs
Revises:
Create Date: 2026-09-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_create_jobs"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_title", sa.String(length=512), nullable=True),
        sa.Column("experience_min", sa.Float(), nullable=True),
        sa.Column("experience_max", sa.Float(), nullable=True),
        sa.Column("location", sa.String(length=512), nullable=True),
        sa.Column("work_mode", sa.String(length=32), nullable=True),
        sa.Column("employment_type", sa.String(length=32), nullable=True),
        sa.Column("must_have_skills", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("preferred_skills", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("education", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("responsibilities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_job_description", sa.Text(), nullable=False),
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


def downgrade() -> None:
    op.drop_table("jobs")
