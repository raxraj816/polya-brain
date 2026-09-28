"""Auditable one-call direct baseline; tool access differs from the runtime."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

try:
    from .evidence import checks_digest, digest, execution_passed, extract_code, load_cases
    from .verify import CHECKS
except ImportError:  # direct script execution
    from evidence import checks_digest, digest, execution_passed, extract_code, load_cases
    from verify import CHECKS

from app.config import Settings
from app.execution import DockerPythonSandbox, DockerSandboxLimits
from app.llm import LLMMessage, LLMRequest, LLMRequestOptions, LLMRole, OpenRouterLLMClient


def _baseline_prompt(problem: str) -> str:
    return (
        "Solve this coding problem directly. Return exactly one complete Python code block "
        "containing the implementation, followed by a concise correctness and complexity "
        "explanation. Do not claim external judge acceptance. You have no execution tool; "
        "distinguish proposed tests from observed execution.\n\nPROBLEM:\n" + problem
    )


def run_case(client: Any, model: str, case: str, prompt: str) -> dict[str, Any]:
    request = LLMRequest(
        model=model,
        messages=[LLMMessage(role=LLMRole.USER, content=_baseline_prompt(prompt))],
        options=LLMRequestOptions(
            max_output_tokens=5000,
            timeout_seconds=90.0,
            total_timeout_seconds=90.0,
            max_retries=0,
        ),
    )
    result: dict[str, Any] = {
        "case": case,
        "passed": False,
        "model_calls": 1,
        "requested_model": model,
        "prompt": prompt,
        "prompt_sha256": digest(prompt),
        "request": request.model_dump(mode="json"),
        "checks_sha256": checks_digest(CHECKS[case]),
        "started_at": datetime.now(UTC).isoformat(),
        "usage": None,
    }
    started = perf_counter()
    try:
        response = client.complete(request)
        result.update(
            model=response.model,
            response=response.model_dump(mode="json"),
            usage=response.usage.model_dump(mode="json"),
            response_id=response.response_id,
            elapsed_ms=round((perf_counter() - started) * 1000, 3),
        )
        code = extract_code(response.text)
        result["code"] = code
        if code is None:
            result["failure"] = "missing_or_ambiguous_python_code"
            return result
        result["code_sha256"] = digest(code)
        sandbox = DockerPythonSandbox(limits=DockerSandboxLimits(timeout_seconds=20))
        execution = sandbox.execute(code, CHECKS[case])
        result["independent_checks"] = execution.model_dump(mode="json")
        result["passed"] = execution_passed(execution, len(CHECKS[case]))
    except Exception as exc:  # provider/tool failures are outcomes, not dropped trials
        result["failure"] = type(exc).__name__
    finally:
        result.setdefault("elapsed_ms", round((perf_counter() - started) * 1000, 3))
        result["total_elapsed_ms"] = round((perf_counter() - started) * 1000, 3)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=Path(__file__).with_name("cases.json"))
    parser.add_argument("--case", action="append", choices=sorted(CHECKS))
    parser.add_argument("--model", help="Override the configured model route.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = load_cases(args.cases)
    selected = args.case or sorted(cases)
    if len(set(selected)) != len(selected) or set(selected) - (set(cases) & set(CHECKS)):
        parser.error("selection must contain unique declared cases with independent checks")
    settings = Settings()
    client = OpenRouterLLMClient.from_settings(settings)
    model = (args.model or settings.openrouter_model).strip()
    if not model:
        parser.error("configure OPENROUTER_MODEL or pass --model")
    summary: dict[str, Any] = {
        "artifact_version": "coding_direct_baseline@0.2.0",
        "baseline": "direct_one_call_no_tools",
        "model": model,
        "planned_cases": selected,
        "attempted_cases": [],
        "in_flight_case": None,
        "cases": [],
        "complete": False,
        "passed": False,
        "standard": {
            "same_independent_checks": True,
            "equal_tool_access": False,
            "external_judge_submission": False,
            "provider_retries": 0,
        },
    }
    # Exclusive reservation prevents replacing earlier failures with selected successes.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(summary, indent=2) + "\n")

    def checkpoint() -> None:
        temporary = args.output.with_suffix(args.output.suffix + ".pending")
        temporary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        temporary.replace(args.output)

    for case in selected:
        summary["attempted_cases"].append(case)
        summary["in_flight_case"] = case
        checkpoint()
        summary["cases"].append(run_case(client, model, case, cases[case]))
        summary["in_flight_case"] = None
        summary["case_count"] = len(summary["cases"])
        summary["passed_cases"] = sum(item["passed"] for item in summary["cases"])
        summary["complete"] = len(summary["cases"]) == len(selected)
        summary["passed"] = summary["complete"] and all(item["passed"] for item in summary["cases"])
        checkpoint()
    print(json.dumps({key: value for key, value in summary.items() if key != "cases"}, indent=2))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
