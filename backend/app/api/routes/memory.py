"""Read-only inspection and retrieval routes for governed memory."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.memory import (
    EpisodicMemoryResult,
    MemoryContext,
    ProceduralMemoryResult,
    SemanticMemoryResult,
    SQLAlchemyMemoryRepository,
)

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])
DB_SESSION_DEPENDENCY = Depends(get_db_session)


@router.get(
    "/semantic",
    response_model=list[SemanticMemoryResult],
    summary="Search admitted semantic memory",
)
def search_semantic_memory(
    query: str = Query(min_length=1, max_length=2_000),
    limit: int = Query(default=3, ge=1, le=20),
    domain: str | None = Query(default=None, max_length=128),
    source_type: str | None = Query(default=None, max_length=128),
    minimum_reliability: float = Query(default=0.5, ge=0.0, le=1.0),
    minimum_similarity: float = Query(default=0.08, ge=0.0, le=1.0),
    db_session: Session = DB_SESSION_DEPENDENCY,
) -> list[SemanticMemoryResult]:
    """Search by meaning while enforcing provenance, freshness, and quality gates."""
    return SQLAlchemyMemoryRepository(db_session).search_semantic(
        query,
        limit=limit,
        domain=domain,
        source_type=source_type,
        minimum_reliability=minimum_reliability,
        minimum_similarity=minimum_similarity,
    )


@router.get(
    "/episodes",
    response_model=list[EpisodicMemoryResult],
    summary="Search verified prior problem-solving episodes",
)
def search_episodic_memory(
    query: str = Query(min_length=1, max_length=2_000),
    limit: int = Query(default=3, ge=1, le=20),
    problem_type: str | None = Query(default=None, max_length=128),
    domain: str | None = Query(default=None, max_length=128),
    minimum_similarity: float = Query(default=0.08, ge=0.0, le=1.0),
    db_session: Session = DB_SESSION_DEPENDENCY,
) -> list[EpisodicMemoryResult]:
    """Find similar verified cases without claiming their outcomes transfer automatically."""
    return SQLAlchemyMemoryRepository(db_session).search_episodes(
        query,
        limit=limit,
        problem_type=problem_type,
        domain=domain,
        minimum_similarity=minimum_similarity,
    )


@router.get(
    "/context",
    response_model=MemoryContext,
    summary="Build bounded memory context for a problem",
)
def get_memory_context(
    query: str = Query(min_length=1, max_length=2_000),
    problem_type: str | None = Query(default=None, max_length=128),
    domain: str | None = Query(default=None, max_length=128),
    db_session: Session = DB_SESSION_DEPENDENCY,
) -> MemoryContext:
    """Return no more than three facts and three verified episodes plus limitations."""
    return SQLAlchemyMemoryRepository(db_session).context_for_problem(
        query,
        problem_type=problem_type,
        domain=domain,
    )


@router.get(
    "/procedures",
    response_model=list[ProceduralMemoryResult],
    summary="Inspect procedural memory",
)
def list_procedural_memory(
    problem_type: str | None = Query(default=None, max_length=128),
    gap_type: str | None = Query(default=None, max_length=128),
    verified_only: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=100),
    db_session: Session = DB_SESSION_DEPENDENCY,
) -> list[ProceduralMemoryResult]:
    """List learned strategies and clearly distinguish unverified seeded playbooks."""
    return SQLAlchemyMemoryRepository(db_session).list_strategies(
        problem_type=problem_type,
        gap_type=gap_type,
        verified_only=verified_only,
        limit=limit,
    )
