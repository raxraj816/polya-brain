"""Chapter 10 deterministic graph runner tests."""

from app.graph.chapter10_stub import run_chapter10_stub_graph
from app.graph.skeleton import GraphNodeName


def test_chapter10_stub_graph_runs_all_engine_stages() -> None:
    state = run_chapter10_stub_graph(
        "Investigate why p95 latency jumped after deploy.",
        session_id="session_chapter_10",
    )

    assert state["final_answer"] is not None
    assert "not a real investigation result yet" in state["final_answer"]
    assert state["verification"] is not None
    assert state["verification"].passed is True
    assert state["reflection"] is not None

    terminal_engine_names = {
        event.engine_name for event in state["events"] if event.event_type == "completed"
    }
    for node_name in GraphNodeName:
        assert node_name.value in terminal_engine_names
