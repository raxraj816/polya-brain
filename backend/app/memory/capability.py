"""Cognitive capability adapter for governed semantic memory."""

from __future__ import annotations

from typing import Protocol

from app.cognition.capabilities import CognitiveCapability, FunctionCapability
from app.cognition.contracts import (
    CapabilityDefinition,
    CapabilityKind,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveObservation,
    CognitiveStateUpdate,
    ObservationStatus,
)
from app.graph.state import PolyaState, StateEvent
from app.memory.contracts import SemanticMemoryResult
from app.models.contracts import EvidenceItem, ReasoningMode, RiskLevel


class SemanticMemorySearch(Protocol):
    """Read boundary used by the cognitive capability."""

    def search_semantic(
        self,
        query: str,
        *,
        limit: int = 3,
        domain: str | None = None,
        source_type: str | None = None,
        minimum_reliability: float = 0.5,
        minimum_similarity: float = 0.08,
    ) -> list[SemanticMemoryResult]:
        """Return governed semantic results."""
        ...

    def has_relevant_memory(self, query: str, domain: str | None = None) -> bool:
        """Return whether a relevance-gated semantic result exists."""
        ...


def semantic_memory_capability(repository: SemanticMemorySearch) -> CognitiveCapability:
    """Expose sourced semantic recall without treating memory as final truth."""

    def execute(action: CognitiveActionCandidate, state: PolyaState) -> CognitiveObservation:
        problem = state["structured_problem"]
        results = repository.search_semantic(
            action.target,
            limit=3,
            domain=problem.domain if problem is not None else None,
            minimum_reliability=0.5,
            minimum_similarity=0.08,
        )
        if not results:
            return CognitiveObservation(
                action_id=action.id,
                capability="memory",
                capability_version="0.1.0",
                status=ObservationStatus.INCONCLUSIVE,
                summary="No admitted, current semantic memory matched the knowledge gap.",
                failure_kind="no_relevant_memory",
            )

        evidence = [
            EvidenceItem(
                source_type=f"memory:{item.source_type}",
                source_uri=item.source_uri or f"memory://knowledge/{item.id}",
                claim=item.content,
                reliability_score=item.reliability_score,
                relevance_score=item.similarity_score,
            )
            for item in results
        ]
        trace = StateEvent(
            engine_name="memory",
            event_type="semantic_memory_retrieved",
            reasoning_mode=ReasoningMode.EXPLORE,
            summary="Retrieved current, sourced semantic memory for present-case verification.",
            metadata={
                "result_count": len(results),
                "memory_ids": [str(item.id) for item in results],
                "transfer_requires_verification": True,
            },
        )
        return CognitiveObservation(
            action_id=action.id,
            capability="memory",
            capability_version="0.1.0",
            status=ObservationStatus.SUCCEEDED,
            summary=(
                "Retrieved governed memory as candidate evidence; current-case verification "
                "is still required."
            ),
            evidence=evidence,
            proposed_update=CognitiveStateUpdate(
                resolved_gap_targets=[action.target],
                trace_events_to_add=[trace],
            ),
        )

    return FunctionCapability(
        definition=CapabilityDefinition(
            name="memory",
            version="0.1.0",
            supported_actions={
                CognitiveActionType.RECALL,
                CognitiveActionType.RETRIEVE_MEMORY,
            },
            risk_level=RiskLevel.LOW,
            approved_for_sensitive_data=True,
            timeout_seconds=5.0,
            estimated_cost=0.02,
            kind=CapabilityKind.MEMORY,
        ),
        executor=execute,
    )
