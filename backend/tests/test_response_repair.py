"""Small explicit edits cannot bypass full admission or spend another repair."""

import hashlib
import json
from copy import deepcopy

import pytest
from backend.tests.test_coding_execution import action_for, proposal, ready_state

from app.cognition.capabilities import AuditedCapabilityError
from app.cognition.model_contracts import PlanGenerationOutput
from app.cognition.model_gateway import CognitiveModelGateway, ModelCapabilityParseError
from app.cognition.on_demand_capabilities import deliberator_capability
from app.cognition.response_repair import apply_response_edits
from app.cognition.semantic_broker import RoutedCognitiveModelGateway, SemanticModelRoute
from app.graph.state import create_initial_state
from app.llm import FakeLLMClient, LLMResponse


def response(data):
    return LLMResponse(provider="fake", model="test", text=json.dumps(data))


def plan():
    return {
        "tasks": [
            {
                "id": "execute",
                "action": "Test double",
                "tool_name": "python_sandbox",
                "params": {"code": "def f(x):\n    return x + x\n", "tests": ["assert f(3)==7"]},
            }
        ]
    }


def patch(value, path=None):
    return {"edits": [{"path": path or ["tasks", 0, "params", "tests", 0], "value": value}]}


def invoke(client, **kwargs):
    return CognitiveModelGateway(client, "test").complete(
        capability="planner",
        instructions="Implement and verify doubling; retain existing tests",
        output_type=PlanGenerationOutput,
        state=create_initial_state("Double the integer"),
        **kwargs,
    )


