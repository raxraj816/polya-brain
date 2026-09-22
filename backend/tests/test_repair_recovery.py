"""Failed transfer must trigger bounded repair, never recycle a failed verdict."""

import copy

import pytest
from test_repair_memory import run
from test_source_check_api import SOURCE
from test_source_patch_investigation import _docker_available

from app.cognition.contracts import CognitiveRunStatus
from app.cognition.kernel import apply_cognitive_observation
from app.cognition.repair_memory import learn_repair
from app.cognition.repair_recovery import EVENT
from app.cognition.task_model import accumulated_usage

CHECK = "def verify(implementation):\n    assert implementation.total(5, 3) == 2\n    assert implementation.total(11, 4) == 7\n"


@pytest.fixture
def learned(tmp_path, monkeypatch):
    if not _docker_available():
        pytest.skip("requires configured pinned Docker sandbox")
    result, _ = run(tmp_path / "first", monkeypatch)
    lesson = learn_repair(result.state)
    assert lesson is not None
    return result, lesson


def test_rejected_memory_recovers_with_one_new_model_proposal(tmp_path, monkeypatch, learned):
    _, lesson = learned
    result, fake = run(
        tmp_path / "recover",
        monkeypatch,
        check=CHECK,
        lessons=[lesson],
        replacement="count - unit_price",
    )
    assert result.status is CognitiveRunStatus.COMPLETED
    assert len(fake.requests) == accumulated_usage(result.state).model_calls == 1
    assert len(result.state["plan"]) == 1
    current = result.state["plan"][0]
    assert current.id == "verify-source-patch-recovery"
    assert current.params["new_text"] == "count - unit_price"
    old, new = result.state["execution_outputs"]
    assert old.output["patch_verified"] is False
    assert new.task_id == current.id and new.output["patch_verified"] is True
    assert new.output["baseline_failed"] is True
    assert old.output["check_snapshot_sha256"] == new.output["check_snapshot_sha256"]
    event = next(e for e in result.state["events"] if e.event_type == EVENT)
    assert event.metadata["retired_task"]["params"]["new_text"] == lesson.new_text
    assert any(e.event_type == "verification_invalidated" for e in result.state["events"])
    content = "\n".join(m.content for m in fake.requests[0].messages)
    assert '"rejected_edit"' in content and lesson.new_text in content
    assert (tmp_path / "recover/source.py").read_text() == SOURCE
    learned_repair = learn_repair(result.state)
    assert learned_repair is not None and learned_repair.new_text == "count - unit_price"


@pytest.mark.parametrize("replacement", ["count / unit_price", "count * unit_price"])
def test_failed_or_repeated_recovery_stops_without_learning(
    tmp_path, monkeypatch, learned, replacement
):
    _, lesson = learned
    result, fake = run(
        tmp_path / "failed", monkeypatch, check=CHECK, lessons=[lesson], replacement=replacement
    )
    assert result.status is not CognitiveRunStatus.COMPLETED
    assert len(fake.requests) == 1
    assert not result.state["final_answer"]
    assert not result.state["verification"].passed
    assert learn_repair(result.state) is None
    assert len(result.state["execution_outputs"]) == (1 if replacement == lesson.new_text else 2)


def test_recovery_does_not_reset_exhausted_budget(tmp_path, monkeypatch, learned):
    _, lesson = learned
    result, fake = run(
        tmp_path / "budget", monkeypatch, check=CHECK, lessons=[lesson], max_model_calls=0
    )
    assert result.status is not CognitiveRunStatus.COMPLETED
    assert not fake.requests
    assert not result.state["verification"].passed


def test_vacuous_check_never_triggers_a_model_repair(tmp_path, monkeypatch, learned):
    _, lesson = learned
    result, fake = run(
        tmp_path / "vacuous",
        monkeypatch,
        check="def verify(implementation):\n    assert True\n",
        lessons=[lesson],
    )
    assert result.status is not CognitiveRunStatus.COMPLETED
    assert not fake.requests
    assert not result.state["verification"].passed


@pytest.mark.parametrize(
    "mutation", ["producer", "binding", "archive", "verdict", "equivalent_edit", "stale_task"]
)
def test_supersession_rejects_mutated_producer_bindings_and_history(
    tmp_path, monkeypatch, learned, mutation
):
    _, lesson = learned
    rejected, _ = run(
        tmp_path / "rejected", monkeypatch, check=CHECK, lessons=[lesson], model=False
    )
    recovered, _ = run(
        tmp_path / "recovered",
        monkeypatch,
        check=CHECK,
        lessons=[lesson],
        replacement="count - unit_price",
    )
    observation = copy.deepcopy(
        next(
            o
            for o in recovered.observations
            if any(e.event_type == EVENT for e in o.proposed_update.trace_events_to_add)
        )
    )
    # Build the exact failed state consumed by that observation from its own run.
    state = copy.deepcopy(recovered.state)
    recovery = next(e for e in state["events"] if e.event_type == EVENT)
    from app.models.contracts import PlanTask

    state["plan"] = [PlanTask.model_validate(recovery.metadata["retired_task"])]
    state["execution_outputs"] = state["execution_outputs"][:1]
    state["verification"] = rejected.state["verification"]
    state["events"] = state["events"][
        : next(i for i, e in enumerate(state["events"]) if e.event_type == EVENT)
    ]
    state["final_answer"] = None
    state["reflection"] = None
    assert (
        apply_cognitive_observation(state, observation)["plan"][0].id
        == "verify-source-patch-recovery"
    )
    if mutation == "producer":
        observation.capability = "untrusted_model"
    elif mutation == "binding":
        observation.proposed_update.plan_tasks_to_add[0].params["check_uri"] = (
            "file:///different.py"
        )
    elif mutation == "archive":
        next(
            e for e in observation.proposed_update.trace_events_to_add if e.event_type == EVENT
        ).metadata["retired_task"]["params"]["new_text"] = "forged"
    elif mutation == "equivalent_edit":
        task = observation.proposed_update.plan_tasks_to_add[0]
        task.params["old_text"] = "return count + unit_price"
        task.params["new_text"] = "return count * unit_price"
    elif mutation == "stale_task":
        observation.proposed_update.plan_tasks_to_add[0].id = state["plan"][0].id
    else:
        observation.proposed_update.verification = recovered.state["verification"]
    applied = apply_cognitive_observation(state, observation)
    assert applied["plan"] == state["plan"]
    assert applied["verification"] == state["verification"]
    assert applied["events"][-1].event_type == "repair_supersession_rejected"
