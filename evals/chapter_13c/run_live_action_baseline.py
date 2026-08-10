#!/usr/bin/env python3
"""Compare Chapter 13-C next-action selection with the same configured model.

The direct model sees the same structured state and declared capability set but
does not receive the deterministic controller's rules or decision. Fixtures are
synthetic and non-confidential. This is an action-selection comparison, not an
end-to-end real-world outcome benchmark.
"""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any

from pydantic import ValidationError

from app.cognition import (
    CapabilityDefinition,
    CapabilityRegistry,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveController,
    CognitiveObservation,
    FunctionCapability,
    ObservationStatus,
)
from app.config import Settings
from app.graph.state import PolyaState, StateEvent, create_initial_state
from app.llm import (
    LLMMessage,
    LLMRequest,
    LLMRequestOptions,
    LLMRole,
    OpenRouterLLMClient,
    complete_with_retry,
)
from app.models.contracts import (
    ContractModel,
    KnowledgeGap,
    PriorityLevel,
    ReasoningMode,
    StructuredProblem,
)

EVAL_ROOT = Path(__file__).resolve().parent
LIVE_EVAL_OPT_IN = "POLYABRAIN_ALLOW_NONCONFIDENTIAL_LIVE_EVAL"


class DirectActionSelection(ContractModel):
    """Strict direct-model action response used by the comparison."""

    action_type: CognitiveActionType
    capability: str
    target: str
    rationale: str


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_cases(limit: int | None) -> list[dict[str, Any]]:
    payload = json.loads((EVAL_ROOT / "cases.json").read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise ValueError("Chapter 13-C cases must be a JSON list of objects")
    return payload[:limit] if limit is not None else payload


def _state(case: dict[str, Any]) -> PolyaState:
    state = create_initial_state(
        str(case["problem_statement"]),
        session_id=f"live-{case['id']}",
    )
    unknown = case.get("unknown")
    state["structured_problem"] = StructuredProblem(
        core_question=str(case["core_question"]),
        problem_type=str(case["problem_type"]),
        knowns=[str(item) for item in case["knowns"]],
        unknowns=[str(unknown)] if isinstance(unknown, str) else [],
        constraints=["Use only declared capabilities."],
        success_criteria=["Choose the next action most likely to enable verification."],
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
            summary="Constraints are pre-discovered to isolate next-action selection.",
            metadata={"status": "ok"},
        )
    ]
    return state


def _dummy_executor(
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
            status=ObservationStatus.SUCCEEDED,
            summary="Live selection comparison does not execute capabilities.",
        )

    return execute


def _registry() -> CapabilityRegistry:
    action_sets = {
        "human_input": {CognitiveActionType.CLARIFY, CognitiveActionType.ASK_HUMAN},
        "reasoner": {
            CognitiveActionType.REFRAME,
            CognitiveActionType.DECOMPOSE,
            CognitiveActionType.COMPARE,
            CognitiveActionType.HYPOTHESIZE,
        },
        "memory": {CognitiveActionType.RETRIEVE_MEMORY, CognitiveActionType.RECALL},
        "web_search": {CognitiveActionType.SEARCH},
        "inspector": {CognitiveActionType.INSPECT},
        "observer": {CognitiveActionType.OBSERVE},
        "measurement": {CognitiveActionType.MEASURE},
        "calculator": {CognitiveActionType.CALCULATE},
        "simulator": {CognitiveActionType.SIMULATE},
        "experiment": {CognitiveActionType.EXPERIMENT},
        "planner": {CognitiveActionType.PLAN, CognitiveActionType.REPLAN},
        "executor": {CognitiveActionType.EXECUTE, CognitiveActionType.RETRY},
        "monitor": {CognitiveActionType.MONITOR},
        "verifier": {CognitiveActionType.VERIFY},
        "reflector": {CognitiveActionType.REFLECT},
    }
    registry = CapabilityRegistry()
    for name, actions in action_sets.items():
        definition = CapabilityDefinition(
            name=name,
            version="live-selection-v1",
            supported_actions=actions,
            estimated_cost=0.05,
        )
        registry.register(FunctionCapability(definition, _dummy_executor(definition)))
    return registry


def _state_payload(state: PolyaState) -> dict[str, Any]:
    return {
        "raw_input": state["raw_input"],
        "structured_problem": (
            state["structured_problem"].model_dump(mode="json")
            if state["structured_problem"] is not None
            else None
        ),
        "gaps": [gap.model_dump(mode="json") for gap in state["gaps"]],
        "evidence": [item.model_dump(mode="json") for item in state["evidence"]],
        "hypotheses": [item.model_dump(mode="json") for item in state["hypotheses"]],
        "plan": [item.model_dump(mode="json") for item in state["plan"]],
        "verification": (
            state["verification"].model_dump(mode="json")
            if state["verification"] is not None
            else None
        ),
    }


