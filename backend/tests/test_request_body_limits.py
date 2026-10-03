"""Bound transport input before routing, parsing, authentication or persistence."""

import asyncio
import json
import time

import pytest
from fastapi.testclient import TestClient
from test_auth import configuration
from test_sessions_api import FakeSessionService

from app.api.body_limits import RequestBodyLimitMiddleware
from app.api.routes.sessions import get_session_service
from app.auth import require_principal
from app.config import Settings
from app.main import create_app


@pytest.mark.parametrize("chunked", [False, True])
def test_oversized_valid_json_cannot_create_a_session(chunked):
    service = FakeSessionService()
    app = create_app(Settings(_env_file=None, POLYABRAIN_ENV="test"))
    app.dependency_overrides[get_session_service] = lambda: service
    body = b" " * 120_001 + json.dumps({"raw_input": "Small valid problem"}).encode()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/sessions",
            content=iter([body[:60000], body[60000:]]) if chunked else body,
            headers={"content-type": "application/json"},
        )
    assert response.status_code == 413
    assert service.sessions == {}


def scope(headers=(), method="POST", http_version="1.1"):
    return {
        "type": "http",
        "http_version": http_version,
        "method": method,
        "path": "/api/v1/sessions",
        "headers": list(headers),
    }


def frame(body=b"", more=False):
    return {"type": "http.request", "body": body, "more_body": more}


def exercise(messages, *, headers=(), limit=8, method="POST", http_version="1.1"):
    received, sent, reads = [], [], []

    async def receive():
        reads.append(True)
        return messages.pop(0)

    async def send(message):
        sent.append(message)

    async def app(current, read, write):
        received.append(await read())
        await write({"type": "http.response.start", "status": 202, "headers": []})
        await write({"type": "http.response.body", "body": b"accepted"})

    asyncio.run(
        RequestBodyLimitMiddleware(app, max_bytes=limit)(
            scope(headers, method, http_version), receive, send
        )
    )
    return received, sent, reads


@pytest.mark.parametrize(
    "headers",
    [
        [],
        [(b"content-length", b"8")],
        [(b"transfer-encoding", b"chunked")],
        [(b"Content-Length", b"0008"), (b"Content-Encoding", b"identity")],
    ],
)
def test_exact_boundary_preserves_bytes_and_dispatches_once(headers):
    raw = "🧠🧠".encode()
    received, sent, _ = exercise([frame(raw[:3], True), frame(raw[3:])], headers=headers)
    assert received == [frame(raw)]
    assert sent[0]["status"] == 202


@pytest.mark.parametrize(
    "headers,status",
    [
        ([(b"content-length", b"9")], 413),
        ([(b"content-length", b"-1")], 400),
        ([(b"content-length", b"1e3")], 400),
        ([(b"content-length", b"1, 1")], 400),
        ([(b"content-length", b"1"), (b"Content-Length", b"1")], 400),
        ([(b"content-length", b"1"), (b"transfer-encoding", b"chunked")], 400),
        ([(b"content-length", b"9" * 10000)], 400),
        ([(b"transfer-encoding", b"gzip, chunked")], 400),
        ([(b"content-encoding", b"gzip")], 415),
    ],
)
def test_header_rejection_does_not_read_or_dispatch(headers, status):
    received, sent, reads = exercise([], headers=headers)
    assert received == [] and reads == []
    assert sent[0]["status"] == status
    headers = dict(sent[0]["headers"])
    assert headers[b"cache-control"] == b"no-store"
    assert headers[b"connection"] == b"close"
    assert b"set-cookie" not in headers


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "GET", "DELETE", "OPTIONS"])
def test_all_methods_count_actual_bytes_without_draining_rejected_body(method):
    received, sent, reads = exercise([frame(b"1234", True), frame(b"56789", True)], method=method)
    assert received == []
    assert sent[0]["status"] == 413
    assert len(reads) == 2


@pytest.mark.parametrize("body", [b"a", b"abcd"])
def test_misleading_length_cannot_dispatch(body):
    received, sent, _ = exercise([frame(body)], headers=[(b"content-length", b"2")])
    assert not received
    assert sent[0]["status"] == 400


def test_http2_rejection_has_no_connection_specific_header():
    _, sent, _ = exercise([], headers=[(b"content-length", b"9")], http_version="2")
    assert b"connection" not in dict(sent[0]["headers"])


