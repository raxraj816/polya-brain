"""Offline HTTP contract tests for live pre-platform baseline clients."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from proofs.pre_platform.core import (
    build_baseline,
    call_openrouter_baseline,
    extract_chat_completion_text,
)


class FakeOpenRouterHandler(BaseHTTPRequestHandler):
    """Minimal OpenAI-compatible chat-completions endpoint."""

    def do_POST(self) -> None:
        if self.path != "/api/v1/chat/completions":
            self.send_response(404)
            self.end_headers()
            return
        if self.headers.get("Authorization") != "Bearer local-test-key":
            self.send_response(401)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", "0"))
        request_payload = json.loads(self.rfile.read(length).decode("utf-8"))
        response_payload = {
            "id": "openrouter_local_smoke",
            "model": request_payload["model"],
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Inspect the release diff and run a reversible canary before changing the timeout.",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 30, "completion_tokens": 15, "total_tokens": 45},
        }
        body = json.dumps(response_payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        """Keep the test output deterministic and quiet."""


@pytest.fixture
def openrouter_server() -> Iterator[HTTPServer]:
    server = HTTPServer(("127.0.0.1", 0), FakeOpenRouterHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_openrouter_baseline_normalizes_text_and_usage(
    openrouter_server: HTTPServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "local-test-key")
    monkeypatch.setenv(
        "OPENROUTER_BASE_URL",
        f"http://127.0.0.1:{openrouter_server.server_port}/api/v1",
    )

    result = call_openrouter_baseline(
        "Investigate a readiness regression.",
        model="local-openrouter-model",
        timeout_seconds=5,
    )

    assert result.kind == "openrouter_chat_completions_api"
    assert result.text.startswith("Inspect the release diff")
    assert result.metadata["provider"] == "openrouter"
    assert result.metadata["model"] == "local-openrouter-model"
    assert result.metadata["total_tokens"] == 45


def test_auto_baseline_prefers_openrouter_and_uses_environment_model(
    openrouter_server: HTTPServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "local-test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "environment-openrouter-model")
    monkeypatch.setenv(
        "OPENROUTER_BASE_URL",
        f"http://127.0.0.1:{openrouter_server.server_port}/api/v1",
    )

    result = build_baseline(
        problem="Investigate a readiness regression.",
        provider="auto",
        baseline_path=None,
        model=None,
        timeout_seconds=5,
    )

    assert result.kind == "openrouter_chat_completions_api"
    assert result.metadata["model"] == "environment-openrouter-model"


def test_openrouter_baseline_requires_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY is not set"):
        call_openrouter_baseline("Investigate a failure.", "model", 1)


def test_openrouter_structured_error_exposes_code_without_provider_message() -> None:
    payload = {
        "error": {
            "code": 503,
            "message": "upstream included sk-or-v1-sensitive-provider-detail",
        }
    }

    with pytest.raises(RuntimeError, match="provider error code 503") as exc_info:
        extract_chat_completion_text(payload)

    assert "sensitive-provider-detail" not in str(exc_info.value)
