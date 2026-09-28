"""Inject one incomplete source edit, then let the unchanged public runtime recover."""

import argparse
import json
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

from evals.chapter_13p.coding_execution.evidence import digest, execution_passed
from evals.chapter_13p.coding_execution.matched import save

from app.cognition.bootstrap import build_cognitive_runtime
from app.cognition.repair_memory import learn_repair
from app.cognition.task_model import accumulated_usage
from app.config import Settings
from app.execution import DockerPythonSandbox, DockerSandboxLimits
from app.investigator.artifacts import export_run
from app.investigator.source_patch import source_patch_state
from app.llm import LLMCapabilities, LLMClientError, LLMErrorCode, LLMResponse, OpenRouterLLMClient


class InjectFirstProposal:
    """The injected proposal is explicitly distinguished from real inference."""

    def __init__(self, delegate, seed, root):
        self.delegate, self.seed, self.root = delegate, seed, root
        self.provider = delegate.provider if delegate is not None else "fixture"
        self.capabilities = (
            delegate.capabilities
            if delegate is not None
            else LLMCapabilities(supports_json_mode=True)
        )
        self.requests = 0
        self.real_calls = 0
        self.responses = []

    def complete(self, request):
        self.requests += 1
        stem = self.root / f"request-{self.requests}"
        save(stem.with_suffix(".json"), request.model_dump(mode="json"))
        if self.requests == 1:
            if "Capability: source_patch_investigator\n" not in request.messages[0].content:
                raise ValueError("Injection did not reach the expected proposal boundary")
            response = LLMResponse(provider="injected", model="fixture", text=json.dumps(self.seed))
            save(stem.with_suffix(".injected-response.json"), response.model_dump(mode="json"))
            return response
        if self.delegate is None:
            raise LLMClientError(
                LLMErrorCode.INVALID_REQUEST, "Offline preflight.", provider="fixture"
            )
        self.real_calls += 1
        try:
            response = self.delegate.complete(request)
        except Exception as exc:
            save(stem.with_suffix(".failure.json"), {"failure": type(exc).__name__, "usage": None})
            raise
        self.responses.append(response)
        save(stem.with_suffix(".response.json"), response.model_dump(mode="json"))
        return response


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="google/gemini-3.7-flash")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    fixture = Path(__file__).with_name("case.json")
    case = json.loads(fixture.read_text())
    source, check = args.output / "source.py", args.output / "check.py"
    source.write_text(case["source"])
    check.write_text(case["check"])
    save(
        args.output / "manifest.json",
        {
            "case_sha256": digest(fixture.read_text()),
            "model": args.model,
            "scope": case["scope"],
            "injected_proposals": 1,
            "runtime_call_budget_includes_injected_proposal": True,
            "independent_checks_visible_to_solver": False,
        },
    )
    config = Settings().model_copy(
        update={
            "openrouter_model": args.model,
            "openrouter_fallback_models": "",
            "artifact_allowed_roots": str(args.output.resolve()),
            "code_execution_enabled": True,
            "search_provider": "",
            "cognitive_max_model_calls": 6,
        }
    )
    seed = {
        **case["injected_edit"],
        "implicated_source_uri": source.resolve().as_uri(),
        "regression_check_uri": check.resolve().as_uri(),
        "remaining_uncertainty": ["The candidate has not yet been executed."],
    }
    provider = None if args.offline else OpenRouterLLMClient.from_settings(config)
    client = InjectFirstProposal(provider, seed, args.output)
    state = source_patch_state(case["problem"], source, check, config)
    started = perf_counter()
    with patch("app.cognition.bootstrap.OpenRouterLLMClient.from_settings", return_value=client):
        result = build_cognitive_runtime(config, enable_source_patch=True).run_state(state)
    elapsed_ms = (perf_counter() - started) * 1000
    artifacts = args.output / "artifacts"
    artifacts.mkdir(mode=0o700)
    export_run(result, artifacts, elapsed_ms=elapsed_ms)
    independent = None
    if result.status.value == "completed":
        task = result.state["plan"][0]
        old, new = task.params["old_text"], task.params["new_text"]
        assert isinstance(old, str) and isinstance(new, str) and case["source"].count(old) == 1
        candidate = case["source"].replace(old, new, 1)
        sandbox = DockerPythonSandbox(limits=DockerSandboxLimits())
        observed = sandbox.execute(candidate, case["independent_checks"])
        independent = {
            "passed": execution_passed(observed, 1),
            "execution": observed.model_dump(mode="json"),
            "code_sha256": digest(candidate),
        }
    record = {
        "runtime_status": result.status.value,
        "elapsed_ms": elapsed_ms,
        "injected_proposals": 1,
        "real_model_calls": client.real_calls,
        "reported_real_tokens": sum(r.usage.total_tokens for r in client.responses),
        "real_usage_complete": client.real_calls == len(client.responses),
        "runtime_usage_including_injection": accumulated_usage(result.state).model_dump(
            mode="json"
        ),
        "patch_verdicts": [
            o.output.get("patch_verified")
            for o in result.state["execution_outputs"]
            if isinstance(o.output, dict)
        ],
        "failed_verification_retained": any(
            e.event_type == "verification_invalidated" for e in result.state["events"]
        ),
        "host_snapshots_unchanged": source.read_text() == case["source"]
        and check.read_text() == case["check"],
        "verified_lesson_available": learn_repair(result.state) is not None,
        "independent": independent,
    }
    save(args.output / "summary.json", record)
    print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
