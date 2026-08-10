#!/usr/bin/env python3
"""Run the Chapter 19 twenty-query cross-domain semantic-memory proof."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for import_path in (ROOT, BACKEND):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from app.config import get_settings  # noqa: E402
from app.db.session import create_database_engine, create_session_factory  # noqa: E402
from app.memory import SQLAlchemyMemoryRepository  # noqa: E402

CASES = (
    ("isolate an unknown equation and verify by substitution", "math_reasoning.md"),
    ("exact arithmetic units and incompatible dimensions", "math_reasoning.md"),
    ("optimization boundary cases and global optimum", "math_reasoning.md"),
    ("probability base rate and conditioning information", "math_reasoning.md"),
    ("minimal reproducible bug expected observed behavior", "software_debugging.md"),
    ("bisect last known good first known bad change", "software_debugging.md"),
    ("choose logs metrics traces as evidence", "software_debugging.md"),
    ("verify fix with reproduction regression boundaries", "software_debugging.md"),
    ("official documentation primary source specification", "technical_research.md"),
    ("independent sources corroborate factual claim", "technical_research.md"),
    ("freshness product version applicability boundary", "technical_research.md"),
    ("resolve contradictory sources insufficient evidence", "technical_research.md"),
    ("define baseline absolute relative change", "data_analysis.md"),
    ("missing values duplicates distribution data quality", "data_analysis.md"),
    ("segment aggregate movement sample size", "data_analysis.md"),
    ("randomized controlled experiment causal question", "data_analysis.md"),
    ("clarify ambiguous real goal success criteria", "problem_solving_playbooks.md"),
    ("decompose dependencies blockers reversible actions", "problem_solving_playbooks.md"),
    ("compare hypotheses evidence falsification verification cost", "problem_solving_playbooks.md"),
    ("verify reflect contradictions stop insufficient evidence", "problem_solving_playbooks.md"),
)


def main() -> None:
    session_factory = create_session_factory(create_database_engine(get_settings().database_url))
    failures: list[str] = []
    with session_factory() as session:
        repository = SQLAlchemyMemoryRepository(session)
        for query, expected_source in CASES:
            results = repository.search_semantic(
                query,
                limit=3,
                source_type="curated_product_knowledge",
                minimum_reliability=0.8,
                minimum_similarity=0.08,
            )
            if not results or expected_source not in (results[0].source_uri or ""):
                actual = results[0].source_uri if results else "no result"
                failures.append(f"{query!r}: expected {expected_source}, got {actual}")
    if failures:
        raise SystemExit("Memory query proof failed:\n" + "\n".join(failures))
    print(f"Semantic memory proof passed: {len(CASES)} cross-domain queries.")


if __name__ == "__main__":
    main()
