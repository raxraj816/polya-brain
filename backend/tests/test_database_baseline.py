"""Database baseline integration tests."""

import os

import pytest

from app.config import get_settings
from app.db.session import create_database_engine
from app.db.smoke import assert_database_baseline, can_seed_database


@pytest.mark.skipif(
    os.environ.get("POLYABRAIN_RUN_DB_TESTS") != "1",
    reason="set POLYABRAIN_RUN_DB_TESTS=1 with a migrated Postgres/pgvector database",
)
def test_chapter_4_database_baseline_supports_seed_graph_and_vector_storage() -> None:
    engine = create_database_engine(get_settings().database_url)

    assert_database_baseline(engine, allow_seed=True)


def test_database_smoke_seed_guard_blocks_non_local_environments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("POLYABRAIN_ALLOW_DB_SEED", raising=False)

    assert can_seed_database("local") is True
    assert can_seed_database("test") is True
    assert can_seed_database("production") is False


def test_database_smoke_seed_guard_allows_explicit_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POLYABRAIN_ALLOW_DB_SEED", "1")

    assert can_seed_database("production") is True
