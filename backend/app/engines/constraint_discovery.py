"""Chapter 14 Constraint Discovery Engine."""

from __future__ import annotations

from typing import Final

from app.constraint_discovery import discover_constraints
from app.engines.contracts import (
    EngineResult,
    EngineRoute,
    EngineRunOutput,
    EngineStatus,
    EngineVersion,
)
from app.graph.state import PolyaState, StateEvent
from app.graph.version import GRAPH_VERSION
from app.models.contracts import ReasoningMode

CONSTRAINT_DISCOVERY_ENGINE_VERSION: Final = "constraint_discovery@1.0.0"


class ConstraintDiscoveryEngine:
    """Identify requirements that determine whether a solution is valid."""

    name = "constraint_discovery"
    reasoning_mode = ReasoningMode.COMPARE
    version = EngineVersion(
        engine=CONSTRAINT_DISCOVERY_ENGINE_VERSION,
        verifier="constraint_discovery_contract@1.0.0",
        graph=GRAPH_VERSION,
    )

    def run(self, state: PolyaState) -> EngineRunOutput:
        result = discover_constraints(state)
        events = [
            StateEvent(
                engine_name=self.name,
                event_type="constraint_discovered",
                reasoning_mode=ReasoningMode.COMPARE,
                summary=f"Discovered {item.category.value} constraint.",
                metadata=item.model_dump(mode="json"),
            )
            for item in result.constraints
        ]
        if result.missing_constraints:
            events.append(
                StateEvent(
                    engine_name=self.name,
                    event_type="constraint_gap",
                    reasoning_mode=ReasoningMode.EXPLORE,
                    summary="A user-owned constraint is required before proceeding.",
                    metadata={
                        "missing_constraints": list(result.missing_constraints),
                        "clarifying_questions": list(result.clarifying_questions),
                    },
                )
            )
            return EngineRunOutput(
                state_delta={"events": events},
                result=EngineResult(
                    status=EngineStatus.NEEDS_INPUT,
                    confidence=0.8,
                    missing_inputs=list(result.clarifying_questions),
                    recommended_route=EngineRoute.CLARIFY,
                    versions=self.version,
                    summary="Constraint discovery needs user clarification.",
                ),
            )

        problem = state["structured_problem"]
        if problem is None:
            raise ValueError("constraint discovery requires structured_problem")
        discovered_statements = [item.statement for item in result.constraints]
        updated_problem = problem.model_copy(
            update={
                "constraints": list(dict.fromkeys([*problem.constraints, *discovered_statements]))
            }
        )
        return EngineRunOutput(
            state_delta={"structured_problem": updated_problem, "events": events},
            result=EngineResult(
                status=EngineStatus.OK,
                confidence=0.9,
                recommended_route=EngineRoute.CONTINUE,
                versions=self.version,
                summary="Discovered and validated explicit and implicit constraints.",
            ),
        )
