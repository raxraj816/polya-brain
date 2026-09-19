"""Public page limits, network pinning, candidate gates and controller routing."""

import asyncio

import httpx
import pytest
from test_scope_review import TARGET, action, state_with_stalled_research

from app.acquisition.page_reader import (
    ATTEMPT_EVENT,
    MAX_BYTES,
    PublicPageReader,
    page_read_target,
    public_page_capability,
    selected_passages,
)
from app.cognition import CapabilityRegistry, CognitiveActionType, CognitiveController
from app.cognition.kernel import apply_cognitive_observation
from app.cognition.task_model import CognitiveResourceBudget, budget_event


async def public_dns(host):
    return ["93.184.216.34"]


def test_reader_pins_public_ip_and_retains_hostname_for_tls_and_http():
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text=(
                "<html><script>bad script instruction</script><style>hidden CSS</style>"
                "<p>GET is safe.</p><p>PUT is idempotent.</p></html>"
            ),
        )

    reader = PublicPageReader(transport=httpx.MockTransport(handle), resolver=public_dns)
    excerpt, metadata = reader.read("https://official.example.org/rule#anchor", "safe idempotent")
    assert calls[0].url.host == "93.184.216.34"
    assert calls[0].headers["host"] == "official.example.org"
    assert calls[0].extensions["sni_hostname"] == "official.example.org"
    assert calls[0].url.fragment == ""
    assert "GET is safe." in excerpt and "PUT is idempotent." in excerpt
    assert "script instruction" not in excerpt and "hidden CSS" not in excerpt
    assert len(metadata["body_sha256"]) == 64
    assert metadata["selected_offsets"]


@pytest.mark.parametrize(
    "addresses",
    [
        [],
        ["127.0.0.1"],
        ["10.0.0.1"],
        ["169.254.169.254"],
        ["::1"],
        ["93.184.216.34", "192.168.0.1"],
    ],
)
def test_nonpublic_or_mixed_dns_never_connects(addresses):
    async def resolve(host):
        return addresses

    def forbidden(request):
        pytest.fail("A disallowed destination was contacted")

    with pytest.raises(ValueError):
        PublicPageReader(resolver=resolve, transport=httpx.MockTransport(forbidden)).read(
            "https://public.example/path", "query"
        )


@pytest.mark.parametrize(
    "url",
    [
        "http://public.example/path",
        "file:///etc/passwd",
        "https://user:pass@public.example/",
        "https://public.example:8080/path",
    ],
)
def test_invalid_url_never_resolves(url):
    async def forbidden(host):
        pytest.fail("Invalid URL was resolved")

    with pytest.raises(ValueError):
        PublicPageReader(resolver=forbidden).read(url, "query")


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(302, headers={"location": "https://127.0.0.1/"}),
        httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"pdf"),
        httpx.Response(200, headers={"content-type": "text/plain"}, content=b"x" * (MAX_BYTES + 1)),
    ],
)
def test_redirect_type_size_and_encoding_fail_without_followup(response):
    calls = []

    def handle(request):
        calls.append(request)
        return response

    with pytest.raises(ValueError):
        PublicPageReader(transport=httpx.MockTransport(handle), resolver=public_dns).read(
            "https://public.example/", "query"
        )
    assert len(calls) == 1


def test_total_deadline_bounds_slow_body_and_dns():
    class SlowBody(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"one"
            await asyncio.sleep(1)
            yield b"two"

    reader = PublicPageReader(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, headers={"content-type": "text/plain"}, stream=SlowBody())
        ),
        resolver=public_dns,
        timeout_seconds=0.02,
    )
    with pytest.raises(TimeoutError):
        reader.read("https://public.example/", "query")

    async def slow_dns(host):
        await asyncio.sleep(1)
        return ["93.184.216.34"]

    with pytest.raises(TimeoutError):
        PublicPageReader(resolver=slow_dns, timeout_seconds=0.02).read(
            "https://public.example/", "query"
        )


def test_passages_find_late_material_with_bounded_nonoverlapping_offsets():
    text = (
        "unrelated preface " * 2000
        + "\nIdempotent methods can be retried after a lost response. " * 40
    )
    excerpt, spans = selected_passages(text, "idempotent retried lost response")
    assert "Idempotent methods" in excerpt and len(excerpt) <= 9000
    assert all(b <= c for (_, b), (c, _) in zip(spans, spans[1:], strict=False))
    assert all(text[a:b] in excerpt for a, b in spans)


def page_action():
    return action().model_copy(
        update={"action_type": CognitiveActionType.SEARCH, "capability": "public_page_reader"}
    )


