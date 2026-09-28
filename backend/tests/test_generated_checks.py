"""Literal guesses are rejected before admission, never locally changed into passes."""

import json
from copy import deepcopy

import pytest

from app.cognition.generated_checks import validate_generated_checks
from app.cognition.model_contracts import DeliberationCapabilityOutput, PlanGenerationOutput
from app.cognition.model_gateway import CognitiveModelGateway, ModelCapabilityParseError
from app.graph.state import create_initial_state
from app.llm import FakeLLMClient, LLMResponse
from app.models.contracts import PlanTask


def task(test):
    return PlanTask(
        id="test",
        action="Test implementation",
        tool_name="python_sandbox",
        params={"code": "def f(x): return x", "tests": [test]},
        risk_level="medium",
    )


@pytest.mark.parametrize(
    "source, check",
    [
        ("Examples: f(1)==2.", "assert f( 1 ) == 2"),
        ("f([]) is None", "assert f([]) is None"),
        ("f('a b') == 'c d'", 'assert f("a b") == "c d"'),
        ("f([1,2]) == [3,4]", "assert f([1, 2]) == [3, 4]"),
        ("Example: f(-1)==-2; keep inputs.", "assert f(-1) == -2"),
    ],
)
def test_explicit_user_examples_keep_their_exact_expectations(source, check):
    proposed = [task(check)]
    before = deepcopy(proposed)
    validate_generated_checks(proposed, {"raw_input": source})
    assert proposed == before


@pytest.mark.parametrize(
    "source, check",
    [
        ("Implement shortest_span.", "assert shortest_span([-1,-2,-3],-5)==2"),
        ("f(1)==20", "assert f(1)==2"),
        ("f(1)==2", "assert f(2)==2"),
        ("f('a b')=='c d'", "assert f('ab')=='cd'"),
        ("f([]) is None", "assert f([]) is False"),
        ("Return twice the number.", "assert 2 == f(1)"),
        ("f(1)==2", "def checks():\n    assert f(2)==4\nchecks()"),
    ],
)
def test_unsupported_values_arguments_and_string_content_cannot_borrow_provenance(source, check):
    proposed = [task(check)]
    before = deepcopy(proposed)
    with pytest.raises(ValueError, match="literal expected"):
        validate_generated_checks(proposed, {"raw_input": source})
    assert proposed == before


def test_previous_checks_are_preserved_without_becoming_correctness_claims():
    original = "assert f(-5)==2"
    context = {"raw_input": "Implement f", "existing_python_tests": [original]}
    validate_generated_checks([task(original)], context)
    with pytest.raises(ValueError):
        validate_generated_checks([task("assert f(-5)==1")], context)


def test_executable_reference_is_allowed_but_static_guard_does_not_certify_it():
    check = "def oracle(x): return 0\nassert f(4)==oracle(4)"
    validate_generated_checks([task(check)], {"raw_input": "Implement f"})
    # This deliberately bad oracle passes the origin screen. Execution and
    # semantic review must still reject it; the screen is not a verifier.


def test_even_correct_invented_literal_needs_the_reference_shape():
    context = {"raw_input": "Implement f to double an integer. Example: f(1)==2"}
    with pytest.raises(ValueError, match="literal expected"):
        validate_generated_checks([task("assert f(4)==8")], context)
    validate_generated_checks(
        [task("assert f(1)==2\ndef reference(x): return x+x\nassert f(4)==reference(4)")],
        context,
    )


def response(check):
    return LLMResponse(
        provider="fake",
        model="fake",
        text=json.dumps({"tasks": [task(check).model_dump(mode="json")]}),
    )


@pytest.mark.parametrize("repair_valid", [False, True])
def test_gateway_screens_initial_and_repair_responses(repair_valid):
    original = "assert f(4)==9"
    repair = (
        "def oracle(x): return x + x\nassert f(4)==oracle(4)" if repair_valid else "assert f(4)==8"
    )
    client = FakeLLMClient([response(original), response(repair)])
    call = dict(
        capability="planner",
        instructions="Use executable references for invented cases.",
        output_type=PlanGenerationOutput,
        state=create_initial_state("Implement f to double its integer input."),
    )
    if repair_valid:
        result = CognitiveModelGateway(client, "fake").complete(**call)
        assert result.output.tasks[0].params["tests"] == [repair]
        assert result.model_calls == 2
    else:
        with pytest.raises(ModelCapabilityParseError, match="literal expected"):
            CognitiveModelGateway(client, "fake").complete(**call)
    assert len(client.requests) == 2
    repair_context = json.loads(client.requests[1].messages[-1].content)
    assert "literal expected" in repair_context["validation_error"]
    assert "double its integer input" in repair_context["original_input"]


def test_one_repair_sees_both_invalid_selection_and_unsourced_test():
    hypothesis = {
        "statement": "Double using addition",
        "origin": "direct_reasoning",
        "status": "selected",
    }
    initial = {
        "hypotheses": [hypothesis],
        "tasks": [task("assert f(4)==9").model_dump(mode="json")],
    }
    repaired = {
        "hypotheses": [{**hypothesis, "status": "candidate"}],
        "tasks": [
            task("def reference(x): return x+x\nassert f(4)==reference(4)").model_dump(mode="json")
        ],
    }
    client = FakeLLMClient(
        [
            LLMResponse(provider="fake", model="fake", text=json.dumps(data))
            for data in (initial, repaired)
        ]
    )
    result = CognitiveModelGateway(client, "fake").complete(
        capability="deliberator",
        instructions="Use candidate hypotheses and derived checks.",
        output_type=DeliberationCapabilityOutput,
        state=create_initial_state("Implement f to double its integer input."),
        max_provider_attempts=2,
    )
    feedback = json.loads(client.requests[1].messages[-1].content)["validation_error"]
    assert "selected hypothesis requires supporting" in feedback
    assert "literal expected output" in feedback
    assert result.model_calls == len(client.requests) == 2
    assert result.output.hypotheses[0].status.value == "candidate"
    assert result.output.tasks[0].params["tests"] == repaired["tasks"][0]["params"]["tests"]
