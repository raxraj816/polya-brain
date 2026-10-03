"""Human-readable report for a verified data answer."""

from __future__ import annotations

import json
import re
from typing import Any

from app.verified_claims.pipeline import AnswerStatus, ClaimsOutcome, ClaimStatus

HEADLINES = {
    AnswerStatus.VERIFIED: "Verified: every number was independently re-derived",
    AnswerStatus.CORRECTED: "Corrected and verified: some numbers in the first answer were wrong",
    AnswerStatus.NEEDS_REVIEW: "Needs review: at least one claim could not be proven",
    AnswerStatus.UNVERIFIED: "Not verified",
}
LABELS = {
    ClaimStatus.PROVEN: "Proven",
    ClaimStatus.CORRECTED: "Corrected",
    ClaimStatus.REVIEWED: "Supported after review",
    ClaimStatus.DISPUTED: "Disputed",
    ClaimStatus.UNVERIFIED: "Unverified",
}


def _value(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    text = re.sub(r"\s+", " ", str(text)).replace("`", "'").replace("|", "/")
    return text if len(text) <= 120 else text[:119] + "…"


def render(outcome: ClaimsOutcome) -> str:
    certificate = outcome.certificate
    lines = [f"# {HEADLINES[certificate.status]}", "", f"**Question:** {certificate.question}", ""]
    if certificate.answer:
        lines += ["## Answer as first written", "", certificate.answer.replace("```", "'''"), ""]
    corrected = [c for c in certificate.claims if c.status is ClaimStatus.CORRECTED]
    if corrected:
        lines += ["## Corrections", ""]
        lines += [
            f"- **{c.statement}** — the answer said `{_value(c.stated_value)}`; verified value `{_value(c.final_value)}`. {c.reason}"
            for c in corrected
        ]
        lines.append("")
    if certificate.claims:
        lines += [
            "## Claim-by-claim proof",
            "",
            "| Claim | Stated | Verified value | Status | Evidence |",
            "| --- | --- | --- | --- | --- |",
        ]
        for c in certificate.claims:
            evidence = (
                f"{c.variants_agreed}/{c.variants_total} data versions agree"
                if c.variants_total
                else "no independent run"
            )
            lines.append(
                f"| {_value(c.statement)} | `{_value(c.stated_value)}` | `{_value(c.final_value)}` "
                f"| {LABELS[c.status]} | {evidence} |"
            )
        lines.append("")
        reasons = [
            c
            for c in certificate.claims
            if c.status not in {ClaimStatus.PROVEN, ClaimStatus.CORRECTED}
        ]
        if reasons:
            lines += ["## Why some claims are not proven", ""]
            lines += [f"- **{c.id}**: {c.reason}" for c in reasons]
            lines.append("")
    if certificate.reason:
        lines += [certificate.reason, ""]
    if certificate.assumptions:
        lines += ["## Interpretations the verifier assumed", ""]
        lines += [f"- {a}" for a in certificate.assumptions]
        lines.append("")
    calls = outcome.model_calls
    costs = [c.cost_usd for c in calls]
    lines += [
        "## How this was checked",
        "",
        "The answer's own analysis code and an independently written derivation (which never saw "
        "the answer's numbers or code) both ran on your data and on four perturbed copies "
        "(shuffled, subsampled, duplicated rows and jittered values) in an isolated sandbox. A claim "
        "is proven only when both derivations agree on every version and the stated number matches.",
        "",
        f"Tables: {', '.join(certificate.tables)} · {len(calls)} model call(s)"
        + (
            f" · provider-reported ${sum(c or 0 for c in costs):.4f}"
            if calls and None not in costs
            else ""
        )
        + f" · {outcome.elapsed_ms / 1000:.1f}s.",
        "",
        "## Limits",
        "",
        *[f"- {item}" for item in certificate.limitations],
        "",
    ]
    return "\n".join(lines)
