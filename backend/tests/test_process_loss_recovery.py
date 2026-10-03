"""Actual SIGKILL probes; exception unwinding must not supply crash durability."""

import json
import os
import selectors
import signal
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import pytest
from fixtures.process_loss_worker import settings
from sqlalchemy import delete, select

from app.cognition.bootstrap import build_cognitive_runtime
from app.cognition.session_runner import CognitiveSessionRunner
from app.cognition.task_model import accumulated_usage, configured_budget
from app.config import get_settings
from app.db.models import ProblemSession, RunAdmission
from app.db.session import create_database_engine, create_session_factory
from app.investigator.recovery import RecoveryError, RecoveryStore
from app.models.contracts import ProductMode
from app.sessions import SessionConflictError
from app.sessions.admission import RunAdmissionPolicy, UsageLimitError
from app.sessions.service import PolyaSessionService

ROOT = Path(__file__).resolve().parents[2]
WORKER = Path(__file__).parent / "fixtures/process_loss_worker.py"


@contextmanager
def worker(root, kind, phase, *arguments):
    env = {
        **os.environ,
        "PYTHONPATH": str(ROOT / "backend"),
        "OPENROUTER_API_KEY": "",
        "OPENROUTER_MODEL": "",
        "SEARCH_API_KEY": "",
        "SEARCH_PROVIDER": "",
    }
    with (root / "worker.stderr").open("w") as log:
        process = subprocess.Popen(
            [sys.executable, str(WORKER), kind, str(root), phase, *map(str, arguments)],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=log,
            text=True,
        )
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                assert selector.select(timeout=15), "Worker did not reach the fault boundary"
                line = process.stdout.readline()
                assert line, (root / "worker.stderr").read_text()
            yield process, json.loads(line)
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=10)
            process.stdout.close()


def kill(process):
    process.kill()
    assert process.wait(timeout=10) == -signal.SIGKILL


@pytest.mark.parametrize("phase", ["before_dispatch", "in_dispatch", "before_result_save"])
def test_sigkill_uncertain_action_refuses_replay_without_exception_cleanup(tmp_path, phase):
    with worker(tmp_path, "local", phase) as (process, ready):
        kill(process)
    store = RecoveryStore(tmp_path / "private")
    try:
        for _ in range(2):
            with pytest.raises(RecoveryError, match="outcome and cost are unknown"):
                store.load(ready["token"], ready["fingerprint"], None)
        row = store.connection.execute(
            "SELECT in_flight, consumed FROM checkpoints WHERE token=?", (ready["token"],)
        ).fetchone()
        assert row == (1, 0)
        dispatched = (
            (tmp_path / "dispatches.txt").read_text().splitlines()
            if (tmp_path / "dispatches.txt").exists()
            else []
        )
        assert dispatched == ([] if phase == "before_dispatch" else ["calculator"])
        completed = (
            (tmp_path / "completed.txt").read_text().splitlines()
            if (tmp_path / "completed.txt").exists()
            else []
        )
        assert completed == (["calculator"] if phase == "before_result_save" else [])
    finally:
        store.close()


def test_sigkill_safe_checkpoint_releases_lease_and_continues_without_repeating_action(tmp_path):
    with worker(tmp_path, "local", "safe_boundary") as (process, ready):
        competitor = RecoveryStore(tmp_path / "private")
        try:
            with pytest.raises(RecoveryError, match="still running"):
                competitor.load(ready["token"], ready["fingerprint"], None)
        finally:
            competitor.close()
        kill(process)
    store = RecoveryStore(tmp_path / "private")
    try:
        saved = store.load(ready["token"], ready["fingerprint"], None)
        child = store.create(ready["fingerprint"])
        store.initialize(child, saved, ready["token"])
        result = build_cognitive_runtime(settings()).run_state(
            saved, checkpoint=lambda state, in_flight: store.save(child, state, in_flight)
        )
        store.finish(child, result)
        assert result.status.value == "completed"
        assert result.state["final_answer"] == "17 * 6 = 102."
        assert configured_budget(result.state) == configured_budget(saved)
        assert accumulated_usage(result.state).normalized_cost >= ready["usage"]["normalized_cost"]
        observations = [
            e
            for e in result.state["events"]
            if e.event_type == "capability_observation"
            and e.metadata.get("capability") == "calculator"
        ]
        assert len(observations) == 1
        assert (tmp_path / "dispatches.txt").read_text().splitlines() == ["calculator"]
        with pytest.raises(RecoveryError, match="already been resumed"):
            store.load(ready["token"], ready["fingerprint"], None)
        with pytest.raises(RecoveryError, match="terminal"):
            store.load(child, ready["fingerprint"], None)
    finally:
        store.close()


