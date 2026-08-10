"""Behavioral tests for Chapter 14 constraint discovery."""

from app.constraint_discovery import ConstraintCategory, discover_constraints
from app.engines import ConstraintDiscoveryEngine, EngineStatus
from app.graph.state import create_initial_state
from app.models.contracts import StructuredProblem


def test_discovers_explicit_and_implicit_constraints_and_updates_problem() -> None:
    state = create_initial_state(
        (
            "Determine why the confidential checkout latency increased today and restore "
            "p95 below 300 ms within two hours with at least 90% confidence."
        ),
        session_id="constraint-discovery-complete",
    )
    state["structured_problem"] = StructuredProblem(
        core_question="Why did checkout latency increase and how should it be restored?",
        problem_type="planning",
        knowns=["Checkout p95 latency increased today."],
        unknowns=["the causal mechanism"],
        constraints=["Do not increase payment errors."],
        success_criteria=["Restore checkout p95 latency below 300 ms within two hours."],
        required_data_sources=["current production metrics"],
        time_window={"label": "today"},
    )

    discovered = discover_constraints(state)
    output = ConstraintDiscoveryEngine().run(state)

    categories = {item.category for item in discovered.constraints}
    assert {
        ConstraintCategory.TIME_WINDOW,
        ConstraintCategory.PRIVACY,
        ConstraintCategory.DATA_AVAILABILITY,
        ConstraintCategory.COMPLIANCE,
        ConstraintCategory.CAUSALITY,
        ConstraintCategory.CONFIDENCE_THRESHOLD,
        ConstraintCategory.RESOURCE,
        ConstraintCategory.SUCCESS,
    } <= categories
    assert not discovered.missing_constraints
    assert output.result.status is EngineStatus.OK
    updated = output.state_delta["structured_problem"]
    assert isinstance(updated, StructuredProblem)
    assert len(updated.constraints) > len(state["structured_problem"].constraints)
    assert any("correlation as causation" in item for item in updated.constraints)
    assert any(
        event.event_type == "constraint_discovered" for event in output.state_delta["events"]
    )


def test_missing_decision_boundary_routes_to_clarification() -> None:
    state = create_initial_state(
        "Choose an architecture for the product.",
        session_id="constraint-discovery-needs-input",
    )
    state["structured_problem"] = StructuredProblem(
        core_question="Which architecture should be selected?",
        problem_type="comparison",
        knowns=["Several architectures are possible."],
        success_criteria=["Select an architecture."],
    )

    output = ConstraintDiscoveryEngine().run(state)

    assert output.result.status is EngineStatus.NEEDS_INPUT
    assert output.result.missing_inputs == [
        "Which cost, time, risk, or quality boundary should determine the acceptable option?"
    ]
    assert "structured_problem" not in output.state_delta
    assert any(event.event_type == "constraint_gap" for event in output.state_delta["events"])
