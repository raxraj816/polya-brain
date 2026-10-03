"""Preferred research must use the actual invocation reservation."""

import pytest
from test_scope_review import state_with_stalled_research

from app.cognition import (
    CapabilityDefinition,
    CapabilityRegistry,
    CognitiveActionType,
    CognitiveController,
    CognitiveKernel,
    FunctionCapability,
)
from app.cognition.contracts import CapabilityKind, CognitiveRunStatus
from app.cognition.task_model import CognitiveResourceBudget, budget_event


@pytest.mark.parametrize(
    "preferred,action,kind",
    [
        ("scope_reviewer", CognitiveActionType.REFRAME, CapabilityKind.MODEL),
        ("public_page_reader", CognitiveActionType.SEARCH, CapabilityKind.EXTERNAL),
    ],
)
@pytest.mark.parametrize("declared,invocation", [(1, 3), (3, 1)])
def test_preferred_route_uses_invocation_budget_and_keeps_rejection_trace(
    preferred, action, kind, declared, invocation
):
    state = state_with_stalled_research()
    state["events"].append(
        budget_event(CognitiveResourceBudget(max_model_calls=2, max_external_calls=2))
    )
    field = "max_model_calls" if kind is CapabilityKind.MODEL else "max_external_calls"
    definition = CapabilityDefinition(
        name=preferred, version="test", kind=kind, supported_actions={action}, **{field: declared}
    )
    registry = CapabilityRegistry()
    registry.register(
        FunctionCapability(
            definition,
            lambda *_: pytest.fail("routing only"),
            reservation=lambda _: definition.model_copy(update={field: invocation}),
        )
    )
    search = CapabilityDefinition(
        name="web_search",
        version="test",
        kind=CapabilityKind.EXTERNAL,
        supported_actions={CognitiveActionType.SEARCH},
        max_external_calls=1,
    )
    registry.register(FunctionCapability(search, lambda *_: pytest.fail("routing only")))
    decision = CognitiveController().decide(state, registry)
    assert decision.selected.capability == ("web_search" if invocation > 2 else preferred)
    if invocation > 2:
        assert any(preferred in r.rationale and "budget" in r.rationale for r in decision.rejected)


@pytest.mark.parametrize("failure", ["budget", "missing"])
def test_pending_evaluation_cannot_be_bypassed_by_buying_more_evidence(failure):
    state = state_with_stalled_research()
    state["events"] = [
        e for e in state["events"] if e.event_type != "evidence_evaluation_completed"
    ]
    state["events"].append(budget_event(CognitiveResourceBudget(max_model_calls=0)))
    registry = CapabilityRegistry()
    if failure == "budget":
        definition = CapabilityDefinition(
            name="evidence_evaluator",
            version="test",
            kind=CapabilityKind.MODEL,
            supported_actions={CognitiveActionType.EVALUATE_EVIDENCE},
            max_model_calls=1,
        )
        registry.register(
            FunctionCapability(definition, lambda *_: pytest.fail("must not dispatch"))
        )
    search = CapabilityDefinition(
        name="web_search", version="test", supported_actions={CognitiveActionType.SEARCH}
    )
    registry.register(
        FunctionCapability(
            search, lambda *_: pytest.fail("pending evidence must not trigger more acquisition")
        )
    )
    result = CognitiveKernel(registry).run(state, max_cycles=2)
    assert result.status is CognitiveRunStatus.INSUFFICIENT_EVIDENCE
    assert not result.observations
    assert result.state["evidence"] == state["evidence"]
    assert result.state["final_answer"] is None
