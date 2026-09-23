"""Opaque authentication sessions and isolated private memory namespaces.

Revision ID: 20260917_0008
Revises: 20260914_0007
"""

import sqlalchemy as sa
from alembic import op

revision = "20260917_0008"
down_revision = "20260914_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])
    for table in ("knowledge_chunks", "episodic_memories", "procedural_strategies"):
        op.add_column(
            table, sa.Column("owner_id", sa.String(128), nullable=False, server_default="__local__")
        )
        op.create_index(f"ix_{table}_owner_id", table, ["owner_id"])
    op.drop_constraint("uq_procedural_strategy_signature", "procedural_strategies", type_="unique")
    op.create_unique_constraint(
        "uq_procedural_strategy_signature",
        "procedural_strategies",
        ["owner_id", "problem_type", "gap_type", "action_type", "capability"],
    )
    op.create_index("ix_problem_sessions_user_id", "problem_sessions", ["user_id"])


def downgrade() -> None:
    # Merging private namespaces would leak data and can collide on signatures.
    raise RuntimeError(
        "Ownership migration is intentionally irreversible; restore a reviewed backup"
    )
