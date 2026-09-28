"""Attach reviewed implementations without asking a model to regenerate tested code."""

from __future__ import annotations

import hashlib
import json
import re

from pydantic import JsonValue

from app.cognition.execution_verification import active_sandbox_tasks, sandbox_verification_failures
from app.execution.sandbox import SandboxExecutionResult
from app.graph.state import PolyaState

VERSION = "tested_code_delivery@0.1.0"
PREFIX = "[[POLYABRAIN_CODE:"
MARKER = re.compile(r"^\[\[POLYABRAIN_CODE:([a-f0-9]{64})\]\]$", re.MULTILINE)


def _implementations(state: PolyaState) -> dict[str, str]:
    if sandbox_verification_failures(state):
        return {}
    result = {}
    for task in active_sandbox_tasks(state):
        code = task.params.get("code")
        if not isinstance(code, str) or not code.strip() or re.search(r"^```", code, re.MULTILINE):
            return {}
        # The execution producer binds exact inputs and outputs, so edits to a
        # saved plan/result cannot borrow an older passing execution observation.
        events = [
            event
            for event in state["events"]
            if event.engine_name == "python_sandbox"
            and event.event_type == "sandbox_execution_completed"
            and event.metadata.get("task_id") == task.id
        ]
        output = next(item for item in state["execution_outputs"] if item.task_id == task.id)
        execution = SandboxExecutionResult.model_validate(output.output)
        expected = {
            "code_sha256": hashlib.sha256(code.encode()).hexdigest(),
            "tests_sha256": hashlib.sha256(
                json.dumps(task.params["tests"], separators=(",", ":")).encode()
            ).hexdigest(),
            "result_sha256": hashlib.sha256(execution.model_dump_json().encode()).hexdigest(),
        }
        if len(events) != 1 or any(
            events[0].metadata.get(key) != value for key, value in expected.items()
        ):
            return {}
        code = code.strip()
        result[hashlib.sha256(code.encode()).hexdigest()] = code
    return result


def code_delivery_context(state: PolyaState) -> dict[str, JsonValue]:
    """Offer only references to complete, successfully executed current code."""
    implementations = _implementations(state)
    if not implementations:
        return {}
    return {
        "tested_code_delivery": {
            "version": VERSION,
            "references": [
                {"marker": f"{PREFIX}{digest}]]", "code_sha256": digest}
                for digest in implementations
            ],
            "scope": "Delivery only. Independently review all code, tests and requirements in canonical state.",
        }
    }


def assemble_tested_code(state: PolyaState, answer: str) -> tuple[str, dict[str, JsonValue] | None]:
    """Expand a complete reference-only delivery; reject ambiguity rather than repair it."""
    if PREFIX not in answer:
        return answer, None
    implementations = _implementations(state)
    matches = list(MARKER.finditer(answer))
    digests = [match.group(1) for match in matches]
    if (
        not implementations
        or "```" in answer
        or answer.count(PREFIX) != len(matches)
        or len(digests) != len(set(digests))
        or set(digests) != set(implementations)
    ):
        raise ValueError(
            "Code delivery references must name every active tested implementation exactly once on separate lines."
        )
    # Replace matches in the original response only; never interpret inserted code.
    assembled = MARKER.sub(
        lambda match: f"```python\n{implementations[match.group(1)]}\n```", answer
    )
    bindings: list[JsonValue] = [
        {
            "task_id": task.id,
            "code_sha256": hashlib.sha256(str(task.params["code"]).strip().encode()).hexdigest(),
        }
        for task in active_sandbox_tasks(state)
    ]
    return assembled, {
        "version": VERSION,
        "bindings": bindings,
        "implementation_count": len(implementations),
        "code_characters_attached": sum(len(code) for code in implementations.values()),
        "provider_answer_sha256": hashlib.sha256(answer.encode()).hexdigest(),
        "delivered_answer_sha256": hashlib.sha256(assembled.encode()).hexdigest(),
    }
