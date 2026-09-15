"""Core Pydantic contracts for the Chapter 5 PolyaBrain MVP surface."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Score = Annotated[float, Field(ge=0.0, le=1.0)]
ConfidenceDelta = Annotated[float, Field(ge=-1.0, le=1.0)]


class ContractModel(BaseModel):
    """Shared strict configuration for engine and API-facing contracts."""

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class ProductMode(StrEnum):
    """Supported MVP product modes."""

    INVESTIGATE = "investigate"
    COMPARE = "compare"
    REVIEW = "review"
    EXPLORE = "explore"


class PriorityLevel(StrEnum):
    """Priority values for gaps and follow-up work."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(StrEnum):
    """Plan/task risk levels before approval mechanics exist."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class HypothesisOrigin(StrEnum):
    """Where a candidate hypothesis came from."""

    DIRECT_REASONING = "direct_reasoning"
    MEMORY_ANALOGY = "memory_analogy"
    USER_SUPPLIED = "user_supplied"
    REFRAME = "reframe"
    INCUBATION = "incubation"


class HypothesisStatus(StrEnum):
    """Lifecycle state for a hypothesis candidate."""

    CANDIDATE = "candidate"
    SELECTED = "selected"
    DEFERRED = "deferred"
    REJECTED = "rejected"
    VERIFIED = "verified"
    FALSIFIED = "falsified"


class ReasoningMode(StrEnum):
    """Trace-visible reasoning modes used by the Polya loop."""

    EXPLORE = "explore"
    COMPARE = "compare"
    REFRAME = "reframe"
    EXECUTE = "execute"
    VERIFY = "verify"
    REFLECT = "reflect"


class StructuredProblem(ContractModel):
    """Canonical structured representation of the current problem."""

    core_question: NonEmptyStr
    problem_type: NonEmptyStr
    domain: NonEmptyStr | None = None
    knowns: list[NonEmptyStr] = Field(default_factory=list)
    unknowns: list[NonEmptyStr] = Field(default_factory=list)
    constraints: list[NonEmptyStr] = Field(default_factory=list)
    success_criteria: list[NonEmptyStr] = Field(default_factory=list)
    affected_entities: list[NonEmptyStr] = Field(default_factory=list)
    time_window: dict[str, Any] = Field(default_factory=dict)
    required_data_sources: list[NonEmptyStr] = Field(default_factory=list)


class KnowledgeGap(ContractModel):
    """Missing information that must be resolved or explicitly carried forward."""

    description: NonEmptyStr
    gap_type: NonEmptyStr
    priority: PriorityLevel = PriorityLevel.MEDIUM
    why_needed: NonEmptyStr
    suggested_source: NonEmptyStr | None = None
    filled: bool = False
    evidence_ids: list[NonEmptyStr] = Field(default_factory=list)


class EvidenceItem(ContractModel):
    """Evidence item with source, claim, and quality metadata."""

    source_type: NonEmptyStr
    source_uri: NonEmptyStr | None = None
    claim: NonEmptyStr
    raw_excerpt: Annotated[str, StringConstraints(min_length=1, strip_whitespace=False)] | None = (
        None
    )
    reliability_score: Score | None = None
    relevance_score: Score | None = None
    supports_hypothesis_ids: list[NonEmptyStr] = Field(default_factory=list)
    contradicts_hypothesis_ids: list[NonEmptyStr] = Field(default_factory=list)

    @field_validator("raw_excerpt")
    @classmethod
    def excerpt_must_have_content(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("evidence excerpt must not be blank")
        return value

    @model_validator(mode="after")
    def evidence_must_keep_provenance(self) -> Self:
        """Require at least one inspectable source handle before evidence can be trusted."""
        if self.source_uri is None and self.raw_excerpt is None:
            raise ValueError("evidence item requires source_uri or raw_excerpt provenance")
        return self


class Hypothesis(ContractModel):
    """Candidate explanation or solution path under investigation."""

    statement: NonEmptyStr
    mechanism: NonEmptyStr | None = None
    origin: HypothesisOrigin
    analogical_source_ids: list[NonEmptyStr] = Field(default_factory=list)
    expected_signals: list[NonEmptyStr] = Field(default_factory=list)
    evidence_for: list[NonEmptyStr] = Field(default_factory=list)
    evidence_against: list[NonEmptyStr] = Field(default_factory=list)
    verification_checks: list[NonEmptyStr] = Field(default_factory=list)
    falsification_criteria: list[NonEmptyStr] = Field(default_factory=list)
    confidence: Score | None = None
    selection_rationale: NonEmptyStr | None = None
    status: HypothesisStatus = HypothesisStatus.CANDIDATE

    @model_validator(mode="after")
    def selected_hypothesis_must_be_testable(self) -> Self:
        """Require selected hypotheses to explain why and how they will be checked."""
        if self.status is HypothesisStatus.SELECTED:
            if not self.evidence_for and not self.evidence_against:
                raise ValueError(
                    "selected hypothesis requires supporting or contradicting evidence"
                )
            if not self.verification_checks:
                raise ValueError("selected hypothesis requires at least one verification check")
            if not self.falsification_criteria:
                raise ValueError(
                    "selected hypothesis requires at least one falsification criterion"
                )
            if self.selection_rationale is None:
                raise ValueError("selected hypothesis requires selection rationale")
        return self


class PlanTask(ContractModel):
    """Executable or proposed investigation step."""

    id: NonEmptyStr
    action: NonEmptyStr
    tool_name: NonEmptyStr | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[NonEmptyStr] = Field(default_factory=list)
    expected_output: NonEmptyStr | None = None
    risk_level: RiskLevel = RiskLevel.LOW


class VerificationReport(ContractModel):
    """Verification result for a session or checkpoint."""

    passed: bool
    checks_run: list[NonEmptyStr] = Field(default_factory=list)
    failed_checks: list[NonEmptyStr] = Field(default_factory=list)
    contradictions: list[NonEmptyStr] = Field(default_factory=list)
    confidence_delta: ConfidenceDelta | None = None
    recommended_route: NonEmptyStr | None = None

    @model_validator(mode="after")
    def verification_outcome_must_match_failure_detail(self) -> Self:
        """Keep pass/fail reports from carrying contradictory failure detail."""
        if not self.checks_run:
            raise ValueError("verification report requires at least one check run")
        if self.passed and self.failed_checks:
            raise ValueError("passing verification report cannot include failed checks")
        if (
            not self.passed
            and not self.failed_checks
            and not self.contradictions
            and self.recommended_route is None
        ):
            raise ValueError(
                "failing verification report requires failed checks, contradictions, or route"
            )
        return self


class Reflection(ContractModel):
    """Lean reflection artifact before the full reflection engine exists."""

    outcome_summary: NonEmptyStr
    what_worked: list[NonEmptyStr] = Field(default_factory=list)
    what_failed: list[NonEmptyStr] = Field(default_factory=list)
    reusable_lessons: list[NonEmptyStr] = Field(default_factory=list)
    memory_updates: list[NonEmptyStr] = Field(default_factory=list)
    strategy_notes: list[NonEmptyStr] = Field(default_factory=list)
    follow_up_actions: list[NonEmptyStr] = Field(default_factory=list)
