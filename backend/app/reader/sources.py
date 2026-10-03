"""Sources PolyaBrain reads directly: Wikipedia, Wikidata and a local corpus.

No search vendor and no language model sit between PolyaBrain and these sources.
All network access goes through one bounded, injectable fetcher.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

USER_AGENT = "PolyaBrain-Reader/0.1"
# Wikimedia: clients without contact details get 10 requests/minute; clients whose
# User-Agent names a contact URL or email get 200/minute. Pace to stay inside them.
ANONYMOUS_INTERVAL_SECONDS = 6.5
IDENTIFIED_INTERVAL_SECONDS = 0.35


def user_agent(contact: str = "") -> str:
    contact = " ".join(contact.split())[:200]
    return f"{USER_AGENT} ({contact}) python-urllib" if contact else f"{USER_AGENT} python-urllib"


MAX_RESPONSE_BYTES = 4_000_000

Fetch = Callable[[str, Mapping[str, str]], Any]


class SourceError(RuntimeError):
    """A source could not be read; the message is safe to show."""


class PoliteFetcher:
    """Bounded JSON GETs that respect source etiquette: pacing, Retry-After and caching.

    Wikimedia asks API clients to identify themselves, avoid bursts and back off when
    rate-limited. Responses are cached in memory and, optionally, on disk so repeated
    questions and evaluations do not re-read the same source.
    """

    def __init__(
        self,
        *,
        contact: str = "",
        min_interval: float | None = None,
        cache_dir: Path | None = None,
        timeout: float = 12.0,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        opener: Callable[..., Any] = urllib.request.urlopen,
    ) -> None:
        self.identified = bool(contact.strip())
        self.user_agent = user_agent(contact)
        self.min_interval = (
            min_interval
            if min_interval is not None
            else IDENTIFIED_INTERVAL_SECONDS
            if self.identified
            else ANONYMOUS_INTERVAL_SECONDS
        )
        self.timeout = timeout
        self.cache_dir = cache_dir
        self._memory: dict[str, Any] = {}
        self._last: dict[str, float] = {}
        self._sleep, self._clock, self._open = sleep, clock, opener
        self.requests = 0

    def _key(self, url: str, params: Mapping[str, str]) -> str:
        query = urllib.parse.urlencode(sorted(params.items()))
        return f"{url}?{query}"

    def __call__(self, url: str, params: Mapping[str, str]) -> Any:
        key = self._key(url, params)
        if key in self._memory:
            return self._memory[key]
        disk = None
        if self.cache_dir is not None:
            disk = self.cache_dir / (hashlib.sha256(key.encode()).hexdigest() + ".json")
            if disk.is_file():
                value = json.loads(disk.read_text(encoding="utf-8"))
                self._memory[key] = value
                return value
        host = urllib.parse.urlsplit(url).hostname or ""
        bucket = (
            "wikimedia"
            if host.endswith(("wikipedia.org", "wikidata.org", "wikimedia.org"))
            else host
        )
        for attempt in range(2):
            wait = self.min_interval - (self._clock() - self._last.get(bucket, -1e9))
            if wait > 0:
                self._sleep(wait)
            self._last[bucket] = self._clock()
            self.requests += 1
            request = urllib.request.Request(key, headers={"User-Agent": self.user_agent})
            try:
                with self._open(request, timeout=self.timeout) as response:  # noqa: S310 - fixed https hosts
                    body = response.read(MAX_RESPONSE_BYTES + 1)
                break
            except urllib.error.HTTPError as exc:
                if exc.code in {429, 503} and attempt == 0:
                    retry_after = exc.headers.get("Retry-After") if exc.headers else None
                    try:
                        delay = float(retry_after) if retry_after else 2.0
                    except ValueError:
                        delay = 2.0
                    if delay > 60:
                        raise SourceError(f"{host} asked PolyaBrain to wait {delay:.0f}s") from exc
                    self._sleep(max(delay, 0.5))
                    continue
                raise SourceError(f"{host} returned HTTP {exc.code}") from exc
            except OSError as exc:
                raise SourceError(f"{host} unavailable ({type(exc).__name__})") from exc
        if len(body) > MAX_RESPONSE_BYTES:
            raise SourceError("source response exceeded its size bound")
        try:
            value = json.loads(body)
        except json.JSONDecodeError as exc:
            raise SourceError("source returned invalid JSON") from exc
        self._memory[key] = value
        if disk is not None:
            disk.parent.mkdir(parents=True, exist_ok=True)
            disk.write_text(json.dumps(value), encoding="utf-8")
        return value


_DEFAULT_FETCHER = PoliteFetcher()


def http_json(url: str, params: Mapping[str, str]) -> Any:
    """Shared polite fetcher for callers that do not configure their own."""
    return _DEFAULT_FETCHER(url, params)


@dataclass(frozen=True)
class Document:
    source: str  # wikipedia | wikidata | local
    title: str
    url: str
    text: str
    rank: int


class Wikipedia:
    api = "https://en.wikipedia.org/w/api.php"

    def __init__(self, fetch: Fetch = http_json) -> None:
        self.fetch = fetch

    def search(self, query: str, limit: int = 4) -> list[str]:
        data = self.fetch(
            self.api,
            {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": str(limit),
                "format": "json",
                "formatversion": "2",
            },
        )
        return [
            item["title"] for item in data.get("query", {}).get("search", []) if "title" in item
        ]

    def page(self, title: str, rank: int) -> Document | None:
        data = self.fetch(
            self.api,
            {
                "action": "query",
                "prop": "extracts",
                "explaintext": "1",
                "exsectionformat": "plain",
                "redirects": "1",
                "titles": title,
                "format": "json",
                "formatversion": "2",
            },
        )
        pages = data.get("query", {}).get("pages", [])
        if not pages or pages[0].get("missing") or not pages[0].get("extract"):
            return None
        resolved = pages[0].get("title", title)
        text = pages[0]["extract"][:300_000]
        url = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(resolved.replace(" ", "_"))
        return Document("wikipedia", resolved, url, text, rank)


@dataclass(frozen=True)
class Claim:
    entity_id: str
    entity_label: str
    property_id: str
    property_label: str
    value: str
    kind: str  # time | quantity | item | string
    qualifier: str = ""

    @property
    def url(self) -> str:
        return f"https://www.wikidata.org/wiki/{self.entity_id}#{self.property_id}"


class Wikidata:
    api = "https://www.wikidata.org/w/api.php"

    def __init__(self, fetch: Fetch = http_json) -> None:
        self.fetch = fetch

    def find(self, text: str, *, kind: str = "item", limit: int = 3) -> list[dict[str, Any]]:
        data = self.fetch(
            self.api,
            {
                "action": "wbsearchentities",
                "search": text,
                "language": "en",
                "uselang": "en",
                "type": kind,
                "limit": str(limit),
                "format": "json",
            },
        )
        return [item for item in data.get("search", []) if isinstance(item, dict) and "id" in item]

    def entities(self, ids: list[str], props: str = "labels|claims") -> dict[str, Any]:
        if not ids:
            return {}
        data = self.fetch(
            self.api,
            {
                "action": "wbgetentities",
                "ids": "|".join(ids[:50]),
                "props": props,
                "languages": "en",
                "format": "json",
            },
        )
        return data.get("entities", {}) if isinstance(data, dict) else {}

    @staticmethod
    def _label(entity: Mapping[str, Any]) -> str:
        return str(entity.get("labels", {}).get("en", {}).get("value", entity.get("id", "")))

    def claims(self, entity_id: str, property_id: str, property_label: str) -> list[Claim]:
        entity = self.entities([entity_id]).get(entity_id, {})
        statements = entity.get("claims", {}).get(property_id, [])
        preferred = [s for s in statements if s.get("rank") == "preferred"] or [
            s for s in statements if s.get("rank") != "deprecated"
        ]
        raw: list[tuple[str, Any, str]] = []
        for statement in preferred[:6]:
            snak = statement.get("mainsnak", {})
            if snak.get("snaktype") != "value":
                continue
            datavalue = snak.get("datavalue", {})
            qualifier = ""
            for qualifier_snak in statement.get("qualifiers", {}).get("P585", [])[:1]:
                time = qualifier_snak.get("datavalue", {}).get("value", {}).get("time", "")
                if time:
                    qualifier = f"as of {time[1:5]}"
            raw.append((datavalue.get("type", ""), datavalue.get("value"), qualifier))
        item_ids = [
            value.get("id")
            for kind, value, _ in raw
            if kind == "wikibase-entityid" and isinstance(value, dict)
        ]
        # An item without an English label is dropped: a bare id like 'Q9661' is not an answer.
        labels = {
            key: label
            for key, value in self.entities([i for i in item_ids if i], "labels").items()
            if (label := self._label(value)) != key
        }
        claims = []
        label = self._label(entity) if entity else entity_id
        for kind, value, qualifier in raw:
            if kind == "time" and isinstance(value, dict):
                time = str(value.get("time", ""))
                precision = int(value.get("precision", 9))
                rendered = time[1:5] if precision <= 9 else time[1:11]
                claims.append(
                    Claim(
                        entity_id, label, property_id, property_label, rendered, "time", qualifier
                    )
                )
            elif kind == "quantity" and isinstance(value, dict):
                amount = str(value.get("amount", "")).lstrip("+")
                if amount.endswith(".0"):
                    amount = amount[:-2]
                claims.append(
                    Claim(
                        entity_id, label, property_id, property_label, amount, "quantity", qualifier
                    )
                )
            elif (
                kind == "wikibase-entityid"
                and isinstance(value, dict)
                and value.get("id") in labels
            ):
                claims.append(
                    Claim(
                        entity_id,
                        label,
                        property_id,
                        property_label,
                        labels[value["id"]],
                        "item",
                        qualifier,
                    )
                )
            elif kind in {"string", "monolingualtext"}:
                text = value.get("text") if isinstance(value, dict) else value
                if isinstance(text, str) and text:
                    claims.append(
                        Claim(
                            entity_id, label, property_id, property_label, text, "string", qualifier
                        )
                    )
        return claims


class LocalCorpus:
    """Plain-text and Markdown files the user supplies: PolyaBrain's own private index."""

    def __init__(self, root: Path, *, max_files: int = 500, max_bytes: int = 20_000_000) -> None:
        self.root = root.expanduser().resolve()
        if not self.root.is_dir():
            raise SourceError(f"{root} is not a directory")
        self.max_files, self.max_bytes = max_files, max_bytes

    def documents(self) -> list[Document]:
        documents: list[Document] = []
        total = 0
        for path in sorted(self.root.rglob("*")):
            if path.suffix.lower() not in {".txt", ".md", ".rst"} or not path.is_file():
                continue
            if len(documents) >= self.max_files:
                break
            data = path.read_bytes()
            total += len(data)
            if total > self.max_bytes:
                break
            text = data.decode("utf-8", errors="replace")
            title = path.relative_to(self.root).as_posix()
            documents.append(Document("local", title, path.as_uri(), text, len(documents) + 1))
        return documents


def strip_parentheticals(text: str) -> str:
    """Remove pronunciation and aside brackets that split names from their predicates."""
    return re.sub(r"\s*\([^()]{0,160}\)", "", text)
