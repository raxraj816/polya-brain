"""Tests for typed deterministic scenario simulation."""

from decimal import Decimal

from app.cognition import CapabilityRegistry, CognitiveActionCandidate, CognitiveActionType
from app.cognition.kernel import CognitiveKernel
from app.execution import (
    ScenarioSimulationSpec,
    run_scenario_simulation,
    scenario_simulation_capability,
)
from app.graph.state import StateEvent, create_initial_state
from app.models.contracts import (
    KnowledgeGap,
    PlanTask,
    PriorityLevel,
    ReasoningMode,
    StructuredProblem,
)


def test_exact_scenarios_project_values_and_threshold_crossing() -> None:
    result = run_scenario_simulation(
        ScenarioSimulationSpec(
            initial_value=Decimal("100"),
            periods=2,
            scenario_rates={"base": Decimal("0.1"), "downside": Decimal("-0.5")},
            threshold=Decimal("120"),
            unit="requests_per_second",
        )
    )

    base = next(item for item in result.projections if item.scenario == "base")
    downside = next(item for item in result.projections if item.scenario == "downside")
    assert base.values == [Decimal("100"), Decimal("110.0"), Decimal("121.00")]
    assert base.threshold_crossing_period == 2
    assert downside.values == [Decimal("100"), Decimal("50.0"), Decimal("25.00")]
    assert downside.threshold_crossing_period is None


def _simulation_state(raw_input: str):
    state = create_initial_state(raw_input, max_iterations=2)
    state["structured_problem"] = StructuredProblem(
        core_question="When does projected demand cross capacity?",
        problem_type="capacity_planning",
        knowns=["Current demand and scenario rates are supplied."],
        constraints=["Use explicit scenarios only."],
        success_criteria=["Report each trajectory and threshold crossing."],
    )
    state["gaps"] = [
        KnowledgeGap(
            description="Capacity crossing under explicit growth scenarios",
            gap_type="scenario_projection",
            priority=PriorityLevel.HIGH,
            why_needed="The decision depends on future sensitivity.",
            suggested_source="simulation",
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


def test_controller_runs_explicit_simulation_spec_and_fills_gap() -> None:
    state = _simulation_state(
        'Project capacity. SIMULATION_SPEC: {"initial_value":"100","periods":3,'
        '"scenario_rates":{"base":"0.1","high":"0.2"},"threshold":"150",'
        '"unit":"requests_per_second"}'
    )
    registry = CapabilityRegistry()
    registry.register(scenario_simulation_capability())

    result = CognitiveKernel(registry).run(state, max_cycles=2)

    assert result.decisions[0].selected.action_type is CognitiveActionType.SIMULATE
    assert result.state["gaps"][0].filled
    assert result.state["evidence"][0].source_type == "deterministic_scenario_simulation"


def test_missing_spec_requests_human_input_instead_of_inventing_numbers() -> None:
    registry = CapabilityRegistry()
    registry.register(scenario_simulation_capability())

    result = CognitiveKernel(registry).run(
        _simulation_state("Project capacity under plausible scenarios."),
        max_cycles=2,
    )

    assert result.status.value == "needs_input"
    assert result.observations[0].failure_kind == "human_input_required"
    assert result.observations[0].proposed_update.questions_to_ask


def test_plan_task_simulation_adds_execution_output() -> None:
    state = create_initial_state("Execute the approved scenario task.")
    state["plan"] = [
        PlanTask(
            id="simulate-task",
            action="Project demand.",
            tool_name="simulator",
            params={
                "simulation_spec": {
                    "initial_value": "10",
                    "periods": 1,
                    "scenario_rates": {"base": "0.5"},
                    "unit": "users",
                }
            },
        )
    ]
    capability = scenario_simulation_capability()
    action = CognitiveActionCandidate(
        id="execute-simulation",
        action_type=CognitiveActionType.EXECUTE,
        target="simulate-task",
        purpose="Execute an explicit scenario.",
        expected_observation="A deterministic projection.",
        expected_usefulness=0.8,
        estimated_cost=0.06,
        capability="simulator",
        success_condition="Projection is recorded.",
        failure_condition="Specification is invalid.",
    )

    observation = capability.execute(action, state)

    assert observation.status.value == "succeeded"
    output = observation.proposed_update.execution_outputs_to_add[0]
    assert output.task_id == "simulate-task"
    assert output.output["projections"][0]["values"] == ["10", "15.0"]
