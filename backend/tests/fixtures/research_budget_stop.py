"""Seed local research-stop reports with no network or paid providers."""

import os

from test_research_budget_stop import public_state, registry

from app.cognition import CognitiveRuntime, CognitiveSessionRunner
from app.config import get_settings
from app.db.session import create_database_engine, create_session_factory
from app.models.contracts import ProductMode
from app.sessions.service import PolyaSessionService


def seed() -> str:
    cause = os.getenv("POLYABRAIN_RESEARCH_STOP_CAUSE", "budget")
    if cause == "budget":
        state, capabilities = public_state(), registry()
    else:
        from test_research_unavailable_stop import blocked_research

        if cause not in {"missing", "failed", "privacy"}:
            raise ValueError("Unsupported research-stop fixture cause")
        state, capabilities, _ = blocked_research(cause)

    def run(raw_input, *, session_id):
        state["session_id"] = session_id
        state["raw_input"] = raw_input
        return CognitiveSessionRunner(CognitiveRuntime(capabilities), initial_state=state)(
            raw_input, session_id=session_id
        )

    engine = create_database_engine(get_settings().database_url)
    with create_session_factory(engine)() as db:
        service = PolyaSessionService(db, runner=run)
        session = service.create_session(
            raw_input="Investigate public evidence within the existing acquisition budget.",
            mode=ProductMode.INVESTIGATE,
            domain=None,
        )
        service.run_session(session.id)
        session_id = str(session.id)
    engine.dispose()
    return session_id


if __name__ == "__main__":
    print(seed())
