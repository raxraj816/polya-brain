"""Offline structural proof for Chapter 13-D on-demand task learning.

The baselines are deterministic simulations of information conditions, not live
model results. The Polya condition executes the real controller, capability
registry, kernel, hard budget, verified procedural memory, and resource ledger.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.cognition import (
    CapabilityDefinition,
    CapabilityKind,
    CapabilityRegistry,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveController,
    CognitiveKernel,
    CognitiveObservation,
    CognitiveResourceBudget,
    CognitiveRunResult,
    CognitiveRunStatus,
    CognitiveStateUpdate,
    FunctionCapability,
    ObservationStatus,
    ProceduralMemory,
    accumulated_usage,
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
    StructuredProblem,
    VerificationReport,
)

ROOT = Path(__file__).resolve().parent
DEFAULT_CASES = ROOT / "cases.json"


def load_cases(path: Path = DEFAULT_CASES) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or len(payload) < 6:
        raise ValueError("Chapter 13-D requires at least six micro-world cases")
    cases = [dict(item) for item in payload if isinstance(item, dict)]
    if len({str(item["family"]) for item in cases}) < 3:
        raise ValueError("Chapter 13-D requires at least three structural families")
    return cases


def _initial_state(case: dict[str, Any]) -> PolyaState:
    state = create_initial_state(str(case["core_question"]), session_id=str(case["id"]))
    state["structured_problem"] = StructuredProblem(
        core_question=str(case["core_question"]),
        problem_type=str(case["problem_type"]),
        domain=str(case["domain"]),
        knowns=["The named micro-world is fictional and has no valid pretrained answer."],
        unknowns=[str(case["unknown"])],
        constraints=["Use only current supplied micro-world evidence."],
        success_criteria=[str(case["success_criterion"])],
        required_data_sources=["authoritative supplied manual artifact"],
    )
    state["gaps"] = [
        KnowledgeGap(
            description=str(case["unknown"]),
            gap_type=str(case["gap_type"]),
            priority=PriorityLevel.HIGH,
            why_needed="The unfamiliar rule is required before the answer can be verified.",
            suggested_source="official current source",
        )
    ]
    state["events"] = [
        StateEvent(
            engine_name="constraint_discovery",
            event_type="completed",
            reasoning_mode=ReasoningMode.COMPARE,
            summary="Micro-world constraints were supplied by the benchmark.",
            metadata={"status": "ok"},
        ),
        StateEvent(
            engine_name="task_gap_detector",
            event_type="gap_detection_completed",
            reasoning_mode=ReasoningMode.EXPLORE,
            summary="The benchmark supplied one explicit unfamiliar-rule gap.",
            metadata={"status": "ok", "gap_count": 1, "llm_call_count": 0},
        ),
    ]
    return state


def _capability(
    definition: CapabilityDefinition,
    executor: Callable[[CognitiveActionCandidate, PolyaState], CognitiveObservation],
) -> FunctionCapability:
    return FunctionCapability(definition, executor)


def _registry(case: dict[str, Any]) -> CapabilityRegistry:
    registry = CapabilityRegistry()
    search_definition = CapabilityDefinition(
        name="web_search",
        version="micro_world_unavailable_search@0.1.0",
        supported_actions={CognitiveActionType.SEARCH},
        kind=CapabilityKind.EXTERNAL,
        max_external_calls=1,
        estimated_cost=0.12,
    )

    def search(
        action: CognitiveActionCandidate,
        _state: PolyaState,
    ) -> CognitiveObservation:
        return CognitiveObservation(
            action_id=action.id,
            capability=search_definition.name,
            capability_version=search_definition.version,
            status=ObservationStatus.FAILED,
            summary="The public web does not contain this fictional micro-world.",
            payload={"external_calls": 1},
            failure_kind="no_results",
        )

    registry.register(_capability(search_definition, search))
    inspect_definition = CapabilityDefinition(
        name="inspector",
        version="micro_world_manual@0.1.0",
        supported_actions={CognitiveActionType.INSPECT},
        estimated_cost=0.11,
    )

    def inspect(
        action: CognitiveActionCandidate,
        _state: PolyaState,
    ) -> CognitiveObservation:
        claim = str(case["observation"])
        return CognitiveObservation(
            action_id=action.id,
            capability=inspect_definition.name,
            capability_version=inspect_definition.version,
            status=ObservationStatus.SUCCEEDED,
            summary="Inspected the authoritative supplied fictional manual.",
            payload={"procedure": "deterministic", "model_calls": 0},
            evidence=[
                EvidenceItem(
                    source_type="evaluated_micro_world_manual",
                    source_uri=f"fixture://chapter-13d/{case['id']}/manual",
                    claim=claim,
                    raw_excerpt=claim,
                    reliability_score=1.0,
                    relevance_score=1.0,
                )
            ],
            proposed_update=CognitiveStateUpdate(
                knowns_to_add=[claim],
                unknowns_to_resolve=[str(case["unknown"])],
                resolved_gap_targets=[action.target],
            ),
        )

    registry.register(_capability(inspect_definition, inspect))
    deliberator_definition = CapabilityDefinition(
        name="deliberator",
        version="micro_world_fused_deliberator@0.1.0",
        supported_actions={CognitiveActionType.HYPOTHESIZE},
        kind=CapabilityKind.MODEL,
        max_model_calls=1,
        max_output_tokens=600,
        estimated_cost=0.2,
    )

    def deliberate(
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        source_uri = state["evidence"][-1].source_uri or "fixture://missing"
        task_id = f"check-{case['id']}"
        return CognitiveObservation(
            action_id=action.id,
            capability=deliberator_definition.name,
            capability_version=deliberator_definition.version,
            status=ObservationStatus.SUCCEEDED,
            summary="Constructed and checked one evidence-grounded candidate.",
            payload={
                "model_calls": 1,
                "usage": {"input_tokens": 180, "output_tokens": 90},
            },
            proposed_update=CognitiveStateUpdate(
                hypotheses_to_add=[
                    Hypothesis(
                        statement=str(case["answer"]),
                        mechanism="Apply the supplied fictional manual rule.",
                        origin=HypothesisOrigin.DIRECT_REASONING,
                        expected_signals=[str(case["observation"])],
                        evidence_for=[source_uri],
                        verification_checks=[str(case["success_criterion"])],
                        falsification_criteria=["The supplied manual states a different rule."],
                    )
                ],
                plan_tasks_to_add=[
                    PlanTask(
                        id=task_id,
                        action="Compare the candidate answer with the authoritative excerpt.",
                        tool_name="deliberator",
                        expected_output="The answer matches the current supplied rule.",
                    )
                ],
                execution_outputs_to_add=[
                    ExecutionOutput(
                        task_id=task_id,
                        summary="The answer terms match the authoritative supplied excerpt.",
                        output={"source_uri": source_uri, "answer": str(case["answer"])},
                    )
                ],
            ),
        )

    registry.register(_capability(deliberator_definition, deliberate))
    verifier_definition = CapabilityDefinition(
        name="conclusion_checker",
        version="micro_world_conclusion_checker@0.1.0",
        supported_actions={CognitiveActionType.VERIFY},
        kind=CapabilityKind.MODEL,
        max_model_calls=1,
        max_output_tokens=500,
        estimated_cost=0.2,
    )

    def verify(
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        answer = str(case["answer"])
        expected = [str(item).casefold() for item in case["expected_terms"]]
        evidence_text = " ".join(item.claim for item in state["evidence"]).casefold()
        passed = all(term in f"{answer} {evidence_text}".casefold() for term in expected)
        return CognitiveObservation(
            action_id=action.id,
            capability=verifier_definition.name,
            capability_version=verifier_definition.version,
            status=ObservationStatus.SUCCEEDED,
            summary="Verified the candidate against the unfamiliar current manual.",
            payload={
                "model_calls": 1,
                "usage": {"input_tokens": 170, "output_tokens": 80},
            },
            proposed_update=CognitiveStateUpdate(
                verification=VerificationReport(
                    passed=passed,
                    checks_run=[str(case["success_criterion"])],
                    failed_checks=[] if passed else ["Expected answer terms were unsupported."],
                    confidence_delta=0.2 if passed else -0.5,
                    recommended_route="finalize" if passed else "replan",
                ),
                final_answer=answer if passed else None,
                reflection=(
                    Reflection(
                        outcome_summary="Resolved an unfamiliar rule from supplied evidence.",
                        what_worked=["Inspected and checked the authoritative local manual."],
                        reusable_lessons=[
                            "When public search cannot know a fictional rule, inspect the supplied manual."
                        ],
                        strategy_notes=["search_failure_then_authoritative_inspection"],
                    )
                    if passed
                    else None
                ),
            ),
        )

    registry.register(_capability(verifier_definition, verify))
    return registry


def _score(case: dict[str, Any], answer: str | None) -> bool:
    text = (answer or "").casefold()
    return all(str(term).casefold() in text for term in case["expected_terms"])


def _simulated_baselines(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    distractors = int(case["distractor_documents"])
    return {
        "direct": {
            "passed": False,
            "model_calls": 1,
            "acquisitions": 0,
            "context_documents": 0,
            "verification": False,
            "note": "Closed-book model cannot inspect a deliberately fictional rule.",
        },
        "full_context": {
            "passed": True,
            "model_calls": 1,
            "acquisitions": 0,
            "context_documents": distractors + 1,
            "verification": False,
            "note": "Simulated answer with every relevant and distractor document supplied.",
        },
        "ordinary_retrieval": {
            "passed": True,
            "model_calls": 1,
            "acquisitions": 1,
            "context_documents": 1,
            "verification": False,
            "note": "Simulated ideal top-1 retrieval followed by one answer call.",
        },
    }


def run_proof(cases: list[dict[str, Any]]) -> dict[str, Any]:
    memories = {str(case["pair"]): ProceduralMemory() for case in cases}
    results: list[dict[str, Any]] = []
    previous_polya_calls: dict[str, int] = {}
    for case in cases:
        pair = str(case["pair"])
        memory = memories[pair]
        result: CognitiveRunResult = CognitiveKernel(
            _registry(case),
            controller=CognitiveController(memory),
        ).run(
            _initial_state(case),
            max_cycles=7,
            budget=CognitiveResourceBudget(
                max_model_calls=2,
                max_external_calls=1,
                max_input_tokens=5_000,
                max_output_tokens=2_000,
                max_normalized_cost=2.0,
            ),
        )
        usage = accumulated_usage(result.state)
        selected_actions = [decision.selected.action_type.value for decision in result.decisions]
        acquisition_actions = [
            action
            for action in selected_actions
            if action in {"search", "inspect", "retrieve_memory", "measure", "observe"}
        ]
        passed = result.status is CognitiveRunStatus.COMPLETED and _score(
            case, result.state["final_answer"]
        )
        learned = memory.learn(result)
        first_calls = previous_polya_calls.get(pair)
        if case["phase"] == "first_encounter":
            previous_polya_calls[pair] = len(acquisition_actions)
        transfer_savings = (
            first_calls - len(acquisition_actions) if first_calls is not None else None
        )
        results.append(
            {
                "case_id": case["id"],
                "pair": pair,
                "phase": case["phase"],
                "family": case["family"],
                "baselines": _simulated_baselines(case),
                "polya": {
                    "passed": passed,
                    "status": result.status.value,
                    "model_calls": usage.model_calls,
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "external_calls": usage.external_calls,
                    "normalized_cost": round(usage.normalized_cost, 3),
                    "acquisition_actions": acquisition_actions,
                    "acquisition_action_count": len(acquisition_actions),
                    "selected_actions": selected_actions,
                    "verification": bool(
                        result.state["verification"] is not None
                        and result.state["verification"].passed
                    ),
                    "source_uris": [
                        item.source_uri for item in result.state["evidence"] if item.source_uri
                    ],
                    "learned_strategy_count": len(learned),
                    "transfer_acquisition_savings": transfer_savings,
                },
            }
        )
    transfer_results = [item for item in results if item["phase"] == "transfer"]
    gate = {
        "structural_proof_passed": all(item["polya"]["passed"] for item in results),
        "six_cases": len(results) >= 6,
        "three_families": len({item["family"] for item in results}) >= 3,
        "all_polya_runs_verified": all(item["polya"]["verification"] for item in results),
        "all_polya_runs_within_two_model_calls": all(
            item["polya"]["model_calls"] <= 2 for item in results
        ),
        "all_transfer_cases_reduce_acquisition_work": all(
            (item["polya"]["transfer_acquisition_savings"] or 0) >= 1 for item in transfer_results
        ),
        "scientific_win_claimed": False,
    }
    gate["structural_proof_passed"] = bool(
        gate["structural_proof_passed"]
        and gate["six_cases"]
        and gate["three_families"]
        and gate["all_polya_runs_verified"]
        and gate["all_polya_runs_within_two_model_calls"]
        and gate["all_transfer_cases_reduce_acquisition_work"]
    )
    return {
        "benchmark": "chapter_13d_micro_world_structural_proof",
        "generated_at": datetime.now(UTC).isoformat(),
        "limitations": [
            "The three non-Polya conditions are deterministic information-condition simulations, not live model calls.",
            "Fixture semantic capabilities establish wiring and accounting, not real-model intelligence.",
            "No scientific PolyaBrain win is claimed without repeated held-out live comparisons.",
        ],
        "gate": gate,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    summary = run_proof(load_cases(args.cases))
    rendered = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if not summary["gate"]["structural_proof_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
