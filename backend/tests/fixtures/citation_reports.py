"""Seed isolated browser cases through real verification/persistence, with fake model outputs.

Run with PYTHONPATH=backend:backend/tests and a disposable DATABASE_URL.
This module is never imported by the application and exposes no fixture HTTP route.
"""

import json
import sys
from pathlib import Path

from sqlalchemy import func, select
from test_citation_provenance import SOURCE, citation_state, review

from app.config import get_settings
from app.db.models import EpisodicMemory
from app.db.session import create_database_engine, create_session_factory
from app.memory import SQLAlchemyMemoryRepository
from app.models.contracts import ProductMode
from app.sessions.service import PolyaSessionService


def seed(output: Path) -> None:
    engine = create_database_engine(get_settings().database_url)
    factory = create_session_factory(engine)
    cases = []
    for name, url, passed in [
        ("unadmitted_source", "https://invented.example/rule", False),
        ("missing_section", SOURCE + "#section-9.3.1", False),
        ("supported_locator_control", SOURCE + "#section-6.4.1", True),
    ]:
        candidate = f"The timeout is 37 ticks. [Manual]({url})"

        def runner(raw_input, *, session_id, candidate=candidate):
            state = citation_state()
            state["session_id"] = session_id
            state["raw_input"] = raw_input
            result, client = review(candidate, state=state)
            assert len(client.requests) == 1
            return result.state

        with factory() as db:
            service = PolyaSessionService(
                db, runner=runner, memory_repository=SQLAlchemyMemoryRepository(db)
            )
            session = service.create_session(
                raw_input=f"Citation browser fixture: {name}",
                mode=ProductMode.INVESTIGATE,
                domain=None,
            )
            service.run_session(session.id)
            report = service.get_report(session.id)
            assert (report.verification_status == "passed") is passed
            if not passed:
                assert session.final_answer is None and report.reflection is None
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(EpisodicMemory)
                        .where(EpisodicMemory.source_session_id == session.id)
                    )
                    == 0
                )
            cases.append(
                {
                    "name": name,
                    "id": str(session.id),
                    "passed": passed,
                    "candidate": candidate,
                    "report": report.model_dump(mode="json"),
                }
            )
    engine.dispose()
    output.write_text(
        json.dumps(
            {
                "scope": "Scripted model outputs through real kernel, database and report service; not live reasoning or whole-run recovery",
                "live_provider_calls": 0,
                "cases": cases,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    seed(Path(sys.argv[1]))
