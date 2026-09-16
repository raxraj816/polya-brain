"""Real database races and session recovery at the resource admission boundary."""

from __future__ import annotations

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from test_sessions_service import awaiting_runner, failing_runner, successful_runner

from app.config import Settings, get_settings
from app.db.models import ClarificationRequest, ProblemSession, RunAdmission
from app.db.session import create_database_engine, create_session_factory
from app.models.contracts import ProductMode
from app.sessions import PolyaSessionService, SessionConflictError, SessionRunFailedError
from app.sessions.admission import RunAdmissionPolicy, UsageLimitError

pytestmark = pytest.mark.skipif(
    os.environ.get("POLYABRAIN_RUN_DB_TESTS") != "1", reason="requires migrated Postgres"
)


@pytest.fixture
def context(monkeypatch):
    factory = create_session_factory(create_database_engine(get_settings().database_url))
    # Each test gets a future day so existing scratch data cannot affect its daily cap.
    now = datetime(2050, 1, 1, tzinfo=UTC) + timedelta(days=uuid4().int % 1000000)
    monkeypatch.setattr("app.sessions.admission.utc_now", lambda: now)
    owners = [str(uuid4()), str(uuid4())]
    settings = Settings(
        _env_file=None,
        POLYABRAIN_DAILY_USER_RUN_LIMIT=2,
        POLYABRAIN_DAILY_GLOBAL_RUN_LIMIT=3,
        POLYABRAIN_CONCURRENT_USER_RUN_LIMIT=1,
        POLYABRAIN_CONCURRENT_GLOBAL_RUN_LIMIT=2,
    )
    yield factory, settings, owners, now
    with factory() as db:
        db.execute(delete(RunAdmission).where(RunAdmission.user_id.in_(owners)))
        db.execute(delete(ProblemSession).where(ProblemSession.user_id.in_(owners)))
        db.commit()


def service(db, settings, owner, runner=successful_runner):
    db.info["owner_id"] = owner
    return PolyaSessionService(
        db, runner=runner, admission_policy=RunAdmissionPolicy(db, settings, owner)
    )


def create(svc):
    return svc.create_session(
        raw_input="What is 17 * 6?", mode=ProductMode.INVESTIGATE, domain=None
    ).id


def test_daily_limit_is_before_dispatch_and_preserves_created_session(context):
    factory, settings, owners, _ = context
    calls = []

    def runner(raw_input, *, session_id):
        calls.append(session_id)
        return successful_runner(raw_input, session_id=session_id)

    with factory() as db:
        svc = service(db, settings, owners[0], runner)
        for _ in range(2):
            svc.run_session(create(svc))
        denied_id = create(svc)
        with pytest.raises(UsageLimitError, match="daily run allowance"):
            svc.run_session(denied_id)
        assert len(calls) == 2
        assert db.get(ProblemSession, denied_id).status == "created"
        rows = list(db.scalars(select(RunAdmission).where(RunAdmission.user_id == owners[0])))
        assert len(rows) == 2 and all(row.finished_at for row in rows)
        assert all(
            row.resource_limits["model_calls"] == settings.cognitive_max_model_calls for row in rows
        )
        snapshot = RunAdmissionPolicy(db, settings, owners[0]).snapshot()
        assert snapshot["daily_remaining"] == 0 and snapshot["active_runs"] == 0


def test_denied_resume_preserves_question_and_answer_can_be_retried(context):
    factory, settings, owners, _ = context
    settings.daily_user_run_limit = 1
    with factory() as db:
        svc = service(db, settings, owners[0], awaiting_runner)
        session_id = create(svc)
        svc.run_session(session_id)
        with pytest.raises(UsageLimitError):
            svc.respond_to_session(session_id, "Use the new success criterion")
        assert db.get(ProblemSession, session_id).status == "awaiting_user_input"
        clarification = db.scalar(
            select(ClarificationRequest).where(ClarificationRequest.session_id == session_id)
        )
        assert clarification.status == "pending" and clarification.answer is None
        settings.daily_user_run_limit = 2
        svc.respond_to_session(session_id, "Use the new success criterion")
        db.refresh(clarification)
        assert clarification.status == "answered"
        assert RunAdmissionPolicy(db, settings, owners[0]).snapshot()["daily_used"] == 2


