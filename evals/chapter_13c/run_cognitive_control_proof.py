#!/usr/bin/env python3
"""Run the offline Chapter 13-C structural cognitive-control proof.

This proof verifies domain-independent state-dependent control and recovery. It
does not claim real-world outcome superiority or replace the required live
tool-enabled model comparison.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any

from app.cognition import (
    CapabilityDefinition,
    CapabilityRegistry,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveController,
    CognitiveKernel,
    CognitiveObservation,
    CognitiveRunStatus,
    CognitiveStateUpdate,
    FunctionCapability,
    ObservationStatus,
    ProceduralMemory,
)
from app.graph.state import ExecutionOutput, PolyaState, StateEvent, create_initial_state
from app.models.contracts import (
    EvidenceItem,
    Hypothesis,
    HypothesisOrigin,
    KnowledgeGap,
    PlanTask,
    PriorityLevel,
    ReasoningMode,
    Reflection,
    RiskLevel,
    StructuredProblem,
    VerificationReport,
)

EVAL_ROOT = Path(__file__).resolve().parent


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_cases() -> list[dict[str, Any]]:
    payload = json.loads((EVAL_ROOT / "cases.json").read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise ValueError("Chapter 13-C cases must be a JSON list of objects")
    return payload


def _definition(
    name: str,
    actions: set[CognitiveActionType],
) -> CapabilityDefinition:
    return CapabilityDefinition(
        name=name,
        version="chapter-13c-proof-v1",
        supported_actions=actions,
        estimated_cost=0.05,
    )


def _observation(
    definition: CapabilityDefinition,
    action: CognitiveActionCandidate,
    *,
    summary: str,
    update: CognitiveStateUpdate,
    evidence: list[EvidenceItem] | None = None,
) -> CognitiveObservation:
    return CognitiveObservation(
        action_id=action.id,
        capability=definition.name,
        capability_version=definition.version,
        status=ObservationStatus.SUCCEEDED,
        summary=summary,
        evidence=evidence or [],
        proposed_update=update,
    )


def _acquisition_executor(
    definition: CapabilityDefinition,
) -> Callable[[CognitiveActionCandidate, PolyaState], CognitiveObservation]:
    def execute(
        action: CognitiveActionCandidate,
        _state: PolyaState,
    ) -> CognitiveObservation:
        return _observation(
            definition,
            action,
            summary=(
                f"{definition.name} returned a fixture-backed observation for {action.target}."
            ),
            evidence=[
                EvidenceItem(
                    source_type="chapter_13c_fixture",
                    source_uri=f"fixture://{definition.name}/{action.id}",
                    claim=f"The selected {action.action_type.value} action resolved {action.target}.",
                    raw_excerpt="Deterministic cross-domain control fixture.",
                    reliability_score=1.0,
                    relevance_score=1.0,
                )
            ],
            update=CognitiveStateUpdate(
                knowns_to_add=[f"Observed result for {action.target}."],
                unknowns_to_resolve=[action.target],
                resolved_gap_targets=[action.target],
            ),
        )

    return execute


def _failed_search_executor(
    definition: CapabilityDefinition,
) -> Callable[[CognitiveActionCandidate, PolyaState], CognitiveObservation]:
    def execute(
        action: CognitiveActionCandidate,
        _state: PolyaState,
    ) -> CognitiveObservation:
        return CognitiveObservation(
            action_id=action.id,
            capability=definition.name,
            capability_version=definition.version,
            status=ObservationStatus.FAILED,
            summary="The primary search capability returned no usable result.",
            failure_kind="no_results",
        )

    return execute


def _registry(case: dict[str, Any]) -> CapabilityRegistry:
    registry = CapabilityRegistry()
    action_sets = {
        "human_input": {CognitiveActionType.CLARIFY, CognitiveActionType.ASK_HUMAN},
        "calculator": {CognitiveActionType.CALCULATE},
        "web_search": {CognitiveActionType.SEARCH},
        "inspector": {CognitiveActionType.INSPECT},
        "observer": {CognitiveActionType.OBSERVE},
        "measurement": {CognitiveActionType.MEASURE},
        "simulator": {CognitiveActionType.SIMULATE},
        "experiment": {CognitiveActionType.EXPERIMENT},
        "memory": {CognitiveActionType.RETRIEVE_MEMORY, CognitiveActionType.RECALL},
    }
    for name, actions in action_sets.items():
        definition = _definition(name, actions)
        if name == "web_search" and case["id"] == "current_api_behavior":
            registry.register(
                FunctionCapability(
                    definition,
                    _failed_search_executor(definition),
                )
            )
        else:
            registry.register(FunctionCapability(definition, _acquisition_executor(definition)))

    reasoner = _definition(
        "reasoner",
        {
            CognitiveActionType.REFRAME,
            CognitiveActionType.DECOMPOSE,
            CognitiveActionType.COMPARE,
            CognitiveActionType.HYPOTHESIZE,
        },
    )

    def reason(
        action: CognitiveActionCandidate,
        _state: PolyaState,
    ) -> CognitiveObservation:
        if action.action_type is not CognitiveActionType.HYPOTHESIZE:
            return _acquisition_executor(reasoner)(action, _state)
        return _observation(
            reasoner,
            action,
            summary="Generated a testable candidate from the acquired observations.",
            update=CognitiveStateUpdate(
                hypotheses_to_add=[
                    Hypothesis(
                        statement=str(case["expected_answer"]),
                        mechanism="Derived from the acquired fixture observation.",
                        origin=HypothesisOrigin.DIRECT_REASONING,
                        expected_signals=["The planned independent check passes."],
                        verification_checks=["Run the independent fixture verifier."],
                        falsification_criteria=["The independent check fails."],
                    )
                ]
            ),
        )

    registry.register(FunctionCapability(reasoner, reason))

    planner = _definition("planner", {CognitiveActionType.PLAN, CognitiveActionType.REPLAN})

    def plan(
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        task_id = f"verify-{case['id']}-{len(state['plan']) + 1}"
        return _observation(
            planner,
            action,
            summary="Created one bounded verification task.",
            update=CognitiveStateUpdate(
                plan_tasks_to_add=[
                    PlanTask(
                        id=task_id,
                        action="Execute the independent case check.",
                        tool_name="executor",
                        expected_output="A deterministic pass or failure signal.",
                        risk_level=RiskLevel.LOW,
                    )
                ]
            ),
        )

    registry.register(FunctionCapability(planner, plan))

    executor = _definition("executor", {CognitiveActionType.EXECUTE})

    def execute(
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        attempt = len(state["execution_outputs"]) + 1
        passed = not bool(case.get("force_first_verification_failure")) or attempt > 1
        return _observation(
            executor,
            action,
            summary="Executed the deterministic independent case check.",
            update=CognitiveStateUpdate(
                execution_outputs_to_add=[
                    ExecutionOutput(
                        task_id=action.target,
                        summary=(
                            "The case fixture check passed."
                            if passed
                            else "The initial case fixture check exposed a contradiction."
                        ),
                        output={
                            "passed": passed,
                            "case_id": case["id"],
                            "attempt": attempt,
                        },
                    )
                ]
            ),
        )

    registry.register(FunctionCapability(executor, execute))

    verifier = _definition("verifier", {CognitiveActionType.VERIFY})

    def verify(
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        passed = bool(
            state["execution_outputs"]
            and isinstance(state["execution_outputs"][-1].output, dict)
            and state["execution_outputs"][-1].output.get("passed") is True
        )
        return _observation(
            verifier,
            action,
            summary="The independent case verifier completed.",
            update=CognitiveStateUpdate(
                verification=VerificationReport(
                    passed=passed,
                    checks_run=["Checked the deterministic case outcome."],
                    failed_checks=[] if passed else ["The case outcome did not pass."],
                    confidence_delta=0.2 if passed else -0.5,
                ),
                final_answer=str(case["expected_answer"]) if passed else None,
            ),
        )

    registry.register(FunctionCapability(verifier, verify))

    reflector = _definition("reflector", {CognitiveActionType.REFLECT})
    registry.register(
        FunctionCapability(
            reflector,
            lambda action, _state: _observation(
                reflector,
                action,
                summary="Reflected only after the independent check passed.",
                update=CognitiveStateUpdate(
                    reflection=Reflection(
                        outcome_summary="The bounded cross-domain case completed.",
                        what_worked=["Selected an action from the explicit obstacle type."],
                        reusable_lessons=["Match the next action to the unresolved gap."],
                        strategy_notes=["state_dependent_action_selection"],
                    )
                ),
            ),
        )
    )
    return registry


def _initial_state(case: dict[str, Any]) -> PolyaState:
    state = create_initial_state(
        str(case["problem_statement"]),
        session_id=str(case["id"]),
        max_iterations=12,
    )
    unknown = case.get("unknown")
    state["structured_problem"] = StructuredProblem(
        core_question=str(case["core_question"]),
        problem_type=str(case["problem_type"]),
        knowns=[str(item) for item in case["knowns"]],
        unknowns=[str(unknown)] if isinstance(unknown, str) else [],
        constraints=["Use the registered low-risk capabilities only."],
        success_criteria=["Pass an independent deterministic case check."],
    )
    if isinstance(unknown, str):
        state["gaps"] = [
            KnowledgeGap(
                description=unknown,
                gap_type=str(case["gap_type"]),
                priority=PriorityLevel.HIGH,
                why_needed="The unknown blocks a verified conclusion.",
                suggested_source=str(case["suggested_source"]),
            )
        ]
    state["events"] = [
        StateEvent(
            engine_name="constraint_discovery",
            event_type="completed",
            reasoning_mode=ReasoningMode.COMPARE,
            summary="Constraints are pre-discovered to isolate the next-action proof.",
            metadata={"status": "ok"},
        )
    ]
    return state


def _trace_payload(result: Any) -> list[dict[str, Any]]:
    return [event.model_dump(mode="json") for event in result.state["events"]]


def _contains_subsequence(actions: list[str], expected: list[str]) -> bool:
    """Return whether expected actions occur contiguously in the trace."""
    width = len(expected)
    return any(actions[index : index + width] == expected for index in range(len(actions)))


def _repeated_non_progress_count(result: Any) -> int:
    """Count failed actions immediately repeated against the same target."""
    count = 0
    for index, observation in enumerate(result.observations):
        if observation.status is ObservationStatus.SUCCEEDED:
            continue
        if index + 1 >= len(result.decisions):
            continue
        current = result.decisions[index].selected
        following = result.decisions[index + 1].selected
        if current.action_type is following.action_type and current.target == following.target:
            count += 1
    return count


def main() -> int:
    cases = _load_cases()
    run_root = EVAL_ROOT / "runs" / date.today().isoformat()
    summaries: list[dict[str, Any]] = []
    verified_recovery_result = None
    for case in cases:
        started = perf_counter()
        result = CognitiveKernel(_registry(case)).run(_initial_state(case), max_cycles=12)
        controller_latency_ms = (perf_counter() - started) * 1000
        if case["id"] == "current_api_behavior":
            verified_recovery_result = result
        actions = [decision.selected.action_type.value for decision in result.decisions]
        first_action = actions[0]
        expected = str(case["expected_first_action"])
        expected_recovery = case.get("expected_recovery_action")
        recovery_correct = expected_recovery is None or (
            len(actions) > 1 and actions[1] == expected_recovery
        )
        expected_verification_recovery = bool(case.get("expected_verification_recovery", False))
        verification_recovery_correct = not expected_verification_recovery or _contains_subsequence(
            actions,
            ["verify", "replan", "execute", "verify"],
        )
        repeated_non_progress_count = _repeated_non_progress_count(result)
        estimated_capability_cost = sum(
            decision.selected.estimated_cost
            for decision in result.decisions
            if decision.selected.action_type is not CognitiveActionType.STOP
        )
        passed = (
            result.status is CognitiveRunStatus.COMPLETED
            and first_action == expected
            and recovery_correct
            and verification_recovery_correct
            and result.state["final_answer"] == case["expected_answer"]
            and result.state["verification"] is not None
            and result.state["verification"].passed
        )
        case_root = run_root / str(case["id"])
        _write_json(case_root / "trace.json", _trace_payload(result))
        _write_json(
            case_root / "result.json",
            {
                "case_id": case["id"],
                "category": case["category"],
                "status": result.status.value,
                "actions": actions,
                "expected_first_action": expected,
                "first_action_correct": first_action == expected,
                "expected_recovery_action": expected_recovery,
                "recovery_correct": recovery_correct,
                "expected_verification_recovery": expected_verification_recovery,
                "verification_recovery_correct": verification_recovery_correct,
                "repeated_non_progress_count": repeated_non_progress_count,
                "controller_latency_ms": controller_latency_ms,
                "estimated_capability_cost": estimated_capability_cost,
                "model_tokens": 0,
                "final_answer": result.state["final_answer"],
                "verification_passed": bool(
                    result.state["verification"] and result.state["verification"].passed
                ),
                "passed": passed,
            },
        )
        summaries.append(
            {
                "case_id": case["id"],
                "category": case["category"],
                "passed": passed,
                "first_action": first_action,
                "expected_first_action": expected,
                "expected_recovery_action": expected_recovery,
                "recovery_correct": recovery_correct,
                "expected_verification_recovery": expected_verification_recovery,
                "verification_recovery_correct": verification_recovery_correct,
                "repeated_non_progress_count": repeated_non_progress_count,
                "controller_latency_ms": controller_latency_ms,
                "estimated_capability_cost": estimated_capability_cost,
                "cycles": result.cycles,
            }
        )

    if verified_recovery_result is None:
        raise RuntimeError("procedural transfer source case did not run")
    memory = ProceduralMemory()
    learned = memory.learn(verified_recovery_result)
    source_case = next(case for case in cases if case["id"] == "current_api_behavior")
    related_case = {
        **source_case,
        "id": "related_api_behavior",
        "problem_statement": "Determine a related endpoint's current official behavior.",
        "core_question": "What is the related endpoint's current official behavior?",
        "unknown": "the related endpoint's current official behavior",
    }
    related_state = _initial_state(related_case)
    related_registry = _registry(related_case)
    without_memory = CognitiveController().decide(related_state, related_registry)
    with_memory = CognitiveController(memory).decide(related_state, related_registry)
    transfer_passed = (
        len(learned) == 1
        and without_memory.selected.action_type is CognitiveActionType.SEARCH
        and with_memory.selected.action_type is CognitiveActionType.INSPECT
    )
    procedural_transfer = {
        "source_case": "current_api_behavior",
        "source_verified": bool(
            verified_recovery_result.state["verification"]
            and verified_recovery_result.state["verification"].passed
        ),
        "learned_strategies": [item.model_dump(mode="json") for item in learned],
        "without_memory_action": without_memory.selected.action_type.value,
        "with_memory_action": with_memory.selected.action_type.value,
        "changed_action": (
            without_memory.selected.action_type is not with_memory.selected.action_type
        ),
        "passed": transfer_passed,
    }
    _write_json(run_root / "procedural_transfer.json", procedural_transfer)

    summary = {
        "proof_type": "offline_structural_cognitive_control",
        "controller_owns_action_selection": True,
        "model_used_for_control": False,
        "case_count": len(summaries),
        "passed_count": sum(bool(item["passed"]) for item in summaries),
        "recovery_case_count": sum(
            item["expected_recovery_action"] is not None for item in summaries
        ),
        "recovery_passed_count": sum(
            item["expected_recovery_action"] is not None and item["recovery_correct"]
            for item in summaries
        ),
        "verification_failure_case_count": sum(
            bool(item["expected_verification_recovery"]) for item in summaries
        ),
        "verification_failure_recovered_count": sum(
            bool(item["expected_verification_recovery"])
            and bool(item["verification_recovery_correct"])
            for item in summaries
        ),
        "repeated_non_progress_count": sum(
            int(item["repeated_non_progress_count"]) for item in summaries
        ),
        "controller_mean_latency_ms": (
            sum(float(item["controller_latency_ms"]) for item in summaries) / len(summaries)
        ),
        "estimated_capability_cost_total": sum(
            float(item["estimated_capability_cost"]) for item in summaries
        ),
        "controller_model_tokens": 0,
        "all_passed": (all(bool(item["passed"]) for item in summaries) and transfer_passed),
        "categories": sorted({str(item["category"]) for item in summaries}),
        "limitations": [
            "Fixture capabilities prove control structure, not real-world answer quality.",
            "No live tool-enabled direct-model baseline is included in this offline proof.",
            (
                "This structural fixture uses in-memory transfer; the persisted runtime "
                "uses verified Postgres procedural memory."
            ),
        ],
        "procedural_transfer": procedural_transfer,
        "cases": summaries,
    }
    _write_json(run_root / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
