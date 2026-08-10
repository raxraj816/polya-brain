"""Experimental contracts for Chapter 13-C cognitive control.

These models intentionally remain outside ``app.models.contracts``. They are a
trace-and-evaluation experiment until cross-domain evidence satisfies the core
contract promotion rule.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field, JsonValue, model_validator

from app.graph.state import ExecutionOutput, StateEvent
from app.models.contracts import (
    ContractModel,
    EvidenceItem,
    Hypothesis,
    KnowledgeGap,
    NonEmptyStr,
    PlanTask,
    Reflection,
    RiskLevel,
    Score,
    StructuredProblem,
    VerificationReport,
)


class CognitiveActionType(StrEnum):
    """Domain-independent actions available to the cognitive controller."""

    INTERPRET = "interpret"
    DISCOVER_CONSTRAINTS = "discover_constraints"
    DETECT_GAPS = "detect_gaps"
    CLARIFY = "clarify"
    REFRAME = "reframe"
    DECOMPOSE = "decompose"
    RECALL = "recall"
    RETRIEVE_MEMORY = "retrieve_memory"
    SEARCH = "search"
    EVALUATE_EVIDENCE = "evaluate_evidence"
    ASK_HUMAN = "ask_human"
    INSPECT = "inspect"
    OBSERVE = "observe"
    MEASURE = "measure"
    CALCULATE = "calculate"
    COMPARE = "compare"
    HYPOTHESIZE = "hypothesize"
    PLAN = "plan"
    SIMULATE = "simulate"
    EXPERIMENT = "experiment"
    EXECUTE = "execute"
    MONITOR = "monitor"
    VERIFY = "verify"
    RETRY = "retry"
    BACKTRACK = "backtrack"
    REPLAN = "replan"
    STOP = "stop"
    REFLECT = "reflect"


class ObservationStatus(StrEnum):
    """Outcome of executing a selected cognitive action."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    INCONCLUSIVE = "inconclusive"


class CognitiveRunStatus(StrEnum):
    """Terminal status for one bounded cognitive-kernel invocation."""

    COMPLETED = "completed"
    NEEDS_INPUT = "needs_input"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    MAX_CYCLES = "max_cycles"
    FAILED = "failed"


class CapabilityDefinition(ContractModel):
    """Auditable metadata for one capability available to PolyaBrain."""

    name: NonEmptyStr
    version: NonEmptyStr
    supported_actions: set[CognitiveActionType]
    risk_level: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False
    approved_for_sensitive_data: bool = False
    timeout_seconds: float = Field(default=30.0, gt=0.0)
    estimated_cost: Score = 0.0

    @model_validator(mode="after")
    def capability_must_support_an_action(self) -> CapabilityDefinition:
        """Prevent inert capability definitions from entering the registry."""
        if not self.supported_actions:
            raise ValueError("capability must support at least one cognitive action")
        return self


class CognitiveActionCandidate(ContractModel):
    """One inspectable proposal for what PolyaBrain should do next."""

    id: NonEmptyStr
    action_type: CognitiveActionType
    target: NonEmptyStr
    purpose: NonEmptyStr
    expected_observation: NonEmptyStr
    distinguishes: list[NonEmptyStr] = Field(default_factory=list)
    expected_usefulness: Score
    estimated_cost: Score
    risk_level: RiskLevel = RiskLevel.LOW
    capability: NonEmptyStr
    success_condition: NonEmptyStr
    failure_condition: NonEmptyStr
    preconditions: list[NonEmptyStr] = Field(default_factory=list)


class RejectedCognitiveAction(ContractModel):
    """Candidate not selected and the controller's inspectable reason."""

    candidate_id: NonEmptyStr
    rationale: NonEmptyStr


class CognitiveActionDecision(ContractModel):
    """Bounded action choice made by the domain-independent controller."""

    policy_version: NonEmptyStr
    state_fingerprint: NonEmptyStr
    selected: CognitiveActionCandidate
    rejected: list[RejectedCognitiveAction] = Field(default_factory=list)
    rationale: NonEmptyStr


class CognitiveStateUpdate(ContractModel):
    """Typed proposed state changes derived from a capability observation."""

    structured_problem: StructuredProblem | None = None
    knowns_to_add: list[NonEmptyStr] = Field(default_factory=list)
    unknowns_to_resolve: list[NonEmptyStr] = Field(default_factory=list)
    constraints_to_add: list[NonEmptyStr] = Field(default_factory=list)
    gaps_to_add: list[KnowledgeGap] = Field(default_factory=list)
    resolved_gap_targets: list[NonEmptyStr] = Field(default_factory=list)
    hypotheses_to_add: list[Hypothesis] = Field(default_factory=list)
    plan_tasks_to_add: list[PlanTask] = Field(default_factory=list)
    execution_outputs_to_add: list[ExecutionOutput] = Field(default_factory=list)
    verification: VerificationReport | None = None
    reflection: Reflection | None = None
    final_answer: NonEmptyStr | None = None
    questions_to_ask: list[NonEmptyStr] = Field(default_factory=list)
    trace_events_to_add: list[StateEvent] = Field(default_factory=list)


class CognitiveObservation(ContractModel):
    """Untrusted result returned by a capability for kernel interpretation."""

    action_id: NonEmptyStr
    capability: NonEmptyStr
    capability_version: NonEmptyStr
    status: ObservationStatus
    summary: NonEmptyStr
    payload: JsonValue = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    proposed_update: CognitiveStateUpdate = Field(default_factory=CognitiveStateUpdate)
    failure_kind: NonEmptyStr | None = None

    @model_validator(mode="after")
    def failed_observation_must_explain_failure(self) -> CognitiveObservation:
        """Keep recovery decisions grounded in an explicit failure signal."""
        if (
            self.status in {ObservationStatus.FAILED, ObservationStatus.BLOCKED}
            and self.failure_kind is None
        ):
            raise ValueError("failed or blocked observation requires failure_kind")
        return self


class LearnedActionPreference(ContractModel):
    """Verified procedural-memory suggestion for a related obstacle."""

    action_type: CognitiveActionType
    capability: NonEmptyStr
    source_session_ids: list[NonEmptyStr]
    verified_successes: Annotated[int, Field(ge=1)]


class ProceduralActionStrategy(ContractModel):
    """Experimental strategy learned only from verified completed runs."""

    problem_type: NonEmptyStr
    gap_type: NonEmptyStr
    action_type: CognitiveActionType
    capability: NonEmptyStr
    verified_successes: Annotated[int, Field(ge=1)] = 1
    verified_failures: Annotated[int, Field(ge=0)] = 0
    source_session_ids: list[NonEmptyStr]
