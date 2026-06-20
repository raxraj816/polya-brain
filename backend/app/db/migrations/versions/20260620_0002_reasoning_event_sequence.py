"""Add deterministic reasoning event sequence ordering.

Revision ID: 20260620_0002
Revises: 20260620_0001
Create Date: 2026-06-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260620_0002"
down_revision: str | None = "20260620_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("reasoning_events", sa.Column("sequence_number", sa.Integer(), nullable=True))
    op.execute(
        """
        with ordered_events as (
            select
                id,
                row_number() over (
                    partition by session_id
                    order by created_at, id
                ) - 1 as sequence_number
            from reasoning_events
        )
        update reasoning_events
        set sequence_number = ordered_events.sequence_number
        from ordered_events
        where reasoning_events.id = ordered_events.id
        """
    )
    op.alter_column("reasoning_events", "sequence_number", nullable=False)
    op.create_index(
        "ix_reasoning_events_session_sequence",
        "reasoning_events",
        ["session_id", "sequence_number"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_reasoning_events_session_sequence", table_name="reasoning_events")
    op.drop_column("reasoning_events", "sequence_number")
