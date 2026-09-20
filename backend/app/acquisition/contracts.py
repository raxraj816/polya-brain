"""Experimental contracts for source discovery and bounded research."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import AnyHttpUrl, Field, JsonValue, field_validator

from app.models.contracts import ContractModel, NonEmptyStr, RiskLevel, Score


class DataSourceKind(StrEnum):
    """Kinds of external or local observations available to the controller."""

    HUMAN = "human"
    LOCAL_ARTIFACT = "local_artifact"
    WEB_SEARCH = "web_search"
    API = "api"
    DATABASE = "database"
    MEMORY = "memory"
    MEASUREMENT = "measurement"
    CALCULATOR = "calculator"
    CODE_EXECUTION = "code_execution"
    SIMULATION = "simulation"
    EXPERIMENT = "experiment"


class DataSourceDefinition(ContractModel):
    """Auditable description of a source the gap detector may request."""

    name: NonEmptyStr
    kind: DataSourceKind
    description: NonEmptyStr
    capability: NonEmptyStr
    available: bool = True
    approved_for_sensitive_data: bool = False
    risk_level: RiskLevel = RiskLevel.LOW


class ResearchBudget(ContractModel):
    """Hard per-run limits that keep curiosity bounded."""

    max_queries: Annotated[int, Field(ge=1, le=20)] = 3
    max_results_per_query: Annotated[int, Field(ge=1, le=20)] = 5
    max_total_candidates: Annotated[int, Field(ge=1, le=100)] = 15


class SearchRequest(ContractModel):
    """Provider-neutral web-search request."""

    query: NonEmptyStr
    max_results: Annotated[int, Field(ge=1, le=20)] = 5
    country: str = Field(default="US", min_length=2, max_length=2)
    search_language: str = Field(default="en", min_length=2, max_length=8)

    @field_validator("query")
    @classmethod
    def query_must_fit_provider_safe_bound(cls, value: str) -> str:
        """Enforce the strictest supported search boundary before network I/O."""
        if len(value) > 400:
            raise ValueError("search query must be at most 400 characters")
        if len(value.split()) > 50:
            raise ValueError("search query must contain at most 50 words")
        return value


class SearchResultCandidate(ContractModel):
    """Untrusted search result awaiting evidence evaluation."""

    id: NonEmptyStr
    title: NonEmptyStr
    url: AnyHttpUrl
    excerpt: NonEmptyStr
    provider_rank: Annotated[int, Field(ge=1)]
    provider_score: Score | None = None
    extra_snippets: list[NonEmptyStr] = Field(default_factory=list)
    published_at: datetime | None = None


class EvidenceCandidate(ContractModel):
    """Source-neutral untrusted observation awaiting evidence evaluation."""

    id: NonEmptyStr
    source_type: NonEmptyStr
    source_uri: NonEmptyStr
    title: NonEmptyStr
    excerpt: NonEmptyStr
    source_rank: Annotated[int, Field(ge=1)]
    source_score: Score | None = None
    published_at: datetime | None = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvidenceRelationship(StrEnum):
    """How an extracted claim relates to the blocking knowledge gap."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    BACKGROUND = "background"
    REJECT = "reject"


class TemporalValidity(StrEnum):
    """Inspectible freshness classification for one candidate."""

    CURRENT = "current"
    STALE = "stale"
    TIMELESS = "timeless"
    UNKNOWN = "unknown"


class EvidenceCandidateAssessment(ContractModel):
    """Bounded semantic assessment proposed for one staged candidate."""

    candidate_id: NonEmptyStr
    extracted_claim: NonEmptyStr
    relationship: EvidenceRelationship
    relevance_score: Score
    reliability_score: Score
    temporal_validity: TemporalValidity
    contradiction_risk: Score
    contradicts_candidate_ids: list[NonEmptyStr] = Field(default_factory=list)
    rationale: NonEmptyStr

    @field_validator("extracted_claim")
    @classmethod
    def keep_null_visible_in_generated_claim(cls, value: str) -> str:
        """Keep malformed model text inspectable and representable in storage."""
        return value.replace("\x00", r"\u0000")


class ResearchContinuation(ContractModel):
    """Optional hint for filling a public gap using already evaluated sources."""

    source_uri: NonEmptyStr | None = Field(default=None, max_length=2000)
    reason: NonEmptyStr = Field(max_length=500)


class EvidenceEvaluationOutput(ContractModel):
    """Structured evidence assessment returned by the bounded evaluator."""

    assessments: list[EvidenceCandidateAssessment] = Field(min_length=1, max_length=20)
    gap_supported: bool
    overall_rationale: NonEmptyStr
    next_query: NonEmptyStr | None = Field(default=None, max_length=300)
    continuation: ResearchContinuation | None = None


class SearchResponse(ContractModel):
    """Normalized provider response without an answer synthesized by the provider."""

    provider: NonEmptyStr
    query: NonEmptyStr
    candidates: list[SearchResultCandidate]
    request_id: NonEmptyStr | None = None
    more_results_available: bool = False
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
