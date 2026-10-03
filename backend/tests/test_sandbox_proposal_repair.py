"""Execution bounds must reach the existing model repair, without silent truncation."""

import json
from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.cognition.capabilities import AuditedCapabilityError
from app.cognition.model_contracts import PlanGenerationOutput
from app.cognition.model_gateway import CognitiveModelGateway
from app.graph.state import create_initial_state
from app.llm import FakeLLMClient, LLMResponse


def payload():
    return {
        "tasks": [
            {
                "id": "code",
                "action": "Implement and check",
                "tool_name": "python_sandbox",
                "risk_level": "medium",
                "params": {"code": "def f(x): return x+x", "tests": ["assert f(1)==2"]},
            }
        ]
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("code", ""),
        ("code", "x" * 20001),
        ("tests", []),
        ("tests", ["assert True"] * 21),
        ("tests", [3]),
        ("tests", [" " * 5]),
        ("tests", ["#" * 2001]),
    ],
)
def test_invalid_sandbox_parameters_rejected_at_model_boundary(field, value):
    data = payload()
    data["tasks"][0]["params"][field] = value
    before = deepcopy(data)
    with pytest.raises(ValidationError, match="Sandbox proposal bounds"):
        PlanGenerationOutput.model_validate(data)
    assert data == before


@pytest.mark.parametrize("repair_valid", [True, False])
def test_oversized_test_gets_one_bounded_model_repair(repair_valid):
    original = payload()
    original["tasks"][0]["params"]["tests"] = ["#" * 2100 + "\nassert f(1)==2"]
    corrected = payload() if repair_valid else original
    client = FakeLLMClient(
        [
            LLMResponse(provider="fake", model="fake", text=json.dumps(p))
            for p in (original, corrected)
        ]
    )
    call = dict(
        capability="planner",
        instructions="Propose bounded code and tests",
        output_type=PlanGenerationOutput,
        state=create_initial_state("Implement f to double input. f(1)==2"),
        max_provider_attempts=2,
    )
    if repair_valid:
        result = CognitiveModelGateway(client, "fake").complete(**call)
        assert result.model_calls == 2
        assert result.output.tasks[0].params["tests"] == ["assert f(1)==2"]
    else:
        with pytest.raises(AuditedCapabilityError) as error:
            CognitiveModelGateway(client, "fake").complete(**call)
        assert "Sandbox proposal bounds" in str(error.value.__cause__)
        assert error.value.payload["model_calls"] == 2
    assert len(client.requests) == 2
    error = json.loads(client.requests[1].messages[-1].content)["validation_error"]
    assert "tasks[0].params.tests[0]" in error
    assert "1..2000" in error
    assert "#" * 100 not in error
