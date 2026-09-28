"""Compact requests preserve evidence, execution failures and contract enforcement."""

import json
from copy import deepcopy

import pytest
from pydantic import Field

from app.cognition.model_contracts import HypothesisGenerationOutput, PlanGenerationOutput
from app.cognition.model_gateway import (
    CognitiveModelGateway,
    ModelCapabilityParseError,
    _state_payload,
)
from app.cognition.model_wire import compact_record, compact_schema
from app.graph.state import ExecutionOutput, create_initial_state
from app.llm import FakeLLMClient, LLMResponse
from app.models.contracts import (
    ContractModel,
    EvidenceItem,
    Hypothesis,
    KnowledgeGap,
    PlanTask,
    StructuredProblem,
    VerificationReport,
)


def test_compact_state_round_trips_without_losing_tool_data_or_failures():
    state = create_initial_state("Keep this exact text, including  two spaces.")
    state["structured_problem"] = StructuredProblem(core_question="Fix it", problem_type="coding")
    state["gaps"] = [KnowledgeGap(description="Execution", gap_type="test", why_needed="Verify")]
    state["evidence"] = [
        EvidenceItem(
            source_type="local",
            source_uri="fixture://source",
            claim="A claim",
            raw_excerpt="a = 1\n\n",
            reliability_score=0.0,
        )
    ]
    state["hypotheses"] = [Hypothesis(statement="Candidate", origin="direct_reasoning")]
    data = {"empty": [], "null": None, "object": {}, "flag": False, "zero": 0}
    state["plan"] = [
        PlanTask(
            id="execute",
            action="Test",
            tool_name="python_sandbox",
            params={"code": "def f():\n    return None\n", "tests": ["assert f() is None"], **data},
        )
    ]
    state["execution_outputs"] = [
        ExecutionOutput(
            task_id="execute",
            summary="Failed check",
            output=data,
            error="AssertionError",
        )
    ]
    state["verification"] = VerificationReport(
        passed=False,
        checks_run=["Executed"],
        failed_checks=["Wrong result"],
        confidence_delta=0.0,
        recommended_route="repair",
    )
    before = deepcopy(state)
    wire = _state_payload(state)
    assert state == before
    assert wire["raw_input"] == state["raw_input"]
    for key in ("structured_problem", "verification"):
        assert type(state[key]).model_validate(wire[key]) == state[key]
    for key in ("gaps", "evidence", "hypotheses", "plan", "execution_outputs"):
        for original, sent in zip(state[key], wire[key], strict=True):
            assert type(original).model_validate(sent) == original
    assert wire["plan"][0]["params"] == state["plan"][0].params
    assert wire["execution_outputs"][0]["output"] == data
    assert wire["execution_outputs"][0]["error"] == "AssertionError"
    assert wire["gaps"][0]["filled"] is False
    assert wire["gaps"][0]["priority"] == "medium"
    assert wire["hypotheses"][0]["status"] == "candidate"
    assert wire["plan"][0]["risk_level"] == "low"
    assert wire["evidence"][0]["reliability_score"] == 0.0
    assert "unknowns" not in wire["structured_problem"]
    assert len(json.dumps(wire["plan"][0])) < len(
        json.dumps(state["plan"][0].model_dump(mode="json"))
    )


def test_schema_compaction_preserves_property_names_defaults_and_constraints():
    class Titled(ContractModel):
        title: str = Field(min_length=2, description="User title")
        metadata: dict = Field(default={"title": "default value", "empty": []})

    original = Titled.model_json_schema()
    schema = compact_schema(Titled, unselected_only=False)
    assert schema["properties"]["title"] == {
        "type": "string",
        "minLength": 2,
        "description": "User title",
    }
    assert schema["properties"]["metadata"]["default"] == {"title": "default value", "empty": []}
    assert schema["required"] == original["required"]
    assert schema["additionalProperties"] is False
    assert Titled.model_json_schema() == original
    assert compact_record(Titled(title="Hello"))["metadata"]["title"] == "default value"


def hypothesis(status):
    return {
        "statement": "Candidate",
        "origin": "direct_reasoning",
        "status": status,
        "evidence_for": ["fixture://source"],
        "verification_checks": ["Check source"],
        "falsification_criteria": ["Source disagrees"],
        "selection_rationale": "Source supports it",
    }


def response(data):
    return LLMResponse(provider="fake", model="fake", text=json.dumps(data))


@pytest.mark.parametrize("status", ["selected", "verified", "falsified"])
@pytest.mark.parametrize("extra", [False, True])
def test_no_evidence_policy_rejects_invented_support_even_after_extra_field_pruning(status, extra):
    data = {"hypotheses": [hypothesis(status)]}
    if extra:
        data["provider_note"] = "Extra field is harmless but status is not"
    client = FakeLLMClient([response(data), response(data)])
    with pytest.raises(ModelCapabilityParseError, match="No admitted evidence"):
        CognitiveModelGateway(client, "fake").complete(
            capability="hypothesizer",
            instructions="Propose candidates",
            output_type=HypothesisGenerationOutput,
            state=create_initial_state("Solve it"),
        )
    assert len(client.requests) == 2
    for request in client.requests:
        assert '"enum":["candidate","deferred","rejected"]' in request.messages[0].content
        assert request.messages[0].content.count("OUTPUT_JSON_SCHEMA:\n") == 1


def test_existing_evidence_keeps_selection_available_and_repairs_keep_context():
    state = create_initial_state("Use the supplied source")
    state["evidence"] = [
        EvidenceItem(source_type="local", source_uri="fixture://source", claim="Fact")
    ]
    client = FakeLLMClient(
        [
            response({"hypotheses": []}),
            response({"hypotheses": [hypothesis("selected")]}),
        ]
    )
    result = CognitiveModelGateway(client, "fake").complete(
        capability="hypothesizer",
        instructions="Apply the supplied source",
        output_type=HypothesisGenerationOutput,
        state=state,
    )
    assert result.output.hypotheses[0].status.value == "selected"
    original, repair = client.requests
    assert original.messages[0].content in repair.messages[0].content
    assert repair.messages[0].content.count("OUTPUT_JSON_SCHEMA:\n") == 1
    assert json.loads(repair.messages[1].content)["original_input"] == original.messages[1].content
    assert '"selected"' in original.messages[0].content
    assert (
        compact_schema(HypothesisGenerationOutput, unselected_only=False)["$defs"][
            "HypothesisStatus"
        ]["enum"]
        == HypothesisGenerationOutput.model_json_schema()["$defs"]["HypothesisStatus"]["enum"]
    )


def test_compact_schema_retains_task_limits_and_free_form_params():
    schema = compact_schema(PlanGenerationOutput, unselected_only=False)
    assert schema["properties"]["tasks"]["maxItems"] == 6
    assert schema["$defs"]["PlanTask"]["properties"]["params"]["additionalProperties"] is True
