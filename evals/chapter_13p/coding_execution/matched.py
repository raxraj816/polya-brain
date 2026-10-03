"""Repeated development pilot: production runtime versus a lean tool repair loop."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.cognition.bootstrap import build_cognitive_runtime
from app.config import Settings
from app.execution import DockerPythonSandbox, DockerSandboxLimits
from app.execution.sandbox import PYTHON_TEST_HARNESS_VERSION
from app.investigator.artifacts import export_run
from app.llm import (
    LLMClientError,
    LLMErrorCode,
    LLMMessage,
    LLMRequest,
    LLMRequestOptions,
    LLMRole,
    OpenRouterLLMClient,
)

from .evidence import checks_digest, digest, execution_passed, extract_code, load_cases
from .verify import CHECKS, verify


@dataclass(frozen=True)
class Limits:
    model_calls: int = 6
    output_tokens: int = 20000
    per_request_output_tokens: int = 6000
    sandbox_calls: int = 4
    seconds: float = 240


DEFAULT_LIMITS = Limits()


def save(path: Path, value) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2) + "\n")


class Meter:
    """One common outer budget and append-only request/tool ledger for either arm."""

    def __init__(self, client, model, sandbox, directory: Path, limits=DEFAULT_LIMITS):
        self.client, self.model, self.sandbox = client, model, sandbox
        self.directory, self.limits = directory, limits
        self.provider, self.capabilities = client.provider, client.capabilities
        self.calls = self.tool_calls = self.input_tokens = self.output_tokens = 0
        self.usage_complete = True
        self.started = perf_counter()

    def remaining_seconds(self):
        return self.limits.seconds - (perf_counter() - self.started)

    def complete(self, request):
        remaining = self.limits.output_tokens - self.output_tokens
        if (
            request.model != self.model
            or self.calls >= self.limits.model_calls
            or remaining <= 0
            or self.remaining_seconds() <= 0
            or not self.usage_complete
        ):
            raise LLMClientError(
                LLMErrorCode.INVALID_REQUEST,
                "Matched pilot budget exhausted or route mismatch.",
                provider=self.provider,
            )
        options = request.options.model_copy(
            update={
                "max_retries": 0,
                "max_output_tokens": min(
                    request.options.max_output_tokens,
                    remaining,
                    self.limits.per_request_output_tokens,
                ),
                "timeout_seconds": min(request.options.timeout_seconds, self.remaining_seconds()),
                "total_timeout_seconds": min(
                    request.options.total_timeout_seconds or 90, self.remaining_seconds()
                ),
            }
        )
        request = request.model_copy(update={"options": options})
        self.calls += 1
        stem = self.directory / f"model-{self.calls}"
        save(stem.with_suffix(".request.json"), request.model_dump(mode="json"))
        try:
            response = self.client.complete(request)
        except Exception as exc:
            self.usage_complete = False
            save(stem.with_suffix(".failure.json"), {"failure": type(exc).__name__, "usage": None})
            raise
        self.input_tokens += response.usage.input_tokens
        self.output_tokens += response.usage.output_tokens
        save(stem.with_suffix(".response.json"), response.model_dump(mode="json"))
        return response

    def execute(self, code, tests=()):
        if self.tool_calls >= self.limits.sandbox_calls or self.remaining_seconds() <= 0:
            raise ValueError("Matched pilot sandbox/time budget exhausted.")
        self.tool_calls += 1
        stem = self.directory / f"sandbox-{self.tool_calls}"
        save(stem.with_suffix(".request.json"), {"code": code, "tests": list(tests)})
        self.sandbox.limits = replace(
            self.sandbox.limits,
            timeout_seconds=min(self.sandbox.limits.timeout_seconds, self.remaining_seconds()),
        )
        try:
            result = self.sandbox.execute(code, tests)
        except Exception as exc:
            save(stem.with_suffix(".failure.json"), {"failure": type(exc).__name__})
            raise
        save(stem.with_suffix(".response.json"), result.model_dump(mode="json"))
        return result

    def usage(self):
        return {
            "model_calls": self.calls,
            "sandbox_calls": self.tool_calls,
            "input_tokens": self.input_tokens if self.usage_complete else None,
            "output_tokens": self.output_tokens if self.usage_complete else None,
            "usage_complete": self.usage_complete,
            "elapsed_ms": round((perf_counter() - self.started) * 1000, 3),
        }


class Proposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=20000)
    tests: list[str] = Field(min_length=1, max_length=20)
    explanation: str = Field(min_length=1)


class MeteredSandbox:
    """Expose sandbox limits separately from the experiment's resource limits."""

    def __init__(self, meter):
        self.meter = meter

    @property
    def limits(self):
        return self.meter.sandbox.limits

    def execute(self, code, tests=()):
        return self.meter.execute(code, tests)


