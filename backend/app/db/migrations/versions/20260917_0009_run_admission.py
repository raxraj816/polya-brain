"""Durable daily invocation and concurrency admission.

Revision ID: 20260917_0009
Revises: 20260917_0008
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260917_0009"
down_revision = "20260917_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "run_admissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("problem_sessions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(64), nullable=True),
        sa.Column("resource_limits", postgresql.JSONB(), nullable=False),
    )
    op.create_index("ix_run_admissions_user_started", "run_admissions", ["user_id", "started_at"])
    op.create_index("ix_run_admissions_started", "run_admissions", ["started_at"])
    op.create_index("ix_run_admissions_finished", "run_admissions", ["finished_at"])


def downgrade() -> None:
    raise RuntimeError(
        "Discarding active admissions can permit unbounded work; use a reviewed backup"
    )
