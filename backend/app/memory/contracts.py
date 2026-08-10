"""Typed outputs for inspectable memory retrieval."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.contracts import ContractModel, NonEmptyStr, Score


class SemanticMemoryResult(ContractModel):
    """One sourced, quality-filtered semantic retrieval result."""

    id: UUID
    content: NonEmptyStr
    source_type: NonEmptyStr
    source_uri: NonEmptyStr | None = None
    domain: NonEmptyStr | None = None
    reliability_score: Score
    similarity_score: Score
    valid_until: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    admission_status: NonEmptyStr


class EpisodicMemoryResult(ContractModel):
    """One prior verified case returned for analogical transfer."""

    id: UUID
    source_session_id: UUID
    problem_type: NonEmptyStr
    domain: NonEmptyStr | None = None
    core_question: NonEmptyStr
    outcome_summary: NonEmptyStr
    final_answer: NonEmptyStr
    similarity_score: Score
    created_at: datetime


class MemoryContext(ContractModel):
    """Bounded memory context safe to expose to a reasoning capability."""

    query: NonEmptyStr
    semantic: list[SemanticMemoryResult] = Field(default_factory=list, max_length=3)
    episodes: list[EpisodicMemoryResult] = Field(default_factory=list, max_length=3)
    limitations: list[NonEmptyStr] = Field(default_factory=list)


class ProceduralMemoryResult(ContractModel):
    """Inspectable learned or seeded problem-solving procedure."""

    id: UUID
    name: NonEmptyStr
    problem_type: NonEmptyStr
    gap_type: NonEmptyStr
    action_type: NonEmptyStr
    capability: NonEmptyStr
    preconditions: list[str] = Field(default_factory=list)
    steps: list[dict[str, object]] = Field(default_factory=list)
    verified_successes: int = Field(ge=0)
    verified_failures: int = Field(ge=0)
    success_rate: Score
    source_session_ids: list[str] = Field(default_factory=list)
    updated_at: datetime
