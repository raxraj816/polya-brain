"""Trace-derived task model and hard per-run cognitive resource ledger.

These contracts are deliberately experimental. Canonical ``PolyaState`` stays
the source of truth; snapshots are derived audit artifacts used by the
controller and Chapter 13-D evaluation.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field

from app.cognition.contracts import CapabilityDefinition, CognitiveActionCandidate
from app.graph.state import PolyaState, StateEvent
from app.models.contracts import ContractModel, NonEmptyStr, ReasoningMode

BUDGET_EVENT = "cognitive_budget_initialized"
USAGE_EVENT = "cognitive_resource_usage"
TASK_MODEL_EVENT = "task_model_snapshot"


class ImpasseKind(StrEnum):
    """Current obstacle preventing a verified terminal result."""

    UNDERSTANDING = "understanding"
    CONSTRAINT = "constraint"
    KNOWLEDGE = "knowledge"
    EVIDENCE = "evidence"
    HYPOTHESIS = "hypothesis"
    EXECUTION = "execution"
    VERIFICATION = "verification"
    RECOVERY = "recovery"
    CONSOLIDATION = "consolidation"
    NONE = "none"


class CognitiveResourceBudget(ContractModel):
    """Hard reservations for one bounded cognitive run."""

    max_model_calls: Annotated[int, Field(ge=0, le=100)] = 12
    max_external_calls: Annotated[int, Field(ge=0, le=100)] = 3
    max_input_tokens: Annotated[int, Field(ge=0, le=10_000_000)] = 120_000
    max_output_tokens: Annotated[int, Field(ge=0, le=1_000_000)] = 16_000
    max_normalized_cost: Annotated[float, Field(ge=0.0, le=1_000.0)] = 6.0
    max_duration_ms: Annotated[float, Field(ge=0.0, le=3_600_000.0)] = 300_000.0


class CognitiveResourceUsage(ContractModel):
    """Auditable resources consumed by accepted capability observations."""

    model_calls: Annotated[int, Field(ge=0)] = 0
    external_calls: Annotated[int, Field(ge=0)] = 0
    input_tokens: Annotated[int, Field(ge=0)] = 0
    output_tokens: Annotated[int, Field(ge=0)] = 0
    normalized_cost: Annotated[float, Field(ge=0.0)] = 0.0
    duration_ms: Annotated[float, Field(ge=0.0)] = 0.0

    def plus(self, other: CognitiveResourceUsage) -> CognitiveResourceUsage:
        """Return an immutable aggregate."""
        return CognitiveResourceUsage(
            model_calls=self.model_calls + other.model_calls,
            external_calls=self.external_calls + other.external_calls,
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            normalized_cost=self.normalized_cost + other.normalized_cost,
            duration_ms=self.duration_ms + other.duration_ms,
        )


class TaskImpasse(ContractModel):
    """One trace-visible reason the task is not yet solved."""

    kind: ImpasseKind
    target: NonEmptyStr
    reason: NonEmptyStr


class TaskModelSnapshot(ContractModel):
    """Derived working model used for attention and resource decisions."""

    session_id: NonEmptyStr
    goal: NonEmptyStr
    known_count: Annotated[int, Field(ge=0)]
    unknown_count: Annotated[int, Field(ge=0)]
    constraint_count: Annotated[int, Field(ge=0)]
    unresolved_gap_count: Annotated[int, Field(ge=0)]
    evidence_count: Annotated[int, Field(ge=0)]
    pending_plan_task_count: Annotated[int, Field(ge=0)]
    verification_passed: bool
    impasse: TaskImpasse
    budget: CognitiveResourceBudget | None = None
    usage: CognitiveResourceUsage = Field(default_factory=CognitiveResourceUsage)


def configured_budget(state: PolyaState) -> CognitiveResourceBudget | None:
    """Read the one run budget from the append-only trace."""
    for event in state["events"]:
        if event.event_type == BUDGET_EVENT:
            return CognitiveResourceBudget.model_validate(event.metadata)
    return None


def accumulated_usage(state: PolyaState) -> CognitiveResourceUsage:
    """Aggregate resource events without trusting capability-local state."""
    usage = CognitiveResourceUsage()
    for event in state["events"]:
        if event.event_type != USAGE_EVENT:
            continue
        raw = {
            key: event.metadata.get(key, 0)
            for key in (
                "model_calls",
                "external_calls",
                "input_tokens",
                "output_tokens",
                "normalized_cost",
                "duration_ms",
            )
        }
        usage = usage.plus(CognitiveResourceUsage.model_validate(raw))
    return usage


def remaining_budget(
    budget: CognitiveResourceBudget,
    usage: CognitiveResourceUsage,
) -> CognitiveResourceBudget:
    """Return the non-negative remainder used for reservations."""
    return CognitiveResourceBudget(
        max_model_calls=max(0, budget.max_model_calls - usage.model_calls),
        max_external_calls=max(0, budget.max_external_calls - usage.external_calls),
        max_input_tokens=max(0, budget.max_input_tokens - usage.input_tokens),
        max_output_tokens=max(0, budget.max_output_tokens - usage.output_tokens),
        max_normalized_cost=max(0.0, budget.max_normalized_cost - usage.normalized_cost),
        max_duration_ms=max(0.0, budget.max_duration_ms - usage.duration_ms),
    )


def reservation_fits(
    definition: CapabilityDefinition,
    budget: CognitiveResourceBudget,
    usage: CognitiveResourceUsage,
) -> bool:
    """Conservatively reserve a capability's declared worst-case resources."""
    remaining = remaining_budget(budget, usage)
    return (
        definition.max_model_calls <= remaining.max_model_calls
        and definition.max_external_calls <= remaining.max_external_calls
        and definition.max_output_tokens <= remaining.max_output_tokens
        and definition.estimated_cost <= remaining.max_normalized_cost
        and definition.timeout_seconds * 1000 <= remaining.max_duration_ms
    )


