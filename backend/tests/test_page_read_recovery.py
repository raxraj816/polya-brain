"""A failed document does not prohibit a bounded read after fresh discovery."""

import hashlib
import json

import httpx
import pytest
from pydantic import TypeAdapter
from test_page_reader import public_dns
from test_scope_review import TARGET, state_with_stalled_research

from app.acquisition.page_reader import (
    ATTEMPT_EVENT,
    PublicPageReader,
    page_read_target,
    public_page_capability,
)
from app.cognition import (
    CapabilityDefinition,
    CapabilityRegistry,
    CognitiveActionType,
    CognitiveController,
    CognitiveKernel,
    FunctionCapability,
)
from app.cognition.task_model import CognitiveResourceBudget, accumulated_usage, budget_event
from app.graph.state import PolyaState, StateEvent
from app.models.contracts import ReasoningMode

FIRST = "https://official.example.org/rule"
SECOND = "https://official.example.org/new-document"


def event(kind, metadata, engine="web_search"):
    return StateEvent(
        engine_name=engine,
        event_type=kind,
        reasoning_mode=ReasoningMode.EXPLORE,
        summary="Controlled recovery fixture.",
        metadata=metadata,
    )


def failed_read(*, limit=4):
    calls = []

    def handle(request):
        calls.append(str(request.url))
        if request.url.path == "/rule":
            return httpx.Response(404)
        return httpx.Response(
            200,
            headers={"content-type": "text/plain"},
            text="A newly discovered passage still requires independent evaluation.",
        )

    capabilities = CapabilityRegistry()
    capabilities.register(
        public_page_capability(
            PublicPageReader(resolver=public_dns, transport=httpx.MockTransport(handle))
        )
    )
    state = state_with_stalled_research()
    state["events"].extend(
        [
            budget_event(CognitiveResourceBudget(max_external_calls=limit)),
            event("cognitive_resource_usage", {"external_calls": 1}, "cognitive_kernel"),
        ]
    )
    result = CognitiveKernel(capabilities).run(state, max_cycles=1)
    assert result.observations[0].failure_kind == "public_page_read_failed"
    assert len(calls) == 1
    assert accumulated_usage(result.state).external_calls == 2
    return result.state, capabilities, calls


def discover(state, *, target=TARGET, source=SECOND, evaluated=True, engine="web_search"):
    state["evidence"].append(state["evidence"][0].model_copy(update={"source_uri": source}))
    state["events"].extend(
        [
            event(
                "evidence_candidates_acquired",
                {"acquisition_id": "fresh", "target_gap": target},
                engine,
            ),
            event("cognitive_resource_usage", {"external_calls": 1}, "cognitive_kernel"),
        ]
    )
    if evaluated:
        state["events"].append(
            event(
                "evidence_evaluation_completed",
                {
                    "acquisition_id": "fresh",
                    "gap_resolved": False,
                    "continuation": {"source_uri": source, "reason": "Read newly found passages."},
                },
                "evidence_evaluator",
            )
        )


def test_fresh_discovery_allows_distinct_read_after_serialized_failure_without_admitting_it():
    state, capabilities, calls = failed_read()
    discover(state)
    state = TypeAdapter(PolyaState).validate_json(TypeAdapter(PolyaState).dump_json(state))
    assert page_read_target(state, TARGET) == SECOND
    before = list(state["evidence"])
    result = CognitiveKernel(capabilities).run(state, max_cycles=1)
    assert result.decisions[0].selected.capability == "public_page_reader"
    assert len(calls) == 2 and calls[0] != calls[1]
    assert accumulated_usage(result.state).external_calls == 4
    assert result.state["evidence"] == before
    assert not result.state["gaps"][0].filled
    assert result.state["verification"] is None
    assert result.state["final_answer"] is None
    attempts = [e for e in result.state["events"] if e.event_type == ATTEMPT_EVENT]
    assert [a.metadata["source_uri"] for a in attempts] == [FIRST, SECOND]
    assert all(a.metadata.get("action_id") for a in attempts)
    capabilities.register(
        FunctionCapability(
            CapabilityDefinition(
                name="evidence_evaluator",
                version="test",
                supported_actions={CognitiveActionType.EVALUATE_EVIDENCE},
            ),
            lambda *_: pytest.fail("Routing only; evaluation must not dispatch here"),
        )
    )
    assert (
        CognitiveController().decide(result.state, capabilities).selected.action_type
        is CognitiveActionType.EVALUATE_EVIDENCE
    )
    discover(result.state, source="https://official.example.org/third")
    assert page_read_target(result.state, TARGET) is None


@pytest.mark.parametrize(
    "condition", ["stale", "unevaluated", "unrelated", "page_batch", "same_url"]
)
def test_failed_read_does_not_retry_without_fresh_evaluated_distinct_discovery(condition):
    state, capabilities, calls = failed_read()
    if condition != "stale":
        discover(
            state,
            evaluated=condition != "unevaluated",
            target="Another gap" if condition == "unrelated" else TARGET,
            engine="public_page_reader" if condition == "page_batch" else "web_search",
            source=FIRST if condition == "same_url" else SECOND,
        )
    assert page_read_target(state, TARGET) is None
    assert (
        CognitiveController().decide(state, capabilities).selected.capability
        != "public_page_reader"
    )
    assert len(calls) == 1


