"""Disposable subprocess fault fixture. Never loaded by the application."""

import json
import os
import signal
import sys
from pathlib import Path
from uuid import UUID, uuid4

from app.cognition.bootstrap import build_cognitive_runtime
from app.cognition.session_runner import CognitiveSessionRunner
from app.cognition.task_model import accumulated_usage
from app.config import Settings, get_settings
from app.db.session import create_database_engine, create_session_factory
from app.graph.state import create_initial_state
from app.investigator.recovery import RecoveryStore, runtime_fingerprint
from app.sessions.admission import RunAdmissionPolicy
from app.sessions.service import PolyaSessionService


def settings():
    return Settings(
        _env_file=None,
        OPENROUTER_API_KEY="",
        OPENROUTER_MODEL="",
        SEARCH_PROVIDER="",
        SEARCH_API_KEY="",
        COGNITIVE_MAX_MODEL_CALLS=0,
        POLYABRAIN_DAILY_USER_RUN_LIMIT=2,
        POLYABRAIN_DAILY_GLOBAL_RUN_LIMIT=100000,
        POLYABRAIN_CONCURRENT_USER_RUN_LIMIT=1,
        POLYABRAIN_CONCURRENT_GLOBAL_RUN_LIMIT=1000,
    )


def witness(path: Path, label: str):
    with path.open("a") as stream:
        stream.write(label + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def park(**metadata):
    print(json.dumps(metadata), flush=True)
    while True:
        signal.pause()


def local(root: Path, phase: str):
    config = settings()
    runtime = build_cognitive_runtime(config)
    store = RecoveryStore(root / "private")
    fingerprint = runtime_fingerprint(config)
    token = store.create(fingerprint)
    state = create_initial_state("What is 17 * 6?", session_id=str(uuid4()))
    store.initialize(token, state, None)
    calculator = runtime._registry.get("calculator")
    original = calculator.execute

    def ready():
        park(token=token, fingerprint=fingerprint, phase=phase)

    def execute(action, current):
        witness(root / "dispatches.txt", "calculator")
        if phase == "in_dispatch":
            ready()
        result = original(action, current)
        witness(root / "completed.txt", "calculator")
        return result

    calculator.execute = execute

    def checkpoint(current, in_flight):
        decision = next(
            (e for e in reversed(current["events"]) if e.event_type == "cognitive_action_decision"),
            None,
        )
        selected = decision.metadata["selected"]["capability"] if decision else None
        if not in_flight and selected == "calculator" and phase == "before_result_save":
            ready()  # The durable store must still have its in-flight marker.
        store.save(token, current, in_flight)
        if in_flight and selected == "calculator" and phase == "before_dispatch":
            ready()
        if not in_flight and selected == "calculator" and phase == "safe_boundary":
            park(
                token=token,
                fingerprint=fingerprint,
                phase=phase,
                usage=accumulated_usage(current).model_dump(mode="json"),
            )

    runtime.run_state(state, checkpoint=checkpoint)
    raise AssertionError("Fault boundary was not reached")


def api(root: Path, phase: str, owner: str, session_id: UUID):
    config = settings()

    class FaultPolicy(RunAdmissionPolicy):
        def finish(self, admission_id, outcome):
            if phase == "terminal_before_release":
                park(phase=phase, session_id=str(session_id), admission_id=str(admission_id))
            return super().finish(admission_id, outcome)

    runtime = CognitiveSessionRunner(build_cognitive_runtime(config))

    def run(raw_input, *, session_id):
        witness(root / "dispatches.txt", session_id)
        if phase == "admitted_before_result":
            park(phase=phase, session_id=session_id)
        return runtime(raw_input, session_id=session_id)

    engine = create_database_engine(get_settings().database_url)
    with create_session_factory(engine)() as db:
        db.info["owner_id"] = owner
        PolyaSessionService(
            db, runner=run, admission_policy=FaultPolicy(db, config, owner)
        ).run_session(session_id)
    raise AssertionError("Fault boundary was not reached")


if __name__ == "__main__":
    kind, directory, phase, *arguments = sys.argv[1:]
    if kind == "local":
        local(Path(directory), phase)
    else:
        api(Path(directory), phase, arguments[0], UUID(arguments[1]))
