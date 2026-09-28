"""Provider-shape repair keeps typed cognition moving without inventing content."""

import json

from app.cognition.model_contracts import DeliberationCapabilityOutput, PlanGenerationOutput
from app.cognition.model_gateway import CognitiveModelGateway
from app.graph.state import create_initial_state
from app.llm import FakeLLMClient, LLMResponse


def test_gateway_drops_only_extra_nested_provider_fields():
    payload = {
        "hypotheses": [
            {
                "statement": "A candidate.",
                "origin": "direct_reasoning",
                "mechanism": "A mechanism.",
                "expected_signals": ["A signal."],
                "evidence_for": [],
                "evidence_against": [],
                "verification_checks": ["A check."],
                "falsification_criteria": ["A failure."],
                "confidence": 0.8,
                "status": "candidate",
                "provider_note": "discard this shape-only field",
            }
        ],
        "tasks": [
            {
                "id": "analysis",
                "action": "Analyze the candidate.",
                "tool_name": "deliberator",
                "params": {},
                "depends_on": [],
                "expected_output": "A result.",
                "risk_level": "low",
            }
        ],
        "execution_outputs": [
            {
                "task_id": "analysis",
                "summary": "A result.",
                "output": {"value": 1},
                "artifact_ids": [],
                "error": None,
                "provider_note": "discard this output field",
            }
        ],
        "provider_note": "discard this root field",
    }
    client = FakeLLMClient([LLMResponse(provider="fake", model="fake", text=json.dumps(payload))])
    result = CognitiveModelGateway(client, "fake").complete(
        capability="deliberator",
        instructions="Return a bounded candidate and analytic result.",
        output_type=DeliberationCapabilityOutput,
        state=create_initial_state("Analyze a candidate."),
    )
    assert result.output.hypotheses[0].statement == "A candidate."
    assert result.output.execution_outputs[0].output == {"value": 1}
    assert result.model_calls == 1


def test_schema_repair_keeps_original_capability_and_tool_context():
    repaired = {
        "tasks": [
            {
                "id": "execute",
                "action": "Run code",
                "tool_name": "python_sandbox",
                "params": {"code": "value=1", "tests": ["assert value==1"]},
            }
        ]
    }
    client = FakeLLMClient(
        [
            LLMResponse(provider="fake", model="fake", text='{"tasks":['),
            LLMResponse(provider="fake", model="fake", text=json.dumps(repaired)),
        ]
    )
    result = CognitiveModelGateway(client, "fake").complete(
        capability="planner",
        instructions="Preserve assertions and keep sandbox tasks pending.",
        output_type=PlanGenerationOutput,
        state=create_initial_state("Implement a function."),
        context={"available_tools": ["python_sandbox"]},
    )
    assert result.model_calls == 2
    first, second = client.requests
    assert first.messages[0].content in second.messages[0].content
    payload = json.loads(second.messages[1].content)
    assert payload["original_input"] == first.messages[1].content
    assert payload["invalid_response"] == '{"tasks":['
    assert result.output.tasks[0].tool_name == "python_sandbox"
