"""Chapter 11 versioned prompt and state-formatting tests."""

import json

import pytest

from app.graph.state import StateEvent, create_initial_state
from app.llm import LLMRequestOptions
from app.models.contracts import ProductMode, ReasoningMode
from app.problem_understanding import (
    PROBLEM_UNDERSTANDING_EXAMPLES,
    PROBLEM_UNDERSTANDING_PROMPT_VERSION,
    PromptExampleCategory,
    build_problem_understanding_request,
    problem_understanding_system_prompt,
)


def test_examples_cover_all_ten_required_categories_once() -> None:
    categories = [example.category for example in PROBLEM_UNDERSTANDING_EXAMPLES]

    assert len(PROBLEM_UNDERSTANDING_EXAMPLES) == 10
    assert len(set(categories)) == 10
    assert set(categories) == set(PromptExampleCategory)


def test_every_example_output_is_contract_valid_and_canonically_mappable() -> None:
    for example in PROBLEM_UNDERSTANDING_EXAMPLES:
        parsed = type(example.output).model_validate_json(example.output.model_dump_json())

        assert parsed == example.output
        assert parsed.to_structured_problem().success_criteria


def test_system_prompt_contains_version_schema_rules_and_all_examples() -> None:
    prompt = problem_understanding_system_prompt()

    assert PROBLEM_UNDERSTANDING_PROMPT_VERSION in prompt
    assert "OUTPUT_JSON_SCHEMA" in prompt
    assert "given, unknown, constraints, goal, success_criteria" in prompt
    assert "literal_framing" in prompt
    assert "deeper_framing" in prompt
    assert "wrong_problem_warning" in prompt
    assert "investigate, compare, review, or explore" in prompt
    assert "supplied mode_hint as the user override" in prompt
    assert "Do not return Markdown" in prompt
    assert "chain-of-thought" in prompt
    for category in PromptExampleCategory:
        assert f"CATEGORY: {category.value}\n" in prompt


def test_compact_examples_reconstruct_every_contract_field() -> None:
    prompt = problem_understanding_system_prompt()
    rendered = [
        json.loads(line.removeprefix("OUTPUT: "))
        for line in prompt.splitlines()
        if line.startswith("OUTPUT: ")
    ]
    expected = [example.output for example in PROBLEM_UNDERSTANDING_EXAMPLES]

    assert len(rendered) == len(expected) == 10
    for payload, example in zip(rendered, expected, strict=True):
        assert type(example).model_validate(payload) == example


def test_request_formats_polya_state_and_user_override_without_trace_leakage() -> None:
    state = create_initial_state(
        "Review whether our queue migration plan is safe.",
        session_id="session-that-must-not-enter-the-prompt",
    )
    state["iteration_count"] = 1
    state["events"] = [
        StateEvent(
            engine_name="test",
            event_type="private",
            reasoning_mode=ReasoningMode.EXPLORE,
            summary="private-trace-content",
        )
    ]

    request = build_problem_understanding_request(
        state,
        model="fake-model",
        mode_hint=ProductMode.REVIEW,
        domain_hint=" software_architecture ",
    )
    user_payload = json.loads(request.messages[1].content)

    assert request.options.json_mode is True
    assert request.options.max_retries == 1
    assert request.options.total_timeout_seconds == 90
    assert request.model == "fake-model"
    assert user_payload == {
        "raw_input": "Review whether our queue migration plan is safe.",
        "mode_hint": "review",
        "domain_hint": "software_architecture",
        "iteration_count": 1,
    }
    assert "session-that-must-not-enter-the-prompt" not in request.messages[1].content
    assert "private-trace-content" not in request.messages[1].content


def test_problem_understanding_request_requires_json_mode() -> None:
    state = create_initial_state("Investigate a timeout.")

    with pytest.raises(ValueError, match="requires JSON mode"):
        build_problem_understanding_request(
            state,
            model="fake-model",
            options=LLMRequestOptions(json_mode=False),
        )