def budget_rejection_reason(
    definition: CapabilityDefinition,
    budget: CognitiveResourceBudget,
    usage: CognitiveResourceUsage,
) -> str:
    """Explain why a worst-case reservation cannot be admitted."""
    remaining = remaining_budget(budget, usage)
    shortages: list[str] = []
    if definition.max_model_calls > remaining.max_model_calls:
        shortages.append(
            f"model calls require {definition.max_model_calls}, remaining {remaining.max_model_calls}"
        )
    if definition.max_external_calls > remaining.max_external_calls:
        shortages.append(
            "external calls require "
            f"{definition.max_external_calls}, remaining {remaining.max_external_calls}"
        )
    if definition.max_output_tokens > remaining.max_output_tokens:
        shortages.append(
            "output tokens require "
            f"{definition.max_output_tokens}, remaining {remaining.max_output_tokens}"
        )
    if definition.estimated_cost > remaining.max_normalized_cost:
        shortages.append(
            "normalized cost requires "
            f"{definition.estimated_cost:.3f}, remaining {remaining.max_normalized_cost:.3f}"
        )
    required_duration_ms = definition.timeout_seconds * 1000
    if required_duration_ms > remaining.max_duration_ms:
        shortages.append(
            "duration requires worst-case "
            f"{required_duration_ms:.1f} ms, remaining {remaining.max_duration_ms:.1f} ms"
        )
    return "; ".join(shortages) or "declared reservation does not fit the remaining budget"


def _current_impasse(state: PolyaState) -> TaskImpasse:
    problem = state["structured_problem"]
    if problem is None:
        return TaskImpasse(
            kind=ImpasseKind.UNDERSTANDING,
            target="raw problem input",
            reason="No validated task representation exists.",
        )
    constraints_completed = any(
        event.engine_name == "constraint_discovery"
        and event.event_type == "completed"
        and event.metadata.get("status") == "ok"
        for event in state["events"]
    )
    if not constraints_completed:
        return TaskImpasse(
            kind=ImpasseKind.CONSTRAINT,
            target=problem.core_question,
            reason="Constraints have not yet been validated.",
        )
    evaluated_acquisitions = {
        acquisition_id
        for event in state["events"]
        if event.event_type == "evidence_evaluation_completed"
        and isinstance((acquisition_id := event.metadata.get("acquisition_id")), str)
    }
    pending_acquisition = next(
        (
            acquisition_id
            for event in state["events"]
            if event.event_type == "evidence_candidates_acquired"
            and isinstance((acquisition_id := event.metadata.get("acquisition_id")), str)
            and acquisition_id not in evaluated_acquisitions
        ),
        None,
    )
    if pending_acquisition is not None:
        return TaskImpasse(
            kind=ImpasseKind.EVIDENCE,
            target=pending_acquisition,
            reason="Acquired candidates have not passed the evidence-admission gate.",
        )
    unresolved = [gap for gap in state["gaps"] if not gap.filled]
    if unresolved:
        gap = unresolved[0]
        failed = any(
            event.event_type == "capability_observation"
            and event.metadata.get("target") == gap.description
            and event.metadata.get("status") in {"failed", "blocked", "inconclusive"}
            for event in state["events"]
        )
        return TaskImpasse(
            kind=ImpasseKind.RECOVERY if failed else ImpasseKind.KNOWLEDGE,
            target=gap.description,
            reason=(
                "The previous acquisition action failed; select a materially different route."
                if failed
                else gap.why_needed
            ),
        )
    if problem.unknowns:
        return TaskImpasse(
            kind=ImpasseKind.KNOWLEDGE,
            target=problem.unknowns[0],
            reason="A declared unknown has not yet been converted into a resolved gap.",
        )
    if not state["hypotheses"]:
        return TaskImpasse(
            kind=ImpasseKind.HYPOTHESIS,
            target=problem.core_question,
            reason="No testable candidate solution has been constructed.",
        )
    completed = {item.task_id for item in state["execution_outputs"]}
    pending = [task for task in state["plan"] if task.id not in completed]
    if not state["plan"] or pending:
        return TaskImpasse(
            kind=ImpasseKind.EXECUTION,
            target=pending[0].id if pending else problem.core_question,
            reason="A verification-producing plan or execution result is still missing.",
        )
    verification = state["verification"]
    if verification is None:
        return TaskImpasse(
            kind=ImpasseKind.VERIFICATION,
            target=problem.core_question,
            reason="The candidate conclusion has not passed an explicit check.",
        )
    if not verification.passed:
        return TaskImpasse(
            kind=ImpasseKind.RECOVERY,
            target=problem.core_question,
            reason="Verification failed and requires a materially different recovery action.",
        )
    if state["reflection"] is None:
        return TaskImpasse(
            kind=ImpasseKind.CONSOLIDATION,
            target=problem.core_question,
            reason="The verified run has not been reflected for bounded reuse.",
        )
    return TaskImpasse(
        kind=ImpasseKind.NONE,
        target="verified task",
        reason="No verification-blocking impasse remains.",
    )


