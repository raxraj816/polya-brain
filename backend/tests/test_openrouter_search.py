"""Online acquisition preserves sources, bounded dispatch and honest usage."""

import asyncio
import json
from time import perf_counter

import httpx
import pytest
from pydantic import ValidationError

from app.acquisition import ResearchBudget, SearchRequest, web_search_capability
from app.acquisition.openrouter import (
    MAX_EXCERPT_CHARACTERS,
    MAX_RESPONSE_BYTES,
    SEARCH_OUTPUT_TOKEN_RESERVE,
    OpenRouterSearchProvider,
)
from app.acquisition.providers import SearchProviderError
from app.cognition import CognitiveActionCandidate, CognitiveActionType
from app.cognition.bootstrap import build_cognitive_runtime
from app.cognition.contracts import CapabilityDefinition, CapabilityKind, ObservationStatus
from app.cognition.task_model import resource_usage_for
from app.config import Settings
from app.graph.state import create_initial_state


def settings(**kwargs):
    return Settings(
        _env_file=None,
        OPENROUTER_API_KEY="private-test-key",
        OPENROUTER_MODEL="test-model",
        OPENROUTER_FALLBACK_MODELS="",
        **kwargs,
    )


def response_payload():
    return {
        "choices": [
            {
                "message": {
                    "content": "UNSUPPORTED SYNTHESIZED ANSWER: all tests passed.",
                    "annotations": [
                        {
                            "type": "url_citation",
                            "url_citation": {
                                "url": "https://science.example.org/result",
                                "title": "Measured result",
                                "content": "The observed period changed by 33 minutes.",
                            },
                        }
                    ],
                }
            }
        ],
        "usage": {
            "prompt_tokens": 120,
            "completion_tokens": 30,
            "cost": 0.008,
            "server_tool_use_details": {"web_search_requests": 1},
        },
    }


def action():
    return CognitiveActionCandidate(
        id="search-gap",
        action_type=CognitiveActionType.SEARCH,
        target="Measured orbital change",
        purpose="Acquire source evidence.",
        expected_observation="Original source excerpts.",
        expected_usefulness=0.8,
        estimated_cost=0.2,
        capability="web_search",
        success_condition="Candidates available.",
        failure_condition="No usable source.",
    )


def test_search_uses_only_annotations_and_bounds_every_provider_control():
    def handler(request):
        assert request.headers["Authorization"] == "Bearer private-test-key"
        payload = json.loads(request.content)
        assert "private-test-key" not in request.content.decode()
        assert payload["max_tool_calls"] == 1
        assert payload["max_tokens"] * 2 == SEARCH_OUTPUT_TOKEN_RESERVE
        assert payload["parallel_tool_calls"] is False
        assert payload["provider"] == {"data_collection": "deny", "zdr": False}
        parameters = payload["tools"][0]["parameters"]
        assert parameters == {
            "engine": "exa",
            "max_uses": 1,
            "max_results": 2,
            "max_total_results": 2,
            "max_characters": MAX_EXCERPT_CHARACTERS,
        }
        return httpx.Response(200, json=response_payload())

    provider = OpenRouterSearchProvider(settings(), transport=httpx.MockTransport(handler))
    result = provider.search(SearchRequest(query="orbital period change", max_results=2))
    assert result.candidates[0].excerpt == "The observed period changed by 33 minutes."
    assert "SYNTHESIZED" not in result.model_dump_json()
    assert "private-test-key" not in result.model_dump_json()
    assert result.metadata["usage"]["input_tokens"] == 120
    assert result.metadata["usage"]["estimated_cost_usd"] == 0.008
    assert result.metadata["server_search_uses"] == 1


@pytest.mark.parametrize(
    "defect",
    [
        "no_annotation",
        "no_excerpt",
        "no_search",
        "too_many_searches",
        "unknown_search",
        "no_usage",
        "negative_usage",
        "bool_usage",
        "provider_error",
        "bad_url",
    ],
)
def test_missing_sources_or_invalid_telemetry_cannot_become_research(defect):
    payload = response_payload()
    citation = payload["choices"][0]["message"]["annotations"][0]["url_citation"]
    if defect == "no_annotation":
        payload["choices"][0]["message"].pop("annotations")
    elif defect == "no_excerpt":
        citation.pop("content")
    elif defect == "no_search":
        payload["usage"]["server_tool_use_details"]["web_search_requests"] = 0
    elif defect == "too_many_searches":
        payload["usage"]["server_tool_use_details"]["web_search_requests"] = 2
    elif defect == "unknown_search":
        payload["usage"].pop("server_tool_use_details")
    elif defect == "no_usage":
        payload.pop("usage")
    elif defect == "negative_usage":
        payload["usage"]["prompt_tokens"] = -1
    elif defect == "bool_usage":
        payload["usage"]["prompt_tokens"] = True
    elif defect == "provider_error":
        payload["error"] = {"message": "private-test-key"}
    elif defect == "bad_url":
        citation["url"] = "file:///private/source"
    provider = OpenRouterSearchProvider(
        settings(), transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload))
    )
    with pytest.raises(SearchProviderError) as failure:
        provider.search(SearchRequest(query="Find evidence."))
    assert "private-test-key" not in str(failure.value)
    assert failure.value.metadata["model_calls"] == 1
    assert failure.value.metadata["external_calls"] == (2 if defect == "too_many_searches" else 1)


