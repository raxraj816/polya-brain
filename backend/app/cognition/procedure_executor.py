"""Governed present-case execution of verified compiled procedures."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from time import perf_counter

from app.cognition.capabilities import CapabilityRegistry, safe_observation_trace_telemetry
from app.cognition.contracts import (
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveObservation,
    ObservationStatus,
)
from app.cognition.kernel import apply_cognitive_observation
from app.cognition.procedure_compiler import (
    CompiledProcedure,
    ProcedureApplicability,
    ProcedureApplicabilityChecker,
    ProcedureApplicabilityStatus,
    ProcedureRegressionCase,
    ProcedureReplayResult,
    ProcedureStep,
)
from app.cognition.task_model import (
    accumulated_usage,
    budget_rejection_reason,
    configured_budget,
    reservation_fits,
    resource_usage_for,
    usage_event,
)
from app.graph.state import PolyaState, StateEvent, append_state_events
from app.models.contracts import ReasoningMode, RiskLevel

PROCEDURE_EXECUTION_STARTED_EVENT = "compiled_procedure_execution_started"
PROCEDURE_STEP_EVENT = "compiled_procedure_step_selected"
PROCEDURE_EXECUTION_FINISHED_EVENT = "compiled_procedure_execution_finished"


class ProcedureExecutionStatus(StrEnum):
    """Terminal disposition of a governed procedure attempt."""

    COMPLETED = "completed"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"
    FAILED = "failed"


@dataclass(frozen=True)
class ProcedureExecutionResult:
    """Inspectable result without claiming a kernel-owned general run."""

    status: ProcedureExecutionStatus
    state: PolyaState
    applicability: ProcedureApplicability
    actions: tuple[CognitiveActionCandidate, ...]
    observations: tuple[CognitiveObservation, ...]
    failure_reason: str | None = None


def _append_event(state: PolyaState, event: StateEvent) -> PolyaState:
    next_state = dict(state)
    next_state["events"] = append_state_events(state["events"], event)
    return next_state  # type: ignore[return-value]


def _sensitive_boundary(state: PolyaState) -> bool:
    problem = state["structured_problem"]
    if problem is None:
        return False
    text = " ".join(problem.constraints).casefold()
    return any(
        token in text for token in ("privacy", "private", "confidential", "sensitive", "pii")
    )


def _target_for_step(step: ProcedureStep, state: PolyaState) -> str | None:
    problem = state["structured_problem"]
    if step.target_role == "task_goal":
        return problem.core_question if problem is not None else None
    if step.target_role == "task_input":
        return state["raw_input"]
    if step.target_role == "plan_task":
        completed = {item.task_id for item in state["execution_outputs"]}
        pending = [task.id for task in state["plan"] if task.id not in completed]
        if pending:
            return pending[0]
        return state["plan"][0].id if state["plan"] else None
    if step.target_role.startswith("gap:"):
        gap_type = step.target_role.partition(":")[2]
        matching = [gap for gap in state["gaps"] if gap.gap_type == gap_type]
        unresolved = [gap for gap in matching if not gap.filled]
        selected = unresolved[0] if unresolved else (matching[0] if matching else None)
        return selected.description if selected is not None else None
    return None


def _step_event(
    procedure: CompiledProcedure,
    step: ProcedureStep,
    action: CognitiveActionCandidate,
) -> StateEvent:
    return StateEvent(
        engine_name="procedure_executor",
        event_type=PROCEDURE_STEP_EVENT,
        reasoning_mode=(
            ReasoningMode.VERIFY
            if step.action_type is CognitiveActionType.VERIFY
            else ReasoningMode.EXECUTE
        ),
        summary=(
            f"Selected compiled procedure {procedure.id} step {step.order}: "
            f"{step.action_type.value} through {step.capability}."
        ),
        metadata={
            "procedure_id": procedure.id,
            "procedure_version": procedure.version,
            "step": step.model_dump(mode="json"),
            "action": action.model_dump(mode="json"),
        },
    )


def _observation_event(
    procedure: CompiledProcedure,
    action: CognitiveActionCandidate,
    observation: CognitiveObservation,
    duration_ms: float,
) -> StateEvent:
    return StateEvent(
        engine_name=observation.capability,
        event_type="capability_observation",
        reasoning_mode=(
            ReasoningMode.VERIFY
            if action.action_type is CognitiveActionType.VERIFY
            else ReasoningMode.EXECUTE
        ),
        summary=observation.summary,
        metadata={
            "source": "compiled_procedure",
            "procedure_id": procedure.id,
            "procedure_version": procedure.version,
            "action_id": action.id,
            "action_type": action.action_type.value,
            "target": action.target,
            "capability": observation.capability,
            "capability_version": observation.capability_version,
            "status": observation.status.value,
            "failure_kind": observation.failure_kind,
            "evidence_count": len(observation.evidence),
            "duration_ms": round(max(0.0, duration_ms), 3),
            **safe_observation_trace_telemetry(observation.payload),
        },
    )


class GovernedProcedureExecutor:
    """Replay verified behavior without bypassing runtime safety or verification."""

    def __init__(
        self,
        registry: CapabilityRegistry,
        *,
        applicability_checker: ProcedureApplicabilityChecker | None = None,
    ) -> None:
        self._registry = registry
        self._applicability_checker = applicability_checker or ProcedureApplicabilityChecker()

    def execute(
        self,
        procedure: CompiledProcedure,
        state: PolyaState,
        *,
        approved: bool = False,
    ) -> ProcedureExecutionResult:
        return self._execute(procedure, state, approved=approved, replay_mode=False)

    def replay(
        self,
        procedure: CompiledProcedure,
        state: PolyaState,
        *,
        case_id: str,
    ) -> tuple[ProcedureExecutionResult, ProcedureReplayResult]:
        """Execute an untrusted proposal in replay mode and derive promotion evidence."""
        execution = self._execute(procedure, state, approved=False, replay_mode=True)
        problem = execution.state["structured_problem"]
        if problem is None:
            raise ValueError("procedure replay requires a represented problem")
        encoded_constraints = json.dumps(
            sorted(problem.constraints),
            separators=(",", ":"),
        ).encode()
        capability_versions_match = len(execution.observations) == len(procedure.steps) and all(
            observation.capability == step.capability
            and observation.capability_version == step.capability_version
            for step, observation in zip(
                procedure.steps,
                execution.observations,
                strict=True,
            )
        )
        verification_passed = bool(
            execution.state["verification"] is not None and execution.state["verification"].passed
        )
        completed = execution.status is ProcedureExecutionStatus.COMPLETED
        replay_result = ProcedureReplayResult(
            case=ProcedureRegressionCase(
                case_id=case_id,
                problem_type=problem.problem_type,
                domain=problem.domain,
                constraint_fingerprint=hashlib.sha256(encoded_constraints).hexdigest()[:16],
                verifier_suite_version=procedure.verifier_suite.version,
                verification_passed=verification_passed,
            ),
            procedure_completed=completed,
            verification_passed=verification_passed,
            capability_versions_match=capability_versions_match,
            failure_reason=(
                None
                if completed and verification_passed and capability_versions_match
                else execution.failure_reason or "Replay did not satisfy every promotion gate."
            ),
        )
        return execution, replay_result

    def _execute(
        self,
        procedure: CompiledProcedure,
        state: PolyaState,
        *,
        approved: bool,
        replay_mode: bool,
    ) -> ProcedureExecutionResult:
        applicability = self._applicability_checker.check(
            procedure,
            state,
            self._registry,
            allow_unverified_replay=replay_mode,
        )
        if applicability.status is not ProcedureApplicabilityStatus.APPLICABLE:
            status = (
                ProcedureExecutionStatus.INCONCLUSIVE
                if applicability.status is ProcedureApplicabilityStatus.INCONCLUSIVE
                else ProcedureExecutionStatus.REJECTED
            )
            return ProcedureExecutionResult(
                status=status,
                state=state,
                applicability=applicability,
                actions=(),
                observations=(),
                failure_reason="; ".join(applicability.reasons),
            )

        current = _append_event(
            state,
            StateEvent(
                engine_name="procedure_executor",
                event_type=PROCEDURE_EXECUTION_STARTED_EVENT,
                reasoning_mode=ReasoningMode.EXECUTE,
                summary=f"Started governed execution of verified procedure {procedure.id}.",
                metadata={
                    "procedure_id": procedure.id,
                    "procedure_version": procedure.version,
                    "replay_mode": replay_mode,
                    "applicability": applicability.model_dump(mode="json"),
                },
            ),
        )
        actions: list[CognitiveActionCandidate] = []
        observations: list[CognitiveObservation] = []
        for step in procedure.steps:
            target = _target_for_step(step, current)
            if target is None:
                return self._finish(
                    procedure,
                    current,
                    applicability,
                    actions,
                    observations,
                    ProcedureExecutionStatus.INCONCLUSIVE,
                    f"Could not bind present-case target role {step.target_role!r}.",
                )
            capability = self._registry.get(step.capability)
            if capability is None or capability.definition.version != step.capability_version:
                return self._finish(
                    procedure,
                    current,
                    applicability,
                    actions,
                    observations,
                    ProcedureExecutionStatus.REJECTED,
                    f"Required capability {step.capability!r} changed after applicability check.",
                )
            if step.action_type not in capability.definition.supported_actions:
                return self._finish(
                    procedure,
                    current,
                    applicability,
                    actions,
                    observations,
                    ProcedureExecutionStatus.REJECTED,
                    f"Capability {step.capability!r} no longer supports {step.action_type.value}.",
                )
            if capability.definition.risk_level is not RiskLevel.LOW and not approved:
                return self._finish(
                    procedure,
                    current,
                    applicability,
                    actions,
                    observations,
                    ProcedureExecutionStatus.REJECTED,
                    f"Capability {step.capability!r} requires explicit approval at current risk.",
                )
            if (
                _sensitive_boundary(current)
                and not capability.definition.approved_for_sensitive_data
            ):
                return self._finish(
                    procedure,
                    current,
                    applicability,
                    actions,
                    observations,
                    ProcedureExecutionStatus.REJECTED,
                    f"Capability {step.capability!r} is not approved for current sensitive data.",
                )
            budget = configured_budget(current)
            usage = accumulated_usage(current)
            if budget is not None and not reservation_fits(capability.definition, budget, usage):
                return self._finish(
                    procedure,
                    current,
                    applicability,
                    actions,
                    observations,
                    ProcedureExecutionStatus.REJECTED,
                    "Compiled step cannot fit the remaining cognitive budget: "
                    + budget_rejection_reason(capability.definition, budget, usage),
                )
            action = CognitiveActionCandidate(
                id=f"procedure-{procedure.id}-v{procedure.version}-step-{step.order}",
                action_type=step.action_type,
                target=target,
                purpose=step.purpose,
                expected_observation=step.expected_observation,
                expected_usefulness=0.85,
                estimated_cost=capability.definition.estimated_cost,
                risk_level=capability.definition.risk_level,
                capability=step.capability,
                success_condition="; ".join(step.expected_postconditions),
                failure_condition="The declared postconditions are absent or present verification fails.",
                preconditions=list(procedure.safety_constraints),
            )
            actions.append(action)
            current = _append_event(current, _step_event(procedure, step, action))
            started = perf_counter()
            observation = self._registry.execute(action, current, approved=approved)
            duration_ms = (perf_counter() - started) * 1000
            observations.append(observation)
            current = _append_event(
                current,
                _observation_event(procedure, action, observation, duration_ms),
            )
            current = _append_event(
                current,
                usage_event(
                    action,
                    capability.definition,
                    resource_usage_for(
                        capability.definition,
                        observation.payload,
                        duration_ms=duration_ms,
                    ),
                ),
            )
            current = apply_cognitive_observation(current, observation)
            if observation.status is not ObservationStatus.SUCCEEDED:
                return self._finish(
                    procedure,
                    current,
                    applicability,
                    actions,
                    observations,
                    ProcedureExecutionStatus.FAILED,
                    f"Step {step.order} returned {observation.status.value}: {observation.summary}",
                )

        verification = current["verification"]
        completed = bool(
            verification is not None
            and verification.passed
            and current["reflection"] is not None
            and current["final_answer"]
        )
        return self._finish(
            procedure,
            current,
            applicability,
            actions,
            observations,
            ProcedureExecutionStatus.COMPLETED if completed else ProcedureExecutionStatus.FAILED,
            None if completed else "Present-case verification did not produce a verified outcome.",
        )

    def _finish(
        self,
        procedure: CompiledProcedure,
        state: PolyaState,
        applicability: ProcedureApplicability,
        actions: list[CognitiveActionCandidate],
        observations: list[CognitiveObservation],
        status: ProcedureExecutionStatus,
        failure_reason: str | None,
    ) -> ProcedureExecutionResult:
        finished = _append_event(
            state,
            StateEvent(
                engine_name="procedure_executor",
                event_type=PROCEDURE_EXECUTION_FINISHED_EVENT,
                reasoning_mode=(
                    ReasoningMode.REFLECT
                    if status is ProcedureExecutionStatus.COMPLETED
                    else ReasoningMode.VERIFY
                ),
                summary=(
                    f"Governed procedure {procedure.id} completed with present-case verification."
                    if status is ProcedureExecutionStatus.COMPLETED
                    else f"Governed procedure {procedure.id} stopped as {status.value}."
                ),
                metadata={
                    "procedure_id": procedure.id,
                    "procedure_version": procedure.version,
                    "status": status.value,
                    "steps_attempted": len(actions),
                    "failure_reason": failure_reason,
                    "verification_passed": bool(
                        state["verification"] is not None and state["verification"].passed
                    ),
                },
            ),
        )
        return ProcedureExecutionResult(
            status=status,
            state=finished,
            applicability=applicability,
            actions=tuple(actions),
            observations=tuple(observations),
            failure_reason=failure_reason,
        )
