"""Add persisted clarification requests.

Revision ID: 20260809_0004
Revises: 20260620_0003
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260809_0004"
down_revision: str | None = "20260620_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "clarification_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("questions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["problem_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_clarification_requests_session_id",
        "clarification_requests",
        ["session_id"],
    )
    op.create_index(
        "ix_clarification_requests_session_status",
        "clarification_requests",
        ["session_id", "status"],
    )
    op.create_index(
        "ix_clarification_requests_expires_at",
        "clarification_requests",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_clarification_requests_expires_at",
        table_name="clarification_requests",
    )
    op.drop_index(
        "ix_clarification_requests_session_status",
        table_name="clarification_requests",
    )
    op.drop_index(
        "ix_clarification_requests_session_id",
        table_name="clarification_requests",
    )
    op.drop_table("clarification_requests")
