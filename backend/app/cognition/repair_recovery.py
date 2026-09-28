"""Bounded source-edit supersession, carried in trusted adapter trace metadata."""

import hashlib

from app.cognition.contracts import CognitiveObservation, ObservationStatus
from app.graph.state import PolyaState, StateEvent
from app.models.contracts import PlanTask, ReasoningMode

EVENT = "source_patch_recovery_proposed"
VERSION = "source_patch_recovery@0.2.0"
CAPABILITY = "source_patch_investigator"


def _observed_failure(value: object) -> bool:
    """Require a complete failed check, not a timeout or missing observation."""
    if not isinstance(value, dict):
        return False
    tests = value.get("test_results")
    return (
        type(value.get("exit_code")) is int
        and value["exit_code"] != 0
        and value.get("timed_out") is False
        and value.get("output_truncated") is False
        and value.get("tests_run") == 1
        and isinstance(tests, list)
        and len(tests) == 1
        and isinstance(tests[0], dict)
        and tests[0].get("index") == 1
        and tests[0].get("passed") is False
    )


def failed_source_patch_task(state: PolyaState) -> PlanTask | None:
    """One measured, rejected model or recalled edit can enter bounded recovery."""
    problem, verdict = state["structured_problem"], state["verification"]
    if (
        problem is None
        or problem.problem_type != "source_patch_investigation"
        or verdict is None
        or verdict.passed
        or len(state["plan"]) != 1
        or any(e.event_type == EVENT for e in state["events"])
    ):
        return None
    task = state["plan"][0]
    outputs = [o for o in state["execution_outputs"] if o.task_id == task.id]
    if task.tool_name != "source_patch_sandbox" or len(outputs) != 1:
        return None
    output = outputs[0].output
    if (
        not isinstance(output, dict)
        or output.get("baseline_failed") is not True
        or output.get("source_admitted") is not True
        or output.get("patch_verified") is not False
        or not _observed_failure(output.get("baseline"))
        or not _observed_failure(output.get("patched"))
    ):
        return None
    for role in ("source", "check"):
        uri = task.params.get(f"{role}_uri")
        admitted = [e for e in state["evidence"] if e.source_uri == uri and e.raw_excerpt]
        if len(admitted) != 1 or output.get(f"{role}_uri") != uri:
            return None
        snapshot = admitted[0].raw_excerpt
        assert snapshot is not None
        if output.get(f"{role}_snapshot_sha256") != hashlib.sha256(snapshot.encode()).hexdigest():
            return None
        if role == "source":
            old_text, new_text = task.params.get("old_text"), task.params.get("new_text")
            if (
                not isinstance(old_text, str)
                or not isinstance(new_text, str)
                or snapshot.count(old_text) != 1
            ):
                return None
            candidate = snapshot.replace(old_text, new_text, 1)
            if (
                output.get("patched_source_sha256")
                != hashlib.sha256(candidate.encode()).hexdigest()
            ):
                return None
    if not any(
        event.event_type == "source_patch_proposed"
        and event.engine_name in {CAPABILITY, "source_patch_recall"}
        and event.metadata.get("source_uri") == task.params.get("source_uri")
        and event.metadata.get("check_uri") == task.params.get("check_uri")
        and event.metadata.get("old_text_occurrences_in_excerpt") == 1
        for event in state["events"]
    ):
        return None
    if not any(
        event.event_type == "source_patch_sandbox_completed"
        and event.engine_name == "source_patch_sandbox"
        and event.metadata.get("source_snapshot_sha256") == output.get("source_snapshot_sha256")
        and event.metadata.get("check_snapshot_sha256") == output.get("check_snapshot_sha256")
        and event.metadata.get("patch_verified") is False
        for event in state["events"]
    ):
        return None
    return task


def supersession_event(state: PolyaState, replacement: PlanTask) -> StateEvent:
    old = failed_source_patch_task(state)
    if old is None:
        raise ValueError("No eligible measured source-edit failure remains for recovery")
    if (
        replacement.id in {t.id for t in state["plan"]}
        or replacement.id in {o.task_id for o in state["execution_outputs"]}
        or replacement.tool_name != old.tool_name
        or any(
            replacement.params.get(key) != old.params.get(key)
            for key in ("source_uri", "check_uri", "verification")
        )
        or (replacement.params.get("old_text"), replacement.params.get("new_text"))
        == (old.params.get("old_text"), old.params.get("new_text"))
    ):
        raise ValueError(
            "Recovery requires a new edit and task ID with unchanged source/check bindings"
        )
    source = next(
        (e.raw_excerpt for e in state["evidence"] if e.source_uri == old.params.get("source_uri")),
        None,
    )
    old_text, old_new = old.params.get("old_text"), old.params.get("new_text")
    new_text, new_new = replacement.params.get("old_text"), replacement.params.get("new_text")
    if not source or not all(
        isinstance(t, str) and t for t in (old_text, old_new, new_text, new_new)
    ):
        raise ValueError("Recovery requires complete admitted source and bounded edits")
    assert isinstance(old_text, str) and isinstance(old_new, str)
    assert isinstance(new_text, str) and isinstance(new_new, str)
    if (
        source.count(new_text) != 1
        or source.count(old_text) != 1
        or source.replace(old_text, old_new, 1) == source.replace(new_text, new_new, 1)
    ):
        raise ValueError(
            "Recovery must change the rejected candidate, not just its edit boundaries"
        )
    return StateEvent(
        engine_name=CAPABILITY,
        event_type=EVENT,
        reasoning_mode=ReasoningMode.REFRAME,
        summary="Retired the rejected source edit; its replacement requires fresh execution and verification.",
        metadata={
            "version": VERSION,
            "retired_task": old.model_dump(mode="json"),
            "replacement_task": replacement.model_dump(mode="json"),
        },
    )


def validated_retired_task(state: PolyaState, observation: CognitiveObservation) -> str | None:
    """Validate optional supersession independently at the state-update boundary."""
    events = [e for e in observation.proposed_update.trace_events_to_add if e.event_type == EVENT]
    if not events:
        return None
    tasks = observation.proposed_update.plan_tasks_to_add
    update = observation.proposed_update
    if (
        len(events) != 1
        or len(tasks) != 1
        or observation.status is not ObservationStatus.SUCCEEDED
        or observation.capability != CAPABILITY
        or update.structured_problem is not None
        or update.verification is not None
        or update.execution_outputs_to_add
        or update.final_answer is not None
        or update.reflection is not None
        or update.constraints_to_add
        or observation.evidence
        or len(update.hypotheses_to_add) != 1
        or update.knowns_to_add
        or update.unknowns_to_resolve
        or update.gaps_to_add
        or update.resolved_gap_targets
        or update.superseded_gap_targets
        or update.questions_to_ask
    ):
        raise ValueError("Invalid repair supersession producer or state update")
    expected = supersession_event(state, tasks[0])
    if events[0].engine_name != CAPABILITY or events[0].metadata != expected.metadata:
        raise ValueError("Repair supersession does not match current and replacement tasks")
    return state["plan"][0].id