def test_candidate_is_staged_not_admitted_and_never_read_twice():
    state = state_with_stalled_research()
    reader = PublicPageReader(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(
                200,
                headers={"content-type": "text/plain"},
                text="The source says a negative response has a lifetime.",
            )
        ),
        resolver=public_dns,
    )
    capability = public_page_capability(reader)
    observation = capability.execute(page_action(), state)
    assert observation.payload["external_calls"] == 1 and observation.payload["model_calls"] == 0
    revised = apply_cognitive_observation(state, observation)
    assert revised["evidence"] == state["evidence"] and revised["gaps"] == state["gaps"]
    assert page_read_target(revised, TARGET) is None
    assert any(
        e.event_type == "evidence_candidates_acquired"
        and e.metadata.get("source_type") == "web_page"
        for e in revised["events"]
    )
    assert capability.execute(page_action(), revised).payload["external_calls"] == 0


def test_failed_read_is_audited_and_cannot_repeat():
    state = state_with_stalled_research()
    reader = PublicPageReader(
        transport=httpx.MockTransport(lambda r: httpx.Response(404)), resolver=public_dns
    )
    observation = public_page_capability(reader).execute(page_action(), state)
    assert observation.failure_kind == "public_page_read_failed"
    revised = apply_cognitive_observation(state, observation)
    assert page_read_target(revised, TARGET) is None
    assert len([e for e in revised["events"] if e.event_type == ATTEMPT_EVENT]) == 1


def test_read_requires_admitted_source_and_controller_privacy_budget():
    state = state_with_stalled_research()
    registry = CapabilityRegistry()
    registry.register(public_page_capability(PublicPageReader()))
    assert CognitiveController().decide(state, registry).selected.capability == "public_page_reader"
    state["events"].append(budget_event(CognitiveResourceBudget(max_external_calls=0)))
    assert CognitiveController().decide(state, registry).selected.capability != "public_page_reader"
    state = state_with_stalled_research()
    state["structured_problem"].constraints.append("Private data must remain private.")
    assert CognitiveController().decide(state, registry).selected.capability != "public_page_reader"
    state["evidence"] = []
    assert page_read_target(state, TARGET) is None


def test_page_budget_stops_before_network():
    state = state_with_stalled_research()
    cap = public_page_capability(PublicPageReader(), max_total_candidates=0)
    assert cap.execute(page_action(), state).payload["external_calls"] == 0


def test_rare_query_terms_outrank_repeated_generic_protocol_words():
    generic = "server client request response method resource " * 2500
    crucial = "Specific idempotent retry semantics establish the bounded guarantee. " * 45
    excerpt, _ = selected_passages(
        generic + crucial,
        "server client request response method resource idempotent retry semantics",
    )
    assert "Specific idempotent retry semantics" in excerpt


def test_page_selection_prefers_document_named_by_residual_query():
    state = state_with_stalled_research()
    original = state["evidence"][0]
    state["evidence"] = [
        original.model_copy(update={"source_uri": url})
        for url in (
            "https://official.example.org/rfc9112.html",
            "https://official.example.org/rfc9110.html",
        )
    ]
    state["events"][-1].metadata["next_query"] = "RFC 9110 safe idempotent methods"
    assert page_read_target(state, TARGET) == "https://official.example.org/rfc9110.html"


def test_offline_composition_omits_page_reader():
    from app.cognition.bootstrap import build_cognitive_runtime
    from app.config import Settings

    runtime = build_cognitive_runtime(
        Settings(SEARCH_PROVIDER="", OPENROUTER_API_KEY="", OPENROUTER_MODEL="")
    )
    assert runtime._registry.get("public_page_reader") is None


def test_numbered_sections_preserve_definition_with_following_examples():
    text = (
        "1. Introduction\n"
        + "General background. " * 180
        + "\n2. Safe methods\nA safe method is read-only.\n"
        + "Safe methods do not request state changes. " * 30
        + "\n3. Idempotent methods\nRepeated identical requests have the same intended effect.\n"
        + "Idempotent retry semantics allow bounded retry. " * 30
        + "\n4. Other information\n"
        + "Unrelated background. " * 180
    )
    excerpt, _ = selected_passages(text, "safe idempotent method retry semantics")
    assert "A safe method is read-only." in excerpt
    assert "Repeated identical requests have the same intended effect." in excerpt
    assert len(excerpt) <= 9000


def test_dns_cancellation_kills_and_reaps_resolver_process(monkeypatch):
    from app.acquisition.page_reader import resolve_public_addresses

    class Process:
        returncode = None
        killed = False
        reaped = False

        async def communicate(self):
            await asyncio.sleep(1)
            return b"[]", b""

        def kill(self):
            self.killed = True
            self.returncode = -9

        async def wait(self):
            self.reaped = True

    process = Process()

    async def create(*args, **kwargs):
        assert args[-1] == "public.example"
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create)

    async def run():
        async with asyncio.timeout(0.02):
            await resolve_public_addresses("public.example")

    with pytest.raises(TimeoutError):
        asyncio.run(run())
    assert process.killed and process.reaped


