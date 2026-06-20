"""Add session run start timestamp.

Revision ID: 20260620_0003
Revises: 20260620_0002
Create Date: 2026-06-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260620_0003"
down_revision: str | None = "20260620_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "problem_sessions",
        sa.Column("run_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Supports future stale-run sweep queries; current recovery is per-session.
    op.create_index("ix_problem_sessions_run_started_at", "problem_sessions", ["run_started_at"])


def downgrade() -> None:
    op.drop_index("ix_problem_sessions_run_started_at", table_name="problem_sessions")
    op.drop_column("problem_sessions", "run_started_at")
