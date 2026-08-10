"""Add governed semantic, episodic, and procedural memory.

Revision ID: 20260809_0005
Revises: 20260809_0004
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260809_0005"
down_revision: str | None = "20260809_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("knowledge_chunks", sa.Column("domain", sa.String(128), nullable=True))
    op.add_column(
        "knowledge_chunks",
        sa.Column("reliability_score", sa.Float(), nullable=False, server_default="0.5"),
    )
    op.add_column(
        "knowledge_chunks", sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "knowledge_chunks",
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "knowledge_chunks",
        sa.Column(
            "admission_status",
            sa.String(64),
            nullable=False,
            server_default="legacy_seed",
        ),
    )
    op.create_index("ix_knowledge_chunks_domain", "knowledge_chunks", ["domain"])
    op.create_index("ix_knowledge_chunks_valid_until", "knowledge_chunks", ["valid_until"])

    op.create_table(
        "episodic_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("problem_type", sa.String(128), nullable=False),
        sa.Column("domain", sa.String(128), nullable=True),
        sa.Column("core_question", sa.Text(), nullable=False),
        sa.Column("outcome_summary", sa.Text(), nullable=False),
        sa.Column("final_answer", sa.Text(), nullable=False),
        sa.Column("verification_checks", postgresql.JSONB(), nullable=False),
        sa.Column("reflection", postgresql.JSONB(), nullable=False),
        sa.Column("evidence_source_uris", postgresql.JSONB(), nullable=False),
        sa.Column("embedding_provider", sa.String(128), nullable=False),
        sa.Column("embedding_model", sa.String(255), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.VECTOR(dim=1536), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_session_id"], ["problem_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_session_id"),
    )
    op.create_index("ix_episodic_memories_problem_type", "episodic_memories", ["problem_type"])
    op.create_index("ix_episodic_memories_domain", "episodic_memories", ["domain"])
    op.create_index("ix_episodic_memories_created_at", "episodic_memories", ["created_at"])

    op.create_table(
        "procedural_strategies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("problem_type", sa.String(128), nullable=False),
        sa.Column("gap_type", sa.String(128), nullable=False),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("capability", sa.String(128), nullable=False),
        sa.Column("preconditions", postgresql.JSONB(), nullable=False),
        sa.Column("steps", postgresql.JSONB(), nullable=False),
        sa.Column("verified_successes", sa.Integer(), nullable=False),
        sa.Column("verified_failures", sa.Integer(), nullable=False),
        sa.Column("success_rate", sa.Float(), nullable=False),
        sa.Column("source_session_ids", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "problem_type",
            "gap_type",
            "action_type",
            "capability",
            name="uq_procedural_strategy_signature",
        ),
    )
    op.create_index(
        "ix_procedural_strategies_problem_gap",
        "procedural_strategies",
        ["problem_type", "gap_type"],
    )
    op.create_index(
        "ix_procedural_strategies_success_rate", "procedural_strategies", ["success_rate"]
    )


def downgrade() -> None:
    op.drop_index("ix_procedural_strategies_success_rate", table_name="procedural_strategies")
    op.drop_index("ix_procedural_strategies_problem_gap", table_name="procedural_strategies")
    op.drop_table("procedural_strategies")
    op.drop_index("ix_episodic_memories_created_at", table_name="episodic_memories")
    op.drop_index("ix_episodic_memories_domain", table_name="episodic_memories")
    op.drop_index("ix_episodic_memories_problem_type", table_name="episodic_memories")
    op.drop_table("episodic_memories")
    op.drop_index("ix_knowledge_chunks_valid_until", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_domain", table_name="knowledge_chunks")
    op.drop_column("knowledge_chunks", "admission_status")
    op.drop_column("knowledge_chunks", "tags")
    op.drop_column("knowledge_chunks", "valid_until")
    op.drop_column("knowledge_chunks", "reliability_score")
    op.drop_column("knowledge_chunks", "domain")
