"""Provider-neutral search protocol and Brave Search adapter."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import datetime
from typing import Any, Protocol

import httpx
from pydantic import TypeAdapter, ValidationError

from app.acquisition.contracts import SearchRequest, SearchResponse, SearchResultCandidate


class SearchProviderError(RuntimeError):
    """Sanitized provider failure safe for trace and recovery policy."""

    def __init__(
        self,
        message: str,
        *,
        kind: str,
        retryable: bool,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.retryable = retryable
        self.status_code = status_code


class SearchProvider(Protocol):
    """Replaceable external-search boundary."""

    name: str

    def search(self, request: SearchRequest) -> SearchResponse:
        """Return normalized candidates, never a trusted conclusion."""
        ...


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _optional_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return TypeAdapter(datetime).validate_python(value)
    except ValidationError:
        return None


class BraveSearchProvider:
    """Brave Web Search adapter using the documented server-side key header."""

    name = "brave"

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.search.brave.com/res/v1/web/search",
        timeout_seconds: float = 15.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("Brave Search API key must not be blank")
        self._api_key = api_key.strip()
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client = client

    def search(self, request: SearchRequest) -> SearchResponse:
        """Execute one bounded request and normalize only ordinary web results."""
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self._api_key,
        }
        params: dict[str, str | int] = {
            "q": request.query,
            "count": request.max_results,
            "country": request.country,
            "search_lang": request.search_language,
            "safesearch": "strict",
            "extra_snippets": "true",
        }
        try:
            if self._client is None:
                with httpx.Client(timeout=self._timeout_seconds) as client:
                    response = client.get(self._base_url, headers=headers, params=params)
            else:
                response = self._client.get(self._base_url, headers=headers, params=params)
        except httpx.TimeoutException as exc:
            raise SearchProviderError(
                "Search provider timed out.", kind="timeout", retryable=True
            ) from exc
        except httpx.HTTPError as exc:
            raise SearchProviderError(
                "Search provider network request failed.",
                kind="network",
                retryable=True,
            ) from exc

        if response.status_code != 200:
            retryable = response.status_code == 429 or response.status_code >= 500
            kind = "rate_limit" if response.status_code == 429 else "provider_http_error"
            raise SearchProviderError(
                f"Search provider returned HTTP {response.status_code}.",
                kind=kind,
                retryable=retryable,
                status_code=response.status_code,
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise SearchProviderError(
                "Search provider returned malformed JSON.",
                kind="malformed_response",
                retryable=False,
                status_code=response.status_code,
            ) from exc
        if not isinstance(payload, Mapping):
            raise SearchProviderError(
                "Search provider returned a non-object response.",
                kind="malformed_response",
                retryable=False,
                status_code=response.status_code,
            )

        web = _mapping(payload.get("web"))
        raw_results = web.get("results")
        results = raw_results if isinstance(raw_results, list) else []
        candidates: list[SearchResultCandidate] = []
        for rank, raw_result in enumerate(results[: request.max_results], start=1):
            result = _mapping(raw_result)
            title = result.get("title")
            url = result.get("url")
            description = result.get("description")
            if (
                not isinstance(title, str)
                or not title.strip()
                or not isinstance(url, str)
                or not url.strip()
                or not isinstance(description, str)
                or not description.strip()
            ):
                continue
            raw_snippets = result.get("extra_snippets")
            snippets = (
                [item.strip() for item in raw_snippets if isinstance(item, str) and item.strip()]
                if isinstance(raw_snippets, list)
                else []
            )
            candidate_id = hashlib.sha256(f"{url}|{description}".encode()).hexdigest()[:16]
            candidates.append(
                SearchResultCandidate.model_validate(
                    {
                        "id": f"brave-{candidate_id}",
                        "title": title.strip(),
                        "url": url.strip(),
                        "excerpt": description.strip(),
                        "provider_rank": rank,
                        "extra_snippets": snippets[:5],
                        "published_at": _optional_datetime(
                            result.get("page_age") or result.get("published_at")
                        ),
                    }
                )
            )

        query = _mapping(payload.get("query"))
        more_results = query.get("more_results_available") is True
        return SearchResponse(
            provider=self.name,
            query=request.query,
            candidates=candidates,
            more_results_available=more_results,
        )
