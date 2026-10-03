"""A provider survives SIGKILL; a missing response must stay an uncertain outcome."""

import json
import os
import selectors
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from fixtures.process_loss_worker import settings
from sqlalchemy import delete, select

from app.config import get_settings
from app.db.models import ProblemSession, RunAdmission
from app.db.session import create_database_engine, create_session_factory
from app.investigator.recovery import RecoveryError, RecoveryStore
from app.models.contracts import ProductMode
from app.sessions import SessionConflictError
from app.sessions.admission import RunAdmissionPolicy, UsageLimitError
from app.sessions.service import PolyaSessionService

ROOT = Path(__file__).resolve().parents[2]
WORKER = Path(__file__).parent / "fixtures/remote_completion_worker.py"


def event(process):
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        assert selector.select(timeout=15), "Child did not reach synchronization boundary"
        line = process.stdout.readline()
        assert line, "Child exited before synchronization"
        return json.loads(line)


@contextmanager
def child(root, kind, *args):
    env = {
        **os.environ,
        "PYTHONPATH": str(ROOT / "backend"),
        "OPENROUTER_API_KEY": "",
        "OPENROUTER_MODEL": "",
        "SEARCH_API_KEY": "",
        "SEARCH_PROVIDER": "",
    }
    log_path = root / f"{kind}-{len(list(root.glob(f'{kind}-*.stderr')))}.stderr"
    with log_path.open("x") as log:
        process = subprocess.Popen(
            [sys.executable, str(WORKER), kind, str(root), *args],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=log,
            text=True,
        )
        try:
            yield process, event(process)
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=10)
            process.stdout.close()


def kill_after_acceptance(caller, provider):
    assert event(provider) == {"event": "accepted"}
    caller.kill()
    assert caller.wait(timeout=10) == -signal.SIGKILL
    assert provider.poll() is None


def complete_provider(root, provider):
    assert not (root / "provider-completions.txt").exists()
    (root / "release-provider").touch()
    assert event(provider) == {"event": "completed"}
    assert provider.poll() is None
    assert (root / "provider-completions.txt").read_text().splitlines() == [
        "completed-after-worker-death"
    ]
    assert not (root / "caller-received.txt").exists()


def test_late_provider_completion_does_not_make_uncertain_checkpoint_replayable(tmp_path):
    with child(tmp_path, "provider") as (provider, address):
        with child(tmp_path, "local", address["url"]) as (caller, ready):
            kill_after_acceptance(caller, provider)
        store = RecoveryStore(tmp_path / "private")
        try:
            for phase in ("before_completion", "after_completion"):
                if phase == "after_completion":
                    complete_provider(tmp_path, provider)
                for _ in range(2):
                    with pytest.raises(RecoveryError, match="outcome and cost are unknown"):
                        store.load(ready["token"], ready["fingerprint"], None)
                assert store.connection.execute(
                    "SELECT in_flight, consumed FROM checkpoints WHERE token=?", (ready["token"],)
                ).fetchone() == (1, 0)
            assert (tmp_path / "provider-dispatches.txt").read_text().splitlines() == ["accepted"]
        finally:
            store.close()


@pytest.mark.skipif(
    os.getenv("POLYABRAIN_RUN_DB_TESTS") != "1", reason="requires migrated Postgres"
)
def test_late_provider_completion_does_not_release_admission_or_publish_success(tmp_path):
    engine = create_database_engine(get_settings().database_url)
    factory, owner, config = create_session_factory(engine), str(uuid4()), settings()
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
        with child(tmp_path, "provider") as (provider, address):
            with child(tmp_path, "api", address["url"], owner, str(ids[0])) as (caller, _ready):
                kill_after_acceptance(caller, provider)
            for phase in ("before_completion", "after_completion"):
                if phase == "after_completion":
                    complete_provider(tmp_path, provider)
                with factory() as db:
                    db.info["owner_id"] = owner
                    policy = RunAdmissionPolicy(db, config, owner)

                    def forbidden(*_args, **_kwargs):
                        pytest.fail("No duplicate dispatch is allowed")

                    service = PolyaSessionService(db, runner=forbidden, admission_policy=policy)
                    assert policy.snapshot()["daily_used"] == 1
                    assert policy.snapshot()["active_runs"] == 1
                    with pytest.raises(SessionConflictError):
                        service.run_session(ids[0])
                    with pytest.raises(UsageLimitError, match="active runs"):
                        service.run_session(ids[1])
                    report = service.get_report(ids[0])
                    assert report.final_conclusion is None
                    assert report.verification_status != "passed"
                    admission_id = db.scalar(
                        select(RunAdmission.id).where(RunAdmission.session_id == ids[0])
                    )
            assert (tmp_path / "provider-dispatches.txt").read_text().splitlines() == ["accepted"]
            released = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/manage_run_admissions.py"),
                    "--release",
                    str(admission_id),
                    "--confirm-worker-stopped",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            assert released.returncode == 0, released.stderr
            with factory() as db:
                db.info["owner_id"] = owner
                policy = RunAdmissionPolicy(db, config, owner)
                assert policy.snapshot()["daily_used"] == 1
                assert policy.snapshot()["active_runs"] == 0
                report = PolyaSessionService(db).get_report(ids[0])
                assert report.verification_status == "operator_stopped"
                assert db.get(RunAdmission, admission_id).outcome == "operator_released"
            assert (tmp_path / "provider-dispatches.txt").read_text().splitlines() == ["accepted"]
    finally:
        with factory() as db:
            db.execute(delete(RunAdmission).where(RunAdmission.user_id == owner))
            db.execute(delete(ProblemSession).where(ProblemSession.user_id == owner))
            db.commit()
        engine.dispose()