def test_failed_page_read_does_not_disable_remaining_search_route():
    from test_knowledge_acquisition import FakeSearchProvider

    from app.acquisition.capabilities import web_search_capability
    from app.cognition.kernel import CognitiveKernel

    state = state_with_stalled_research()
    registry = CapabilityRegistry()
    registry.register(
        public_page_capability(
            PublicPageReader(
                resolver=public_dns, transport=httpx.MockTransport(lambda r: httpx.Response(404))
            )
        )
    )
    registry.register(web_search_capability(FakeSearchProvider()))
    result = CognitiveKernel(registry).run(state, max_cycles=1)
    assert result.observations[0].failure_kind == "public_page_read_failed"
    assert CognitiveController().decide(result.state, registry).selected.capability == "web_search"


def test_section_titles_match_singular_query_and_ignore_status_sentences():
    text = "1. General HTTP material\n" + "Server request response semantics. " * 80
    text += (
        "\n2. Safe Methods\nSafe methods are essentially read-only.\n"
        + "A method can cause incidental effects. " * 65
    )
    text += (
        "\n3. Idempotent Methods\nMultiple identical requests have the same intended effect.\n"
        + "An idempotent method may be retried after failure. " * 40
    )
    text += (
        "\n4. Other HTTP material\n"
        + "304 Not Modified response and HTTP request semantics.\n" * 120
    )
    excerpt, _ = selected_passages(
        text, "HTTP safe method idempotent method request response semantics retry"
    )
    assert "Safe methods are essentially read-only." in excerpt
    assert "Multiple identical requests have the same intended effect." in excerpt


def test_acquisition_module_imports_without_prior_cognition_import():
    import os
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-c", "from app.acquisition.page_reader import PublicPageReader"],
        env={**os.environ, "PYTHONPATH": "backend"},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr


def test_passage_budget_covers_six_named_sections_without_one_crowding_out_others():
    names = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta"]
    text = "\n".join(
        f"{i}. {name}\n" + "Shared background discussion. " * 180 for i, name in enumerate(names, 1)
    )
    excerpt, spans = selected_passages(text, "Compare " + " ".join(names))
    assert all(f"{i}. {name}" in excerpt for i, name in enumerate(names, 1))
    assert len(spans) == 6 and len(excerpt) <= 9000


def test_unresolved_page_read_returns_to_search_before_reading_another_page():
    from test_knowledge_acquisition import FakeSearchProvider

    from app.acquisition.capabilities import web_search_capability
    from app.graph.state import StateEvent
    from app.models.contracts import ReasoningMode

    state = state_with_stalled_research()
    state["evidence"].append(
        state["evidence"][0].model_copy(update={"source_uri": "https://official.example.org/other"})
    )
    cap = public_page_capability(
        PublicPageReader(
            resolver=public_dns,
            transport=httpx.MockTransport(
                lambda r: httpx.Response(
                    200,
                    headers={"content-type": "text/plain"},
                    text="A relevant but incomplete source passage.",
                )
            ),
        )
    )
    observation = cap.execute(page_action(), state)
    state = apply_cognitive_observation(state, observation)
    state["events"].append(
        StateEvent(
            engine_name="evidence_evaluator",
            event_type="evidence_evaluation_completed",
            reasoning_mode=ReasoningMode.EXPLORE,
            summary="Still missing applicability.",
            metadata={
                "acquisition_id": observation.payload["acquisition_id"],
                "gap_resolved": False,
            },
        )
    )
    registry = CapabilityRegistry()
    registry.register(cap)
    registry.register(web_search_capability(FakeSearchProvider()))
    assert page_read_target(state, TARGET) is None
    assert CognitiveController().decide(state, registry).selected.capability == "web_search"
    for kind, metadata in [
        (
            "evidence_candidates_acquired",
            {"acquisition_id": "fresh-discovery", "target_gap": TARGET},
        ),
        (
            "evidence_evaluation_completed",
            {"acquisition_id": "fresh-discovery", "gap_resolved": False},
        ),
    ]:
        state["events"].append(
            StateEvent(
                engine_name="web_search",
                event_type=kind,
                reasoning_mode=ReasoningMode.EXPLORE,
                summary="Fresh research.",
                metadata=metadata,
            )
        )
    assert page_read_target(state, TARGET) == "https://official.example.org/other"
