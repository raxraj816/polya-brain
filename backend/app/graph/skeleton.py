"""Chapter 8 LangGraph skeleton for the PolyaBrain engine loop."""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import Any, Final, cast

from langgraph.graph import END, StateGraph
from pydantic import JsonValue

from app.engines import EngineRoute, EngineStatus, PolyaEngine, run_engine
from app.graph.state import (
    DEFAULT_MAX_ITERATIONS,
    PolyaState,
    StateEvent,
    create_initial_state,
)
from app.models.contracts import ReasoningMode

GRAPH_VERSION: Final = "polya_graph@0.1.0"


class GraphNodeName(StrEnum):
    """Stable node names for the nine logical MVP engines."""

    PROBLEM_REPRESENTATION = "problem_representation"
    CONSTRAINT_DISCOVERY = "constraint_discovery"
    KNOWLEDGE_GAP_DETECTION = "knowledge_gap_detection"
    RESEARCH_ACQUISITION = "research_acquisition"
    EVIDENCE_EVALUATION = "evidence_evaluation"
    HYPOTHESIS_REASONING = "hypothesis_reasoning"
    EXECUTION = "execution"
    VERIFICATION = "verification"
    REFLECTION_MEMORY = "reflection_memory"


class RouterNodeName(StrEnum):
    """Internal graph nodes owned by the skeleton rather than engines."""

    ITERATION_GUARD = "iteration_guard"
    SAFE_STOP = "safe_stop"
    TERMINAL_SAFE_STOP = "terminal_safe_stop"


class PolyaGraphEngines:
    """Container for the engine implementations required by the graph skeleton."""

    def __init__(
        self,
        *,
        problem_representation: PolyaEngine,
        constraint_discovery: PolyaEngine,
        knowledge_gap_detection: PolyaEngine,
        research_acquisition: PolyaEngine,
        evidence_evaluation: PolyaEngine,
        hypothesis_reasoning: PolyaEngine,
        execution: PolyaEngine,
        verification: PolyaEngine,
        reflection_memory: PolyaEngine,
    ) -> None:
        self.problem_representation = problem_representation
        self.constraint_discovery = constraint_discovery
        self.knowledge_gap_detection = knowledge_gap_detection
        self.research_acquisition = research_acquisition
        self.evidence_evaluation = evidence_evaluation
        self.hypothesis_reasoning = hypothesis_reasoning
        self.execution = execution
        self.verification = verification
        self.reflection_memory = reflection_memory

    def by_node_name(self) -> dict[GraphNodeName, PolyaEngine]:
        """Return engines keyed by their graph node names."""
        return {
            GraphNodeName.PROBLEM_REPRESENTATION: self.problem_representation,
            GraphNodeName.CONSTRAINT_DISCOVERY: self.constraint_discovery,
            GraphNodeName.KNOWLEDGE_GAP_DETECTION: self.knowledge_gap_detection,
            GraphNodeName.RESEARCH_ACQUISITION: self.research_acquisition,
            GraphNodeName.EVIDENCE_EVALUATION: self.evidence_evaluation,
            GraphNodeName.HYPOTHESIS_REASONING: self.hypothesis_reasoning,
            GraphNodeName.EXECUTION: self.execution,
            GraphNodeName.VERIFICATION: self.verification,
            GraphNodeName.REFLECTION_MEMORY: self.reflection_memory,
        }


GRAPH_ENGINE_ORDER: Final[tuple[GraphNodeName, ...]] = (
    GraphNodeName.PROBLEM_REPRESENTATION,
    GraphNodeName.CONSTRAINT_DISCOVERY,
    GraphNodeName.KNOWLEDGE_GAP_DETECTION,
    GraphNodeName.RESEARCH_ACQUISITION,
    GraphNodeName.EVIDENCE_EVALUATION,
    GraphNodeName.HYPOTHESIS_REASONING,
    GraphNodeName.EXECUTION,
    GraphNodeName.VERIFICATION,
    GraphNodeName.REFLECTION_MEMORY,
)