def _request(
    model: str,
    state: PolyaState,
    registry: CapabilityRegistry,
) -> LLMRequest:
    capabilities = [item.model_dump(mode="json") for item in registry.definitions()]
    return LLMRequest(
        model=model,
        messages=[
            LLMMessage(
                role=LLMRole.SYSTEM,
                content=(
                    "Select exactly one next problem-solving action. You control only this "
                    "single decision. Use the explicit state and declared capabilities. Do not "
                    "solve the whole problem, invent observations, or select an unavailable "
                    "capability. Return only a JSON object with string fields action_type, "
                    "capability, target, and rationale. action_type must be one of the declared "
                    "supported action values; capability must be its exact declared name."
                ),
            ),
            LLMMessage(
                role=LLMRole.USER,
                content=(
                    "CURRENT STATE:\n"
                    f"{json.dumps(_state_payload(state), sort_keys=True)}\n\n"
                    "DECLARED CAPABILITIES:\n"
                    f"{json.dumps(capabilities, sort_keys=True)}"
                ),
            ),
        ],
        options=LLMRequestOptions(
            temperature=0.0,
            max_output_tokens=800,
            json_mode=True,
            timeout_seconds=120,
            max_retries=1,
            max_retry_delay_seconds=8,
        ),
    )


def _parse_selection(text: str) -> DirectActionSelection:
    normalized = text.strip()
    if normalized.startswith("```"):
        first_newline = normalized.find("\n")
        last_fence = normalized.rfind("```")
        if first_newline != -1 and last_fence > first_newline:
            normalized = normalized[first_newline + 1 : last_fence].strip()
    start = normalized.find("{")
    end = normalized.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("direct model returned no JSON object")
    try:
        return DirectActionSelection.model_validate_json(normalized[start : end + 1])
    except ValidationError as exc:
        raise ValueError("direct model returned an invalid action selection") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    if os.environ.get(LIVE_EVAL_OPT_IN) != "1":
        raise RuntimeError(
            f"Set {LIVE_EVAL_OPT_IN}=1 only for these non-confidential synthetic fixtures."
        )

    settings = Settings()
    if not settings.openrouter_model:
        raise RuntimeError("OPENROUTER_MODEL is not configured")
    client = OpenRouterLLMClient.from_settings(settings)
    registry = _registry()
    cases = _load_cases(args.limit)
    run_root = EVAL_ROOT / "live_action_runs" / date.today().isoformat()
    results: list[dict[str, Any]] = []

    for case in cases:
        state = _state(case)
        controller_started = perf_counter()
        controller_selection = CognitiveController().decide(state, registry).selected
        controller_latency_ms = (perf_counter() - controller_started) * 1000

        response = complete_with_retry(client, _request(settings.openrouter_model, state, registry))
        parse_error: str | None = None
        try:
            direct_selection = _parse_selection(response.text)
        except ValueError as exc:
            direct_selection = None
            parse_error = str(exc)

        expected = CognitiveActionType(str(case["expected_first_action"]))
        accepted = {
            CognitiveActionType(item)
            for item in case.get("accepted_first_actions", [expected.value])
        }
        direct_supported = bool(
            direct_selection is not None
            and registry.supports(
                direct_selection.capability,
                direct_selection.action_type,
            )
        )
        item = {
            "case_id": case["id"],
            "category": case["category"],
            "expected_action": expected.value,
            "accepted_actions": sorted(item.value for item in accepted),
            "controller_action": controller_selection.action_type.value,
            "controller_correct": controller_selection.action_type in accepted,
            "controller_latency_ms": controller_latency_ms,
            "controller_model_tokens": 0,
            "direct_action": (
                direct_selection.action_type.value if direct_selection is not None else None
            ),
            "direct_capability": (
                direct_selection.capability if direct_selection is not None else None
            ),
            "direct_target": direct_selection.target if direct_selection is not None else None,
            "direct_rationale": (
                direct_selection.rationale if direct_selection is not None else None
            ),
            "direct_supported": direct_supported,
            "direct_correct": bool(
                direct_selection is not None
                and direct_selection.action_type in accepted
                and direct_supported
            ),
            "direct_latency_ms": response.duration_ms,
            "direct_usage": response.usage.model_dump(mode="json"),
            "parse_error": parse_error,
        }
        _write_json(run_root / str(case["id"]) / "result.json", item)
        results.append(item)
        print(
            f"{case['id']}: expected={expected.value} "
            f"controller={item['controller_action']} direct={item['direct_action']}"
        )

    summary = {
        "comparison_type": "live_first_action_selection",
        "model": settings.openrouter_model,
        "case_count": len(results),
        "controller_correct": sum(bool(item["controller_correct"]) for item in results),
        "direct_correct": sum(bool(item["direct_correct"]) for item in results),
        "direct_parse_failures": sum(item["parse_error"] is not None for item in results),
        "controller_mean_latency_ms": (
            sum(float(item["controller_latency_ms"]) for item in results) / len(results)
        ),
        "direct_mean_latency_ms": (
            sum(float(item["direct_latency_ms"]) for item in results) / len(results)
        ),
        "direct_total_tokens": sum(
            int(item["direct_usage"]["input_tokens"]) + int(item["direct_usage"]["output_tokens"])
            for item in results
        ),
        "limitations": [
            "This compares the first state-dependent action, not complete real-world outcomes.",
            "Synthetic cases make the expected action deterministic and auditable.",
            "Capability execution quality is evaluated by the separate structural proof.",
        ],
        "cases": results,
    }
    _write_json(run_root / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
