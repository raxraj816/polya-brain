"""Tests for bounded controlled numeric experiment evaluation."""

from decimal import Decimal

from app.cognition import CapabilityRegistry, CognitiveActionCandidate, CognitiveActionType
from app.cognition.kernel import CognitiveKernel
from app.execution import (
    ControlledExperimentSpec,
    EffectDirection,
    controlled_experiment_capability,
    evaluate_controlled_experiment,
)
from app.graph.state import StateEvent, create_initial_state
from app.models.contracts import KnowledgeGap, PriorityLevel, ReasoningMode, StructuredProblem


def test_controlled_experiment_computes_effect_and_interval() -> None:
    result = evaluate_controlled_experiment(
        ControlledExperimentSpec(
            metric="throughput",
            control_values=[Decimal("9"), Decimal("10"), Decimal("10"), Decimal("11")],
            treatment_values=[Decimal("19"), Decimal("20"), Decimal("20"), Decimal("21")],
            desired_direction=EffectDirection.HIGHER,
            minimum_effect=Decimal("5"),
            randomized=True,
            independent_observations=True,
        )
    )

    assert result.control_mean == Decimal("10")
    assert result.treatment_mean == Decimal("20")
    assert result.absolute_effect == Decimal("10")
    assert result.relative_effect_percent == Decimal("100")
    assert result.desired_effect_observed
    assert result.minimum_effect_met
    assert result.interval_excludes_zero_in_desired_direction


def _experiment_state(raw_input: str):
    state = create_initial_state(raw_input, max_iterations=2)
    state["structured_problem"] = StructuredProblem(
        core_question="Did the treatment improve throughput?",
        problem_type="scientific_reasoning",
        constraints=["Use randomized independent observations."],
        success_criteria=["Estimate effect and uncertainty."],
    )
    state["gaps"] = [
        KnowledgeGap(
            description="Controlled treatment effect on throughput",
            gap_type="controlled_experiment",
            priority=PriorityLevel.HIGH,
            why_needed="Competing mechanisms require an observed intervention.",
            suggested_source="controlled experiment",
        )
    ]
    state["events"] = [
        StateEvent(
            engine_name="constraint_discovery",
            event_type="completed",
            reasoning_mode=ReasoningMode.COMPARE,
            summary="Constraints completed.",
            metadata={"status": "ok"},
        ),
        StateEvent(
            engine_name="gap_detector",
            event_type="gap_detection_completed",
            reasoning_mode=ReasoningMode.EXPLORE,
            summary="Gaps completed.",
            metadata={"status": "ok"},
        ),
    ]
    return state


def test_controller_evaluates_explicit_controlled_observations() -> None:
    state = _experiment_state(
        'EXPERIMENT_SPEC: {"metric":"throughput","control_values":[9,10,11],'
        '"treatment_values":[19,20,21],"desired_direction":"higher",'
        '"minimum_effect":5,"randomized":true,"independent_observations":true}'
    )
    registry = CapabilityRegistry()
    registry.register(controlled_experiment_capability())

    result = CognitiveKernel(registry).run(state, max_cycles=2)

    assert result.decisions[0].selected.action_type is CognitiveActionType.EXPERIMENT
    assert result.state["gaps"][0].filled
    assert result.state["evidence"][0].source_type == "controlled_experiment_evaluation"


def test_missing_observations_pause_and_invalid_design_fails_closed() -> None:
    registry = CapabilityRegistry()
    capability = controlled_experiment_capability()
    registry.register(capability)
    missing = CognitiveKernel(registry).run(
        _experiment_state("Test whether the treatment helps."), max_cycles=2
    )
    invalid_state = _experiment_state(
        'EXPERIMENT_SPEC: {"metric":"throughput","control_values":[1,2],'
        '"treatment_values":[2,3],"desired_direction":"higher",'
        '"randomized":false,"independent_observations":true}'
    )
    action = CognitiveActionCandidate(
        id="invalid-experiment",
        action_type=CognitiveActionType.EXPERIMENT,
        target="Controlled treatment effect on throughput",
        purpose="Evaluate the comparison.",
        expected_observation="A controlled effect estimate.",
        expected_usefulness=0.9,
        estimated_cost=0.07,
        capability="experiment",
        success_condition="Effect is estimated.",
        failure_condition="Design is invalid.",
    )
    invalid = capability.execute(action, invalid_state)

    assert missing.status.value == "needs_input"
    assert missing.observations[0].failure_kind == "human_input_required"
    assert invalid.status.value == "failed"
    assert invalid.failure_kind == "experiment_spec_invalid"
