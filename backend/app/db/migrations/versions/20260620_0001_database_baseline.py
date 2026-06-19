"""Create Chapter 4 database baseline.

Revision ID: 20260620_0001
Revises:
Create Date: 2026-06-20
"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260620_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "problem_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=True),
        sa.Column("raw_input", sa.Text(), nullable=False),
        sa.Column("domain", sa.String(length=128), nullable=True),
        sa.Column("mode", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("final_answer", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("verification_status", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_problem_sessions")),
    )
    op.create_index("ix_problem_sessions_created_at", "problem_sessions", ["created_at"])
    op.create_index("ix_problem_sessions_status", "problem_sessions", ["status"])

    op.create_table(
        "structured_problems",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("core_question", sa.Text(), nullable=False),
        sa.Column("problem_type", sa.String(length=128), nullable=False),
        sa.Column("domain", sa.String(length=128), nullable=True),
        sa.Column("knowns", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("unknowns", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("constraints", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("success_criteria", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("affected_entities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("time_window", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("required_data_sources", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["problem_sessions.id"],
            name=op.f("fk_structured_problems_session_id_problem_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_structured_problems")),
        sa.UniqueConstraint("session_id", name=op.f("uq_structured_problems_session_id")),
    )

    op.create_table(
        "artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_type", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("uri_or_storage_key", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("sensitivity", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["problem_sessions.id"],
            name=op.f("fk_artifacts_session_id_problem_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_artifacts")),
    )
    op.create_index("ix_artifacts_session_id", "artifacts", ["session_id"])

    op.create_table(
        "evidence_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(length=128), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=True),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("raw_excerpt", sa.Text(), nullable=True),
        sa.Column("reliability_score", sa.Float(), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column(
            "supports_hypothesis_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "contradicts_hypothesis_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["problem_sessions.id"],
            name=op.f("fk_evidence_items_session_id_problem_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence_items")),
    )
    op.create_index("ix_evidence_items_session_id", "evidence_items", ["session_id"])

    op.create_table(
        "hypotheses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("mechanism", sa.Text(), nullable=True),
        sa.Column("origin", sa.String(length=128), nullable=False),
        sa.Column("analogical_source_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expected_signals", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence_for", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence_against", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("verification_checks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "falsification_criteria", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("selection_rationale", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["problem_sessions.id"],
            name=op.f("fk_hypotheses_session_id_problem_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_hypotheses")),
    )
    op.create_index("ix_hypotheses_session_id", "hypotheses", ["session_id"])

    op.create_table(
        "knowledge_gaps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("gap_type", sa.String(length=128), nullable=False),
        sa.Column("priority", sa.String(length=64), nullable=False),
        sa.Column("why_needed", sa.Text(), nullable=False),
        sa.Column("suggested_source", sa.Text(), nullable=True),
        sa.Column("filled", sa.Boolean(), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["problem_sessions.id"],
            name=op.f("fk_knowledge_gaps_session_id_problem_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_gaps")),
    )
    op.create_index("ix_knowledge_gaps_session_id", "knowledge_gaps", ["session_id"])

    op.create_table(
        "plan_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("tool_name", sa.String(length=128), nullable=True),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("depends_on", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expected_output", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["problem_sessions.id"],
            name=op.f("fk_plan_tasks_session_id_problem_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plan_tasks")),
    )
    op.create_index("ix_plan_tasks_session_id", "plan_tasks", ["session_id"])

    op.create_table(
        "reasoning_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("engine_name", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("reasoning_mode", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["problem_sessions.id"],
            name=op.f("fk_reasoning_events_session_id_problem_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reasoning_events")),
    )
    op.create_index("ix_reasoning_events_created_at", "reasoning_events", ["created_at"])
    op.create_index("ix_reasoning_events_session_id", "reasoning_events", ["session_id"])

    op.create_table(
        "verification_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("checks_run", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("failed_checks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("contradictions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence_delta", sa.Float(), nullable=True),
        sa.Column("recommended_route", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["problem_sessions.id"],
            name=op.f("fk_verification_reports_session_id_problem_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_verification_reports")),
    )
    op.create_index("ix_verification_reports_session_id", "verification_reports", ["session_id"])

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_artifact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("source_type", sa.String(length=128), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("embedding_provider", sa.String(length=128), nullable=True),
        sa.Column("embedding_model", sa.String(length=255), nullable=True),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=True),
        sa.Column("embedding", pgvector.sqlalchemy.VECTOR(dim=1536), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["problem_sessions.id"],
            name=op.f("fk_knowledge_chunks_session_id_problem_sessions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_artifact_id"],
            ["artifacts.id"],
            name=op.f("fk_knowledge_chunks_source_artifact_id_artifacts"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_chunks")),
    )
    op.create_index("ix_knowledge_chunks_session_id", "knowledge_chunks", ["session_id"])
    op.create_index(
        "ix_knowledge_chunks_source_artifact_id", "knowledge_chunks", ["source_artifact_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_source_artifact_id", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_session_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.drop_index("ix_verification_reports_session_id", table_name="verification_reports")
    op.drop_table("verification_reports")
    op.drop_index("ix_reasoning_events_session_id", table_name="reasoning_events")
    op.drop_index("ix_reasoning_events_created_at", table_name="reasoning_events")
    op.drop_table("reasoning_events")
    op.drop_index("ix_plan_tasks_session_id", table_name="plan_tasks")
    op.drop_table("plan_tasks")
    op.drop_index("ix_knowledge_gaps_session_id", table_name="knowledge_gaps")
    op.drop_table("knowledge_gaps")
    op.drop_index("ix_hypotheses_session_id", table_name="hypotheses")
    op.drop_table("hypotheses")
    op.drop_index("ix_evidence_items_session_id", table_name="evidence_items")
    op.drop_table("evidence_items")
    op.drop_index("ix_artifacts_session_id", table_name="artifacts")
    op.drop_table("artifacts")
    op.drop_table("structured_problems")
    op.drop_index("ix_problem_sessions_status", table_name="problem_sessions")
    op.drop_index("ix_problem_sessions_created_at", table_name="problem_sessions")
    op.drop_table("problem_sessions")
    op.execute("DROP EXTENSION IF EXISTS vector")
