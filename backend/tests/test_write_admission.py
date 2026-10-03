"""Real multi-connection races and rollback at the write admission boundary."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select, text
from test_auth import configuration

from app.config import get_settings
from app.db.models import HumanFeedback, ProblemSession
from app.db.session import create_database_engine, create_session_factory
from app.sessions.admission import UsageLimitError
from app.sessions.write_admission import FeedbackCapacityError, WriteAdmissionPolicy, database_now

pytestmark = pytest.mark.skipif(
    os.environ.get("POLYABRAIN_RUN_DB_TESTS") != "1", reason="requires migrated Postgres"
)


@pytest.fixture
def context(monkeypatch):
    engine = create_database_engine(get_settings().database_url)
    factory = create_session_factory(engine)
    now = datetime(2050, 1, 1, 12, tzinfo=UTC) + timedelta(days=uuid4().int % 1000000)
    monkeypatch.setattr("app.sessions.write_admission.database_now", lambda db: now)
    owners = [str(uuid4()), str(uuid4())]
    settings = configuration(
        POLYABRAIN_DAILY_USER_SESSION_LIMIT=2,
        POLYABRAIN_DAILY_GLOBAL_SESSION_LIMIT=3,
        POLYABRAIN_DAILY_USER_FEEDBACK_LIMIT=2,
        POLYABRAIN_DAILY_GLOBAL_FEEDBACK_LIMIT=3,
    )
    targets = []
    with factory() as db:
        for owner in owners:
            record = ProblemSession(
                user_id=owner,
                raw_input="Existing target",
                status="completed",
                created_at=now - timedelta(days=1),
            )
            db.add(record)
            db.flush()
            targets.append(record.id)
        db.commit()
    yield factory, settings, owners, targets, now
    with factory() as db:
        db.execute(delete(ProblemSession).where(ProblemSession.user_id.in_(owners)))
        db.commit()
    engine.dispose()


def write(db, settings, owner, kind, target):
    db.info["owner_id"] = owner
    when = WriteAdmissionPolicy(db, settings).acquire(kind, session_id=target)
    record = (
        ProblemSession(user_id=owner, raw_input="New problem", created_at=when)
        if kind == "session"
        else HumanFeedback(session_id=target, feedback_type="useful", created_at=when)
    )
    db.add(record)
    db.flush()
    return record.id


@pytest.mark.parametrize("kind", ["session", "feedback"])
@pytest.mark.parametrize("same_owner", [True, False])
def test_concurrent_last_slot_is_atomic_for_user_and_global_caps(context, kind, same_owner):
    factory, settings, owners, targets, _ = context
    setattr(settings, f"daily_{'user' if same_owner else 'global'}_{kind}_limit", 1)
    barrier = Barrier(4)

    def attempt(i):
        owner_index = 0 if same_owner else i % 2
        with factory() as db:
            barrier.wait(timeout=5)
            try:
                result = write(db, settings, owners[owner_index], kind, targets[owner_index])
                db.commit()
                return result
            except UsageLimitError:
                db.rollback()
                return None

    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = list(pool.map(attempt, range(4)))
    assert sum(result is not None for result in outcomes) == 1


@pytest.mark.parametrize("kind", ["session", "feedback"])
def test_rollback_does_not_charge_and_new_connection_keeps_committed_charge(context, kind):
    factory, settings, owners, targets, _ = context
    setattr(settings, f"daily_user_{kind}_limit", 1)
    with factory() as db:
        write(db, settings, owners[0], kind, targets[0])
        db.rollback()
        write(db, settings, owners[0], kind, targets[0])
        db.commit()
    engine = create_database_engine(get_settings().database_url)
    with create_session_factory(engine)() as db:
        with pytest.raises(UsageLimitError):
            write(db, settings, owners[0], kind, targets[0])
        db.rollback()
        write(db, settings, owners[1], kind, targets[1])
        db.commit()
    engine.dispose()


@pytest.mark.parametrize("kind", ["session", "feedback"])
def test_utc_rollover_and_global_daily_cap(context, kind, monkeypatch):
    factory, settings, owners, targets, now = context
    setattr(settings, f"daily_global_{kind}_limit", 1)
    with factory() as db:
        write(db, settings, owners[0], kind, targets[0])
        db.commit()
        with pytest.raises(UsageLimitError, match="service's daily") as failure:
            write(db, settings, owners[1], kind, targets[1])
        assert failure.value.retry_after == 43200
        db.rollback()
        monkeypatch.setattr(
            "app.sessions.write_admission.database_now", lambda db: now + timedelta(days=1)
        )
        write(db, settings, owners[1], kind, targets[1])
        db.commit()


def test_database_clock_is_utc_even_when_connection_timezone_is_not(context):
    factory, _, _, _, _ = context
    with factory() as db:
        db.execute(text("SET LOCAL TIME ZONE 'Asia/Kolkata'"))
        assert database_now(db).tzinfo == UTC


@pytest.mark.parametrize("kind", ["session", "feedback"])
@pytest.mark.parametrize("scope", ["user", "global"])
def test_zero_closes_that_authenticated_write_path(context, kind, scope):
    factory, settings, owners, targets, _ = context
    setattr(settings, f"daily_{scope}_{kind}_limit", 0)
    with factory() as db:
        with pytest.raises(UsageLimitError):
            write(db, settings, owners[0], kind, targets[0])
        db.rollback()


def test_per_session_feedback_cap_survives_daily_reset(context):
    factory, settings, owners, targets, now = context
    with factory() as db:
        db.add_all(
            [
                HumanFeedback(
                    session_id=targets[0],
                    feedback_type="useful",
                    created_at=now - timedelta(days=1),
                )
                for _ in range(100)
            ]
        )
        db.commit()
        with pytest.raises(FeedbackCapacityError):
            write(db, settings, owners[0], "feedback", targets[0])
        db.rollback()
        assert (
            db.scalar(
                select(func.count())
                .select_from(HumanFeedback)
                .where(HumanFeedback.session_id == targets[0])
            )
            == 100
        )


def test_policy_rejects_missing_owner_and_cross_account_feedback(context):
    factory, settings, owners, targets, _ = context
    with factory() as db:
        with pytest.raises(ValueError, match="authenticated owner"):
            WriteAdmissionPolicy(db, settings).acquire("session")
        db.info["owner_id"] = owners[0]
        with pytest.raises(ValueError, match="outside this owner"):
            WriteAdmissionPolicy(db, settings).acquire("feedback", session_id=targets[1])


def test_operator_local_mode_does_not_apply_shared_service_quotas(context):
    factory, settings, _, targets, _ = context
    settings.auth_required = False
    settings.daily_global_session_limit = 0
    settings.daily_global_feedback_limit = 0
    with factory() as db:
        policy = WriteAdmissionPolicy(db, settings)
        assert policy.acquire("session")
        assert policy.acquire("feedback", session_id=targets[0])