NORMAL_CONTINUE_TARGETS: Final[dict[GraphNodeName, GraphNodeName]] = {
    GraphNodeName.PROBLEM_REPRESENTATION: GraphNodeName.CONSTRAINT_DISCOVERY,
    GraphNodeName.CONSTRAINT_DISCOVERY: GraphNodeName.KNOWLEDGE_GAP_DETECTION,
    GraphNodeName.KNOWLEDGE_GAP_DETECTION: GraphNodeName.HYPOTHESIS_REASONING,
    GraphNodeName.RESEARCH_ACQUISITION: GraphNodeName.EVIDENCE_EVALUATION,
    GraphNodeName.EVIDENCE_EVALUATION: GraphNodeName.HYPOTHESIS_REASONING,
    GraphNodeName.HYPOTHESIS_REASONING: GraphNodeName.EXECUTION,
    GraphNodeName.EXECUTION: GraphNodeName.VERIFICATION,
    GraphNodeName.VERIFICATION: GraphNodeName.REFLECTION_MEMORY,
}

ROUTE_TARGETS: Final[dict[EngineRoute, GraphNodeName | RouterNodeName]] = {
    EngineRoute.CLARIFY: RouterNodeName.SAFE_STOP,
    EngineRoute.RESEARCH: GraphNodeName.RESEARCH_ACQUISITION,
    EngineRoute.REFRAME: GraphNodeName.PROBLEM_REPRESENTATION,
    EngineRoute.REPLAN: GraphNodeName.HYPOTHESIS_REASONING,
    EngineRoute.RETRY_EXECUTION: GraphNodeName.EXECUTION,
    EngineRoute.FINALIZE: RouterNodeName.SAFE_STOP,
    EngineRoute.FINALIZE_INSUFFICIENT_EVIDENCE: RouterNodeName.SAFE_STOP,
}


class RouteDecision:
    """Latest engine routing decision reconstructed from trace metadata."""

    def __init__(
        self,
        *,
        status: EngineStatus,
        route: EngineRoute,
        engine_name: str,
        summary: str,
        missing_inputs: list[str],
        errors: list[str],
    ) -> None:
        self.status = status
        self.route = route
        self.engine_name = engine_name
        self.summary = summary
        self.missing_inputs = missing_inputs
        self.errors = errors


def _node_index(node: GraphNodeName) -> int:
    return GRAPH_ENGINE_ORDER.index(node)


def _engine_node(engine: PolyaEngine) -> Callable[[PolyaState], dict[str, Any]]:
    def run_node(state: PolyaState) -> dict[str, Any]:
        return run_engine(engine, state).state_delta

    return run_node


def _latest_route_decision(state: PolyaState) -> RouteDecision:
    for event in reversed(state["events"]):
        if event.event_type not in {"completed", "failed"}:
            continue
        metadata = event.metadata
        raw_status = metadata.get("status", EngineStatus.FAILED.value)
        raw_route = metadata.get("recommended_route", EngineRoute.FINALIZE.value)
        status = raw_status if isinstance(raw_status, str) else EngineStatus.FAILED.value
        route = raw_route if isinstance(raw_route, str) else EngineRoute.FINALIZE.value
        raw_missing_inputs = metadata.get("missing_inputs", [])
        raw_errors = metadata.get("errors", [])
        return RouteDecision(
            status=EngineStatus(status),
            route=EngineRoute(route),
            engine_name=event.engine_name,
            summary=event.summary,
            missing_inputs=[
                value for value in raw_missing_inputs if isinstance(value, str) and value
            ]
            if isinstance(raw_missing_inputs, list)
            else [],
            errors=[value for value in raw_errors if isinstance(value, str) and value]
            if isinstance(raw_errors, list)
            else [],
        )
    return RouteDecision(
        status=EngineStatus.FAILED,
        route=EngineRoute.FINALIZE,
        engine_name="graph_router",
        summary="No terminal engine event was available for routing.",
        missing_inputs=[],
        errors=["missing terminal engine event"],
    )