def test_upload_disconnect_does_not_dispatch_or_send_a_response():
    received, sent, _ = exercise([frame(b"123", True), {"type": "http.disconnect"}])
    assert received == [] and sent == []


@pytest.mark.parametrize("behavior", ["silent", "trickle", "empty_frames"])
def test_total_upload_deadline_cannot_be_renewed(behavior):
    async def run():
        sent, calls = [], []

        async def receive():
            if behavior == "silent":
                await asyncio.Event().wait()
            if behavior == "trickle":
                await asyncio.sleep(0.01)
            return frame(b"x" if behavior == "trickle" else b"", True)

        async def send(message):
            sent.append(message)

        async def app(*args):
            calls.append(True)

        started = time.monotonic()
        await asyncio.wait_for(
            RequestBodyLimitMiddleware(app, timeout_seconds=0.04)(scope(), receive, send), 1
        )
        assert not calls and sent[0]["status"] == 408
        assert time.monotonic() - started >= 0.03

    asyncio.run(run())


def test_execution_and_response_streaming_are_not_under_upload_deadline():
    async def run():
        sent = []
        messages = [frame(b"{}")]
        disconnected = asyncio.Event()

        async def receive():
            if messages:
                return messages.pop(0)
            await disconnected.wait()
            return {"type": "http.disconnect"}

        async def send(message):
            sent.append(message)

        async def app(current, read, write):
            assert await read() == frame(b"{}")
            await asyncio.sleep(0.04)
            await write(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        (b"set-cookie", b"opaque=fixture"),
                        (b"content-type", b"text/event-stream"),
                    ],
                }
            )
            await write({"type": "http.response.body", "body": b"data: one\n\n", "more_body": True})
            disconnected.set()
            assert await read() == {"type": "http.disconnect"}
            await write({"type": "http.response.body", "body": b"data: done\n\n"})

        await RequestBodyLimitMiddleware(app, timeout_seconds=0.01)(scope(), receive, send)
        assert sent[0]["status"] == 200 and len(sent) == 3
        assert (b"set-cookie", b"opaque=fixture") in sent[0]["headers"]

    asyncio.run(run())


def test_task_cancellation_is_not_swallowed_or_translated_to_timeout():
    async def run():
        started = asyncio.Event()

        async def receive():
            started.set()
            await asyncio.Event().wait()

        async def unexpected(*args):
            raise AssertionError("Cancelled upload must not dispatch or respond")

        task = asyncio.create_task(
            RequestBodyLimitMiddleware(unexpected)(scope(), receive, unexpected)
        )
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run())


def test_non_http_scopes_are_forwarded_unchanged():
    async def run():
        original = {"type": "lifespan"}

        async def app(current, read, send):
            assert current is original and read is receive and send is receive

        async def receive():
            raise AssertionError("Do not consume non-HTTP messages")

        await RequestBodyLimitMiddleware(app)(original, receive, receive)

    asyncio.run(run())


def test_api_boundary_accepts_exact_limit_and_preserves_validation_errors():
    service = FakeSessionService()
    app = create_app(Settings(_env_file=None, POLYABRAIN_ENV="test"))
    app.dependency_overrides[get_session_service] = lambda: service
    payload = json.dumps({"raw_input": "A valid question"}).encode()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/sessions",
            content=payload + b" " * (120000 - len(payload)),
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 201
        assert (
            client.post(
                "/api/v1/sessions", content=b"{", headers={"content-type": "application/json"}
            ).status_code
            == 422
        )
    assert len(service.sessions) == 1


@pytest.mark.parametrize(
    "path",
    ["/api/v1/sessions", "/api/v1/source-check", "/api/v1/auth/callback", "/unknown", "/health"],
)
def test_public_and_unknown_paths_reject_before_authentication_or_storage(path):
    app = create_app(configuration())

    def unexpected():
        raise AssertionError("Oversized request reached a dependency")

    app.dependency_overrides[require_principal] = unexpected
    app.dependency_overrides[get_session_service] = unexpected
    with TestClient(app) as client:
        response = client.post(path, content=b"x" * 120001)
        assert response.status_code == 413
        assert "set-cookie" not in response.headers
