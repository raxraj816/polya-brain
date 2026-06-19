#!/usr/bin/env python3
"""Smoke-test the OpenAI baseline runner against a local compatible endpoint."""

from __future__ import annotations

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from proofs.pre_platform.core import call_openai_baseline


class FakeResponsesHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/v1/responses":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if not self.headers.get("Authorization", "").startswith("Bearer "):
            self.send_response(401)
            self.end_headers()
            return
        response = {
            "id": "resp_local_smoke",
            "output": [
                {
                    "content": [
                        {
                            "type": "output_text",
                            "text": f"Direct baseline answer for model {payload['model']}. Inspect logs, compare evidence, and test the likely fix.",
                        }
                    ]
                }
            ],
        }
        body = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    server = HTTPServer(("127.0.0.1", 0), FakeResponsesHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    old_key = os.environ.get("OPENAI_API_KEY")
    old_base_url = os.environ.get("OPENAI_BASE_URL")
    os.environ["OPENAI_API_KEY"] = "sk-local-smoke-test"
    os.environ["OPENAI_BASE_URL"] = f"http://127.0.0.1:{server.server_port}/v1"
    try:
        result = call_openai_baseline(
            "Investigate why a deploy caused readiness checks to fail.",
            model="local-smoke-model",
            timeout_seconds=5,
        )
    finally:
        server.shutdown()
        if old_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = old_key
        if old_base_url is None:
            os.environ.pop("OPENAI_BASE_URL", None)
        else:
            os.environ["OPENAI_BASE_URL"] = old_base_url
    if result.kind != "openai_responses_api":
        raise SystemExit(f"unexpected baseline kind: {result.kind}")
    if "Direct baseline answer" not in result.text:
        raise SystemExit("baseline text was not parsed from the response")
    print("OpenAI baseline runner smoke verified with a local compatible endpoint")


if __name__ == "__main__":
    main()
