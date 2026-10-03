"""Raw HTTP checks against real Uvicorn parsers; no database/provider needed."""

import json
import socket
import threading
import time

import pytest
import uvicorn
from test_sessions_api import FakeSessionService

from app.api.routes.sessions import get_session_service
from app.config import Settings
from app.main import create_app


@pytest.fixture(params=["h11", "httptools"])
def server(request):
    service = FakeSessionService()
    app = create_app(Settings(_env_file=None, POLYABRAIN_ENV="test"))
    app.dependency_overrides[get_session_service] = lambda: service
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    address = sock.getsockname()
    running = uvicorn.Server(
        uvicorn.Config(app, http=request.param, lifespan="off", log_level="error")
    )
    worker = threading.Thread(target=running.run, kwargs={"sockets": [sock]}, daemon=True)
    worker.start()
    try:
        until = time.monotonic() + 5
        while not running.started and time.monotonic() < until:
            time.sleep(0.01)
        assert running.started
        yield address, service
    finally:
        running.should_exit = True
        worker.join(timeout=5)
        sock.close()
        assert not worker.is_alive()


def exchange(address, headers, body=b"", *, timeout=15):
    with socket.create_connection(address, timeout=timeout) as connection:
        connection.sendall(
            b"POST /api/v1/sessions HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\n"
            + headers
            + b"\r\n"
            + body
        )
        with connection.makefile("rb") as response:
            # Do not silently skip a 100 Continue when a size rejection should be immediate.
            status = int(response.readline().split()[1])
            received = {}
            while (line := response.readline()) != b"\r\n":
                assert line
                key, value = line.split(b":", 1)
                received[key.lower()] = value.strip()
            payload = response.read(int(received[b"content-length"]))
            assert response.read(1) == b"", "Rejected uploads must close HTTP/1 connections"
            return status, received, json.loads(payload)


def test_declared_oversize_is_rejected_without_reading_or_100_continue(server):
    address, service = server
    status, headers, _ = exchange(address, b"Content-Length: 120001\r\nExpect: 100-continue\r\n")
    assert status == 413 and headers[b"connection"] == b"close"
    assert not service.sessions


def test_real_chunked_oversize_is_rejected_before_final_chunk(server):
    address, service = server
    body = b"EA60\r\n" + b" " * 60000 + b"\r\nEA61\r\n" + b" " * 60001 + b"\r\n"
    status, _, _ = exchange(address, b"Transfer-Encoding: chunked\r\n", body)
    assert status == 413 and not service.sessions


def test_real_partial_upload_times_out_before_dispatch(server):
    address, service = server
    started = time.monotonic()
    status, _, payload = exchange(address, b"Content-Length: 100\r\n", b"{")
    elapsed = time.monotonic() - started
    assert status == 408
    assert 9.5 <= elapsed < 14
    assert "before processing" in payload["detail"]
    assert not service.sessions


def test_real_exact_limit_is_admitted_and_short_followup_remains_available(server):
    address, service = server
    payload = json.dumps({"raw_input": "Small valid question"}).encode()
    body = payload + b" " * (120000 - len(payload))
    status, _, _ = exchange(address, b"Content-Length: 120000\r\nConnection: close\r\n", body)
    assert status == 201 and len(service.sessions) == 1
    status, _, _ = exchange(
        address, f"Content-Length: {len(payload)}\r\nConnection: close\r\n".encode(), payload
    )
    assert status == 201 and len(service.sessions) == 2


def test_real_disconnect_mid_upload_leaves_no_created_session(server):
    address, service = server
    with socket.create_connection(address, timeout=2) as connection:
        connection.sendall(
            b"POST /api/v1/sessions HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\nContent-Length: 100\r\n\r\n{"
        )
    # A subsequent complete request proves the server is responsive after the disconnect.
    status, _, _ = exchange(address, b"Content-Length: 0\r\nConnection: close\r\n")
    assert status == 422 and not service.sessions
