"""Failed checks trigger bounded research, reanalysis and independent verification."""

import json

import pytest
from pydantic import ValidationError
from test_knowledge_acquisition import FakeSearchProvider
from test_on_demand_cognition import _conclusion_json, _deliberation_json, _ready_state, _response

from app.acquisition import evidence_evaluator_capability, web_search_capability
from app.cognition import CognitiveKernel, CognitiveModelGateway, CognitiveResourceBudget
from app.cognition.capabilities import CapabilityRegistry
from app.cognition.contracts import CognitiveRunStatus
from app.cognition.model_contracts import ConclusionCheckOutput, DeliberationCapabilityOutput
from app.cognition.on_demand_capabilities import on_demand_cognitive_capabilities
from app.cognition.verification_research import ANALYSIS_EVENT, RESEARCH_EVENT, research_update
from app.llm import FakeLLMClient
from app.models.contracts import VerificationReport


def failed_output():
    return ConclusionCheckOutput(
        report=VerificationReport(
            passed=False,
            checks_run=["Checked whether the documented default is supported."],
            failed_checks=["The current public specification's default is missing."],
        ),
        public_research_needs=[
            {
                "failed_check_index": 0,
                "question": "What public measurement documents the current default behavior in the specification?",
            }
        ],
    )


def failed_state():
    state = _ready_state()
    state["structured_problem"] = state["structured_problem"].model_copy(
        update={
            "constraints": ["Use authoritative public sources."],
            "core_question": "What is the current documented default behavior?",
            "success_criteria": ["State the documented default with public source evidence."],
        }
    )
    state["raw_input"] = "What is the current documented default behavior?"
    previous = DeliberationCapabilityOutput.model_validate_json(_deliberation_json())
    state["hypotheses"] = previous.hypotheses
    state["plan"] = previous.tasks
    state["execution_outputs"] = previous.execution_outputs
    state["evidence"] = []
    state["verification"] = failed_output().report
    gaps, events = research_update(state, failed_output(), action_id="first-check")
    state["gaps"] = gaps
    state["events"].extend(events)
    return state


def setup_registry(responses):
    provider = FakeSearchProvider()
    client = FakeLLMClient([_response(text) for text in responses])
    registry = CapabilityRegistry()
    for capability in on_demand_cognitive_capabilities(CognitiveModelGateway(client, "fake")):
        registry.register(capability)
    registry.register(web_search_capability(provider))
    registry.register(evidence_evaluator_capability())
    return registry, client, provider


def test_failed_verification_researches_then_reanalyzes_and_verifies():
    final = json.loads(_conclusion_json())
    final["final_answer"] = "The public specification documents the behavior as enabled by default."
    registry, client, provider = setup_registry(
        [failed_output().model_dump_json(), _deliberation_json(), json.dumps(final)]
    )
    state = failed_state()
    state["verification"] = None
    state["gaps"] = []
    state["events"] = [event for event in state["events"] if event.event_type != RESEARCH_EVENT]
    result = CognitiveKernel(registry).run(
        state,
        max_cycles=8,
        budget=CognitiveResourceBudget(
            max_model_calls=8,
            max_external_calls=1,
            max_output_tokens=15000,
        ),
    )
    assert result.status is CognitiveRunStatus.COMPLETED
    assert [decision.selected.capability for decision in result.decisions] == [
        "conclusion_checker",
        "web_search",
        "evidence_evaluator",
        "deliberator",
        "conclusion_checker",
        "cognitive_controller",
    ]
    assert len(provider.requests) == 1
    assert len(client.requests) == 3
    assert len(result.state["evidence"]) == 2
    assert len({task.id for task in result.state["plan"]}) == 2
    assert state["plan"][0] == result.state["plan"][0]
    assert result.state["plan"][1].id == result.state["execution_outputs"][1].task_id
    events = result.state["events"]
    history = next(event for event in events if event.event_type == "verification_invalidated")
    assert history.metadata["report"]["failed_checks"] == failed_output().report.failed_checks
    assert sum(event.event_type == RESEARCH_EVENT for event in events) == 1
    assert sum(event.event_type == ANALYSIS_EVENT for event in events) == 1
    assert result.state["verification"].passed
    assert (
        result.state["structured_problem"].success_criteria
        == state["structured_problem"].success_criteria
    )


