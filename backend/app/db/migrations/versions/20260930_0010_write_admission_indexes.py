"""Index durable write counts without rewriting existing records."""

from alembic import op

revision = "20260930_0010"
down_revision = "20260917_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_problem_sessions_user_created", "problem_sessions", ["user_id", "created_at"]
    )
    op.create_index("ix_human_feedback_created", "human_feedback", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_human_feedback_created", table_name="human_feedback")
    op.drop_index("ix_problem_sessions_user_created", table_name="problem_sessions")