def test_failure_charges_allowance_but_releases_slot_and_conflicts_do_not_charge(context):
    factory, settings, owners, _ = context
    with factory() as db:
        svc = service(db, settings, owners[0], failing_runner)
        session_id = create(svc)
        with pytest.raises(SessionRunFailedError):
            svc.run_session(session_id)
        with pytest.raises(SessionConflictError):
            svc.run_session(session_id)
        snap = RunAdmissionPolicy(db, settings, owners[0]).snapshot()
        assert snap["daily_used"] == 1 and snap["active_runs"] == 0


def test_concurrent_claims_across_database_connections_admit_only_one(context):
    factory, settings, owners, _ = context
    with factory() as db:
        svc = service(db, settings, owners[0])
        ids = [create(svc), create(svc)]
    barrier = Barrier(2)

    def attempt(session_id):
        with factory() as db:
            barrier.wait(timeout=5)
            try:
                result = RunAdmissionPolicy(db, settings, owners[0]).acquire(session_id)
                db.commit()
                return result
            except UsageLimitError:
                db.rollback()
                return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, ids))
    assert sum(item is not None for item in outcomes) == 1


def test_global_daily_cap_and_active_slots_survive_midnight(context, monkeypatch):
    factory, settings, owners, now = context
    settings.daily_global_run_limit = 1
    with factory() as db:
        svc = service(db, settings, owners[0])
        first_id = create(svc)
        policy = RunAdmissionPolicy(db, settings, owners[0])
        policy.acquire(first_id)
        db.commit()  # Simulate a worker disappearing after admission; no automatic refund.
        svc2 = service(db, settings, owners[1])
        second_id = create(svc2)
        with pytest.raises(UsageLimitError, match="service's daily"):
            svc2.run_session(second_id)
        assert db.get(ProblemSession, second_id).status == "created"
        monkeypatch.setattr("app.sessions.admission.utc_now", lambda: now + timedelta(days=1))
        settings.concurrent_global_run_limit = 1
        with pytest.raises(UsageLimitError, match="concurrent run limit"):
            svc2.run_session(second_id)
        assert policy.snapshot()["daily_used"] == 0
        assert policy.snapshot()["active_runs"] == 1


def test_interrupted_worker_keeps_slot_until_operator_review(context):
    factory, settings, owners, _ = context

    def interrupted(raw_input, *, session_id):
        raise KeyboardInterrupt("simulated worker interruption")

    with factory() as db:
        svc = service(db, settings, owners[0], interrupted)
        session_id = create(svc)
        with pytest.raises(KeyboardInterrupt):
            svc.run_session(session_id)
        assert RunAdmissionPolicy(db, settings, owners[0]).snapshot()["active_runs"] == 1


def test_operator_release_requires_explicit_confirmation_and_keeps_daily_charge(context):
    factory, settings, owners, _ = context
    with factory() as db:
        svc = service(db, settings, owners[0])
        session_id = create(svc)
        record = db.get(ProblemSession, session_id)
        record.status = "running"
        policy = RunAdmissionPolicy(db, settings, owners[0])
        admission_id = policy.acquire(session_id)
        db.commit()
        command = [
            sys.executable,
            str(Path("scripts/manage_run_admissions.py")),
            "--release",
            str(admission_id),
        ]
        rejected = subprocess.run(command, capture_output=True, text=True)
        assert rejected.returncode != 0
        assert "confirm-worker-stopped" in rejected.stderr
        assert policy.snapshot()["active_runs"] == 1
        released = subprocess.run(
            [*command, "--confirm-worker-stopped"], capture_output=True, text=True
        )
        assert released.returncode == 0, released.stderr
        db.expire_all()
        assert db.get(ProblemSession, session_id).status == "failed"
        assert policy.snapshot()["active_runs"] == 0
        assert policy.snapshot()["daily_used"] == 1
        assert db.get(RunAdmission, admission_id).outcome == "operator_released"