@pytest.mark.parametrize("gate", ["privacy", "budget", "offline"])
def test_research_cannot_bypass_existing_external_gates(gate):
    registry, client, provider = setup_registry([])
    state = failed_state()
    budget = CognitiveResourceBudget(max_external_calls=0 if gate == "budget" else 2)
    if gate == "privacy":
        state["structured_problem"].constraints.append(
            "Private confidential inputs must remain local."
        )
    if gate == "offline":
        registry = CapabilityRegistry()
    result = CognitiveKernel(registry).run(state, max_cycles=2, budget=budget)
    assert not provider.requests
    assert not client.requests
    assert result.status is not CognitiveRunStatus.COMPLETED
    assert result.state["verification"].failed_checks == failed_output().report.failed_checks
    assert not result.state["gaps"][0].filled


def test_no_second_research_round_even_if_checker_repeats_request():
    state = failed_state()
    assert research_update(state, failed_output(), action_id="second-check") == ([], [])


def test_private_or_execution_failure_without_public_need_does_not_research():
    output = ConclusionCheckOutput(
        report=VerificationReport(
            passed=False,
            checks_run=["Require actual test output."],
            failed_checks=["Private deployment logs and observed test execution are missing."],
        )
    )
    assert research_update(_ready_state(), output, action_id="private-check") == ([], [])


@pytest.mark.parametrize("index", [-1, 1, 32])
def test_research_must_bind_to_an_existing_failed_check(index):
    data = failed_output().model_dump()
    data["public_research_needs"][0]["failed_check_index"] = index
    with pytest.raises(ValidationError):
        ConclusionCheckOutput.model_validate(data)


def test_passing_checker_cannot_request_blocking_research():
    data = json.loads(_conclusion_json())
    data["public_research_needs"] = failed_output().model_dump()["public_research_needs"]
    with pytest.raises(ValidationError):
        ConclusionCheckOutput.model_validate(data)


def test_second_failure_cannot_finalize_or_research_again():
    registry, _, provider = setup_registry(
        [_deliberation_json(), failed_output().model_dump_json()]
    )
    result = CognitiveKernel(registry).run(
        failed_state(),
        max_cycles=4,
        budget=CognitiveResourceBudget(
            max_model_calls=8, max_external_calls=2, max_output_tokens=15000
        ),
    )
    assert len(provider.requests) == 1
    assert result.state["verification"] is not None
    assert not result.state["verification"].passed
    assert result.state["final_answer"] is None
    assert all(gap.filled for gap in result.state["gaps"])
    assert sum(event.event_type == RESEARCH_EVENT for event in result.state["events"]) == 1


@pytest.mark.parametrize("cycle_limit,completed", [(None, True), (12, False)])
def test_persisted_runtime_has_room_for_final_check_and_honors_explicit_cycle_limit(
    cycle_limit, completed
):
    from app.cognition.capabilities import FunctionCapability
    from app.cognition.contracts import (
        CapabilityDefinition,
        CognitiveActionType,
        CognitiveObservation,
        CognitiveStateUpdate,
        ObservationStatus,
    )
    from app.cognition.runtime import CognitiveRuntime
    from app.cognition.session_runner import CognitiveSessionRunner
    from app.graph.state import ExecutionOutput
    from app.models.contracts import PlanTask

    state = failed_state()
    state["gaps"] = []
    state["events"] = [event for event in state["events"] if event.event_type != RESEARCH_EVENT]
    state["verification"] = None
    state["execution_outputs"] = []
    state["plan"] = [
        PlanTask(id=f"check-{i}", action="Check fixture", tool_name="fixture") for i in range(13)
    ]
    registry, client, _ = setup_registry([_conclusion_json()])

    def execute(action, current):
        return CognitiveObservation(
            action_id=action.id,
            capability="fixture",
            capability_version="fixture@1",
            status=ObservationStatus.SUCCEEDED,
            summary="Recorded deterministic fixture check.",
            proposed_update=CognitiveStateUpdate(
                execution_outputs_to_add=[
                    ExecutionOutput(
                        task_id=action.target,
                        summary="Fixture check completed.",
                        output={"passed": True},
                    )
                ]
            ),
        )

    registry.register(
        FunctionCapability(
            CapabilityDefinition(
                name="fixture", version="fixture@1", supported_actions={CognitiveActionType.EXECUTE}
            ),
            execute,
        )
    )
    kwargs = {} if cycle_limit is None else {"max_cycles": cycle_limit}
    result = CognitiveSessionRunner(CognitiveRuntime(registry), initial_state=state, **kwargs)(
        state["raw_input"],
        session_id=state["session_id"],
    )
    assert bool(result.state["verification"] and result.state["verification"].passed) is completed
    assert len(result.state["execution_outputs"]) == (13 if completed else 12)
    assert len(client.requests) == (1 if completed else 0)
