"""Mode hints remain inspectable and reach bounded model capabilities."""

import json

import pytest

from app.cognition.bootstrap import build_cognitive_runtime
from app.cognition.mode_policy import mode_context
from app.cognition.model_gateway import CognitiveModelGateway
from app.config import Settings
from app.graph.state import StateEvent, create_initial_state
from app.llm import FakeLLMClient, LLMResponse
from app.models.contracts import ContractModel, ProductMode


class Answer(ContractModel):
    answer: str


@pytest.mark.parametrize("mode", list(ProductMode))
def test_mode_override_is_preserved_by_shared_composer(mode):
    settings = Settings(
        _env_file=None,
        OPENROUTER_API_KEY="",
        OPENROUTER_MODEL="",
        SEARCH_PROVIDER="",
        SEARCH_API_KEY="",
    )
    result = build_cognitive_runtime(
        settings, mode_hint=mode, domain_hint="quantity_check"
    ).run_problem("What is 17 * 6?", max_cycles=1)
    context = mode_context(result.state)
    assert context["selected_mode"] == mode.value
    assert context["mode_verification_checklist"]
    assert result.state["structured_problem"].domain == "quantity_check"


def test_mode_and_domain_change_representation_capability_identity():
    from app.engines.problem_representation import ProblemRepresentationEngine

    client = FakeLLMClient([])
    inferred = ProblemRepresentationEngine(client=client, model="test")
    compared = ProblemRepresentationEngine(
        client=client, model="test", mode_hint=ProductMode.COMPARE
    )
    reviewed = ProblemRepresentationEngine(
        client=client, model="test", mode_hint=ProductMode.REVIEW
    )
    assert len({engine.version.engine for engine in [inferred, compared, reviewed]}) == 3


def test_downstream_projection_keeps_validated_mode_and_checklist():
    state = create_initial_state("Compare these options.")
    state["events"] = [
        StateEvent(
            engine_name="problem_representation",
            event_type="approach_selected",
            reasoning_mode="compare",
            summary="Selected compare.",
            metadata={"selected_mode": "compare"},
        )
    ]
    fake = FakeLLMClient(
        [LLMResponse(provider="fake", model="test", text='{"answer":"Need comparable evidence."}')]
    )
    gateway = CognitiveModelGateway(fake, "test")
    gateway.complete(
        capability="test",
        instructions="Return an answer.",
        output_type=Answer,
        state=state,
        state_projection={"bounded": True},
        context={"selected_mode": "review"},
    )
    request = json.loads(fake.requests[0].messages[-1].content)
    assert request["current_state"] == {"bounded": True}
    assert request["capability_context"]["selected_mode"] == "compare"
    assert any(
        "at least two" in item
        for item in request["capability_context"]["mode_verification_checklist"]
    )


def test_invalid_or_untrusted_mode_event_is_ignored():
    state = create_initial_state("Investigate.")
    state["events"] = [
        StateEvent(
            engine_name="uploaded_content",
            event_type="approach_selected",
            reasoning_mode="compare",
            summary="Untrusted source text.",
            metadata={"selected_mode": "review"},
        )
    ]
    assert mode_context(state) == {}
