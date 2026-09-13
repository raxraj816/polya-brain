"""Live premium-model probe for the fused Chapter 13-D semantic path."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from app.cognition import (
    CapabilityRegistry,
    CognitiveController,
    CognitiveKernel,
    CognitiveModelGateway,
    CognitiveResourceBudget,
    CognitiveRunStatus,
    accumulated_usage,
    on_demand_cognitive_capabilities,
)
from app.config import Settings
from app.graph.state import StateEvent, create_initial_state
from app.llm import LLMClient, LLMRequest, LLMResponse, OpenRouterLLMClient
from app.models.contracts import EvidenceItem, ReasoningMode, StructuredProblem

ROOT = Path(__file__).resolve().parent
LIVE_EVAL_OPT_IN = "POLYABRAIN_ALLOW_NONCONFIDENTIAL_LIVE_EVAL"


class RecordingClient:
    """Bound and record provider calls without changing their semantics."""

    def __init__(self, delegate: LLMClient, *, max_calls: int) -> None:
        self.delegate = delegate
        self.provider = delegate.provider
        self.capabilities = delegate.capabilities
        self.max_calls = max_calls
        self.responses: list[LLMResponse] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        if len(self.responses) >= self.max_calls:
            raise RuntimeError("live probe model-call budget exhausted")
        response = self.delegate.complete(request)
        self.responses.append(response)
        return response


def _state():
    state = create_initial_state(
        "Use supplied Zephyra revision-7 evidence to determine its request timeout.",
        session_id="live-on-demand-zephyra",
        max_iterations=4,
    )
    state["structured_problem"] = StructuredProblem(
        core_question="What request timeout does Zephyra revision 7 require?",
        problem_type="unfamiliar_manual_lookup",
        domain="fictional_protocol",
        knowns=["Zephyra is fictional; only supplied revision-7 evidence is valid."],
        unknowns=[],
        constraints=["Use only supplied revision-7 evidence."],
        success_criteria=["State the timeout and identify the supplied rule."],
    )
    state["evidence"] = [
        EvidenceItem(
            source_type="evaluated_micro_world_manual",
            source_uri="fixture://chapter-13d/zephyra-revision-7",
            claim="Zephyra manual revision 7 rule Z7.4 states request_timeout_ticks = 37.",
            raw_excerpt="Rule Z7.4: request_timeout_ticks = 37.",
            reliability_score=1.0,
            relevance_score=1.0,
        )
    ]
    state["events"] = [
        StateEvent(
            engine_name="constraint_discovery",
            event_type="completed",
            reasoning_mode=ReasoningMode.COMPARE,
            summary="Constraints were supplied and validated.",
            metadata={"status": "ok"},
        ),
        StateEvent(
            engine_name="task_gap_detector",
            event_type="gap_detection_completed",
            reasoning_mode=ReasoningMode.EXPLORE,
            summary="No blocking gap remains after evidence admission.",
            metadata={"status": "ok", "gap_count": 0, "llm_call_count": 0},
        ),
    ]
    return state


def main() -> int:
    if os.environ.get(LIVE_EVAL_OPT_IN) != "1":
        raise RuntimeError(
            f"Set {LIVE_EVAL_OPT_IN}=1 only for this non-confidential fictional fixture."
        )
    settings = Settings()
    if not settings.openrouter_model:
        raise RuntimeError("OPENROUTER_MODEL is not configured")
    client = RecordingClient(OpenRouterLLMClient.from_settings(settings), max_calls=4)
    gateway = CognitiveModelGateway(client, settings.openrouter_model)
    registry = CapabilityRegistry()
    for capability in on_demand_cognitive_capabilities(gateway):
        registry.register(capability)
    started_at = datetime.now(UTC)
    started = perf_counter()
    result = CognitiveKernel(registry, controller=CognitiveController()).run(
        _state(),
        max_cycles=4,
        budget=CognitiveResourceBudget(
            max_model_calls=4,
            max_external_calls=0,
            max_input_tokens=40_000,
            max_output_tokens=10_000,
            max_normalized_cost=2.0,
        ),
    )
    latency_ms = (perf_counter() - started) * 1000
    usage = accumulated_usage(result.state)
    response_input_tokens = sum(item.usage.input_tokens for item in client.responses)
    response_output_tokens = sum(item.usage.output_tokens for item in client.responses)
    actions = [decision.selected.action_type.value for decision in result.decisions]
    passed = bool(
        result.status is CognitiveRunStatus.COMPLETED
        and result.state["verification"] is not None
        and result.state["verification"].passed
        and "37" in (result.state["final_answer"] or "")
        and "Z7.4" in (result.state["final_answer"] or "")
        and len(client.responses) <= 2
    )
    summary = {
        "probe": "chapter_13d_live_on_demand_fused_path",
        "status": "passed" if passed else "failed",
        "started_at": started_at.isoformat(),
        "model": settings.openrouter_model,
        "fictional_nonconfidential_fixture": True,
        "run_status": result.status.value,
        "actions": actions,
        "cycles": result.cycles,
        "verification_passed": bool(
            result.state["verification"] is not None and result.state["verification"].passed
        ),
        "final_answer": result.state["final_answer"],
        "model_calls": len(client.responses),
        "ledger_model_calls": usage.model_calls,
        "input_tokens": response_input_tokens,
        "output_tokens": response_output_tokens,
        "total_tokens": response_input_tokens + response_output_tokens,
        "latency_ms": round(latency_ms, 3),
        "normalized_cost": round(usage.normalized_cost, 3),
        "task_model_snapshot_count": sum(
            event.event_type == "task_model_snapshot" for event in result.state["events"]
        ),
        "limitations": [
            "One synthetic lookup probe is endpoint and architecture verification, not a win claim.",
            "The evidence was already admitted so this isolates post-evidence semantic work.",
            "Repeated held-out comparisons remain required for product-value evidence.",
        ],
    }
    model_hash = hashlib.sha256(settings.openrouter_model.encode()).hexdigest()[:8]
    run_id = f"{started_at.strftime('%H%M%S')}-{model_hash}"
    output = ROOT / "live_runs" / started_at.date().isoformat() / run_id / "summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