@pytest.mark.parametrize(
    "condition",
    ["missing_attempt", "mismatched_action", "legacy_attempt", "missing_url", "unknown_failure"],
)
def test_unbound_or_unknown_failures_remain_blocked_even_after_discovery(condition):
    state, _, calls = failed_read()
    if condition == "missing_attempt":
        state["events"] = [e for e in state["events"] if e.event_type != ATTEMPT_EVENT]
    elif condition == "mismatched_action":
        next(e for e in state["events"] if e.event_type == ATTEMPT_EVENT).metadata["action_id"] = (
            "wrong-action"
        )
    elif condition == "legacy_attempt":
        next(e for e in state["events"] if e.event_type == ATTEMPT_EVENT).metadata.pop("action_id")
    elif condition == "missing_url":
        next(e for e in state["events"] if e.event_type == ATTEMPT_EVENT).metadata["source_uri"] = (
            ""
        )
    else:
        next(e for e in state["events"] if e.event_type == "capability_observation").metadata[
            "failure_kind"
        ] = "capability_exception"
    discover(state)
    assert page_read_target(state, TARGET) is None
    assert len(calls) == 1


@pytest.mark.parametrize("condition", ["privacy", "budget"])
def test_fresh_read_still_obeys_privacy_and_shared_budget(condition):
    state, capabilities, calls = failed_read(limit=3 if condition == "budget" else 4)
    discover(state)
    if condition == "privacy":
        state["structured_problem"].constraints.append("Keep private information local.")
    assert page_read_target(state, TARGET) == SECOND
    result = CognitiveKernel(capabilities).run(state, max_cycles=1)
    assert result.decisions[0].selected.action_type is CognitiveActionType.STOP
    assert len(calls) == 1
    assert accumulated_usage(result.state).external_calls == 3


def test_actual_search_evaluation_and_page_pipeline_preserves_failure_and_exports_report(tmp_path):
    from app.acquisition import (
        SearchResponse,
        SearchResultCandidate,
        evidence_evaluator_capability,
        web_search_capability,
    )
    from app.cognition import CognitiveModelGateway, CognitiveRunStatus
    from app.investigator.artifacts import export_run
    from app.llm import FakeLLMClient, LLMResponse, LLMTokenUsage

    state, capabilities, calls = failed_read()
    snippet = "Grouped public questions require the full documented lifetime conditions."
    passage = "A newly discovered passage still requires independent evaluation."

    class Search:
        name = "fixture-search"
        requests = 0

        def search(self, request):
            self.requests += 1
            assert self.requests == 1, "Recovery must respect the remaining external budget"
            return SearchResponse(
                provider=self.name,
                query=request.query,
                candidates=[
                    SearchResultCandidate(
                        id="new-source",
                        title="New document",
                        url=SECOND,
                        excerpt=snippet,
                        provider_rank=1,
                    )
                ],
            )

    search = Search()
    page_id = "page-" + hashlib.sha256((SECOND + passage).encode()).hexdigest()[:16]
    responses = []
    for candidate_id, excerpt in [("new-source", snippet), (page_id, passage)]:
        responses.append(
            LLMResponse(
                provider="fake",
                model="fake",
                finish_reason="stop",
                text=json.dumps(
                    {
                        "assessments": [
                            {
                                "candidate_id": candidate_id,
                                "extracted_claim": excerpt,
                                "relationship": "background",
                                "relevance_score": 0.8,
                                "reliability_score": 0.8,
                                "temporal_validity": "timeless",
                                "contradiction_risk": 0,
                                "rationale": "Useful but incomplete fixture evidence.",
                            }
                        ],
                        "gap_supported": False,
                        "overall_rationale": "Important questions remain.",
                        "next_query": "documented applicability limits",
                        "continuation": {
                            "source_uri": SECOND if candidate_id == "new-source" else None,
                            "reason": "Read the newly discovered document or find further evidence.",
                        },
                    }
                ),
                usage=LLMTokenUsage(input_tokens=100, output_tokens=100),
            )
        )
    capabilities.register(web_search_capability(search))
    capabilities.register(
        evidence_evaluator_capability(CognitiveModelGateway(FakeLLMClient(responses), "fake"))
    )
    result = CognitiveKernel(capabilities).run(state, max_cycles=6)
    assert [d.selected.capability for d in result.decisions] == [
        "web_search",
        "evidence_evaluator",
        "public_page_reader",
        "evidence_evaluator",
        "cognitive_controller",
    ]
    assert result.status is CognitiveRunStatus.INSUFFICIENT_EVIDENCE
    assert search.requests == 1 and len(calls) == 2
    assert accumulated_usage(result.state).external_calls == 4
    assert accumulated_usage(result.state).model_calls == 2
    assert not result.state["gaps"][0].filled
    assert result.state["verification"] is None
    assert result.state["final_answer"] is None
    assert result.state["reflection"] is None
    assert any(e.raw_excerpt == passage for e in result.state["evidence"])
    assert any(
        e.metadata.get("failure_kind") == "public_page_read_failed" for e in result.state["events"]
    )
    (tmp_path / "recovered-investigation").mkdir()
    report = export_run(result, tmp_path / "recovered-investigation", elapsed_ms=0)
    assert report.verification_status == "insufficient_evidence"
    saved = json.loads((tmp_path / "recovered-investigation" / "report.json").read_text())
    assert saved["final_conclusion"] == "No verified conclusion is available."
    assert any(e["source_uri"] == SECOND for e in saved["evidence_used"])