@pytest.mark.skipif(
    os.getenv("POLYABRAIN_RUN_DB_TESTS") != "1", reason="requires migrated Postgres"
)
@pytest.mark.parametrize("phase", ["admitted_before_result", "terminal_before_release"])
def test_sigkill_api_admission_requires_operator_release_and_never_refunds(tmp_path, phase):
    engine = create_database_engine(get_settings().database_url)
    factory = create_session_factory(engine)
    owner = str(uuid4())
    config = settings()
    try:
        with factory() as db:
            db.info["owner_id"] = owner
            service = PolyaSessionService(db)
            ids = [
                service.create_session(
                    raw_input="What is 17 * 6?", mode=ProductMode.INVESTIGATE, domain=None
                ).id
                for _ in range(2)
            ]
        with worker(tmp_path, "api", phase, owner, ids[0]) as (process, _ready):
            kill(process)
        with factory() as db:
            db.info["owner_id"] = owner
            policy = RunAdmissionPolicy(db, config, owner)
            service = PolyaSessionService(
                db,
                runner=lambda *_args, **_kwargs: pytest.fail(
                    "Interrupted admission must prevent dispatch"
                ),
                admission_policy=policy,
            )
            assert policy.snapshot()["daily_used"] == 1
            assert policy.snapshot()["active_runs"] == 1
            with pytest.raises(UsageLimitError, match="active runs"):
                service.run_session(ids[1])
            with pytest.raises(SessionConflictError):
                service.run_session(ids[0])
            assert service.get_session(ids[1]).status == "created"
            before = service.get_report(ids[0]).model_dump(mode="json")
            if phase == "terminal_before_release":
                assert before["final_conclusion"] == "17 * 6 = 102."
                assert before["verification_status"] == "passed"
            else:
                assert before["final_conclusion"] is None
                assert before["verification_status"] != "passed"
            admission_id = db.scalar(
                select(RunAdmission.id).where(RunAdmission.session_id == ids[0])
            )
        command = [
            sys.executable,
            str(ROOT / "scripts/manage_run_admissions.py"),
            "--release",
            str(admission_id),
        ]
        refused = subprocess.run(command, capture_output=True, text=True, timeout=10)
        assert refused.returncode != 0 and "confirm-worker-stopped" in refused.stderr
        released = subprocess.run(
            [*command, "--confirm-worker-stopped"], capture_output=True, text=True, timeout=10
        )
        assert released.returncode == 0, released.stderr
        with factory() as db:
            db.info["owner_id"] = owner
            policy = RunAdmissionPolicy(db, config, owner)
            service = PolyaSessionService(
                db,
                runner=CognitiveSessionRunner(build_cognitive_runtime(config)),
                admission_policy=policy,
            )
            assert policy.snapshot()["active_runs"] == 0
            assert policy.snapshot()["daily_used"] == 1
            after = service.get_report(ids[0]).model_dump(mode="json")
            if phase == "terminal_before_release":
                assert after == before
            else:
                assert service.get_session(ids[0]).status == "failed"
                assert after["verification_status"] == "operator_stopped"
            service.run_session(ids[1])
            assert policy.snapshot()["daily_used"] == 2
            assert policy.snapshot()["active_runs"] == 0
            assert db.get(RunAdmission, admission_id).outcome == "operator_released"
        assert (tmp_path / "dispatches.txt").read_text().splitlines() == [str(ids[0])]
    finally:
        with factory() as db:
            db.execute(delete(RunAdmission).where(RunAdmission.user_id == owner))
            db.execute(delete(ProblemSession).where(ProblemSession.user_id == owner))
            db.commit()
        engine.dispose()
