"""Unit tests for deterministic and governed memory behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.cognition.contracts import CognitiveActionCandidate, CognitiveActionType
from app.graph.state import create_initial_state
from app.memory import HashingEmbeddingProvider, SemanticMemoryResult, semantic_memory_capability
from app.models.contracts import RiskLevel, StructuredProblem


def test_hashing_embeddings_are_deterministic_normalized_and_content_sensitive() -> None:
    provider = HashingEmbeddingProvider()

    first = provider.embed("inspect database query latency")
    second = provider.embed("inspect database query latency")
    different = provider.embed("compare treatment conversion rate")

    assert first == second
    assert first != different
    assert len(first) == 1536
    assert sum(value * value for value in first) == pytest.approx(1.0)


def test_hashing_embeddings_reject_content_without_tokens() -> None:
    with pytest.raises(ValueError, match="alphanumeric token"):
        HashingEmbeddingProvider().embed("--- ...")


class FakeSemanticMemory:
    def __init__(self, results: list[SemanticMemoryResult]) -> None:
        self.results = results

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
        del query, limit, domain, source_type, minimum_reliability, minimum_similarity
        return self.results


def memory_action() -> CognitiveActionCandidate:
    return CognitiveActionCandidate(
        id="memory-action",
        action_type=CognitiveActionType.RETRIEVE_MEMORY,
        target="How should query latency be investigated?",
        purpose="Recall relevant sourced knowledge.",
        expected_observation="Relevant current memory or an explicit no-match.",
        expected_usefulness=0.8,
        estimated_cost=0.01,
        risk_level=RiskLevel.LOW,
        capability="memory",
        success_condition="Current sourced knowledge is retrieved.",
        failure_condition="No relevant memory is available.",
    )


def test_memory_capability_preserves_source_and_requires_current_case_verification() -> None:
    result = SemanticMemoryResult(
        id=uuid4(),
        content="Inspect the query path before adding a cache.",
        source_type="official_documentation",
        source_uri="https://example.com/database/diagnostics",
        domain="software_debugging",
        reliability_score=0.95,
        similarity_score=0.84,
        valid_until=datetime(2027, 1, 1, tzinfo=UTC),
        tags=["database"],
        admission_status="evaluated",
    )
    state = create_initial_state("Investigate database latency.")
    state["structured_problem"] = StructuredProblem(
        core_question="Why did database latency increase?",
        problem_type="diagnosis",
        domain="software_debugging",
    )

    observation = semantic_memory_capability(FakeSemanticMemory([result])).execute(
        memory_action(), state
    )

    assert observation.status.value == "succeeded"
    assert observation.evidence[0].source_uri == result.source_uri
    assert observation.evidence[0].claim == result.content
    assert observation.proposed_update.resolved_gap_targets == [memory_action().target]
    assert (
        observation.proposed_update.trace_events_to_add[0].metadata[
            "transfer_requires_verification"
        ]
        is True
    )


def test_memory_capability_returns_explicit_no_match_without_fabricating_evidence() -> None:
    state = create_initial_state("Solve an unfamiliar problem.")

    observation = semantic_memory_capability(FakeSemanticMemory([])).execute(memory_action(), state)

    assert observation.status.value == "inconclusive"
    assert observation.failure_kind == "no_relevant_memory"
    assert observation.evidence == []