def _target_requires_iteration_guard(
    *,
    current_node: GraphNodeName,
    target_node: GraphNodeName | RouterNodeName,
) -> bool:
    if isinstance(target_node, RouterNodeName):
        return False
    return _node_index(target_node) <= _node_index(current_node)


def _route_after_engine(current_node: GraphNodeName) -> Callable[[PolyaState], str]:
    def route(state: PolyaState) -> str:
        decision = _latest_route_decision(state)
        if current_node is GraphNodeName.REFLECTION_MEMORY:
            if decision.status is EngineStatus.OK and decision.route is EngineRoute.CONTINUE:
                return END
            return RouterNodeName.TERMINAL_SAFE_STOP.value

        target: GraphNodeName | RouterNodeName
        if decision.route is EngineRoute.CONTINUE:
            target = NORMAL_CONTINUE_TARGETS.get(current_node, GraphNodeName.REFLECTION_MEMORY)
        else:
            target = ROUTE_TARGETS[decision.route]

        if isinstance(target, RouterNodeName):
            return target.value

        if _target_requires_iteration_guard(current_node=current_node, target_node=target):
            if state["iteration_count"] >= state["max_iterations"]:
                return RouterNodeName.SAFE_STOP.value
            return RouterNodeName.ITERATION_GUARD.value

        return target.value

    return route


def _next_recovery_target(state: PolyaState) -> str:
    decision = _latest_route_decision(state)
    target = ROUTE_TARGETS.get(decision.route, RouterNodeName.SAFE_STOP)
    if isinstance(target, RouterNodeName):
        return RouterNodeName.SAFE_STOP.value
    return target.value


def _iteration_guard_node(state: PolyaState) -> dict[str, Any]:
    decision = _latest_route_decision(state)
    next_target = _next_recovery_target(state)
    next_iteration_count = state["iteration_count"] + 1
    return {
        "iteration_count": next_iteration_count,
        "events": StateEvent(
            engine_name="graph_router",
            event_type="iteration_guard",
            reasoning_mode=ReasoningMode.COMPARE,
            summary=(
                "Routed recovery pass "
                f"{next_iteration_count}/{state['max_iterations']} to {next_target}."
            ),
            metadata={
                "status": decision.status.value,
                "recommended_route": decision.route.value,
                "next_node": next_target,
                "iteration_count": next_iteration_count,
                "max_iterations": state["max_iterations"],
                "graph": GRAPH_VERSION,
            },
        ),
    }


def _route_after_iteration_guard(state: PolyaState) -> str:
    latest_event = state["events"][-1] if state["events"] else None
    if latest_event is None:
        return RouterNodeName.SAFE_STOP.value
    next_node = latest_event.metadata.get("next_node", RouterNodeName.SAFE_STOP.value)
    return next_node if isinstance(next_node, str) else RouterNodeName.SAFE_STOP.value


def _safe_stop_node(state: PolyaState) -> dict[str, Any]:
    decision = _latest_route_decision(state)
    reasons = []
    if decision.missing_inputs:
        reasons.append(f"missing inputs: {', '.join(decision.missing_inputs)}")
    if decision.errors:
        reasons.append(f"errors: {'; '.join(decision.errors)}")
    if not reasons:
        reasons.append(decision.summary)
    final_answer = state["final_answer"] or (
        "PolyaBrain stopped safely before continuing because "
        f"{decision.engine_name} reported {decision.status.value} "
        f"and recommended {decision.route.value}. "
        f"Reason: {' | '.join(reasons)}"
    )
    return {
        "final_answer": final_answer,
        "events": StateEvent(
            engine_name="graph_router",
            event_type="safe_stop",
            reasoning_mode=ReasoningMode.VERIFY,
            summary="Stopped the graph safely instead of continuing with weak output.",
            metadata={
                "status": decision.status.value,
                "recommended_route": decision.route.value,
                "source_engine": decision.engine_name,
                "missing_inputs": cast(JsonValue, decision.missing_inputs),
                "errors": cast(JsonValue, decision.errors),
                "iteration_count": state["iteration_count"],
                "max_iterations": state["max_iterations"],
                "graph": GRAPH_VERSION,
            },
        ),
    }


