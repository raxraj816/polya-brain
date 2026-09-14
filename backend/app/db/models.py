"""SQLAlchemy models for the Chapter 4 durable MVP database baseline."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    """Return a timezone-aware timestamp for Python-side defaults."""
    return datetime.now(UTC)


class ProblemSession(Base):
    """Top-level record for one PolyaBrain problem-solving run."""

    __tablename__ = "problem_sessions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_input: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mode: Mapped[str] = mapped_column(String(64), nullable=False, default="investigate")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="created")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    run_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    final_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    verification_status: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        Index("ix_problem_sessions_status", "status"),
        Index("ix_problem_sessions_created_at", "created_at"),
        Index("ix_problem_sessions_run_started_at", "run_started_at"),
    )


class HumanFeedback(Base):
    """User corrections for manual review; never automatic verified knowledge."""

    __tablename__ = "human_feedback"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("problem_sessions.id", ondelete="CASCADE"), nullable=False
    )
    feedback_type: Mapped[str] = mapped_column(String(32), nullable=False)
    correction: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    __table_args__ = (Index("ix_human_feedback_session_created", "session_id", "created_at"),)


class ClarificationRequest(Base):
    """One persisted pause for missing user-owned information."""

    __tablename__ = "clarification_requests"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("problem_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    questions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="pending")
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_clarification_requests_session_id", "session_id"),
        Index("ix_clarification_requests_session_status", "session_id", "status"),
        Index("ix_clarification_requests_expires_at", "expires_at"),
    )


class StructuredProblem(Base):
    """Structured representation produced from raw problem input."""

    __tablename__ = "structured_problems"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("problem_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    core_question: Mapped[str] = mapped_column(Text, nullable=False)
    problem_type: Mapped[str] = mapped_column(String(128), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(128), nullable=True)
    knowns: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    unknowns: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    constraints: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    success_criteria: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    affected_entities: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    time_window: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    required_data_sources: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)


class KnowledgeGap(Base):
    """Missing information that must be resolved or explicitly carried forward."""

    __tablename__ = "knowledge_gaps"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("problem_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    gap_type: Mapped[str] = mapped_column(String(128), nullable=False)
    priority: Mapped[str] = mapped_column(String(64), nullable=False, default="medium")
    why_needed: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    filled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evidence_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)

    __table_args__ = (Index("ix_knowledge_gaps_session_id", "session_id"),)


class EvidenceItem(Base):
    """Evidence item with source, claim, and relevance metadata."""

    __tablename__ = "evidence_items"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("problem_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(128), nullable=False)
    source_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    raw_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    reliability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    supports_hypothesis_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    contradicts_hypothesis_ids: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list
    )

    __table_args__ = (Index("ix_evidence_items_session_id", "session_id"),)


class Hypothesis(Base):
    """Candidate explanation or solution path under investigation."""

    __tablename__ = "hypotheses"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("problem_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    mechanism: Mapped[str | None] = mapped_column(Text, nullable=True)
    origin: Mapped[str] = mapped_column(String(128), nullable=False)
    analogical_source_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    expected_signals: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    evidence_for: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    evidence_against: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    verification_checks: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    falsification_criteria: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    selection_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="candidate")

    __table_args__ = (Index("ix_hypotheses_session_id", "session_id"),)


class PlanTask(Base):
    """Executable or proposed investigation step."""

    __tablename__ = "plan_tasks"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("problem_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)
    tool_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    depends_on: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(64), nullable=False, default="low")

    __table_args__ = (Index("ix_plan_tasks_session_id", "session_id"),)


class ReasoningEvent(Base):
    """User-visible trace event from one engine or product stage."""

    __tablename__ = "reasoning_events"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("problem_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    engine_name: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    reasoning_mode: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    event_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        Index("ix_reasoning_events_session_id", "session_id"),
        Index("ix_reasoning_events_session_sequence", "session_id", "sequence_number", unique=True),
        Index("ix_reasoning_events_created_at", "created_at"),
    )


class VerificationReport(Base):
    """Verification result for a session or checkpoint."""

    __tablename__ = "verification_reports"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("problem_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    checks_run: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    failed_checks: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    contradictions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    confidence_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    recommended_route: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (Index("ix_verification_reports_session_id", "session_id"),)


class Artifact(Base):
    """Stored or referenced artifact used by a problem-solving session."""

    __tablename__ = "artifacts"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("problem_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_type: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    uri_or_storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    artifact_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    sensitivity: Mapped[str] = mapped_column(String(64), nullable=False, default="internal")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (Index("ix_artifacts_session_id", "session_id"),)


class KnowledgeChunk(Base):
    """Semantic memory chunk with optional pgvector embedding."""

    __tablename__ = "knowledge_chunks"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("problem_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_artifact_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_type: Mapped[str] = mapped_column(String(128), nullable=False)
    source_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reliability_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tags: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    admission_status: Mapped[str] = mapped_column(String(64), nullable=False, default="evaluated")
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    embedding_provider: Mapped[str | None] = mapped_column(String(128), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    embedding_dimensions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(VECTOR(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        Index("ix_knowledge_chunks_session_id", "session_id"),
        Index("ix_knowledge_chunks_source_artifact_id", "source_artifact_id"),
        Index("ix_knowledge_chunks_domain", "domain"),
        Index("ix_knowledge_chunks_valid_until", "valid_until"),
    )


class EpisodicMemory(Base):
    """A completed, verified problem-solving episode available for transfer."""

    __tablename__ = "episodic_memories"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("problem_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    problem_type: Mapped[str] = mapped_column(String(128), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(128), nullable=True)
    core_question: Mapped[str] = mapped_column(Text, nullable=False)
    outcome_summary: Mapped[str] = mapped_column(Text, nullable=False)
    final_answer: Mapped[str] = mapped_column(Text, nullable=False)
    verification_checks: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    reflection: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    evidence_source_uris: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    embedding_provider: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(255), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(VECTOR(1536), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        Index("ix_episodic_memories_problem_type", "problem_type"),
        Index("ix_episodic_memories_domain", "domain"),
        Index("ix_episodic_memories_created_at", "created_at"),
    )


class ProceduralStrategy(Base):
    """A reusable action preference learned only from verified outcomes."""

    __tablename__ = "procedural_strategies"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    problem_type: Mapped[str] = mapped_column(String(128), nullable=False)
    gap_type: Mapped[str] = mapped_column(String(128), nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    capability: Mapped[str] = mapped_column(String(128), nullable=False)
    preconditions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    steps: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    verified_successes: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    verified_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_rate: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source_session_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        UniqueConstraint(
            "problem_type",
            "gap_type",
            "action_type",
            "capability",
            name="uq_procedural_strategy_signature",
        ),
        Index("ix_procedural_strategies_problem_gap", "problem_type", "gap_type"),
        Index("ix_procedural_strategies_success_rate", "success_rate"),
    )
