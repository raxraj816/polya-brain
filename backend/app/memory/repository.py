"""SQLAlchemy persistence and retrieval for governed long-term memory."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.cognition.contracts import (
    CognitiveActionType,
    LearnedActionPreference,
    ObservationStatus,
)
from app.cognition.procedure_compiler import (
    PROCEDURE_COMPILED_EVENT,
    PROCEDURE_REPLAYED_EVENT,
    CompiledProcedure,
    ProcedureLifecycle,
    procedure_integrity_valid,
)
from app.cognition.repair_memory import GAP_TYPE, RepairLesson, learn_repair
from app.db.models import (
    EpisodicMemory,
    KnowledgeChunk,
    ProblemSession,
    ProceduralStrategy,
    utc_now,
)
from app.graph.state import PolyaState
from app.memory.contracts import (
    EpisodicMemoryResult,
    MemoryContext,
    ProceduralMemoryResult,
    SemanticMemoryResult,
)
from app.memory.embeddings import EmbeddingProvider, HashingEmbeddingProvider

_LEARNABLE_ACTIONS = {
    CognitiveActionType.CLARIFY.value,
    CognitiveActionType.REFRAME.value,
    CognitiveActionType.RECALL.value,
    CognitiveActionType.RETRIEVE_MEMORY.value,
    CognitiveActionType.SEARCH.value,
    CognitiveActionType.ASK_HUMAN.value,
    CognitiveActionType.INSPECT.value,
    CognitiveActionType.OBSERVE.value,
    CognitiveActionType.MEASURE.value,
    CognitiveActionType.CALCULATE.value,
    CognitiveActionType.COMPARE.value,
    CognitiveActionType.SIMULATE.value,
    CognitiveActionType.EXPERIMENT.value,
}
_ADMITTED_STATUSES = {"evaluated", "verified_seed"}
_MAX_CONTENT_CHARACTERS = 20_000
_DEFAULT_CHUNK_CHARACTERS = 1_200


class SQLAlchemyMemoryRepository:
    """Store only inspectable memory and retrieve it under quality gates."""

    def __init__(
        self,
        db_session: Session,
        *,
        embeddings: EmbeddingProvider | None = None,
    ) -> None:
        self._db_session = db_session
        self._owner_id: str = db_session.info.get("owner_id") or "__local__"
        self._embeddings = embeddings or HashingEmbeddingProvider()

    def _require_owned_session(self, session_id: UUID) -> None:
        record = self._db_session.get(ProblemSession, session_id)
        if record is None or (record.user_id or "__local__") != self._owner_id:
            raise ValueError("Memory source session is outside this owner namespace")

    def ingest_semantic(
        self,
        content: str,
        *,
        source_type: str,
        source_uri: str,
        reliability_score: float,
        domain: str | None = None,
        valid_until: datetime | None = None,
        tags: Sequence[str] = (),
        session_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        admission_status: str = "evaluated",
    ) -> KnowledgeChunk:
        """Stage one evaluated semantic unit with source and freshness metadata."""
        if session_id is not None:
            self._require_owned_session(session_id)
        normalized = content.strip()
        normalized_source = source_uri.strip()
        if not normalized or len(normalized) > _MAX_CONTENT_CHARACTERS:
            raise ValueError("semantic content must contain 1 to 20000 characters")
        if not source_type.strip() or not normalized_source:
            raise ValueError("semantic memory requires source_type and source_uri")
        if not 0.0 <= reliability_score <= 1.0:
            raise ValueError("reliability_score must be between 0 and 1")
        if admission_status not in _ADMITTED_STATUSES:
            raise ValueError("semantic memory must be evaluated before admission")

        content_hash = hashlib.sha256(normalized.encode()).hexdigest()
        existing = self._db_session.scalar(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.owner_id == self._owner_id)
            .where(
                KnowledgeChunk.content_hash == content_hash,
                KnowledgeChunk.source_uri == normalized_source,
            )
        )
        if existing is not None:
            return existing

        embedding = self._embeddings.embed(normalized)
        chunk = KnowledgeChunk(
            owner_id=self._owner_id,
            session_id=session_id,
            content=normalized,
            content_hash=content_hash,
            source_type=source_type.strip(),
            source_uri=normalized_source,
            domain=domain.strip() if domain else None,
            reliability_score=reliability_score,
            valid_until=valid_until,
            tags=list(dict.fromkeys(tag.strip() for tag in tags if tag.strip())),
            admission_status=admission_status,
            chunk_metadata=metadata or {},
            embedding_provider=self._embeddings.name,
            embedding_model=self._embeddings.model,
            embedding_dimensions=self._embeddings.dimensions,
            embedding=embedding,
        )
        self._db_session.add(chunk)
        self._db_session.flush()
        return chunk

    def ingest_document(
        self,
        content: str,
        *,
        source_type: str,
        source_uri: str,
        reliability_score: float,
        domain: str | None = None,
        valid_until: datetime | None = None,
        tags: Sequence[str] = (),
        chunk_characters: int = _DEFAULT_CHUNK_CHARACTERS,
        admission_status: str = "evaluated",
    ) -> list[KnowledgeChunk]:
        """Chunk a bounded document on paragraphs and ingest each sourced unit."""
        normalized = content.strip()
        if chunk_characters < 200 or chunk_characters > 4_000:
            raise ValueError("chunk_characters must be between 200 and 4000")
        paragraphs = [item.strip() for item in normalized.split("\n\n") if item.strip()]
        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if len(paragraph) > chunk_characters:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(
                    paragraph[index : index + chunk_characters]
                    for index in range(0, len(paragraph), chunk_characters)
                )
            elif current and len(current) + len(paragraph) + 2 > chunk_characters:
                chunks.append(current)
                current = paragraph
            else:
                current = f"{current}\n\n{paragraph}" if current else paragraph
        if current:
            chunks.append(current)
        if not chunks:
            raise ValueError("document content must not be blank")
        return [
            self.ingest_semantic(
                chunk,
                source_type=source_type,
                source_uri=f"{source_uri}#chunk-{index}",
                reliability_score=reliability_score,
                domain=domain,
                valid_until=valid_until,
                tags=tags,
                metadata={"document_source_uri": source_uri, "chunk_index": index},
                admission_status=admission_status,
            )
            for index, chunk in enumerate(chunks, start=1)
        ]

    def search_semantic(
        self,
        query: str,
        *,
        limit: int = 3,
        domain: str | None = None,
        source_type: str | None = None,
        minimum_reliability: float = 0.5,
        minimum_similarity: float = 0.08,
        now: datetime | None = None,
    ) -> list[SemanticMemoryResult]:
        """Return relevant admitted facts, excluding stale or low-quality chunks."""
        normalized = query.strip()
        if not normalized:
            raise ValueError("memory query must not be blank")
        if not 1 <= limit <= 20:
            raise ValueError("memory result limit must be between 1 and 20")
        if not 0.0 <= minimum_reliability <= 1.0:
            raise ValueError("minimum_reliability must be between 0 and 1")
        if not 0.0 <= minimum_similarity <= 1.0:
            raise ValueError("minimum_similarity must be between 0 and 1")
        query_vector = self._embeddings.embed(normalized)
        distance = KnowledgeChunk.embedding.cosine_distance(query_vector).label("distance")
        statement = (
            select(KnowledgeChunk, distance)
            .where(KnowledgeChunk.owner_id == self._owner_id)
            .where(
                KnowledgeChunk.embedding.is_not(None),
                KnowledgeChunk.reliability_score >= minimum_reliability,
                KnowledgeChunk.admission_status.in_(_ADMITTED_STATUSES),
                distance <= 1.0 - minimum_similarity,
                or_(
                    KnowledgeChunk.valid_until.is_(None),
                    KnowledgeChunk.valid_until >= (now or utc_now()),
                ),
            )
        )
        if domain is not None:
            statement = statement.where(KnowledgeChunk.domain == domain)
        if source_type is not None:
            statement = statement.where(KnowledgeChunk.source_type == source_type)
        rows = self._db_session.execute(statement.order_by(distance).limit(limit)).all()
        return [
            SemanticMemoryResult(
                id=chunk.id,
                content=chunk.content,
                source_type=chunk.source_type,
                source_uri=chunk.source_uri,
                domain=chunk.domain,
                reliability_score=chunk.reliability_score,
                similarity_score=max(0.0, min(1.0, 1.0 - float(row_distance))),
                valid_until=chunk.valid_until,
                tags=[str(item) for item in chunk.tags],
                admission_status=chunk.admission_status,
            )
            # Positional access preserves each column's type across SQLAlchemy
            # 2.0/2.1; direct Row iteration can widen both values to object.
            for chunk, row_distance in ((row[0], row[1]) for row in rows)
        ]

    def search_episodes(
        self,
        query: str,
        *,
        limit: int = 3,
        problem_type: str | None = None,
        domain: str | None = None,
        minimum_similarity: float = 0.08,
    ) -> list[EpisodicMemoryResult]:
        """Return structurally similar prior cases that passed verification."""
        if not query.strip():
            raise ValueError("episode query must not be blank")
        if not 1 <= limit <= 20:
            raise ValueError("memory result limit must be between 1 and 20")
        if not 0.0 <= minimum_similarity <= 1.0:
            raise ValueError("minimum_similarity must be between 0 and 1")
        vector = self._embeddings.embed(query)
        distance = EpisodicMemory.embedding.cosine_distance(vector).label("distance")
        statement = (
            select(EpisodicMemory, distance)
            .where(EpisodicMemory.owner_id == self._owner_id)
            .where(distance <= 1.0 - minimum_similarity)
        )
        if problem_type is not None:
            statement = statement.where(EpisodicMemory.problem_type == problem_type)
        if domain is not None:
            statement = statement.where(EpisodicMemory.domain == domain)
        rows = self._db_session.execute(statement.order_by(distance).limit(limit)).all()
        return [
            EpisodicMemoryResult(
                id=episode.id,
                source_session_id=episode.source_session_id,
                problem_type=episode.problem_type,
                domain=episode.domain,
                core_question=episode.core_question,
                outcome_summary=episode.outcome_summary,
                final_answer=episode.final_answer,
                similarity_score=max(0.0, min(1.0, 1.0 - float(row_distance))),
                created_at=episode.created_at,
            )
            for episode, row_distance in ((row[0], row[1]) for row in rows)
        ]

    def has_relevant_memory(self, query: str, domain: str | None = None) -> bool:
        """Support attention gating without retrieving irrelevant content into state."""
        return bool(
            self.search_semantic(
                query,
                limit=1,
                domain=domain,
                minimum_reliability=0.5,
                minimum_similarity=0.08,
            )
        )

    def context_for_problem(
        self,
        query: str,
        *,
        problem_type: str | None = None,
        domain: str | None = None,
    ) -> MemoryContext:
        """Build bounded top-three context with explicit transfer limitations."""
        semantic = self.search_semantic(query, limit=3, domain=domain)
        episodes = self.search_episodes(query, limit=3, problem_type=problem_type, domain=domain)
        limitations = [
            "Retrieved memory is context, not a conclusion; current evidence must verify transfer."
        ]
        if episodes:
            limitations.append(
                "Prior outcomes may suggest an approach, but their constraints may differ."
            )
        return MemoryContext(
            query=query,
            semantic=semantic,
            episodes=episodes,
            limitations=limitations,
        )

    def learn_verified_outcome(self, session_id: UUID, state: PolyaState) -> bool:
        """Persist episode and successful procedures only after verification/reflection."""
        self._require_owned_session(session_id)
        verification = state["verification"]
        reflection = state["reflection"]
        problem = state["structured_problem"]
        final_answer = state["final_answer"]
        if (
            verification is None
            or not verification.passed
            or reflection is None
            or problem is None
            or not final_answer
        ):
            return False

        episode = self._db_session.scalar(
            select(EpisodicMemory)
            .where(EpisodicMemory.owner_id == self._owner_id)
            .where(EpisodicMemory.source_session_id == session_id)
        )
        if episode is None:
            episode_text = "\n".join(
                [problem.core_question, reflection.outcome_summary, final_answer]
            )
            episode = EpisodicMemory(
                owner_id=self._owner_id,
                source_session_id=session_id,
                problem_type=problem.problem_type,
                domain=problem.domain,
                core_question=problem.core_question,
                outcome_summary=reflection.outcome_summary,
                final_answer=final_answer,
                verification_checks=list(verification.checks_run),
                reflection=reflection.model_dump(mode="json"),
                evidence_source_uris=list(
                    dict.fromkeys(item.source_uri for item in state["evidence"] if item.source_uri)
                ),
                embedding_provider=self._embeddings.name,
                embedding_model=self._embeddings.model,
                embedding=self._embeddings.embed(episode_text),
            )
            self._db_session.add(episode)

        self._store_compiled_procedure_artifacts(session_id, state)
        self._store_repair_lesson(session_id, state)
        self._learn_procedures(session_id, state)
        self._db_session.flush()
        return True

    def _store_repair_lesson(self, session_id: UUID, state: PolyaState) -> None:
        lesson = learn_repair(state)
        if lesson is None or lesson.source_session_id != str(session_id):
            return
        edit_key = hashlib.sha256(
            repr(
                (lesson.version, lesson.sandbox_version, lesson.old_text, lesson.new_text)
            ).encode()
        ).hexdigest()
        capability = f"candidate_edit:{edit_key}"
        existing = self._db_session.scalar(
            select(ProceduralStrategy).where(
                ProceduralStrategy.owner_id == self._owner_id,
                ProceduralStrategy.gap_type == GAP_TYPE,
                ProceduralStrategy.capability == capability,
            )
        )
        if existing is not None:
            return
        self._db_session.add(
            ProceduralStrategy(
                owner_id=self._owner_id,
                name=f"Candidate repair from {session_id}",
                problem_type="source_patch_investigation",
                gap_type=GAP_TYPE,
                action_type=CognitiveActionType.HYPOTHESIZE.value,
                capability=capability,
                preconditions=[
                    "Candidate only; must pass the current supplied check on changed code."
                ],
                steps=[{"repair_lesson": lesson.model_dump(mode="json")}],
                verified_successes=0,
                verified_failures=0,
                success_rate=0.0,
                source_session_ids=[str(session_id)],
            )
        )

    def load_repair_lessons(self) -> list[RepairLesson]:
        """Read at most twenty owner-scoped proposals; never grant execution authority."""
        rows = self._db_session.scalars(
            select(ProceduralStrategy)
            .where(
                ProceduralStrategy.owner_id == self._owner_id,
                ProceduralStrategy.gap_type == GAP_TYPE,
            )
            .order_by(ProceduralStrategy.updated_at.desc(), ProceduralStrategy.id)
            .limit(20)
        )
        lessons: list[RepairLesson] = []
        for row in rows:
            try:
                lesson = RepairLesson.model_validate(row.steps[0]["repair_lesson"])
            except ValueError, TypeError, KeyError, IndexError:
                continue
            if lesson.valid() and lesson.source_session_id in row.source_session_ids:
                lessons.append(lesson)
        return lessons

    def _store_compiled_procedure_artifacts(
        self,
        session_id: UUID,
        state: PolyaState,
    ) -> None:
        """Persist trace-validated compiled artifacts as untrusted playbooks first."""
        for event in state["events"]:
            if event.event_type not in {PROCEDURE_COMPILED_EVENT, PROCEDURE_REPLAYED_EVENT}:
                continue
            try:
                procedure = CompiledProcedure.model_validate(event.metadata)
            except ValueError:
                continue
            if not procedure_integrity_valid(procedure):
                continue
            capability = f"compiled_procedure:{procedure.id}"
            existing = self._db_session.scalar(
                select(ProceduralStrategy)
                .where(ProceduralStrategy.owner_id == self._owner_id)
                .where(
                    ProceduralStrategy.problem_type == procedure.task_family,
                    ProceduralStrategy.gap_type == "compiled_procedure",
                    ProceduralStrategy.action_type == CognitiveActionType.EXECUTE.value,
                    ProceduralStrategy.capability == capability,
                )
            )
            trusted = procedure.lifecycle in {
                ProcedureLifecycle.VERIFIED,
                ProcedureLifecycle.DEPLOYED,
                ProcedureLifecycle.MONITORED,
            }
            passing_replays = len(
                {item.case_id for item in procedure.regression_cases if item.verification_passed}
            )
            source_ids = list(dict.fromkeys([*procedure.source_session_ids, str(session_id)]))
            steps = [{"compiled_procedure": procedure.model_dump(mode="json")}]
            preconditions = [
                f"task_family={procedure.task_family}",
                *procedure.safety_constraints,
            ]
            if existing is None:
                self._db_session.add(
                    ProceduralStrategy(
                        owner_id=self._owner_id,
                        name=f"compiled:{procedure.id}:v{procedure.version}",
                        problem_type=procedure.task_family,
                        gap_type="compiled_procedure",
                        action_type=CognitiveActionType.EXECUTE.value,
                        capability=capability,
                        preconditions=preconditions,
                        steps=steps,
                        verified_successes=passing_replays if trusted else 0,
                        verified_failures=0,
                        success_rate=1.0 if trusted else 0.0,
                        source_session_ids=source_ids,
                    )
                )
                continue
            stored_payload = (
                existing.steps[0].get("compiled_procedure")
                if existing.steps and isinstance(existing.steps[0], dict)
                else None
            )
            stored_version = (
                stored_payload.get("version", 0) if isinstance(stored_payload, dict) else 0
            )
            if isinstance(stored_version, int) and stored_version > procedure.version:
                continue
            existing.name = f"compiled:{procedure.id}:v{procedure.version}"
            existing.preconditions = preconditions
            existing.steps = steps
            existing.verified_successes = passing_replays if trusted else 0
            existing.success_rate = 1.0 if trusted else 0.0
            existing.source_session_ids = source_ids
            existing.updated_at = utc_now()

    def _learn_procedures(self, session_id: UUID, state: PolyaState) -> None:
        problem = state["structured_problem"]
        if problem is None:
            return
        decisions: dict[str, dict[str, Any]] = {}
        succeeded: set[str] = set()
        failed: set[str] = set()
        for event in state["events"]:
            if event.event_type == "cognitive_action_decision":
                selected = event.metadata.get("selected")
                if isinstance(selected, dict):
                    action_id = selected.get("id")
                    if isinstance(action_id, str):
                        decisions[action_id] = selected
            elif event.event_type == "capability_observation":
                action_id = event.metadata.get("action_id")
                if isinstance(action_id, str):
                    status = event.metadata.get("status")
                    if status == ObservationStatus.SUCCEEDED.value:
                        succeeded.add(action_id)
                    elif status in {
                        ObservationStatus.FAILED.value,
                        ObservationStatus.BLOCKED.value,
                        ObservationStatus.INCONCLUSIVE.value,
                    }:
                        failed.add(action_id)

        for gap in state["gaps"]:
            matching = [
                (action_id, item)
                for action_id, item in decisions.items()
                if item.get("target") == gap.description
            ]
            for action_id, selected in matching:
                if action_id in failed:
                    self._record_procedure_outcome(
                        session_id,
                        problem.problem_type,
                        gap.gap_type,
                        list(problem.constraints),
                        selected,
                        succeeded=False,
                    )
                elif action_id in succeeded and gap.filled:
                    self._record_procedure_outcome(
                        session_id,
                        problem.problem_type,
                        gap.gap_type,
                        list(problem.constraints),
                        selected,
                        succeeded=True,
                    )

    def _record_procedure_outcome(
        self,
        session_id: UUID,
        problem_type: str,
        gap_type: str,
        preconditions: list[str],
        selected: dict[str, Any],
        *,
        succeeded: bool,
    ) -> None:
        action_type = selected.get("action_type")
        capability = selected.get("capability")
        if action_type not in _LEARNABLE_ACTIONS or not isinstance(capability, str):
            return
        strategy = self._db_session.scalar(
            select(ProceduralStrategy)
            .where(ProceduralStrategy.owner_id == self._owner_id)
            .where(
                ProceduralStrategy.problem_type == problem_type,
                ProceduralStrategy.gap_type == gap_type,
                ProceduralStrategy.action_type == action_type,
                ProceduralStrategy.capability == capability,
            )
        )
        session_key = str(session_id)
        if strategy is None:
            strategy = ProceduralStrategy(
                owner_id=self._owner_id,
                name=f"{problem_type}:{gap_type}:{action_type}",
                problem_type=problem_type,
                gap_type=gap_type,
                action_type=action_type,
                capability=capability,
                preconditions=preconditions,
                steps=[
                    {
                        "action_type": action_type,
                        "capability": capability,
                        "target_pattern": gap_type,
                    }
                ],
                verified_successes=1 if succeeded else 0,
                verified_failures=0 if succeeded else 1,
                success_rate=1.0 if succeeded else 0.0,
                source_session_ids=[session_key],
            )
            self._db_session.add(strategy)
            return
        if session_key in strategy.source_session_ids:
            return
        if succeeded:
            strategy.verified_successes += 1
        else:
            strategy.verified_failures += 1
        strategy.source_session_ids = [*strategy.source_session_ids, session_key]
        strategy.success_rate = strategy.verified_successes / (
            strategy.verified_successes + strategy.verified_failures
        )
        strategy.updated_at = utc_now()

    def preference(
        self,
        problem_type: str,
        gap_type: str,
    ) -> LearnedActionPreference | None:
        """Return the strongest verified procedural preference for a structural gap."""
        strategy = self._db_session.scalar(
            select(ProceduralStrategy)
            .where(ProceduralStrategy.owner_id == self._owner_id)
            .where(
                ProceduralStrategy.problem_type == problem_type,
                ProceduralStrategy.gap_type == gap_type,
                ProceduralStrategy.verified_successes >= 1,
                ProceduralStrategy.success_rate >= 0.5,
            )
            .order_by(
                ProceduralStrategy.success_rate.desc(),
                ProceduralStrategy.verified_successes.desc(),
            )
            .limit(1)
        )
        if strategy is None:
            return None
        try:
            action_type = CognitiveActionType(strategy.action_type)
        except ValueError:
            return None
        return LearnedActionPreference(
            action_type=action_type,
            capability=strategy.capability,
            source_session_ids=[str(item) for item in strategy.source_session_ids],
            verified_successes=strategy.verified_successes,
        )

    def list_strategies(
        self,
        *,
        problem_type: str | None = None,
        gap_type: str | None = None,
        verified_only: bool = False,
        limit: int = 20,
    ) -> list[ProceduralMemoryResult]:
        """Inspect learned procedures and human-authored unverified playbooks."""
        if not 1 <= limit <= 100:
            raise ValueError("strategy result limit must be between 1 and 100")
        statement = select(ProceduralStrategy).where(ProceduralStrategy.owner_id == self._owner_id)
        if problem_type is not None:
            statement = statement.where(ProceduralStrategy.problem_type == problem_type)
        if gap_type is not None:
            statement = statement.where(ProceduralStrategy.gap_type == gap_type)
        if verified_only:
            statement = statement.where(ProceduralStrategy.verified_successes >= 1)
        strategies = self._db_session.scalars(
            statement.order_by(
                ProceduralStrategy.success_rate.desc(),
                ProceduralStrategy.verified_successes.desc(),
                ProceduralStrategy.name,
            ).limit(limit)
        )
        return [
            ProceduralMemoryResult(
                id=strategy.id,
                name=strategy.name,
                problem_type=strategy.problem_type,
                gap_type=strategy.gap_type,
                action_type=strategy.action_type,
                capability=strategy.capability,
                preconditions=[str(item) for item in strategy.preconditions],
                steps=[
                    {str(key): value for key, value in item.items()}
                    for item in strategy.steps
                    if isinstance(item, dict)
                ],
                verified_successes=strategy.verified_successes,
                verified_failures=strategy.verified_failures,
                success_rate=strategy.success_rate,
                source_session_ids=[str(item) for item in strategy.source_session_ids],
                updated_at=strategy.updated_at,
            )
            for strategy in strategies
        ]