@pytest.mark.skipif(
    os.getenv("POLYABRAIN_RUN_DB_TESTS") != "1", reason="requires migrated Postgres"
)
def test_killed_http_backend_restarts_with_uncertain_run_and_retained_allowance(tmp_path):
    engine = create_database_engine(get_settings().database_url)
    factory, owner = create_session_factory(engine), str(uuid4())

    def wait_ready(url):
        deadline = time.monotonic() + 10
        while True:
            try:
                response = httpx.get(url + "/health", timeout=1, trust_env=False)
                if response.status_code == 200:
                    return
            except httpx.TransportError:
                pass
            assert time.monotonic() < deadline, "HTTP backend did not start"
            time.sleep(0.02)

    try:
        with child(tmp_path, "provider") as (provider, remote):
            with child(tmp_path, "http", remote["url"], owner) as (backend, address):
                wait_ready(address["url"])
                with httpx.Client(base_url=address["url"], trust_env=False, timeout=15) as client:
                    ids = []
                    for _ in range(2):
                        created = client.post(
                            "/api/v1/sessions", json={"raw_input": "What is 17 * 6?"}
                        )
                        assert created.status_code == 201, created.text
                        ids.append(created.json()["id"])
                    with ThreadPoolExecutor(max_workers=1) as pool:
                        pending = pool.submit(client.post, f"/api/v1/sessions/{ids[0]}/run")
                        kill_after_acceptance(backend, provider)
                        with pytest.raises(httpx.TransportError):
                            pending.result(timeout=5)
            # This is a fresh Uvicorn process, not a new client in the original app.
            with child(tmp_path, "http", remote["url"], owner) as (_replacement, recovered):
                wait_ready(recovered["url"])
                with httpx.Client(base_url=recovered["url"], trust_env=False, timeout=10) as client:
                    for phase in ("before_completion", "after_completion"):
                        if phase == "after_completion":
                            complete_provider(tmp_path, provider)
                        session = client.get(f"/api/v1/sessions/{ids[0]}")
                        assert session.status_code == 200 and session.json()["status"] == "running"
                        report = client.get(f"/api/v1/sessions/{ids[0]}/report")
                        assert report.status_code == 200
                        assert report.json()["final_conclusion"] is None
                        assert report.json()["verification_status"] != "passed"
                        assert (
                            "refresh status before retrying"
                            in report.json()["recommended_next_action"]
                        )
                        usage = client.get("/api/v1/usage").json()
                        assert usage["active_runs"] == usage["daily_used"] == 1
                        assert client.post(f"/api/v1/sessions/{ids[0]}/run").status_code == 409
                        assert client.post(f"/api/v1/sessions/{ids[1]}/run").status_code == 429
                    with factory() as db:
                        admission = db.scalar(
                            select(RunAdmission.id).where(RunAdmission.user_id == owner)
                        )
                    released = subprocess.run(
                        [
                            sys.executable,
                            str(ROOT / "scripts/manage_run_admissions.py"),
                            "--release",
                            str(admission),
                            "--confirm-worker-stopped",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    assert released.returncode == 0, released.stderr
                    report = client.get(f"/api/v1/sessions/{ids[0]}/report").json()
                    assert report["verification_status"] == "operator_stopped"
                    assert (
                        "does not establish external completion or cost"
                        in report["recommended_next_action"]
                    )
                    assert client.get(f"/api/v1/sessions/{ids[0]}").json()["status"] == "failed"
                    usage = client.get("/api/v1/usage").json()
                    assert usage["active_runs"] == 0 and usage["daily_used"] == 1
                    assert (tmp_path / "provider-dispatches.txt").read_text().splitlines() == [
                        "accepted"
                    ]
    finally:
        with factory() as db:
            db.execute(delete(RunAdmission).where(RunAdmission.user_id == owner))
            db.execute(delete(ProblemSession).where(ProblemSession.user_id == owner))
            db.commit()
        engine.dispose()
