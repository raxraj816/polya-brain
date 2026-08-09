#!/usr/bin/env python3
"""Run all Chapter 11 golden examples through the fake-client boundary."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for import_path in (ROOT, BACKEND):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from app.graph.state import create_initial_state
from app.llm import FakeLLMClient, LLMResponse
from app.problem_understanding import (
    PROBLEM_UNDERSTANDING_EXAMPLES,
    PromptExampleCategory,
    generate_problem_understanding,
)


def main() -> None:
    expected_categories = {category.value for category in PromptExampleCategory}
    actual_categories = {example.category.value for example in PROBLEM_UNDERSTANDING_EXAMPLES}
    if len(PROBLEM_UNDERSTANDING_EXAMPLES) != 10 or actual_categories != expected_categories:
        raise SystemExit("Chapter 11 requires exactly one example for each required category")

    verified_categories: list[str] = []
    for index, example in enumerate(PROBLEM_UNDERSTANDING_EXAMPLES):
        client = FakeLLMClient(
            [
                LLMResponse(
                    provider="fake",
                    model="chapter11-golden-model",
                    text=example.output.model_dump_json(),
                    response_id=f"chapter11_example_{index}",
                )
            ]
        )
        result = generate_problem_understanding(
            client,
            create_initial_state(example.raw_input, session_id=f"chapter11_{index}"),
            model="chapter11-golden-model",
            mode_hint=example.mode_hint,
            domain_hint=example.domain_hint,
            sleep=lambda _: None,
        )
        if result.output != example.output:
            raise SystemExit(f"Chapter 11 example failed: {example.category.value}")
        if result.structured_problem != example.output.to_structured_problem():
            raise SystemExit(f"Chapter 11 contract mapping failed: {example.category.value}")
        verified_categories.append(example.category.value)

    print(
        f"Chapter 11 examples verified: {len(verified_categories)} "
        f"({', '.join(verified_categories)})"
    )


if __name__ == "__main__":
    main()
