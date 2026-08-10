"""Seed human-authored procedural playbooks without claiming verified success.

Revision ID: 20260809_0006
Revises: 20260809_0005
Create Date: 2026-08-09
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260809_0006"
down_revision: str | None = "20260809_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SEEDS = (
    (
        "solve-by-substitution",
        "math_reasoning",
        "unknown_variable",
        "calculate",
        "calculator",
        ["An equation and known values are explicit."],
        ["Isolate the unknown.", "Substitute known values.", "Verify by substitution."],
    ),
    (
        "verify-boundaries",
        "data_analysis",
        "boundary_condition",
        "measure",
        "measurement",
        ["Boundary conditions affect the conclusion."],
        ["Enumerate boundaries.", "Measure each boundary.", "Compare with criteria."],
    ),
    (
        "reproduce-bug",
        "software_debugging",
        "reproduction",
        "inspect",
        "inspector",
        ["A concrete failing behavior is available."],
        ["Record expected behavior.", "Reproduce minimally.", "Vary one condition."],
    ),
    (
        "search-official-docs",
        "technical_research",
        "external_fact",
        "search",
        "web_search",
        ["The answer depends on current external information."],
        ["Find the primary source.", "Cross-check independently.", "Record freshness."],
    ),
    (
        "compare-baselines",
        "data_analysis",
        "missing_metric",
        "measure",
        "measurement",
        ["A change claim requires a reference condition."],
        ["Define the baseline.", "Measure both conditions.", "Quantify the difference."],
    ),
    (
        "decompose-plan",
        "planning",
        "unresolved_unknown",
        "observe",
        "observer",
        ["The goal is too broad for one action."],
        ["Split by dependency.", "Identify blockers.", "Order verifiable milestones."],
    ),
    (
        "ask-clarifying-question",
        "general",
        "ambiguous_requirement",
        "clarify",
        "human_input",
        ["A user-owned decision boundary is missing."],
        ["Name the ambiguity.", "Ask one focused question.", "Resume with the answer."],
    ),
)


def upgrade() -> None:
    table = sa.table(
        "procedural_strategies",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String()),
        sa.column("problem_type", sa.String()),
        sa.column("gap_type", sa.String()),
        sa.column("action_type", sa.String()),
        sa.column("capability", sa.String()),
        sa.column("preconditions", postgresql.JSONB()),
        sa.column("steps", postgresql.JSONB()),
        sa.column("verified_successes", sa.Integer()),
        sa.column("verified_failures", sa.Integer()),
        sa.column("success_rate", sa.Float()),
        sa.column("source_session_ids", postgresql.JSONB()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(UTC)
    op.bulk_insert(
        table,
        [
            {
                "id": uuid4(),
                "name": name,
                "problem_type": problem_type,
                "gap_type": gap_type,
                "action_type": action_type,
                "capability": capability,
                "preconditions": preconditions,
                "steps": [{"instruction": step} for step in steps],
                "verified_successes": 0,
                "verified_failures": 0,
                "success_rate": 0.0,
                "source_session_ids": [],
                "created_at": now,
                "updated_at": now,
            }
            for name, problem_type, gap_type, action_type, capability, preconditions, steps in _SEEDS
        ],
    )


def downgrade() -> None:
    names = [item[0] for item in _SEEDS]
    table = sa.table("procedural_strategies", sa.column("name"))
    op.execute(table.delete().where(table.c.name.in_(names)))