def _terminal_safe_stop_node(state: PolyaState) -> dict[str, Any]:
    decision = _latest_route_decision(state)
    reasons = []
    if decision.missing_inputs:
        reasons.append(f"missing inputs: {', '.join(decision.missing_inputs)}")
    if decision.errors:
        reasons.append(f"errors: {'; '.join(decision.errors)}")
    if not reasons:
        reasons.append(decision.summary)
    terminal_answer = (
        "PolyaBrain stopped at the terminal stage because "
        f"{decision.engine_name} reported {decision.status.value} "
        f"and recommended {decision.route.value}. "
        f"Reason: {' | '.join(reasons)}"
    )
    final_answer = (
        f"{state['final_answer']}\n\nAdditionally, {terminal_answer}"
        if state["final_answer"]
        else terminal_answer
    )
    return {
        "final_answer": final_answer,
        "events": StateEvent(
            engine_name="graph_router",
            event_type="terminal_safe_stop",
            reasoning_mode=ReasoningMode.VERIFY,
            summary="Stopped at the terminal stage after reflection could not complete.",
            metadata={
                "status": decision.status.value,
                "recommended_route": decision.route.value,
                "source_engine": decision.engine_name,
                "missing_inputs": cast(JsonValue, decision.missing_inputs),
                "errors": cast(JsonValue, decision.errors),
                "iteration_count": state["iteration_count"],
                "max_iterations": state["max_iterations"],
                "graph": GRAPH_VERSION,
            },
        ),
    }


def build_polya_graph(engines: PolyaGraphEngines) -> Any:
    """Build the Chapter 8 compiled graph around the supplied engines."""
    graph = StateGraph(PolyaState)

    for node_name, engine in engines.by_node_name().items():
        graph.add_node(node_name.value, cast(Any, _engine_node(engine)))

    graph.add_node(RouterNodeName.ITERATION_GUARD.value, cast(Any, _iteration_guard_node))
    graph.add_node(RouterNodeName.SAFE_STOP.value, cast(Any, _safe_stop_node))
    graph.add_node(
        RouterNodeName.TERMINAL_SAFE_STOP.value,
        cast(Any, _terminal_safe_stop_node),
    )
    graph.set_entry_point(GraphNodeName.PROBLEM_REPRESENTATION.value)

    engine_nodes = [node.value for node in GraphNodeName]
    router_nodes = [node.value for node in RouterNodeName]
    possible_routes = [*engine_nodes, *router_nodes, END]

    for node_name in GraphNodeName:
        graph.add_conditional_edges(
            node_name.value,
            _route_after_engine(node_name),
            {route: route for route in possible_routes},
        )

    graph.add_conditional_edges(
        RouterNodeName.ITERATION_GUARD.value,
        _route_after_iteration_guard,
        {route: route for route in possible_routes},
    )
    graph.add_edge(RouterNodeName.SAFE_STOP.value, GraphNodeName.REFLECTION_MEMORY.value)
    graph.add_edge(RouterNodeName.TERMINAL_SAFE_STOP.value, END)

    return graph.compile()


def run_polya_graph(
    raw_input: str,
    *,
    engines: PolyaGraphEngines,
    session_id: str | None = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> PolyaState:
    """Create initial state and run it through the Chapter 8 graph skeleton."""
    app = build_polya_graph(engines)
    state = create_initial_state(
        raw_input,
        session_id=session_id,
        max_iterations=max_iterations,
    )
    result = app.invoke(state)
    return cast(PolyaState, result)
