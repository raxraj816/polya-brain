"""Seed the local Chapter 4 database with one representative investigation run."""

from __future__ import annotations

from hashlib import sha256
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import (
    Artifact,
    EvidenceItem,
    Hypothesis,
    KnowledgeChunk,
    KnowledgeGap,
    PlanTask,
    ProblemSession,
    ReasoningEvent,
    StructuredProblem,
    VerificationReport,
)
from app.db.session import create_database_engine, create_session_factory

SEED_RAW_INPUT = (
    "Chapter 4 seed: API p95 latency jumped after deploy; decide whether to add Redis "
    "or inspect the query path first."
)
SEED_EMBEDDING_DIMENSIONS = 1536


def _content_hash(content: str) -> str:
    return sha256(content.encode("utf-8")).hexdigest()


def seed_database(session: Session) -> UUID:
    """Insert the local MVP investigation seed if it does not already exist."""
    existing_id = session.scalar(
        select(ProblemSession.id).where(ProblemSession.raw_input == SEED_RAW_INPUT)
    )
    if existing_id is not None:
        return existing_id

    problem_session = ProblemSession(
        raw_input=SEED_RAW_INPUT,
        domain="software_debugging",
        mode="investigate",
        status="verified",
        final_answer="Inspect the query path before adding Redis.",
        confidence=0.74,
        verification_status="passed",
    )
    session.add(problem_session)
    session.flush()

    structured_problem = StructuredProblem(
        session_id=problem_session.id,
        core_question="What changed in the request path after deploy?",
        problem_type="technical_investigation",
        domain="software_debugging",
        knowns=["p95 latency increased after deploy"],
        unknowns=["query plan changes", "cache hit rate", "deployment diff"],
        constraints=["avoid unnecessary infrastructure", "preserve audit trace"],
        success_criteria=["identify likely cause", "recommend next check"],
        affected_entities=["api", "database", "cache"],
        time_window={"relative": "after deploy"},
        required_data_sources=["deploy diff", "database query metrics", "application traces"],
    )
    session.add(structured_problem)

    knowledge_gap = KnowledgeGap(
        session_id=problem_session.id,
        description="Need query-level evidence before choosing a caching solution.",
        gap_type="missing_metric",
        priority="high",
        why_needed="A cache recommendation is premature without knowing whether the query path regressed.",
        suggested_source="database slow query log",
        filled=True,
        evidence_ids=[],
    )
    session.add(knowledge_gap)

    evidence_item = EvidenceItem(
        session_id=problem_session.id,
        source_type="local_seed",
        source_uri="seed://chapter-4/evidence/query-path",
        claim="The investigation should inspect query path evidence before adding Redis.",
        raw_excerpt="Stored seed evidence for Chapter 4 database smoke checks.",
        reliability_score=0.8,
        relevance_score=0.9,
        supports_hypothesis_ids=[],
        contradicts_hypothesis_ids=[],
    )
    session.add(evidence_item)
    session.flush()

    hypothesis = Hypothesis(
        session_id=problem_session.id,
        statement="The deploy changed the query path, making database work more likely than cache absence.",
        mechanism="A code or query-plan change can increase p95 latency immediately after deploy.",
        origin="direct_reasoning",
        analogical_source_ids=[],
        expected_signals=["slow query log regression", "changed query count", "new query plan"],
        evidence_for=[str(evidence_item.id)],
        evidence_against=[],
        verification_checks=["inspect deploy diff", "compare slow query logs"],
        falsification_criteria=["no query path change", "cache hit rate collapse explains latency"],
        confidence=0.7,
        selection_rationale="Query-path inspection has lower cost and higher falsifiability than adding Redis.",
        status="selected",
    )
    session.add(hypothesis)
    session.flush()
    evidence_item.supports_hypothesis_ids = [str(hypothesis.id)]
    knowledge_gap.evidence_ids = [str(evidence_item.id)]

    plan_task = PlanTask(
        session_id=problem_session.id,
        action="Inspect slow query logs and deploy diff before proposing Redis.",
        tool_name="database_metric_review",
        params={"metric": "p95_latency", "window": "post_deploy"},
        depends_on=[],
        expected_output="Evidence-backed root-cause candidate",
        risk_level="low",
    )
    session.add(plan_task)

    reasoning_event = ReasoningEvent(
        session_id=problem_session.id,
        sequence_number=0,
        engine_name="chapter_4_seed",
        event_type="seed_trace",
        reasoning_mode="verify",
        summary="Seeded a trace-visible verification event for the database baseline.",
        event_metadata={"chapter": 4, "seed": True},
    )
    session.add(reasoning_event)

    artifact = Artifact(
        session_id=problem_session.id,
        artifact_type="report",
        name="Chapter 4 seed report",
        uri_or_storage_key="seed://chapter-4/report",
        content_hash="chapter-4-seed",
        artifact_metadata={"chapter": 4, "purpose": "db_smoke"},
        source="local_seed",
        sensitivity="internal",
    )
    session.add(artifact)
    session.flush()

    knowledge_content = (
        "Inspect the query path before adding Redis when latency changes immediately after deploy."
    )
    knowledge_chunk = KnowledgeChunk(
        session_id=problem_session.id,
        source_artifact_id=artifact.id,
        content=knowledge_content,
        content_hash=_content_hash(knowledge_content),
        source_type="local_seed",
        source_uri="seed://chapter-4/knowledge/query-path-before-cache",
        chunk_metadata={
            "memory_type": "semantic",
            "chapter": 4,
            "embedding_provenance_required": True,
        },
        embedding_provider="local_seed",
        embedding_model="zero-vector-1536",
        embedding_dimensions=SEED_EMBEDDING_DIMENSIONS,
        embedding=[0.0] * SEED_EMBEDDING_DIMENSIONS,
    )
    session.add(knowledge_chunk)

    verification_report = VerificationReport(
        session_id=problem_session.id,
        passed=True,
        checks_run=["session_inserted", "evidence_inserted", "trace_inserted", "vector_inserted"],
        failed_checks=[],
        contradictions=[],
        confidence_delta=0.1,
        recommended_route="continue_to_core_contracts",
    )
    session.add(verification_report)

    session.commit()
    return problem_session.id


def main() -> None:
    """CLI entrypoint for local seed execution."""
    engine = create_database_engine(get_settings().database_url)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        session_id = seed_database(session)
    print(f"Seeded Chapter 4 database baseline session: {session_id}")


if __name__ == "__main__":
    main()
