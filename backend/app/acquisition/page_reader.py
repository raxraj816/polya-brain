"""Bounded public page acquisition with pinned DNS and deterministic passages."""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import json
import math
import re
import sys
from collections import Counter
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from urllib.parse import urlsplit

import httpx
from pydantic import JsonValue

from app.acquisition.capabilities import (
    ACQUISITION_EVENT,
    _candidate_count,
    _evaluations_for_target,
)
from app.acquisition.contracts import EvidenceCandidate
from app.cognition.capabilities import FunctionCapability
from app.cognition.contracts import (
    CapabilityDefinition,
    CapabilityKind,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveObservation,
    CognitiveStateUpdate,
    ObservationStatus,
)
from app.graph.state import PolyaState, StateEvent
from app.models.contracts import ReasoningMode

CAPABILITY = "public_page_reader"
VERSION = "public_page_reader@0.1.1"
MAX_BYTES = 2_000_000
MAX_PASSAGE_CHARS = 9000
TIMEOUT_SECONDS = 20.0
ATTEMPT_EVENT = "public_page_read_attempted"


class VisibleText(HTMLParser):
    """Extract text while excluding scripts, styles and embedded document content."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "iframe", "svg"}:
            self.hidden += 1
        elif not self.hidden and tag in {
            "p",
            "div",
            "br",
            "li",
            "pre",
            "h1",
            "h2",
            "h3",
            "h4",
            "tr",
        }:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "iframe", "svg"}:
            self.hidden = max(0, self.hidden - 1)
        elif not self.hidden:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def _words(text: str) -> list[str]:
    return [
        word[:-1] if len(word) > 4 and word.endswith("s") else word
        for word in re.findall(r"[a-z0-9]{3,}", text.casefold())
    ]


def selected_passages(text: str, query: str) -> tuple[str, list[list[int]]]:
    """Rank overlapping text windows; return them in document order with offsets."""
    terms = set(_words(query)) - {
        "the",
        "and",
        "for",
        "from",
        "that",
        "this",
        "with",
        "what",
        "source",
        "relevant",
        "retrieved",
        "official",
        "explain",
        "particular",
        "which",
        "specification",
        "document",
        "passage",
        "cite",
        "supplied",
    }
    headings = [m.start() for m in re.finditer(r"(?m)^\d+(?:\.\d+)*\. [^\n]{1,160}\n", text)]
    if len(headings) >= 3:
        # Start at section headings so definitions are retained, and reserve
        # space for several requested topics instead of one long section.
        starts = sorted(set([0, *headings]))
        windows = [
            (a, min(b, a + 1450)) for a, b in zip(starts, [*starts[1:], len(text)], strict=True)
        ]
    else:
        windows = [(start, min(len(text), start + 2900)) for start in range(0, len(text), 1500)]
    frequencies = [Counter(_words(text[a:b])) for a, b in windows]
    document_frequency = Counter(term for counts in frequencies for term in counts if term in terms)
    weights = {
        term: math.log(1 + (len(windows) - count + 0.5) / (count + 0.5))
        for term, count in document_frequency.items()
    }
    heading_terms = [
        terms & set(_words(text[a:b].split("\n", 1)[0])) if headings else set() for a, b in windows
    ]
    scores = [
        sum(weights[term] * counts[term] / (counts[term] + 1.2) for term in terms if counts[term])
        for counts in frequencies
    ]
    remaining = list(range(len(windows)))
    selected: list[tuple[int, int]] = []
    covered_headings: set[str] = set()
    used_characters = 0
    while remaining and len(selected) < 6:
        index = max(
            remaining,
            key=lambda i: (
                scores[i] + 8 * sum(weights[t] for t in heading_terms[i] - covered_headings)
            ),
        )
        remaining.remove(index)
        span = windows[index]
        cost = span[1] - span[0] + (len("\n[...passage boundary...]\n") if selected else 0)
        if cost + used_characters > MAX_PASSAGE_CHARS:
            continue
        if all(span[1] <= a or span[0] >= b for a, b in selected):
            selected.append(span)
            covered_headings.update(heading_terms[index])
            used_characters += cost
    selected.sort()
    return "\n[...passage boundary...]\n".join(text[a:b] for a, b in selected), [
        list(s) for s in selected
    ]


async def resolve_public_addresses(host: str) -> list[str]:
    # A cancellable child avoids an OS DNS call outliving asyncio's deadline in
    # the default thread executor, whose shutdown otherwise waits for that call.
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        "import json,socket,sys; print(json.dumps(list(dict.fromkeys("
        "str(e[4][0]) for e in socket.getaddrinfo(sys.argv[1],443,type=socket.SOCK_STREAM)))))",
        host,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        stdout, _ = await process.communicate()
        if process.returncode != 0 or len(stdout) > 65536:
            raise OSError("Public page DNS resolution failed")
        addresses = json.loads(stdout)
        if not isinstance(addresses, list) or any(not isinstance(a, str) for a in addresses):
            raise OSError("Invalid public page DNS result")
        return [str(a) for a in addresses]
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()


class PublicPageReader:
    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        resolver: Callable[[str], Awaitable[list[str]]] = resolve_public_addresses,
        timeout_seconds: float = TIMEOUT_SECONDS,
    ) -> None:
        self.transport = transport
        self.resolver = resolver
        if not 0 < timeout_seconds <= TIMEOUT_SECONDS:
            raise ValueError("Invalid page-read deadline")
        self.timeout_seconds = timeout_seconds

    async def _read(self, url: str, query: str) -> tuple[str, dict[str, JsonValue]]:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in {None, 443}
        ):
            raise ValueError("Only credential-free standard-port HTTPS pages are eligible")
        async with asyncio.timeout(self.timeout_seconds):
            addresses = await self.resolver(parsed.hostname)
            if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
                raise ValueError("Page host must resolve exclusively to public addresses")
            # The connection uses this validated address, never a second DNS lookup.
            # SNI also sets the TLS certificate hostname in httpcore's HTTPS transport.
            pinned = httpx.URL(url).copy_with(host=addresses[0], fragment=None)
            async with (
                httpx.AsyncClient(
                    transport=self.transport,
                    timeout=self.timeout_seconds,
                    follow_redirects=False,
                    trust_env=False,
                ) as client,
                client.stream(
                    "GET",
                    pinned,
                    headers={
                        "Host": parsed.hostname,
                        "Accept": "text/html, text/plain",
                        "User-Agent": "PolyaBrain/0.1 (bounded source reader)",
                    },
                    extensions={"sni_hostname": parsed.hostname},
                ) as response,
            ):
                if response.status_code != 200:
                    raise ValueError("Page read requires HTTP 200 without redirects")
                media_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                if media_type not in {"text/html", "text/plain", "application/xhtml+xml"}:
                    raise ValueError("Page read only accepts text or HTML")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(body) + len(chunk) > MAX_BYTES:
                        raise ValueError("Page exceeds decoded-body byte limit")
                    body.extend(chunk)
                try:
                    content = bytes(body).decode(response.encoding or "utf-8", errors="replace")
                except LookupError as exc:
                    raise ValueError("Unsupported page character encoding") from exc
        if media_type != "text/plain":
            parser = VisibleText()
            parser.feed(content)
            content = "".join(parser.parts)
        text = "\n".join(
            re.sub(r"\s+", " ", line).strip() for line in content.splitlines() if line.strip()
        )
        if not text:
            raise ValueError("Page contains no extractable text")
        excerpt, offsets = selected_passages(text, query)
        return excerpt, {
            "source_uri": url,
            "body_sha256": hashlib.sha256(body).hexdigest(),
            "decoded_bytes": len(body),
            "text_characters": len(text),
            "selected_offsets": [[a, b] for a, b in offsets],
            "passage_character_limit": MAX_PASSAGE_CHARS,
            "source_coverage": "selected passages from bounded complete text response",
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "selection_truncated": len(text) > sum(b - a for a, b in offsets),
        }

    def read(self, url: str, query: str) -> tuple[str, dict[str, JsonValue]]:
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="polya-page") as pool:
            return pool.submit(lambda: asyncio.run(self._read(url, query))).result()


def page_read_target(state: PolyaState, target: str) -> str | None:
    if any(
        e.event_type == "capability_observation"
        and e.metadata.get("capability") == CAPABILITY
        and e.metadata.get("target") == target
        and e.metadata.get("status") in {"failed", "blocked", "inconclusive"}
        for e in state["events"]
    ):
        return None
    attempts = [e for e in state["events"] if e.event_type == ATTEMPT_EVENT]
    if len(attempts) >= 2:
        return None
    # Require a failed evaluation, including the parent group of a scope reframe.
    evaluations = _evaluations_for_target(state, target)
    if not evaluations:
        for event in reversed(state["events"]):
            if event.event_type == "knowledge_scope_reviewed":
                dispositions = event.metadata.get("dispositions", [])
                if isinstance(dispositions, list) and any(
                    isinstance(d, dict) and d.get("question") == target for d in dispositions
                ):
                    parent = event.metadata.get("target_gap")
                    if isinstance(parent, str):
                        evaluations = _evaluations_for_target(state, parent)
                    break
    if not evaluations or evaluations[-1].metadata.get("gap_resolved") is not False:
        return None
    latest_acquisition = evaluations[-1].metadata.get("acquisition_id")
    if any(
        e.event_type == ACQUISITION_EVENT
        and e.engine_name == CAPABILITY
        and e.metadata.get("acquisition_id") == latest_acquisition
        for e in state["events"]
    ):
        # Reading did not provide the residual fact. Discover a more relevant
        # source before spending another external call on the same batch.
        return None
    tried = {str(e.metadata.get("source_uri")) for e in attempts}
    urls = list(
        dict.fromkeys(
            e.source_uri
            for e in state["evidence"]
            if e.source_type == "evaluated_web_source"
            and e.source_uri
            and e.source_uri.startswith("https://")
            and e.source_uri not in tried
            and not urlsplit(e.source_uri).path.lower().endswith(".pdf")
        )
    )
    # Prefer a document page over a publisher's short bibliographic landing page.
    next_query = str(evaluations[-1].metadata.get("next_query") or "")
    query_terms = set(re.findall(r"[a-z]+|[0-9]+", next_query.casefold()))

    def rank(url: str) -> tuple[bool, int, bool]:
        url_terms = set(re.findall(r"[a-z]+|[0-9]+", url.casefold()))
        return (
            "/info/" in url,
            -len(query_terms & url_terms),
            not urlsplit(url).path.endswith((".html", ".txt")),
        )

    urls.sort(key=rank)
    return urls[0] if urls else None


def public_page_capability(
    reader: PublicPageReader, *, max_total_candidates: int = 15
) -> FunctionCapability:
    definition = CapabilityDefinition(
        name=CAPABILITY,
        version=VERSION,
        supported_actions={CognitiveActionType.SEARCH},
        kind=CapabilityKind.EXTERNAL,
        timeout_seconds=TIMEOUT_SECONDS,
        max_external_calls=1,
        estimated_cost=0.01,
        approved_for_sensitive_data=False,
    )

    def execute(action: CognitiveActionCandidate, state: PolyaState) -> CognitiveObservation:
        url = page_read_target(state, action.target)
        if url is None or _candidate_count(state) >= max_total_candidates:
            return CognitiveObservation(
                action_id=action.id,
                capability=CAPABILITY,
                capability_version=VERSION,
                status=ObservationStatus.BLOCKED,
                summary="No eligible untried public page.",
                failure_kind="page_read_unavailable",
                payload={"external_calls": 0, "model_calls": 0},
            )
        attempt = StateEvent(
            engine_name=CAPABILITY,
            event_type=ATTEMPT_EVENT,
            reasoning_mode=ReasoningMode.EXPLORE,
            summary="Attempted one bounded public page read.",
            metadata={"source_uri": url, "target_gap": action.target},
        )
        # The page was already selected for the residual gap. Passage selection
        # must preserve coverage of the user's whole requested deliverable;
        # generated meta-questions can otherwise outrank the actual subject.
        query = state["raw_input"]
        try:
            excerpt, metadata = reader.read(url, query)
        except (ValueError, OSError, TimeoutError, httpx.HTTPError) as exc:
            return CognitiveObservation(
                action_id=action.id,
                capability=CAPABILITY,
                capability_version=VERSION,
                status=ObservationStatus.FAILED,
                summary="Public page unavailable or rejected by read limits.",
                failure_kind="public_page_read_failed",
                payload={"external_calls": 1, "model_calls": 0, "error_type": type(exc).__name__},
                proposed_update=CognitiveStateUpdate(trace_events_to_add=[attempt]),
            )
        acquisition_id = "page-" + hashlib.sha256((url + excerpt).encode()).hexdigest()[:16]
        candidate = EvidenceCandidate(
            id=acquisition_id,
            source_type="web_page",
            source_uri=url,
            title=urlsplit(url).path,
            excerpt=excerpt,
            source_rank=1,
        )
        acquired = StateEvent(
            engine_name=CAPABILITY,
            event_type=ACQUISITION_EVENT,
            reasoning_mode=ReasoningMode.EXPLORE,
            summary="Read selected source passages; evidence evaluation is required.",
            metadata={
                "acquisition_id": acquisition_id,
                "target_gap": action.target,
                "source_type": "web_page",
                "candidate_count": 1,
                "candidates": [candidate.model_dump(mode="json")],
                "provider_metadata": metadata,
            },
        )
        return CognitiveObservation(
            action_id=action.id,
            capability=CAPABILITY,
            capability_version=VERSION,
            status=ObservationStatus.SUCCEEDED,
            summary=acquired.summary,
            payload={"external_calls": 1, "model_calls": 0, "acquisition_id": acquisition_id},
            proposed_update=CognitiveStateUpdate(trace_events_to_add=[attempt, acquired]),
        )

    return FunctionCapability(definition, execute)