def test_search_failure_and_success_both_record_model_and_external_resources():
    provider = OpenRouterSearchProvider(
        settings(),
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=response_payload())),
    )
    capability = web_search_capability(
        provider, max_model_calls=1, max_output_tokens=SEARCH_OUTPUT_TOKEN_RESERVE
    )
    state = create_initial_state("Find measured orbital change.")
    observation = capability.execute(action(), state)
    usage = resource_usage_for(capability.definition, observation.payload)
    assert observation.status is ObservationStatus.SUCCEEDED
    assert (usage.model_calls, usage.external_calls, usage.input_tokens, usage.output_tokens) == (
        1,
        1,
        120,
        30,
    )
    assert observation.evidence == []  # Candidates still need the separate evidence gate.
    assert (
        observation.proposed_update.trace_events_to_add[-1].metadata["provider_metadata"][
            "server_search_uses"
        ]
        == 1
    )

    failed_provider = OpenRouterSearchProvider(
        settings(),
        transport=httpx.MockTransport(
            lambda r: httpx.Response(429, json={"error": "private-test-key"})
        ),
    )
    capability = web_search_capability(
        failed_provider, max_model_calls=1, max_output_tokens=SEARCH_OUTPUT_TOKEN_RESERVE
    )
    observation = capability.execute(action(), state)
    usage = resource_usage_for(capability.definition, observation.payload)
    assert observation.status is ObservationStatus.FAILED
    assert usage.model_calls == usage.external_calls == 1
    assert observation.payload["provider_usage_known"] is False
    assert "private-test-key" not in observation.model_dump_json()


def test_exhausted_research_budget_does_not_spend_model_or_external_calls():
    def unexpected(request):
        raise AssertionError("Network must not be called")

    provider = OpenRouterSearchProvider(settings(), transport=httpx.MockTransport(unexpected))
    capability = web_search_capability(
        provider,
        max_model_calls=1,
        budget=ResearchBudget(max_queries=1),
        prior_query_count=lambda s: 1,
    )
    observation = capability.execute(action(), create_initial_state("Find evidence."))
    usage = resource_usage_for(capability.definition, observation.payload)
    assert usage.model_calls == usage.external_calls == 0


def test_total_deadline_cancels_trickling_body_and_closes_stream():
    class Trickle(httpx.AsyncByteStream):
        closed = False

        async def __aiter__(self):
            while True:
                await asyncio.sleep(0.01)
                yield b" "

        async def aclose(self):
            self.closed = True

    stream = Trickle()
    provider = OpenRouterSearchProvider(
        settings(),
        transport=httpx.MockTransport(lambda r: httpx.Response(200, stream=stream)),
        timeout_seconds=0.05,
    )
    started = perf_counter()
    with pytest.raises(SearchProviderError, match="timed out"):
        provider.search(SearchRequest(query="Find evidence."))
    assert perf_counter() - started < 1
    assert stream.closed


def test_oversized_body_fails_before_parsing_or_promotion():
    provider = OpenRouterSearchProvider(
        settings(),
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, content=b"x" * (MAX_RESPONSE_BYTES + 1))
        ),
    )
    with pytest.raises(SearchProviderError):
        provider.search(SearchRequest(query="Find evidence."))


def test_search_is_explicitly_configured_and_reserves_both_budgets():
    runtime = build_cognitive_runtime(settings(SEARCH_PROVIDER="openrouter"))
    definition = runtime._registry.get("web_search").definition
    assert definition.kind is CapabilityKind.EXTERNAL
    assert definition.max_model_calls == definition.max_external_calls == 1
    assert definition.max_output_tokens == SEARCH_OUTPUT_TOKEN_RESERVE
    assert build_cognitive_runtime(settings(SEARCH_PROVIDER=""))._registry.get("web_search") is None
    with pytest.raises(ValidationError):
        CapabilityDefinition(
            name="fake-free-model",
            version="test",
            supported_actions={CognitiveActionType.SEARCH},
            kind=CapabilityKind.DETERMINISTIC,
            max_model_calls=1,
        )
