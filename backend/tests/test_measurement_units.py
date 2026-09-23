"""Source uncertainty units must survive synthesis without a false verification pass."""

import json

import pytest
from test_on_demand_cognition import _conclusion_json, _deliberation_json, _ready_state, _response

from app.cognition import CognitiveKernel, CognitiveModelGateway, CognitiveResourceBudget
from app.cognition.capabilities import CapabilityRegistry
from app.cognition.measurement_units import uncertainty_failures
from app.cognition.model_contracts import DeliberationCapabilityOutput
from app.cognition.on_demand_capabilities import conclusion_checker_capability
from app.llm import FakeLLMClient
from app.models.contracts import EvidenceItem


def measurement_state(excerpt="The change was –33.24 min ± 1.4 s."):
    state = _ready_state()
    state["evidence"] = [
        EvidenceItem(
            source_type="evaluated_web_source",
            source_uri="https://example.org/measurement",
            claim="The change was 33.24 ± 1.4 minutes.",
            raw_excerpt=excerpt,
        )
    ]
    return state


@pytest.mark.parametrize(
    "answer",
    [
        "The change was −33.24 ± 1.4 minutes.",
        "The period changed by 33.24 minutes plus or minus 1.4 min.",
        "The change was 1994.4 seconds +/- 84 seconds.",
    ],
)
def test_incorrect_uncertainty_unit_is_rejected_even_if_extracted_claim_repeats_it(answer):
    assert uncertainty_failures(measurement_state(), answer)


@pytest.mark.parametrize(
    "answer",
    [
        "The change was −33.24 min ± 1.4 s.",
        "The change was 1994.4 ± 1.4 seconds.",
        "The change was 33.24 minutes plus or minus 1.4 seconds.",
    ],
)
def test_equivalent_mixed_units_and_conversions_pass_necessary_check(answer):
    assert not uncertainty_failures(measurement_state(), answer)


def test_unmatched_or_unparsed_measurements_are_outside_narrow_guard():
    assert not uncertainty_failures(measurement_state(), "Another measurement was 20 ± 2 minutes.")
    assert not uncertainty_failures(measurement_state(), "The mass was 33.24 ± 1.4 kg.")
    assert not uncertainty_failures(
        measurement_state("No uncertainty is supplied."), "33.24 ± 1.4 min"
    )


def test_model_pass_with_wrong_units_is_not_finalized():
    state = measurement_state()
    analysis = DeliberationCapabilityOutput.model_validate_json(_deliberation_json())
    state["hypotheses"] = analysis.hypotheses
    state["plan"] = analysis.tasks
    state["execution_outputs"] = analysis.execution_outputs
    output = json.loads(_conclusion_json())
    output["final_answer"] = "The technical report gives a period change of −33.24 ± 1.4 minutes."
    registry = CapabilityRegistry()
    registry.register(
        conclusion_checker_capability(
            CognitiveModelGateway(
                FakeLLMClient([_response(json.dumps(output))]),
                "fake",
            )
        )
    )
    result = CognitiveKernel(registry).run(
        state, max_cycles=1, budget=CognitiveResourceBudget(max_model_calls=4)
    )
    assert not result.state["verification"].passed
    assert "Time uncertainty mismatch" in result.state["verification"].failed_checks[0]
    assert result.state["final_answer"] is None
    assert result.state["reflection"] is None
    event = next(
        e for e in result.state["events"] if e.event_type == "time_uncertainty_consistency_checked"
    )
    assert event.metadata["rejected_answer"] == output["final_answer"]