def lean_solve(meter: Meter, prompt: str) -> str | None:
    messages = [
        LLMMessage(
            role=LLMRole.USER,
            content=(
                "Solve the problem using a networkless Python standard-library sandbox. "
                "Return a JSON object with code (complete implementation, max 20000 chars), "
                "tests (1..20 Python assertion strings, each max 2000 chars), and explanation "
                "(correctness and complexity). Your code/tests will run; if execution fails, "
                "use the feedback to repair it. Preserve earlier tests when repairing code. "
                "Do not claim external judge acceptance.\n\nPROBLEM:\n" + prompt
            ),
        )
    ]
    for _ in range(meter.limits.model_calls):
        response = meter.complete(
            LLMRequest(
                model=meter.model,
                messages=messages,
                options=LLMRequestOptions(
                    max_output_tokens=6000, json_mode=True, timeout_seconds=90
                ),
            )
        )
        messages.append(LLMMessage(role=LLMRole.ASSISTANT, content=response.text))
        try:
            proposal = Proposal.model_validate_json(response.text)
        except ValidationError:
            messages.append(
                LLMMessage(
                    role=LLMRole.USER,
                    content="Invalid schema. Return only the requested JSON object.",
                )
            )
            continue
        result = meter.execute(proposal.code, proposal.tests)
        if execution_passed(result, len(proposal.tests)):
            return f"```python\n{proposal.code}\n```\n\n{proposal.explanation}"
        messages.append(
            LLMMessage(
                role=LLMRole.USER,
                content=("Observed sandbox result; repair and rerun: " + result.model_dump_json()),
            )
        )
    return None


def run_arm(settings, case, prompt, arm, directory, limits=DEFAULT_LIMITS, *, client=None):
    directory.mkdir()
    sandbox = DockerPythonSandbox(
        image=settings.code_execution_image,
        limits=DockerSandboxLimits(timeout_seconds=5, memory_megabytes=64),
    )
    meter = Meter(
        client if client is not None else OpenRouterLLMClient.from_settings(settings),
        settings.openrouter_model,
        sandbox,
        directory,
        limits,
    )
    record = {"case": case, "arm": arm, "prompt_sha256": digest(prompt), "delivered_answer": None}
    save(
        directory / "input.json",
        {"prompt": prompt, "limits": asdict(limits), "model": settings.openrouter_model},
    )
    try:
        if arm == "lean":
            record["delivered_answer"] = lean_solve(meter, prompt)
        else:
            with (
                patch(
                    "app.cognition.bootstrap.OpenRouterLLMClient.from_settings", return_value=meter
                ),
                patch(
                    "app.cognition.bootstrap.DockerPythonSandbox",
                    return_value=MeteredSandbox(meter),
                ),
            ):
                result = build_cognitive_runtime(settings).run_problem(prompt)
            export_run(result, directory, elapsed_ms=meter.usage()["elapsed_ms"])
            record["runtime_status"] = result.status.value
            record["delivered_answer"] = result.state["final_answer"]
    except Exception as exc:
        record["failure"] = type(exc).__name__
    record["usage"] = meter.usage()
    save(directory / "outcome.json", record)
    return record


def score(case, record):
    code = extract_code(record["delivered_answer"] or "")
    result = {"passed": False, "checks_sha256": checks_digest(CHECKS[case])}
    if code is not None:
        sandbox = DockerPythonSandbox(limits=DockerSandboxLimits(timeout_seconds=20))
        execution = sandbox.execute(code, CHECKS[case])
        result.update(
            passed=execution_passed(execution, len(CHECKS[case])),
            code_sha256=digest(code),
            execution=execution.model_dump(mode="json"),
        )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cases", type=Path, default=Path(__file__).with_name("matched-cases.json")
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--repeats", type=int, default=2, choices=range(1, 11))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = load_cases(args.cases)
    if set(cases) - set(CHECKS):
        parser.error("every case needs independent checks")
    limits = Limits()
    settings = Settings().model_copy(
        update={
            "openrouter_model": args.model,
            "openrouter_fallback_models": "",
            "code_execution_enabled": True,
            "verified_coding_enabled": False,
            "search_provider": "",
            "artifact_allowed_roots": "",
            "cognitive_max_model_calls": limits.model_calls,
            "cognitive_max_external_calls": 0,
            "cognitive_max_input_tokens": 10000000,
            "cognitive_max_output_tokens": limits.output_tokens,
            "cognitive_max_duration_ms": limits.seconds * 1000,
            "cognitive_max_normalized_cost": 1000,
        }
    )
    if not settings.openrouter_api_key.get_secret_value().strip():
        parser.error("configured OpenRouter credentials required")
    args.output.mkdir(parents=True, exist_ok=False)
    save(
        args.output / "manifest.json",
        {
            "version": "matched_coding_pilot@0.2.0",
            "test_harness_version": PYTHON_TEST_HARNESS_VERSION,
            "cases": cases,
            "repeats": args.repeats,
            "model": args.model,
            "limits": asdict(limits),
            "checks": {case: checks_digest(CHECKS[case]) for case in cases},
            "limitations": [
                "Developer-authored development pilot; not held out.",
                "Common outer ceilings; runtime retains its internal scheduling policy.",
                "Input tokens measured, not a shared hard pre-request ceiling.",
                "Model explanations are not independently scored for semantic quality.",
            ],
        },
    )
    records = []
    for repeat in range(args.repeats):
        for case, prompt in cases.items():
            arms = ["lean", "polya"] if repeat % 2 == 0 else ["polya", "lean"]
            pair = []
            for arm in arms:
                directory = args.output / f"{case}-{repeat}-{arm}"
                record = run_arm(settings, case, prompt, arm, directory, limits)
                pair.append((directory, record))
                print(
                    json.dumps(
                        {"case": case, "repeat": repeat, "arm": arm, "usage": record["usage"]}
                    ),
                    flush=True,
                )
            # Neither arm receives independent check feedback during solving.
            for directory, record in pair:
                record["repeat"] = repeat
                record["independent"] = score(case, record)
                if record["arm"] == "polya":
                    record["runtime_acceptance"] = verify(case, directory)
                save(directory / "score.json", record)
                records.append(record)
    save(args.output / "summary.json", {"records": records, "superiority_established": False})


if __name__ == "__main__":
    main()
