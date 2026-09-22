"""Candidate edit learning, bounded transfer and current-case falsification."""

import copy

import pytest
from test_source_check_api import CHECK, SOURCE, DynamicProposal
from test_source_patch_investigation import _docker_available

from app.cognition.bootstrap import build_cognitive_runtime
from app.cognition.contracts import CognitiveRunStatus
from app.cognition.repair_memory import EVENT, learn_repair
from app.cognition.task_model import accumulated_usage
from app.config import Settings
from app.investigator.source_patch import source_patch_state


def settings(root):
    return Settings(
        _env_file=None,
        OPENROUTER_API_KEY="fake",
        OPENROUTER_MODEL="test-model",
        SEARCH_PROVIDER="",
        ARTIFACT_ALLOWED_ROOTS=str(root),
        CODE_EXECUTION_ENABLED=True,
    )


def run(
    root,
    monkeypatch,
    source=SOURCE,
    check=CHECK,
    lessons=(),
    model=True,
    replacement="count * unit_price",
    max_model_calls=None,
):
    root.mkdir(parents=True)
    (root / "source.py").write_text(source)
    (root / "check.py").write_text(check)
    fake = DynamicProposal(replacement)
    monkeypatch.setattr("app.cognition.bootstrap.OpenRouterLLMClient.from_settings", lambda _: fake)
    config = settings(root)
    if not model:
        config = Settings(
            _env_file=None,
            OPENROUTER_API_KEY="",
            OPENROUTER_MODEL="",
            SEARCH_PROVIDER="",
            ARTIFACT_ALLOWED_ROOTS=str(root),
            CODE_EXECUTION_ENABLED=True,
        )
    if max_model_calls is not None:
        config = config.model_copy(update={"cognitive_max_model_calls": max_model_calls})
    state = source_patch_state(
        "Repair the supplied function according to its independent check.",
        root / "source.py",
        root / "check.py",
        config,
    )
    result = build_cognitive_runtime(
        config, enable_source_patch=True, repair_lesson_loader=lambda: list(lessons)
    ).run_state(state)
    return result, fake


@pytest.fixture
def learned(tmp_path, monkeypatch):
    if not _docker_available():
        pytest.skip("requires configured pinned Docker sandbox")
    result, fake = run(tmp_path / "first", monkeypatch)
    assert result.status is CognitiveRunStatus.COMPLETED
    assert len(fake.requests) == 1
    lesson = learn_repair(result.state)
    assert lesson is not None and lesson.valid()
    return result, lesson


def test_changed_code_reuses_edit_but_executes_new_check_without_a_model(
    tmp_path, monkeypatch, learned
):
    first, lesson = learned
    source = SOURCE.replace("total", "invoice")
    check = "def verify(implementation):\n    assert implementation.invoice(11, 9) == 99\n    assert implementation.invoice(-2, 3) == -6\n"
    result, fake = run(tmp_path / "transfer", monkeypatch, source, check, [lesson], model=False)
    assert result.status is CognitiveRunStatus.COMPLETED
    assert not fake.requests and accumulated_usage(result.state).model_calls == 0
    event = next(e for e in result.state["events"] if e.event_type == EVENT)
    assert event.metadata["source_session_id"] == first.state["session_id"]
    assert event.metadata["prior_verdict_reused"] is False
    output = result.state["execution_outputs"][0].output
    assert output["patch_verified"] and output["baseline_failed"]
    assert output["source_snapshot_sha256"] != lesson.source_sha256
    assert output["check_snapshot_sha256"] != lesson.check_sha256
    assert (tmp_path / "transfer/source.py").read_text() == source


@pytest.mark.parametrize("vacuous", [False, True])
def test_wrong_transfer_is_falsified_by_current_check(tmp_path, monkeypatch, learned, vacuous):
    _, lesson = learned
    check = "def verify(implementation):\n    assert implementation.total(5, 3) == 2\n"
    if vacuous:
        check = "def verify(implementation):\n    assert True\n"
    result, _ = run(tmp_path / "negative", monkeypatch, SOURCE, check, [lesson], model=False)
    assert result.status is not CognitiveRunStatus.COMPLETED
    assert not result.state["final_answer"]
    assert result.state["execution_outputs"][0].output["patch_verified"] is False
    assert result.state["verification"] is not None and not result.state["verification"].passed
    assert any(decision.selected.capability == "verifier_factory" for decision in result.decisions)
    assert learn_repair(result.state) is None


@pytest.mark.parametrize("change", ["poison", "stale", "ambiguous", "absent"])
def test_unusable_memory_falls_back_to_model(tmp_path, monkeypatch, learned, change):
    _, lesson = learned
    if change == "poison":
        lessons = [lesson.model_copy(update={"new_text": "0"})]
    elif change == "stale":
        candidate = lesson.model_copy(update={"sandbox_version": "obsolete"})
        lessons = [candidate.model_copy(update={"integrity_hash": candidate.digest()})]
    elif change == "ambiguous":
        candidate = lesson.model_copy(update={"new_text": "count - unit_price"})
        lessons = [lesson, candidate.model_copy(update={"integrity_hash": candidate.digest()})]
    else:
        lessons = []
    result, fake = run(tmp_path / change, monkeypatch, lessons=lessons)
    assert result.status is CognitiveRunStatus.COMPLETED
    assert len(fake.requests) == 1
    assert not any(e.event_type == EVENT for e in result.state["events"])


@pytest.mark.parametrize(
    "failure", ["verification", "reflection", "snapshot", "baseline", "version", "edit"]
)
def test_failed_or_unbound_work_cannot_be_learned(learned, failure):
    result, _ = learned
    state = copy.deepcopy(result.state)
    if failure == "verification":
        state["verification"].passed = False
    elif failure == "reflection":
        state["reflection"] = None
    elif failure == "snapshot":
        state["execution_outputs"][0].output["check_snapshot_sha256"] = "mutated"
    elif failure == "baseline":
        state["execution_outputs"][0].output["baseline_failed"] = False
    elif failure == "edit":
        state["plan"][0].params["new_text"] = "count - unit_price"
    else:
        for event in state["events"]:
            if (
                event.event_type == "capability_observation"
                and event.metadata.get("capability") == "source_patch_sandbox"
            ):
                event.metadata["capability_version"] = "obsolete"
    assert learn_repair(state) is None
