"""LangGraph state primitives for the PolyaBrain loop."""

from app.graph.state import (
    DEFAULT_MAX_ITERATIONS,
    ExecutionOutput,
    PolyaState,
    StateEvent,
    append_state_events,
    create_initial_state,
)

_SKELETON_EXPORTS = {
    "GRAPH_VERSION",
    "GraphNodeName",
    "PolyaGraphEngines",
    "RouterNodeName",
    "build_polya_graph",
    "run_polya_graph",
}


def __getattr__(name: str) -> object:
    """Lazily expose graph skeleton exports without circular engine imports."""
    if name in _SKELETON_EXPORTS:
        from app.graph import skeleton

        return getattr(skeleton, name)
    raise AttributeError(f"module 'app.graph' has no attribute {name!r}")


__all__ = [
    "DEFAULT_MAX_ITERATIONS",
    "ExecutionOutput",
    "GRAPH_VERSION",
    "GraphNodeName",
    "PolyaState",
    "PolyaGraphEngines",
    "RouterNodeName",
    "StateEvent",
    "append_state_events",
    "build_polya_graph",
    "create_initial_state",
    "run_polya_graph",
]
