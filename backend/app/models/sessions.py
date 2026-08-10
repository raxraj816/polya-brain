"""API models for Chapter 10 problem sessions."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.contracts import ContractModel, NonEmptyStr, ProductMode, Score


class CreateSessionRequest(ContractModel):
    """Create a new PolyaBrain problem session."""

    raw_input: NonEmptyStr = Field(
        examples=[
            "Our API p95 latency jumped after deploy. Should we add Redis or inspect queries first?"
        ]
    )
    mode: ProductMode = ProductMode.INVESTIGATE
    domain: NonEmptyStr | None = None


class SessionResponse(ContractModel):
    """Public summary for one problem session."""

    id: UUID
    raw_input: NonEmptyStr
    domain: NonEmptyStr | None = None
    mode: ProductMode
    status: NonEmptyStr
    created_at: datetime
    completed_at: datetime | None = None
    final_answer: NonEmptyStr | None = None
    confidence: Score | None = None
    verification_status: NonEmptyStr | None = None


class RunSessionResponse(SessionResponse):
    """Session summary returned after a synchronous Chapter 10 run."""

    event_count: int = Field(ge=0)
    clarifying_questions: list[NonEmptyStr] = Field(default_factory=list)


class ClarificationAnswerRequest(ContractModel):
    """User-owned information supplied to resume a paused session."""

    answer: NonEmptyStr


class SessionReportEvidence(ContractModel):
    """One concise evidence item exposed in the user-facing report."""

    source_type: NonEmptyStr
    source_uri: NonEmptyStr | None = None
    claim: NonEmptyStr
    reliability_score: Score | None = None
    relevance_score: Score | None = None


class SessionReportResponse(ContractModel):
    """Auditable problem-solving result for one persisted session."""

    session_id: UUID
    final_conclusion: NonEmptyStr | None = None
    confidence_level: NonEmptyStr
    verification_status: NonEmptyStr
    evidence_used: list[SessionReportEvidence] = Field(default_factory=list)
    evidence_against: list[SessionReportEvidence] = Field(default_factory=list)
    checks_performed: list[NonEmptyStr] = Field(default_factory=list)
    failed_checks: list[NonEmptyStr] = Field(default_factory=list)
    contradictions: list[NonEmptyStr] = Field(default_factory=list)
    open_questions: list[NonEmptyStr] = Field(default_factory=list)
    recommended_next_action: NonEmptyStr
    reflection: dict[str, object] | None = None
    audit_trace_path: NonEmptyStr
