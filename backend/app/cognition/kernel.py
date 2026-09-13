"""Bounded observe-decide-act-update-verify cognitive loop."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from app.cognition.capabilities import CapabilityRegistry, safe_observation_trace_telemetry
from app.cognition.contracts import (
    CognitiveActionDecision,
    CognitiveActionType,
    CognitiveObservation,
    CognitiveRunStatus,
    ObservationStatus,
)
from app.cognition.controller import CognitiveController
from app.cognition.task_model import (
    CognitiveResourceBudget,
    accumulated_usage,
    budget_event,
    configured_budget,
    derive_task_model,
    resource_usage_for,
    task_model_event,
    usage_event,
)
from app.graph.state import PolyaState, StateEvent, append_state_events
from app.models.contracts import KnowledgeGap, ReasoningMode, StructuredProblem


@dataclass(frozen=True)
class CognitiveRunResult:
    """Inspectable result of one bounded cognitive-kernel run."""

    status: CognitiveRunStatus
    state: PolyaState
    decisions: tuple[CognitiveActionDecision, ...]
    observations: tuple[CognitiveObservation, ...]
    cycles: int


def _append_event(state: PolyaState, event: StateEvent) -> PolyaState:
    next_state = dict(state)
    next_state["events"] = append_state_events(state["events"], event)
    return next_state  # type: ignore[return-value]


def _deadline_event(*, elapsed_ms: float, budget_ms: float) -> StateEvent:
    return StateEvent(
        engine_name="cognitive_kernel",
        event_type="cognitive_run_deadline_exhausted",
        reasoning_mode=ReasoningMode.VERIFY,
        summary="Stopped safely because the hard cognitive run deadline was exhausted.",
        metadata={
            "elapsed_ms": round(max(0.0, elapsed_ms), 3),
            "budget_ms": budget_ms,
            "terminal_status": CognitiveRunStatus.INSUFFICIENT_EVIDENCE.value,
        },
    )


def _decision_event(decision: CognitiveActionDecision) -> StateEvent:
    selected = decision.selected
    return StateEvent(
        engine_name="cognitive_controller",
        event_type="cognitive_action_decision",
        reasoning_mode=ReasoningMode.EXPLORE,
        summary=(
            f"Selected {selected.action_type.value} for {selected.target} through "
            f"{selected.capability}."
        ),
        metadata=decision.model_dump(mode="json"),
    )


def _observation_event(
    action: CognitiveActionDecision,
    observation: CognitiveObservation,
    duration_ms: float,
) -> StateEvent:
    return StateEvent(
        engine_name=observation.capability,
        event_type="capability_observation",
        reasoning_mode=(
            ReasoningMode.VERIFY
            if action.selected.action_type is CognitiveActionType.VERIFY
            else ReasoningMode.EXECUTE
        ),
        summary=observation.summary,
        metadata={
            "action_id": action.selected.id,
            "action_type": action.selected.action_type.value,
            "target": action.selected.target,
            "capability": observation.capability,
            "capability_version": observation.capability_version,
            "status": observation.status.value,
            "failure_kind": observation.failure_kind,
            "evidence_count": len(observation.evidence),
            "duration_ms": round(max(0.0, duration_ms), 3),
            **safe_observation_trace_telemetry(observation.payload),
        },
    )


def _merge_unique(existing: list[str], additions: list[str]) -> list[str]:
    return list(dict.fromkeys([*existing, *additions]))


def _merge_gaps(
    existing: list[KnowledgeGap],
    additions: list[KnowledgeGap],
) -> list[KnowledgeGap]:
    """Keep one canonical gap per normalized description."""
    merged = list(existing)
    seen = {item.description.casefold() for item in existing}
    for item in additions:
        key = item.description.casefold()
        if key in seen:
            continue
        merged.append(item)
        seen.add(key)
    return merged


def _update_problem(
    problem: StructuredProblem,
    *,
    knowns_to_add: list[str],
    unknowns_to_resolve: list[str],
    constraints_to_add: list[str],
) -> StructuredProblem:
    resolved = set(unknowns_to_resolve)
    return problem.model_copy(
        update={
            "knowns": _merge_unique(problem.knowns, knowns_to_add),
            "unknowns": [item for item in problem.unknowns if item not in resolved],
            "constraints": _merge_unique(problem.constraints, constraints_to_add),
        }
    )


def apply_cognitive_observation(
    state: PolyaState,
    observation: CognitiveObservation,
) -> PolyaState:
    """Apply only validated, typed updates from a successful observation."""
    next_state = dict(state)
    next_state["evidence"] = [*state["evidence"], *observation.evidence]
    next_events = state["events"]
    for trace_event in observation.proposed_update.trace_events_to_add:
        next_events = append_state_events(next_events, trace_event)
    next_state["events"] = next_events

    if observation.status is not ObservationStatus.SUCCEEDED:
        return next_state  # type: ignore[return-value]

    update = observation.proposed_update
    materially_revised = bool(
        observation.evidence
        or update.structured_problem is not None
        or update.knowns_to_add
        or update.unknowns_to_resolve
        or update.constraints_to_add
        or update.gaps_to_add
        or update.resolved_gap_targets
        or update.hypotheses_to_add
        or update.plan_tasks_to_add
        or update.execution_outputs_to_add
    )
    if state["verification"] is not None and update.verification is None and materially_revised:
        # A changed evidence or execution state invalidates the earlier check.
        # The revised state must be verified again before it can be accepted.
        next_state["verification"] = None
        next_state["final_answer"] = None
        next_state["reflection"] = None

    problem = update.structured_problem or state["structured_problem"]
    if problem is not None:
        resolved_unknowns = _merge_unique(
            update.unknowns_to_resolve,
            [target for target in update.resolved_gap_targets if target in problem.unknowns],
        )
        problem = _update_problem(
            problem,
            knowns_to_add=update.knowns_to_add,
            unknowns_to_resolve=resolved_unknowns,
            constraints_to_add=update.constraints_to_add,
        )
    next_state["structured_problem"] = problem

    resolved_targets = set(update.resolved_gap_targets)
    evidence_refs = [
        f"{observation.action_id}:evidence:{index}"
        for index, _ in enumerate(observation.evidence, start=1)
    ]
    resolution_refs = evidence_refs or [f"{observation.action_id}:observation"]
    current_gaps = [
        gap.model_copy(
            update={
                "filled": True,
                "evidence_ids": _merge_unique(gap.evidence_ids, resolution_refs),
            }
        )
        if gap.description in resolved_targets
        else gap
        for gap in state["gaps"]
    ]
    next_state["gaps"] = _merge_gaps(current_gaps, update.gaps_to_add)
    next_state["hypotheses"] = [
        *state["hypotheses"],
        *update.hypotheses_to_add,
    ]
    next_state["plan"] = [*state["plan"], *update.plan_tasks_to_add]
    next_state["execution_outputs"] = [
        *state["execution_outputs"],
        *update.execution_outputs_to_add,
    ]
    verification_accepted = True
    if update.verification is not None:
        verification = update.verification
        criteria = problem.success_criteria if problem is not None else []
        if verification.passed and len(verification.checks_run) < len(criteria):
            verification_accepted = False
            verification = verification.model_copy(
                update={
                    "passed": False,
                    "failed_checks": _merge_unique(
                        verification.failed_checks,
                        [
                            "Verification did not run at least one explicit check for "
                            "every success criterion."
                        ],
                    ),
                    "confidence_delta": min(verification.confidence_delta or 0.0, -0.2),
                }
            )
            next_events = append_state_events(
                next_events,
                StateEvent(
                    engine_name="cognitive_kernel",
                    event_type="success_criteria_verification_failed",
                    reasoning_mode=ReasoningMode.VERIFY,
                    summary=(
                        "Rejected a passing verification report because it did not cover "
                        "every success criterion."
                    ),
                    metadata={
                        "success_criteria_count": len(criteria),
                        "checks_run_count": len(verification.checks_run),
                    },
                ),
            )
            next_state["events"] = next_events
        next_state["verification"] = verification
    if update.reflection is not None:
        next_state["reflection"] = update.reflection
    if update.final_answer is not None and verification_accepted:
        next_state["final_answer"] = update.final_answer
    next_state["iteration_count"] = state["iteration_count"] + 1
    return next_state  # type: ignore[return-value]


class CognitiveKernel:
    """Run the controller and capabilities until a verified stop or safe halt."""

    def __init__(
        self,
        registry: CapabilityRegistry,
        *,
        controller: CognitiveController | None = None,
    ) -> None:
        self.registry = registry
        self.controller = controller or CognitiveController()

    def run(
        self,
        initial_state: PolyaState,
        *,
        max_cycles: int | None = None,
        budget: CognitiveResourceBudget | None = None,
    ) -> CognitiveRunResult:
        """Execute a bounded state-dependent loop without delegating control to an LLM."""
        cycle_budget = max_cycles or initial_state["max_iterations"]
        if cycle_budget < 1:
            raise ValueError("max_cycles must be at least 1")

        state = initial_state
        existing_budget = configured_budget(state)
        if budget is not None and existing_budget is None:
            state = _append_event(state, budget_event(budget))
        elif budget is not None and existing_budget != budget:
            raise ValueError("initial state already declares a different cognitive budget")
        active_budget = configured_budget(state)
        prior_duration_ms = accumulated_usage(state).duration_ms
        run_started = perf_counter()
        decisions: list[CognitiveActionDecision] = []
        observations: list[CognitiveObservation] = []

        for cycle in range(1, cycle_budget + 1):
            elapsed_ms = prior_duration_ms + ((perf_counter() - run_started) * 1000)
            if active_budget is not None and elapsed_ms >= active_budget.max_duration_ms:
                state = _append_event(
                    state,
                    _deadline_event(
                        elapsed_ms=elapsed_ms,
                        budget_ms=active_budget.max_duration_ms,
                    ),
                )
                return CognitiveRunResult(
                    status=CognitiveRunStatus.INSUFFICIENT_EVIDENCE,
                    state=state,
                    decisions=tuple(decisions),
                    observations=tuple(observations),
                    cycles=cycle - 1,
                )
            state = _append_event(state, task_model_event(derive_task_model(state)))
            decision = self.controller.decide(state, self.registry)
            decisions.append(decision)
            state = _append_event(state, _decision_event(decision))

            if decision.selected.action_type is CognitiveActionType.STOP:
                verification = state["verification"]
                status = (
                    CognitiveRunStatus.COMPLETED
                    if verification is not None
                    and verification.passed
                    and state["reflection"] is not None
                    else CognitiveRunStatus.INSUFFICIENT_EVIDENCE
                )
                return CognitiveRunResult(
                    status=status,
                    state=state,
                    decisions=tuple(decisions),
                    observations=tuple(observations),
                    cycles=cycle,
                )

            started = perf_counter()
            observation = self.registry.execute(decision.selected, state)
            duration_ms = (perf_counter() - started) * 1000
            observations.append(observation)
            state = _append_event(
                state,
                _observation_event(decision, observation, duration_ms),
            )
            capability = self.registry.get(decision.selected.capability)
            if capability is not None:
                state = _append_event(
                    state,
                    usage_event(
                        decision.selected,
                        capability.definition,
                        resource_usage_for(
                            capability.definition,
                            observation.payload,
                            duration_ms=duration_ms,
                        ),
                    ),
                )
            state = apply_cognitive_observation(state, observation)

            if observation.status is ObservationStatus.BLOCKED and (
                observation.failure_kind in {"approval_required", "human_input_required"}
                or decision.selected.action_type
                in {CognitiveActionType.CLARIFY, CognitiveActionType.ASK_HUMAN}
            ):
                return CognitiveRunResult(
                    status=CognitiveRunStatus.NEEDS_INPUT,
                    state=state,
                    decisions=tuple(decisions),
                    observations=tuple(observations),
                    cycles=cycle,
                )

        return CognitiveRunResult(
            status=CognitiveRunStatus.MAX_CYCLES,
            state=state,
            decisions=tuple(decisions),
            observations=tuple(observations),
            cycles=cycle_budget,
        )
