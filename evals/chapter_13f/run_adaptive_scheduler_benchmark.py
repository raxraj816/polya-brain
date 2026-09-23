"""Repeated offline static-vs-adaptive routing benchmark for Chapter 13-F."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Literal

from pydantic import Field

from app.cognition import (
    CapabilityDefinition,
    CapabilityKind,
    CapabilityPerformanceLedger,
    CapabilityPerformanceSample,
    CapabilityRegistry,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveController,
    CognitiveObservation,
    FunctionCapability,
    ObservationStatus,
)
from app.graph.state import PolyaState, StateEvent, create_initial_state
from app.models.contracts import (
    ContractModel,
    KnowledgeGap,
    PriorityLevel,
    ReasoningMode,
    StructuredProblem,
)

ROOT = Path(__file__).resolve().parent
CASES_PATH = ROOT / "cases.json"
RESULTS_ROOT = ROOT / "results"
CONDITIONS = ("healthy", "degraded", "recovered", "version_changed")


class SchedulerCase(ContractModel):
    """One held-out routing task with a prior capability-health regime."""

    id: str = Field(min_length=1)
    problem_type: str = Field(min_length=1)
    condition: Literal["healthy", "degraded", "recovered", "version_changed"]
    question: str = Field(min_length=1)
    gap: str = Field(min_length=1)


def load_cases() -> list[SchedulerCase]:
    payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    cases = [SchedulerCase.model_validate(item) for item in payload]
    if len(cases) < 8:
        raise ValueError("Chapter 13-F requires at least eight held-out scheduler cases")
    if {case.condition for case in cases} != set(CONDITIONS):
        raise ValueError("cases must cover healthy, degraded, recovered, and version-changed")
    if len({case.problem_type for case in cases}) != len(cases):
        raise ValueError("each held-out case requires a distinct task family")
    return cases


def condition_order(case_index: int, repetition: int) -> tuple[str, str]:
    """Rotate controller evaluation order to expose order-sensitive harness bugs."""
    return ("static", "adaptive") if (case_index + repetition) % 2 == 0 else ("adaptive", "static")


def _state(case: SchedulerCase, repetition: int) -> PolyaState:
    state = create_initial_state(
        case.question,
        session_id=f"{case.id}-held-out-{repetition}",
    )
    state["structured_problem"] = StructuredProblem(
        core_question=case.question,
        problem_type=case.problem_type,
        knowns=["The answer depends on current public behavior."],
        unknowns=[case.gap],
        constraints=["Use an inspectable source and verify the present case."],
        success_criteria=["Resolve the gap with a present-case check."],
    )
    state["gaps"] = [
        KnowledgeGap(
            description=case.gap,
            gap_type="current_external_fact",
            priority=PriorityLevel.HIGH,
            why_needed="The current fact blocks a verified outcome.",
            suggested_source="official web source",
        )
    ]
    state["events"] = [
        StateEvent(
            engine_name="constraint_discovery",
            event_type="completed",
            reasoning_mode=ReasoningMode.COMPARE,
            summary="Benchmark constraints were supplied.",
            metadata={"status": "ok"},
        )
    ]
    return state


def _registry(case: SchedulerCase) -> CapabilityRegistry:
    web_version = "web-v2" if case.condition == "version_changed" else "web-v1"
    registry = CapabilityRegistry()

    def register(definition: CapabilityDefinition) -> None:
        def execute(
            action: CognitiveActionCandidate,
            _state: PolyaState,
        ) -> CognitiveObservation:
            return CognitiveObservation(
                action_id=action.id,
                capability=definition.name,
                capability_version=definition.version,
                status=ObservationStatus.SUCCEEDED,
                summary="Returned the benchmark observation for independent scoring.",
                payload={"procedure": "deterministic_benchmark_fixture"},
            )

        registry.register(FunctionCapability(definition, execute))

    register(
        CapabilityDefinition(
            name="web_search",
            version=web_version,
            supported_actions={CognitiveActionType.SEARCH},
            kind=CapabilityKind.EXTERNAL,
            max_external_calls=1,
            estimated_cost=0.05,
        )
    )
    register(
        CapabilityDefinition(
            name="inspector",
            version="inspector-v1",
            supported_actions={CognitiveActionType.INSPECT},
            approved_for_sensitive_data=True,
            estimated_cost=0.2,
        )
    )
    return registry


def _sample(
    case: SchedulerCase,
    index: int,
    *,
    succeeded: bool,
    verified: bool,
    version: str,
) -> CapabilityPerformanceSample:
    return CapabilityPerformanceSample(
        session_id=f"{case.id}-prior-{index}",
        task_family=case.problem_type,
        action_type=CognitiveActionType.SEARCH,
        capability="web_search",
        capability_version=version,
        capability_kind=CapabilityKind.EXTERNAL,
        operational_success=succeeded,
        contributed_to_verified_outcome=verified,
        duration_ms=900.0 if succeeded else 8_000.0,
        external_calls=1,
        input_tokens=1_800 if succeeded else 600,
        output_tokens=700 if succeeded else 0,
        normalized_cost=0.05,
    )


def prior_ledger(case: SchedulerCase) -> CapabilityPerformanceLedger:
    """Build prior observations only; the held-out decision is never pre-recorded."""
    ledger = CapabilityPerformanceLedger()
    if case.condition == "healthy":
        history = [(True, True)] * 8
    elif case.condition == "degraded":
        history = [(False, False)] * 8
    elif case.condition == "recovered":
        history = [*([(False, False)] * 8), *([(True, True)] * 20)]
    else:
        history = [(False, False)] * 8
    for index, (succeeded, verified) in enumerate(history, start=1):
        ledger.record(
            _sample(
                case,
                index,
                succeeded=succeeded,
                verified=verified,
                version="web-v1",
            )
        )
    return ledger


def _expected_action(case: SchedulerCase) -> CognitiveActionType:
    return (
        CognitiveActionType.INSPECT if case.condition == "degraded" else CognitiveActionType.SEARCH
    )


def _outcome(
    case: SchedulerCase,
    action: CognitiveActionType,
) -> dict[str, int | float | bool]:
    expected = _expected_action(case)
    verified = action is expected
    if action is CognitiveActionType.SEARCH:
        latency_ms = 8_000.0 if case.condition == "degraded" else 900.0
        return {
            "verified_outcome": verified,
            "external_calls": 1,
            "tokens": 2_500 if verified else 600,
            "latency_ms": latency_ms,
        }
    return {
        "verified_outcome": verified,
        "external_calls": 0,
        "tokens": 0,
        "latency_ms": 180.0,
    }


def _run_condition(
    case: SchedulerCase,
    repetition: int,
    controller_kind: str,
) -> dict[str, Any]:
    state = _state(case, repetition)
    registry = _registry(case)
    controller = (
        CognitiveController()
        if controller_kind == "static"
        else CognitiveController(performance_policy=prior_ledger(case))
    )
    started = perf_counter()
    decision = controller.decide(state, registry)
    overhead_ms = (perf_counter() - started) * 1000
    observation = registry.execute(decision.selected, state)
    outcome = _outcome(case, decision.selected.action_type)
    best_outcome = _outcome(case, _expected_action(case))
    failure_penalty_ms = 10_000.0 if not outcome["verified_outcome"] else 0.0
    regret_ms = max(
        0.0,
        float(outcome["latency_ms"]) - float(best_outcome["latency_ms"]) + failure_penalty_ms,
    )
    return {
        "case_id": case.id,
        "task_family": case.problem_type,
        "capability_condition": case.condition,
        "repetition": repetition,
        "controller": controller_kind,
        "selected_action": decision.selected.action_type.value,
        "selected_capability": decision.selected.capability,
        "expected_action": _expected_action(case).value,
        "route_correct": decision.selected.action_type is _expected_action(case),
        "observation_status": observation.status.value,
        "scheduler_overhead_ms": overhead_ms,
        "regret_ms": regret_ms,
        **outcome,
    }


def summarize(results: list[dict[str, Any]], repetitions: int) -> dict[str, Any]:
    by_controller: dict[str, dict[str, Any]] = {}
    for controller in ("static", "adaptive"):
        items = [item for item in results if item["controller"] == controller]
        count = len(items)
        by_controller[controller] = {
            "runs": count,
            "verified_outcomes": sum(bool(item["verified_outcome"]) for item in items),
            "verified_outcome_rate": (
                sum(bool(item["verified_outcome"]) for item in items) / count
            ),
            "wrong_routes": sum(not bool(item["route_correct"]) for item in items),
            "external_calls": sum(int(item["external_calls"]) for item in items),
            "tokens": sum(int(item["tokens"]) for item in items),
            "total_latency_ms": sum(float(item["latency_ms"]) for item in items),
            "total_regret_ms": sum(float(item["regret_ms"]) for item in items),
            "mean_scheduler_overhead_ms": sum(
                float(item["scheduler_overhead_ms"]) for item in items
            )
            / count,
        }
    static = by_controller["static"]
    adaptive = by_controller["adaptive"]
    expected_runs = len(load_cases()) * repetitions
    gate = bool(
        repetitions >= 5
        and adaptive["runs"] == expected_runs
        and adaptive["verified_outcome_rate"] >= static["verified_outcome_rate"]
        and adaptive["wrong_routes"] < static["wrong_routes"]
        and adaptive["external_calls"] < static["external_calls"]
        and adaptive["tokens"] < static["tokens"]
        and adaptive["total_latency_ms"] < static["total_latency_ms"]
        and adaptive["total_regret_ms"] < static["total_regret_ms"]
    )
    return {
        "benchmark": "chapter_13f_adaptive_scheduler",
        "repetitions": repetitions,
        "case_count": len(load_cases()),
        "controllers": by_controller,
        "gate": {
            "adaptive_scheduler_gate_passed": gate,
            "scope": "scheduler-specific held-out deterministic capability regimes",
            "general_intelligence_win_claimed": False,
        },
    }


def run_benchmark(*, repetitions: int = 5) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if repetitions < 1:
        raise ValueError("repetitions must be at least one")
    results: list[dict[str, Any]] = []
    for repetition in range(1, repetitions + 1):
        for case_index, case in enumerate(load_cases()):
            for controller_kind in condition_order(case_index, repetition):
                results.append(_run_condition(case, repetition, controller_kind))
    return summarize(results, repetitions), results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--write-artifact", action="store_true")
    args = parser.parse_args()
    summary, results = run_benchmark(repetitions=args.repetitions)
    if args.write_artifact:
        run_id = datetime.now(UTC).strftime("%Y-%m-%d/%H%M%S")
        run_dir = RESULTS_ROOT / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        (run_dir / "results.json").write_text(
            json.dumps(results, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (run_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        summary["artifact_dir"] = str(run_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
