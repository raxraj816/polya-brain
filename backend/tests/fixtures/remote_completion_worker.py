"""Independent loopback provider and disposable callers; no paid credentials."""

import json
import socket
import subprocess
import sys
import time
from contextlib import suppress
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from process_loss_worker import settings, witness

from app.cognition.bootstrap import build_cognitive_runtime
from app.config import get_settings
from app.db.session import create_database_engine, create_session_factory
from app.graph.state import create_initial_state
from app.investigator.recovery import RecoveryStore, runtime_fingerprint
from app.sessions.admission import RunAdmissionPolicy
from app.sessions.service import PolyaSessionService


def emit(**fields):
    print(json.dumps(fields), flush=True)


def provider(root):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            witness(root / "provider-dispatches.txt", "accepted")
            emit(event="accepted")
            deadline = time.monotonic() + 30
            while not (root / "release-provider").exists():
                if time.monotonic() >= deadline:
                    raise TimeoutError("Parent did not release provider")
                time.sleep(0.01)
            witness(root / "provider-completions.txt", "completed-after-worker-death")
            emit(event="completed")
            with suppress(BrokenPipeError, ConnectionResetError):
                body = b'{"result":102,"fixture_charge":1}'
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

    with HTTPServer(("127.0.0.1", 0), Handler) as server:
        emit(url=f"http://127.0.0.1:{server.server_port}")
        server.serve_forever()


def call_provider(root, url):
    with httpx.Client(trust_env=False, timeout=20) as client:
        response = client.post(url, json={"problem": "17 * 6"})
        response.raise_for_status()
        witness(root / "caller-received.txt", "received")


def local(root, url):
    config = settings()
    runtime = build_cognitive_runtime(config)
    store = RecoveryStore(root / "private")
    fingerprint = runtime_fingerprint(config)
    token = store.create(fingerprint)
    state = create_initial_state("What is 17 * 6?", session_id=str(uuid4()))
    store.initialize(token, state, None)
    calculator = runtime._registry.get("calculator")
    original = calculator.execute

    def execute(action, current):
        emit(token=token, fingerprint=fingerprint)
        call_provider(root, url)
        return original(action, current)

    calculator.execute = execute
    runtime.run_state(state, checkpoint=lambda current, flight: store.save(token, current, flight))
    raise AssertionError("Caller should have been killed")


def api(root, url, owner, session_id):
    config = settings()

    def runner(_raw_input, *, session_id):
        emit(session_id=session_id)
        call_provider(root, url)
        raise AssertionError("Caller should have been killed")

    engine = create_database_engine(get_settings().database_url)
    with create_session_factory(engine)() as db:
        db.info["owner_id"] = owner
        PolyaSessionService(
            db, runner=runner, admission_policy=RunAdmissionPolicy(db, config, owner)
        ).run_session(UUID(session_id))


def http_backend(root, provider_url, owner, port="0"):
    import uvicorn

    from app import auth
    from app.api.routes import sessions
    from app.auth import require_principal
    from app.main import create_app

    config = settings().model_copy(
        update={
            "database_url": get_settings().database_url,
            "auth_required": True,
        }
    )
    app = create_app(config)
    # Trusted fixture identity only; this is not an OIDC/authentication test.
    app.dependency_overrides[require_principal] = lambda: owner
    auth.authenticated_user = lambda _request: owner

    def runner(_raw_input, *, session_id):
        call_provider(root, provider_url)
        raise AssertionError("Backend should have been killed")

    sessions.build_representation_session_runner = lambda *_args, **_kwargs: runner
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", int(port)))
        emit(url=f"http://127.0.0.1:{sock.getsockname()[1]}")
        uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False)).run(sockets=[sock])


def release_admission(owner):
    from sqlalchemy import select

    from app.db.models import RunAdmission

    engine = create_database_engine(get_settings().database_url)
    with create_session_factory(engine)() as db:
        admission = db.scalar(select(RunAdmission.id).where(RunAdmission.user_id == owner))
        assert admission is not None
    engine.dispose()
    subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[3] / "scripts/manage_run_admissions.py"),
            "--release",
            str(admission),
            "--confirm-worker-stopped",
        ],
        check=True,
    )


if __name__ == "__main__":
    kind, directory, *args = sys.argv[1:]
    root = Path(directory)
    if kind == "provider":
        provider(root)
    elif kind == "local":
        local(root, *args)
    elif kind == "release":
        release_admission(args[0])
    elif kind == "http":
        http_backend(root, *args)
    else:
        api(root, *args)
