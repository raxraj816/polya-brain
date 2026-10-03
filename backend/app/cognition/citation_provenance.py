"""Necessary citation provenance checks; never a semantic truth certificate."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit, urlunsplit

from markdown_it import MarkdownIt
from markdown_it.token import Token

from app.graph.state import PolyaState, StateEvent
from app.models.contracts import ReasoningMode, VerificationReport

VERSION = "citation_provenance@0.1.0"
EVENT = "citation_provenance_checked"
MAX_ANSWER_CHARS = 200_000
MAX_SOURCE_CHARS = 2_000_000
MAX_LINKS = 128
MAX_URL_CHARS = 2048
UNVERIFIED_PREFIX = "Unverified link (not evidence):"
INSTRUCTIONS = (
    "Cite only web sources present in admitted evidence with a raw excerpt. "
    "A numbered section citation must name a heading actually retained in that "
    "source excerpt, not a cross-reference to an unread section. Other anchors must "
    "already be part of the admitted source URI; otherwise cite the document URL. "
    "Do not invent URLs, drop distinguishing query parameters or infer redirects. "
    "All narrative web links are treated as citations. Put example URLs in code. "
    "For a future research target, use a standalone paragraph containing only "
    "'Unverified link (not evidence):' and one link, with no factual claim. "
    "Neither such a link nor a matching URL/heading proves the associated claim. "
)
_NUMBERED_FRAGMENT = re.compile(r"(?:section-)?(\d+(?:\.\d+)*)\Z", re.IGNORECASE)
# A cross-reference such as '(Section 9.3.1)' must not manufacture a heading.
_HEADING = re.compile(r"(?m)^[ \t]{0,3}(?:#{1,6}[ \t]+)?(\d+(?:\.\d+)*)(?:\.)?[ \t]+[^\n]+$")


@dataclass(frozen=True)
class CitationCheck:
    checked_links: int = 0
    unverified_links: int = 0
    failures: tuple[str, ...] = ()

    def event(self, answer: str, engine: str) -> StateEvent:
        return StateEvent(
            engine_name=engine,
            event_type=EVENT,
            reasoning_mode=ReasoningMode.VERIFY,
            summary="Citation provenance failed."
            if self.failures
            else "No detected citation provenance failure; semantic verification remains required.",
            metadata={
                "version": VERSION,
                "passed": not self.failures,
                "checked_links": self.checked_links,
                "unverified_links": self.unverified_links,
                "failures": list(self.failures),
                "answer_sha256": hashlib.sha256(answer.encode()).hexdigest(),
                "rejected_answer": answer[:16_000] if self.failures else None,
                "rejected_answer_truncated": bool(self.failures and len(answer) > 16_000),
                "scope": "Source and locator coverage only, not semantic entailment or source truth.",
            },
        )

    def reject(self, report: VerificationReport) -> VerificationReport:
        return VerificationReport(
            passed=False,
            checks_run=[*report.checks_run, "Checked citations against admitted source excerpts."],
            failed_checks=[*report.failed_checks, *self.failures],
            contradictions=report.contradictions,
            confidence_delta=-0.2,
            recommended_route=(
                "Revise citations to match admitted evidence, or acquire the missing source "
                "passage, then independently verify again."
            ),
        )


def _url(value: str) -> tuple[str, str] | None:
    """Do not merge schemes, paths, queries, credentials or redirect aliases."""
    if (
        len(value) > MAX_URL_CHARS
        or any(c.isspace() or ord(c) < 32 for c in value)
        or "\\" in value
        or re.search(r"%(?![0-9a-fA-F]{2})", value)
    ):
        return None
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
        ):
            return None
        host = parsed.hostname.encode("idna").decode("ascii").lower()
        if ":" in host:
            host = f"[{host}]"
        port = parsed.port
        if port is not None and port != (443 if parsed.scheme == "https" else 80):
            host += f":{port}"
        # Percent-escape hex case is equivalent; reserved escapes remain escaped.
        path = re.sub(r"%[0-9a-fA-F]{2}", lambda m: m[0].upper(), parsed.path or "/")
        query = re.sub(r"%[0-9a-fA-F]{2}", lambda m: m[0].upper(), parsed.query)
        return urlunsplit((parsed.scheme, host, path, query, "")), unquote(
            parsed.fragment, errors="strict"
        )
    except ValueError, UnicodeError:
        return None


def _unverified_target(children: list[Token]) -> bool:
    """Only an entire explicitly disclaimed paragraph can opt out of evidence."""
    # Restrict content to the prefix, one link and optional terminal punctuation.
    # A later factual sentence or a second link cannot inherit the disclaimer.
    if not children or children[0].type != "text":
        return False
    if children[0].content.strip() != UNVERIFIED_PREFIX:
        return False
    if len(children) < 4 or children[1].type != "link_open":
        return False
    closing = next((i for i, token in enumerate(children) if token.type == "link_close"), -1)
    if closing < 3:
        return False
    # Labels may have emphasis, but not another destination or embedded code.
    if any(
        t.type not in {"text", "em_open", "em_close", "strong_open", "strong_close"}
        for t in children[2:closing]
    ):
        return False
    return all(t.type == "text" and not t.content.strip(" .") for t in children[closing + 1 :])


def check_citations(state: PolyaState, answer: str) -> CitationCheck:
    """Screen rendered web references while leaving code examples untouched."""
    if len(answer) > MAX_ANSWER_CHARS:
        return CitationCheck(failures=("Citation check exceeded its answer-size limit.",))
    parser = MarkdownIt("gfm-like", {"html": False, "maxNesting": 32})
    links: list[str] = []
    unverified = 0
    previous: Token | None = None
    for block in parser.parse(answer):
        if block.type == "inline":
            children = block.children or []
            targets = [
                str(child.attrGet("href"))
                for child in children
                if child.type == "link_open"
                and str(child.attrGet("href")).lower().startswith(("http:", "https:", "//"))
            ]
            if len(links) + unverified + len(targets) > MAX_LINKS:
                return CitationCheck(failures=("Citation check exceeded its link-count limit.",))
            if (
                previous is not None
                and previous.type == "paragraph_open"
                and len(targets) == 1
                and _unverified_target(children)
            ):
                unverified += 1
            else:
                links.extend(targets)
        previous = block
    if not links:
        return CitationCheck(unverified_links=unverified)
    if sum(len(item.raw_excerpt or "") for item in state["evidence"]) > MAX_SOURCE_CHARS:
        return CitationCheck(failures=("Citation check exceeded its source-size limit.",))
    sources: dict[str, list[tuple[str, str]]] = {}
    for item in state["evidence"]:
        parsed = _url(item.source_uri or "")
        if parsed is not None and item.raw_excerpt and item.raw_excerpt.strip():
            uri, fragment = parsed
            sources.setdefault(uri, []).append((fragment, item.raw_excerpt))
    failures: list[str] = []
    for target in dict.fromkeys(links):
        parsed = _url(target)
        if parsed is None:
            failures.append(
                f"Citation has an invalid or unsupported web URL: {target[:MAX_URL_CHARS]}"
            )
            continue
        uri, fragment = parsed
        snapshots = sources.get(uri, [])
        if not snapshots:
            failures.append(f"Citation has no admitted source with a raw excerpt: {target}")
            continue
        if not fragment:
            continue
        numbered = _NUMBERED_FRAGMENT.fullmatch(fragment)
        if numbered:
            if not any(numbered[1] in _HEADING.findall(excerpt) for _, excerpt in snapshots):
                failures.append(
                    f"Citation section is absent from admitted source headings: {target}"
                )
        elif not any(fragment == source_fragment for source_fragment, _ in snapshots):
            failures.append(
                f"Citation locator is not recorded in the admitted source URI: {target}"
            )
    return CitationCheck(len(links), unverified, tuple(failures))
