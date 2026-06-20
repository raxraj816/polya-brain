"""Chapter 6 LangGraph state tests."""

import pytest
from langgraph.graph import END, StateGraph
from pydantic import ValidationError

from app.graph.state import (
    DEFAULT_MAX_ITERATIONS,
    ExecutionOutput,
    PolyaState,
    StateEvent,
    append_state_events,
    create_initial_state,
)
from app.models.contracts import KnowledgeGap, ReasoningMode


def valid_state_event(**overrides: object) -> StateEvent:
    payload: dict[str, object] = {
        "engine_name": "state_initializer",
        "event_type": "created",
        "reasoning_mode": ReasoningMode.EXPLORE,
        "summary": "Initial state created from raw input.",
        "metadata": {"chapter": 6},
    }
    payload.update(overrides)
    return StateEvent.model_validate(payload)


def valid_execution_output(**overrides: object) -> ExecutionOutput:
    payload: dict[str, object] = {
        "task_id": "task_query_diff",
        "summary": "Compared query metrics.",
        "output": {"rows_checked": 12},
        "artifact_ids": ["artifact_query_report"],
        "error": None,
    }
    payload.update(overrides)
    return ExecutionOutput.model_validate(payload)


def test_create_initial_state_from_raw_input() -> None:
    state = create_initial_state("  Investigate why p95 latency jumped.  ")

    assert state["session_id"]
    assert state["raw_input"] == "Investigate why p95 latency jumped."
    assert state["structured_problem"] is None
    assert state["gaps"] == []
    assert state["evidence"] == []
    assert state["hypotheses"] == []
    assert state["plan"] == []
    assert state["execution_outputs"] == []
    assert state["verification"] is None
    assert state["reflection"] is None
    assert state["iteration_count"] == 0
    assert state["max_iterations"] == DEFAULT_MAX_ITERATIONS
    assert state["final_answer"] is None
    assert state["events"] == []


def test_create_initial_state_preserves_overrides() -> None:
    state = create_initial_state(
        "Diagnose duplicate billing webhooks.",
        session_id="session_123",
        max_iterations=5,
    )

    assert state["session_id"] == "session_123"
    assert state["max_iterations"] == 5


def test_create_initial_state_rejects_blank_raw_input() -> None:
    with pytest.raises(ValueError, match="raw_input must not be blank"):
        create_initial_state("   ")


def test_create_initial_state_rejects_invalid_max_iterations() -> None:
    with pytest.raises(ValueError, match="max_iterations must be at least 1"):
        create_initial_state("Investigate deploy failure.", max_iterations=0)


def test_create_initial_state_rejects_blank_session_id() -> None:
    with pytest.raises(ValueError, match="session_id must not be blank"):
        create_initial_state("Investigate deploy failure.", session_id="  ")


def test_create_initial_state_uses_fresh_mutable_lists() -> None:
    first_state = create_initial_state("Investigate cache behavior.")
    second_state = create_initial_state("Investigate memory growth.")
    event = valid_state_event()

    first_state["events"].append(event)
    first_state["gaps"].append(
        KnowledgeGap.model_validate(
            {
                "description": "Need cache hit rate.",
                "gap_type": "missing_metric",
                "why_needed": "Cache advice requires measured hit rate.",
            }
        )
    )

    assert second_state["events"] == []
    assert second_state["gaps"] == []


def test_append_state_events_appends_without_mutating_existing_list() -> None:
    first_event = valid_state_event(summary="First event.")
    second_event = valid_state_event(summary="Second event.")
    existing = [first_event]

    updated = append_state_events(existing, second_event)

    assert updated == [first_event, second_event]
    assert existing == [first_event]
    assert updated is not existing


def test_append_state_events_handles_none_single_event_and_list_updates() -> None:
    first_event = valid_state_event(summary="First event.")
    second_event = valid_state_event(summary="Second event.")

    assert append_state_events(None, None) == []
    assert append_state_events(None, first_event) == [first_event]
    assert append_state_events([first_event], [second_event]) == [first_event, second_event]


def test_append_state_events_validates_dict_updates() -> None:
    event_payload = {
        "engine_name": "representation",
        "event_type": "completed",
        "reasoning_mode": "explore",
        "summary": "Structured the raw input.",
        "metadata": {"confidence": 0.8, "tags": ["chapter_6"]},
    }

    updated = append_state_events(None, event_payload)

    assert updated == [StateEvent.model_validate(event_payload)]


def test_append_state_events_rejects_malformed_updates() -> None:
    with pytest.raises(ValidationError):
        append_state_events(
            None,
            {
                "engine_name": "representation",
                "event_type": "completed",
                "reasoning_mode": "explore",
                "summary": "",
            },
        )


def test_state_event_rejects_malformed_payload() -> None:
    with pytest.raises(ValidationError):
        valid_state_event(summary="")

    with pytest.raises(ValidationError):
        valid_state_event(reasoning_mode="unsupported")

    with pytest.raises(ValidationError):
        valid_state_event(metadata={"not_json": object()})


def test_execution_output_rejects_malformed_payload() -> None:
    with pytest.raises(ValidationError):
        valid_execution_output(task_id="")

    with pytest.raises(ValidationError):
        valid_execution_output(artifact_ids=[""])

    with pytest.raises(ValidationError):
        valid_execution_output(output=object())


def test_langgraph_accepts_polya_state_schema() -> None:
    graph = StateGraph(PolyaState)

    assert graph is not None


def test_langgraph_reducer_accumulates_state_events() -> None:
    graph = StateGraph(PolyaState)

    def first_node(state: PolyaState) -> dict[str, object]:
        return {
            "events": {
                "engine_name": "representation",
                "event_type": "started",
                "reasoning_mode": "explore",
                "summary": f"Started representation for {state['session_id']}.",
            }
        }

    def second_node(state: PolyaState) -> dict[str, object]:
        return {
            "events": [
                {
                    "engine_name": "representation",
                    "event_type": "completed",
                    "reasoning_mode": "explore",
                    "summary": "Completed representation.",
                }
            ]
        }

    graph.add_node("first", first_node)
    graph.add_node("second", second_node)
    graph.set_entry_point("first")
    graph.add_edge("first", "second")
    graph.add_edge("second", END)

    app = graph.compile()
    result = app.invoke(create_initial_state("Investigate graph reducer behavior."))

    assert [event.event_type for event in result["events"]] == ["started", "completed"]
    assert all(isinstance(event, StateEvent) for event in result["events"])
