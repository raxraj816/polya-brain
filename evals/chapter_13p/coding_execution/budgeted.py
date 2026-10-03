"""Spend-bounded development batch; unknown cost stops the entire batch."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

from app.config import Settings
from app.llm import OpenRouterLLMClient

from .evidence import checks_digest, load_cases
from .matched import Limits, run_arm, save, score
from .verify import CHECKS, verify


class SpendGuard:
    """Serial local reservation ledger, not a provider-account billing limit."""

    def __init__(self, client, *, model, dollars, input_rate, output_rate, directory):
        self.client, self.model = client, model
        self.provider, self.capabilities = client.provider, client.capabilities
        self.cap, self.input_rate, self.output_rate = map(
            Decimal, (dollars, input_rate, output_rate)
        )
        if not all(x.is_finite() and x > 0 for x in (self.cap, self.input_rate, self.output_rate)):
            raise ValueError("Finite positive budget and rates required")
        self.directory = directory
        directory.mkdir()
        self.spent = Decimal(0)
        self.blocked = False
        self.calls = 0

    def complete(self, request):
        if self.blocked:
            raise ValueError("Batch stopped; cost or route requires reconciliation")
        size = len(request.model_dump_json().encode())
        if request.model != self.model or request.options.max_retries != 0 or size > 131072:
            self.blocked = True
            raise ValueError("Pinned route, zero retries and shared request-byte limit required")
        # Conservative UTF-8-byte proxy plus framing allowance; double the output
        # reserve for reasoning telemetry. This is not a tokenizer or invoice guarantee.
        reserve = (
            size + 16384
        ) * self.input_rate + 2 * request.options.max_output_tokens * self.output_rate
        if self.spent + reserve > self.cap:
            self.blocked = True
            raise ValueError("Batch dollar reservation does not fit")
        self.calls += 1
        stem = self.directory / str(self.calls)
        save(
            stem.with_suffix(".reserved.json"),
            {
                "model": self.model,
                "request_bytes": size,
                "reserve_usd": str(reserve),
                "previous_charged_usd": str(self.spent),
                "cap_usd": str(self.cap),
            },
        )
        self.spent += reserve  # Unknown failures retain the entire reservation.
        try:
            response = self.client.complete(request)
        except Exception as exc:
            self.blocked = True
            save(
                stem.with_suffix(".unknown.json"),
                {"failure": type(exc).__name__, "cost_unknown": True},
            )
            raise
        cost = response.usage.estimated_cost_usd
        save(stem.with_suffix(".response.json"), response.model_dump(mode="json"))
        valid_cost = cost is not None and Decimal(str(cost)).is_finite() and cost >= 0
        save(
            stem.with_suffix(".reported.json"),
            {
                "response_id": response.response_id,
                "model": response.model,
                "provider_reported_cost_usd": cost,
            },
        )
        if valid_cost:
            self.spent += Decimal(str(cost)) - reserve
        if not valid_cost or response.model != self.model or Decimal(str(cost)) > reserve:
            self.blocked = True
            raise ValueError(
                "Unknown cost, mismatched route or cost above reservation; reconcile before more calls"
            )
        return response


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--dollars", default="5")
    parser.add_argument("--input-rate", required=True)
    parser.add_argument("--output-rate", required=True)
    parser.add_argument("--repeats", type=int, choices=range(1, 4), default=2)
    args = parser.parse_args()
    cases = load_cases(args.cases)
    if set(cases) - set(CHECKS):
        parser.error("Missing independent checks")
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
        parser.error("Configured OpenRouter credential required")
    args.output.mkdir(parents=True, exist_ok=False)
    client = SpendGuard(
        OpenRouterLLMClient.from_settings(settings),
        model=args.model,
        dollars=args.dollars,
        input_rate=args.input_rate,
        output_rate=args.output_rate,
        directory=args.output / "spend",
    )
    save(
        args.output / "manifest.json",
        {
            "version": "budgeted_matched_development@1",
            "source_sha256": {
                str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                for base in (Path("backend/app"), Path("evals/chapter_13p/coding_execution"))
                for path in sorted(base.rglob("*.py"))
            },
            "cases": cases,
            "repeats": args.repeats,
            "model": args.model,
            "limits": asdict(limits),
            "dollar_cap": args.dollars,
            "pricing_per_token": {"input": args.input_rate, "output": args.output_rate},
            "checks": {case: checks_digest(CHECKS[case]) for case in cases},
            "limitations": [
                "Known developer cases; not held out.",
                "Reported provider costs are not invoices.",
                "Byte-based local dollar reservations are estimates; no provider-account cap changed.",
                "Human explanation review, independent private tasks and real-user return use remain pending.",
            ],
        },
    )
    records = []
    for repeat in range(args.repeats):
        for case, prompt in cases.items():
            for arm in ["lean", "polya"] if repeat % 2 == 0 else ["polya", "lean"]:
                if client.blocked:
                    continue
                directory = args.output / f"{case}-{repeat}-{arm}"
                record = run_arm(settings, case, prompt, arm, directory, limits, client=client)
                record["repeat"] = repeat
                try:
                    record["independent"] = score(case, record)
                    if arm == "polya":
                        record["runtime_acceptance"] = verify(case, directory)
                except Exception as exc:
                    record["scoring_failure"] = type(exc).__name__
                save(directory / "score.json", record)
                records.append(record)
                print(
                    json.dumps(
                        {
                            "case": case,
                            "repeat": repeat,
                            "arm": arm,
                            "independent_pass": record.get("independent", {}).get("passed", False),
                            "usage": record["usage"],
                            "batch_charged_usd": str(client.spent),
                            "batch_blocked": client.blocked,
                        }
                    ),
                    flush=True,
                )
    save(
        args.output / "summary.json",
        {
            "records": records,
            "expected_attempts": len(cases) * args.repeats * 2,
            "complete": len(records) == len(cases) * args.repeats * 2,
            "batch_blocked": client.blocked,
            "reported_or_reserved_usd": str(client.spent),
            "superiority_established": False,
        },
    )


if __name__ == "__main__":
    main()