def derive_task_model(state: PolyaState) -> TaskModelSnapshot:
    """Project canonical state into one compact, inspectable working model."""
    problem = state["structured_problem"]
    completed = {item.task_id for item in state["execution_outputs"]}
    pending = [task for task in state["plan"] if task.id not in completed]
    verification = state["verification"]
    return TaskModelSnapshot(
        session_id=state["session_id"],
        goal=problem.core_question if problem is not None else state["raw_input"],
        known_count=len(problem.knowns) if problem is not None else 0,
        unknown_count=len(problem.unknowns) if problem is not None else 0,
        constraint_count=len(problem.constraints) if problem is not None else 0,
        unresolved_gap_count=sum(not gap.filled for gap in state["gaps"]),
        evidence_count=len(state["evidence"]),
        pending_plan_task_count=len(pending),
        verification_passed=bool(verification is not None and verification.passed),
        impasse=_current_impasse(state),
        budget=configured_budget(state),
        usage=accumulated_usage(state),
    )


def budget_event(budget: CognitiveResourceBudget) -> StateEvent:
    """Create the immutable budget declaration event."""
    return StateEvent(
        engine_name="cognitive_kernel",
        event_type=BUDGET_EVENT,
        reasoning_mode=ReasoningMode.EXPLORE,
        summary="Initialized the hard per-run cognitive resource budget.",
        metadata=budget.model_dump(mode="json"),
    )


def task_model_event(snapshot: TaskModelSnapshot) -> StateEvent:
    """Expose attention state without mutating canonical problem fields."""
    return StateEvent(
        engine_name="cognitive_kernel",
        event_type=TASK_MODEL_EVENT,
        reasoning_mode=ReasoningMode.EXPLORE,
        summary=(f"Current impasse is {snapshot.impasse.kind.value}: {snapshot.impasse.target}."),
        metadata=snapshot.model_dump(mode="json"),
    )


def resource_usage_for(
    definition: CapabilityDefinition,
    observation_payload: object,
    *,
    duration_ms: float = 0.0,
) -> CognitiveResourceUsage:
    """Normalize typed provider telemetry; reserve honestly when absent."""
    payload = observation_payload if isinstance(observation_payload, dict) else {}
    procedure = payload.get("procedure")
    usage = payload.get("usage")
    usage_data = usage if isinstance(usage, dict) else {}
    raw_calls = payload.get("model_calls")
    model_calls = (
        int(raw_calls)
        if isinstance(raw_calls, int) and not isinstance(raw_calls, bool)
        else (0 if procedure == "deterministic" else definition.max_model_calls)
    )
    raw_external = payload.get("external_calls")
    external_calls = (
        int(raw_external)
        if isinstance(raw_external, int) and not isinstance(raw_external, bool)
        else definition.max_external_calls
    )

    def count(name: str) -> int:
        value = usage_data.get(name, 0)
        return int(value) if isinstance(value, int) and not isinstance(value, bool) else 0

    unreported_output = payload.get("unreported_output_token_reservation", 0)
    if type(unreported_output) is not int or unreported_output < 0:
        unreported_output = 0
    return CognitiveResourceUsage(
        model_calls=max(0, model_calls),
        external_calls=max(0, external_calls),
        input_tokens=count("input_tokens"),
        output_tokens=count("output_tokens") + unreported_output,
        normalized_cost=definition.estimated_cost,
        duration_ms=max(0.0, duration_ms),
    )


def usage_event(
    candidate: CognitiveActionCandidate,
    definition: CapabilityDefinition,
    usage: CognitiveResourceUsage,
) -> StateEvent:
    """Record every resource charge next to the selected cognitive action."""
    return StateEvent(
        engine_name="cognitive_kernel",
        event_type=USAGE_EVENT,
        reasoning_mode=ReasoningMode.EXECUTE,
        summary=f"Recorded resources used by {candidate.capability}.",
        metadata={
            "action_id": candidate.id,
            "action_type": candidate.action_type.value,
            "capability": candidate.capability,
            "capability_kind": definition.kind.value,
            **usage.model_dump(mode="json"),
        },
    )