def test_explicit_edits_preserve_every_unmentioned_value_and_original_object():
    original = plan()
    before = deepcopy(original)
    tests = "def reference(x): return x+x\nassert f(3)==reference(3)"
    repaired, metadata = apply_response_edits(original, patch(tests))
    expected = deepcopy(original)
    expected["tasks"][0]["params"]["tests"][0] = tests
    assert original == before
    assert repaired == expected
    assert metadata["paths"] == [["tasks", 0, "params", "tests", 0]]
    assert (
        metadata["original_sha256"]
        == hashlib.sha256(
            json.dumps(original, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
    )
    assert metadata["original_sha256"] != metadata["reconstructed_sha256"]
    repaired["tasks"][0]["params"]["code"] = "changed later"
    assert original == before


@pytest.mark.parametrize(
    "path",
    [
        [],
        ["missing", "child"],
        ["tasks", -1],
        ["tasks", 1],
        ["tasks", True],
        ["tasks", "0"],
        [0],
        ["tasks", 0, "params", "code", 0],
        ["x"] * 13,
    ],
)
def test_invalid_paths_are_rejected_without_partial_mutation(path):
    original = plan()
    before = deepcopy(original)
    with pytest.raises(ValueError):
        apply_response_edits(original, {"edits": [{"path": path, "value": "replacement"}]})
    assert original == before


@pytest.mark.parametrize(
    "paths",
    [
        [["tasks"], ["tasks", 0]],
        [["tasks", 0], ["tasks"]],
        [["tasks"], ["tasks"]],
    ],
)
def test_duplicate_and_ancestor_paths_are_rejected(paths):
    with pytest.raises(ValueError, match="overlap"):
        apply_response_edits(plan(), {"edits": [{"path": p, "value": []} for p in paths]})


def test_size_bounds_required_value_and_unknown_operations():
    for data in [
        patch("x" * 64001),
        {"edits": []},
        {"edits": [{"path": [str(i)], "value": None} for i in range(17)]},
        {"edits": [{"path": ["tasks"]}]},
        {"edits": [{"path": ["tasks"], "value": [], "op": "delete"}]},
    ]:
        with pytest.raises(ValueError):
            apply_response_edits(plan(), data)


def test_missing_object_field_can_be_added_and_none_is_explicit():
    original = {"tasks": [{"id": "execute"}]}
    result, _ = apply_response_edits(original, patch(None, ["tasks", 0, "expected_output"]))
    assert result == {"tasks": [{"id": "execute", "expected_output": None}]}
    assert original == {"tasks": [{"id": "execute"}]}


def test_gateway_applies_small_edit_then_validates_complete_plan_with_two_calls():
    check = "def reference(x): return x+x\nassert f(3)==reference(3)"
    client = FakeLLMClient([response(plan()), response(patch(check))])
    result = invoke(client, max_provider_attempts=2)
    assert result.output.tasks[0].params["code"] == plan()["tasks"][0]["params"]["code"]
    assert result.output.tasks[0].params["tests"] == [check]
    assert result.response_repair["response_form"] == "edits"
    assert result.model_calls == len(client.requests) == 2
    assert "REPAIR_JSON_SCHEMA" in client.requests[1].messages[0].content


@pytest.mark.parametrize(
    "edit",
    [
        patch("assert f(3)==6"),  # Correct-looking new literal still fails admission.
        patch([], ["tasks"]),  # The original planner contract still requires work.
        patch("low", ["tasks", 1, "risk_level"]),  # No implicit list insertion.
    ],
)
def test_invalid_reconstruction_has_no_third_attempt(edit):
    client = FakeLLMClient([response(plan()), response(edit), response({"tasks": []})])
    with pytest.raises(ModelCapabilityParseError):
        invoke(client)
    assert len(client.requests) == 2


def test_single_attempt_ceiling_stops_before_edit_request():
    client = FakeLLMClient([response(plan())])
    with pytest.raises(AuditedCapabilityError):
        invoke(client, max_provider_attempts=1)
    assert len(client.requests) == 1


def test_truncated_original_keeps_full_response_repair():
    valid = plan()
    valid["tasks"][0]["params"]["tests"] = ["assert 1+1 == 2"]
    client = FakeLLMClient(
        [LLMResponse(provider="fake", model="test", text='{"tasks":['), response(valid)]
    )
    result = invoke(client)
    assert result.response_repair["response_form"] == "full"
    assert result.response_repair["original_sha256"] is None
    assert "REPAIR_JSON_SCHEMA" not in client.requests[1].messages[0].content


def test_repair_metadata_survives_routing_and_enters_capability_observation():
    initial = proposal()
    initial["tasks"][0]["params"]["tests"].append("assert count_odd([1])==1")
    edited_tests = proposal()["tasks"][0]["params"]["tests"]
    client = FakeLLMClient(
        [response(initial), response(patch(edited_tests, ["tasks", 0, "params", "tests"]))]
    )
    gateway = RoutedCognitiveModelGateway(client, [SemanticModelRoute(model_slug="test")])
    capability = deliberator_capability(gateway, allow_python_sandbox=True)
    state = ready_state()
    observed = capability.execute(action_for(capability, state), state)
    metadata = observed.payload["response_repair"]
    assert metadata["response_form"] == "edits"
    assert metadata["paths"] == [["tasks", 0, "params", "tests"]]
    assert observed.payload["model_calls"] == 2
    assert (
        observed.proposed_update.plan_tasks_to_add[0].params["code"]
        == initial["tasks"][0]["params"]["code"]
    )


def test_edits_cannot_promote_unverified_hypotheses():
    initial = proposal()
    initial["tasks"][0]["params"]["tests"].append("assert count_odd([1])==1")
    edit = patch(proposal()["tasks"][0]["params"]["tests"], ["tasks", 0, "params", "tests"])
    edit["edits"].append({"path": ["hypotheses", 0, "status"], "value": "verified"})
    client = FakeLLMClient([response(initial), response(edit)])
    capability = deliberator_capability(
        CognitiveModelGateway(client, "test"), allow_python_sandbox=True
    )
    state = ready_state()
    with pytest.raises(ModelCapabilityParseError, match="No admitted evidence"):
        capability.execute(action_for(capability, state), state)
    assert len(client.requests) == 2
    assert state["plan"] == []
    assert state["hypotheses"] == []


def test_durable_trace_keeps_bounded_repair_identity_without_values():
    from app.cognition.capabilities import safe_observation_trace_telemetry

    _, metadata = apply_response_edits(plan(), patch("private replacement body"))
    metadata["value"] = "private replacement body"
    safe = safe_observation_trace_telemetry({"response_repair": metadata})
    assert safe["response_repair"]["paths"] == metadata["paths"]
    assert "private replacement body" not in json.dumps(safe)
    metadata["reconstructed_sha256"] = "not a hash"
    assert safe_observation_trace_telemetry({"response_repair": metadata}) == {}
