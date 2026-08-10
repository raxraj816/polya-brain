#!/usr/bin/env python3
"""Ingest the governed Chapter 19 knowledge seed into semantic memory."""

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

KNOWLEDGE_SOURCES = {
    "math_reasoning.md": "mathematics",
    "software_debugging.md": "software_debugging",
    "technical_research.md": "technical_research",
    "data_analysis.md": "data_analysis",
    "problem_solving_playbooks.md": "general_problem_solving",
}


def main() -> None:
    session_factory = create_session_factory(create_database_engine(get_settings().database_url))
    ingested = 0
    with session_factory() as session:
        repository = SQLAlchemyMemoryRepository(session)
        for filename, domain in KNOWLEDGE_SOURCES.items():
            path = ROOT / "docs" / "knowledge" / filename
            chunks = repository.ingest_document(
                path.read_text(encoding="utf-8"),
                source_type="curated_product_knowledge",
                source_uri=f"repo://docs/knowledge/{filename}",
                reliability_score=0.85,
                domain=domain,
                tags=["seed", "problem_solving", domain],
                chunk_characters=700,
                admission_status="verified_seed",
            )
            ingested += len(chunks)
        session.commit()
    print(
        f"Governed knowledge seed ready: {ingested} chunks across {len(KNOWLEDGE_SOURCES)} sources."
    )


if __name__ == "__main__":
    main()
