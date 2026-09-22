"""Experimental exact-edit lessons: proposals always retested on current code."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence

from pydantic import Field

from app.cognition.capabilities import FunctionCapability
from app.cognition.contracts import (
    CapabilityDefinition,
    CapabilityKind,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveObservation,
    ObservationStatus,
)
from app.cognition.source_patch_investigation import (
    SourcePatchProposal,
    proposal_observation,
)
from app.cognition.structural_repair import VERSION as STRUCTURAL_VERSION
from app.cognition.structural_repair import structural_candidates
from app.execution.source_patch import SOURCE_PATCH_SANDBOX_VERSION, SourcePatchTask
from app.graph.state import PolyaState, StateEvent
from app.models.contracts import ContractModel, HypothesisOrigin, NonEmptyStr, ReasoningMode

VERSION = "candidate_repair_memory@0.1.0"
RECALL_VERSION = "candidate_repair_memory@0.2.0"
CAPABILITY = "source_patch_recall"
GAP_TYPE = "candidate_source_edit"
EVENT = "source_patch_memory_proposed"


class RepairLesson(ContractModel):
    """A past checked edit, never a present-case correctness assertion."""

    version: NonEmptyStr = VERSION
    old_text: NonEmptyStr = Field(max_length=800)
    new_text: NonEmptyStr = Field(max_length=800)
    source_session_id: NonEmptyStr
    source_sha256: NonEmptyStr
    check_sha256: NonEmptyStr
    sandbox_version: NonEmptyStr = SOURCE_PATCH_SANDBOX_VERSION
    integrity_hash: NonEmptyStr

    def digest(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.model_dump(mode="json", exclude={"integrity_hash"}), sort_keys=True
            ).encode()
        ).hexdigest()

    def valid(self) -> bool:
        return (
            self.version == VERSION
            and self.sandbox_version == SOURCE_PATCH_SANDBOX_VERSION
            and self.old_text != self.new_text
            and "\x00" not in self.old_text + self.new_text
            and self.integrity_hash == self.digest()
        )


def learn_repair(state: PolyaState) -> RepairLesson | None:
    """Extract only an explicitly admitted, snapshot-bound successful source edit."""
    problem, verification = state["structured_problem"], state["verification"]
    if (
        problem is None
        or problem.problem_type != "source_patch_investigation"
        or verification is None
        or not verification.passed
        or state["reflection"] is None
        or not state["final_answer"]
    ):
        return None
    tasks = [t for t in state["plan"] if t.tool_name == "source_patch_sandbox"]
    if len(tasks) != 1:
        return None
    task = tasks[0]
    try:
        params = SourcePatchTask.model_validate(task.params)
    except ValueError:
        return None
    outputs = [o for o in state["execution_outputs"] if o.task_id == task.id]
    if len(outputs) != 1 or outputs[0].error or not isinstance(outputs[0].output, dict):
        return None
    output = outputs[0].output
    if any(
        output.get(key) is not True
        for key in ["patch_verified", "baseline_failed", "source_admitted", "correction_verified"]
    ):
        return None
    hashes = {}
    for role, uri in [("source", params.source_uri), ("regression check", params.check_uri)]:
        matches = [
            e
            for e in state["events"]
            if e.event_type == "source_patch_artifact_admitted"
            and e.engine_name == "explicit_source_patch_request"
            and e.metadata.get("role") == role
            and e.metadata.get("source_uri") == uri
        ]
        if len(matches) != 1:
            return None
        digest = matches[0].metadata.get("sha256")
        key = "source" if role == "source" else "check"
        if not isinstance(digest, str) or output.get(f"{key}_snapshot_sha256") != digest:
            return None
        hashes[key] = digest
    source = next(
        (e.raw_excerpt for e in state["evidence"] if e.source_uri == params.source_uri), None
    )
    if (
        not source
        or hashlib.sha256(source.encode()).hexdigest() != hashes["source"]
        or source.count(params.old_text) != 1
        or hashlib.sha256(source.replace(params.old_text, params.new_text, 1).encode()).hexdigest()
        != output.get("patched_source_sha256")
    ):
        return None
    if not any(
        e.event_type == "capability_observation"
        and e.metadata.get("capability") == "source_patch_sandbox"
        and e.metadata.get("capability_version") == SOURCE_PATCH_SANDBOX_VERSION
        and e.metadata.get("status") == "succeeded"
        for e in state["events"]
    ):
        return None
    lesson = RepairLesson(
        old_text=params.old_text,
        new_text=params.new_text,
        source_session_id=state["session_id"],
        source_sha256=hashes["source"],
        check_sha256=hashes["check"],
        integrity_hash="pending",
    )
    return lesson.model_copy(update={"integrity_hash": lesson.digest()})


def repair_recall_capability(
    loader: Callable[[], Sequence[RepairLesson]],
) -> FunctionCapability:
    definition = CapabilityDefinition(
        name=CAPABILITY,
        version=RECALL_VERSION,
        supported_actions={CognitiveActionType.HYPOTHESIZE},
        kind=CapabilityKind.MEMORY,
        estimated_cost=0.01,
        timeout_seconds=5,
        approved_for_sensitive_data=True,
    )

    def execute(action: CognitiveActionCandidate, state: PolyaState) -> CognitiveObservation:
        def miss(reason: str) -> CognitiveObservation:
            return CognitiveObservation(
                action_id=action.id,
                capability=CAPABILITY,
                capability_version=RECALL_VERSION,
                status=ObservationStatus.INCONCLUSIVE,
                summary=reason,
                failure_kind="no_unambiguous_repair_lesson",
                payload={"model_calls": 0},
            )

        problem = state["structured_problem"]
        if problem is None or problem.problem_type != "source_patch_investigation":
            return miss("Candidate repair memory requires explicit source/check admission.")
        roles: dict[str, str] = {}
        for event in state["events"]:
            if (
                event.event_type == "source_patch_artifact_admitted"
                and event.engine_name == "explicit_source_patch_request"
            ):
                role, uri = event.metadata.get("role"), event.metadata.get("source_uri")
                if isinstance(role, str) and isinstance(uri, str):
                    if role in roles:
                        return miss("Ambiguous source/check admission roles.")
                    roles[role] = uri
        source_uri, check_uri = roles.get("source"), roles.get("regression check")
        source = next(
            (e.raw_excerpt for e in state["evidence"] if e.source_uri == source_uri), None
        )
        if not source or not source_uri or not check_uri or source_uri == check_uri:
            return miss("Complete, distinct current source/check snapshots are required.")
        lessons = [
            lesson
            for lesson in list(loader())[:20]
            if lesson.valid() and lesson.source_session_id != state["session_id"]
        ]
        matches = {
            (lesson.old_text, lesson.new_text): lesson
            for lesson in lessons
            if source.count(lesson.old_text) == 1
        }
        names: dict[str, str] = {}
        transfer_kind = "exact"
        if not matches:
            adapted = {}
            for lesson in lessons:
                candidates = structural_candidates(source, lesson.old_text, lesson.new_text)
                if candidates is None:
                    return miss(
                        "Structural repair matches multiple sites; use normal investigation."
                    )
                for candidate in candidates:
                    adapted[(candidate.old_text, candidate.new_text)] = (lesson, candidate.names)
            if len(adapted) != 1:
                return miss("No unique structural repair candidate; use normal investigation.")
            (old_text, new_text), (lesson, names) = next(iter(adapted.items()))
            transfer_kind = "alpha_expression"
        else:
            if len(matches) != 1:
                return miss("No unique compatible candidate edit; use normal investigation.")
            (old_text, new_text), lesson = next(iter(matches.items()))
        observation = proposal_observation(
            SourcePatchProposal(
                diagnosis=f"Memory suggests testing replacement of {old_text!r} with {new_text!r}; the present cause is unproven.",
                implicated_source_uri=source_uri,
                old_text=old_text,
                new_text=new_text,
                correction_rationale="A prior verified edit suggests this candidate; current transfer remains unverified.",
                regression_check_uri=check_uri,
                regression_check_summary="Run the current supplied check on both original and candidate snapshots.",
                remaining_uncertainty=[
                    "Exact or structural matching does not establish equivalent semantics, types or general correctness."
                ],
            ),
            action,
            state,
            definition=definition,
            failure_payload={"model_calls": 0},
            origin=HypothesisOrigin.MEMORY_ANALOGY,
        )
        observation.proposed_update.trace_events_to_add.append(
            StateEvent(
                engine_name=CAPABILITY,
                event_type=EVENT,
                reasoning_mode=ReasoningMode.EXPLORE,
                summary="Recalled a candidate edit; current execution and verification remain mandatory.",
                metadata={
                    "version": RECALL_VERSION,
                    "transfer_kind": transfer_kind,
                    "name_mapping": {key: value for key, value in names.items()},
                    "pattern_version": STRUCTURAL_VERSION if names else None,
                    "source_session_id": lesson.source_session_id,
                    "lesson_hash": lesson.integrity_hash,
                    "current_source_uri": source_uri,
                    "current_check_uri": check_uri,
                    "prior_verdict_reused": False,
                },
            )
        )
        return observation

    return FunctionCapability(definition, execute)
