"""Probe the configured model under PolyaBrain's fail-closed data policy."""

from __future__ import annotations

import json

import httpx

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    response = httpx.post(
        f"{settings.openrouter_base_url.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key.get_secret_value()}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.openrouter_model,
            "messages": [{"role": "user", "content": "Reply with OK."}],
            "max_completion_tokens": 16,
            "provider": {"data_collection": "deny"},
        },
        timeout=30,
    )
    payload = response.json() if response.content else {}
    error = payload.get("error", {}) if isinstance(payload, dict) else {}
    print(
        json.dumps(
            {
                "status_code": response.status_code,
                "model": settings.openrouter_model,
                "requested_data_collection": "deny",
                "error_code": error.get("code") if isinstance(error, dict) else None,
                "error_message": error.get("message") if isinstance(error, dict) else None,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
