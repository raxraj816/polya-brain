"""Human-readable report for a verified change."""

from __future__ import annotations

import re

from app.verified_change.pipeline import ChangeCertificate, ChangeOutcome, ChangeStatus

HEADLINES = {
    ChangeStatus.NO_DIFFERENCE: "No behavior change found",
    ChangeStatus.INTENDED_ONLY: "Only intended behavior changes found",
    ChangeStatus.REGRESSIONS: "Regression found: the change alters behavior it should not",
    ChangeStatus.UNCLEAR: "Behavior changed in ways your stated intent does not settle",
    ChangeStatus.UNVERIFIED: "Not verified",
}


def _inline(text: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", text).replace("`", "'")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _summary(certificate: ChangeCertificate) -> str:
    sizes = certificate.sizes_covered
    span = f"input sizes {min(sizes)}–{max(sizes)}" if sizes else "no completed inputs"
    compared = (
        f"PolyaBrain ran the old ({certificate.base_ref}) and new ({certificate.head}) versions of "
        f"`{certificate.qualified_name}` side by side on {certificate.cases_compared:,} generated "
        f"inputs ({span}) in an isolated sandbox."
    )
    if certificate.status is ChangeStatus.NO_DIFFERENCE:
        if certificate.reason:
            return certificate.reason
        return compared + " Every output, raised exception type and input mutation matched."
    if certificate.status is ChangeStatus.UNVERIFIED:
        return "PolyaBrain could not establish a behavior comparison. " + (certificate.reason or "")
    return (
        compared
        + f" At least {certificate.total_differences:,} inputs behaved differently; the smallest are listed below."
    )


def render(outcome: ChangeOutcome) -> str:
    certificate = outcome.certificate
    lines = [
        f"# {HEADLINES[certificate.status]}",
        "",
        f"`{certificate.module_path}` · `{certificate.qualified_name}` · {certificate.base_ref} → {certificate.head}",
        "",
        _summary(certificate),
        "",
        "## Stated intent",
        "",
        f"> {_inline(certificate.intent, 1200) or '(none stated)'}",
        "",
    ]
    if certificate.behavior_preserving_intent:
        lines += [
            "The intent says behavior should be preserved, so every difference counts as a regression.",
            "",
        ]
    if certificate.differences:
        lines += ["## Behavior differences", ""]
        for index, item in enumerate(certificate.differences, start=1):
            label = {
                "regression": "Regression",
                "intended": "Intended",
                "unclear": "Needs your review",
            }.get(item.verdict, item.verdict)
            lines += [
                f"### {index}. {label}",
                "",
                f"- Input: `{_inline(item.args)}`",
                f"- Old ({certificate.base_ref}): `{_inline(item.old_output)}`",
                f"- New ({certificate.head}): `{_inline(item.new_output)}`",
            ]
            if item.kind == "input_mutated":
                lines.append("- The new version modifies its input arguments.")
            if item.expected_output:
                lines.append(f"- Expected per the contract: `{_inline(item.expected_output)}`")
            if item.intent_quote:
                lines.append(f'- Intent: "{_inline(item.intent_quote)}"')
            if item.explanation:
                lines.append(f"- {_inline(item.explanation, 400)}")
            lines.append("")
    if certificate.reason and certificate.status is not ChangeStatus.NO_DIFFERENCE:
        lines += [certificate.reason, ""]
    if certificate.function_diff:
        lines += ["## Function diff", "", "```diff", certificate.function_diff.rstrip(), "```", ""]
    if certificate.input_notes:
        lines += ["## Inputs exercised", ""]
        lines += [f"- {_inline(note)}" for note in certificate.input_notes]
        lines.append("")
    calls = outcome.model_calls
    cost = [call.cost_usd for call in calls]
    lines += [
        "## Resources",
        "",
        f"{len(calls)} model call(s) · {sum(c.input_tokens + c.output_tokens for c in calls):,} tokens"
        + (
            f" · provider-reported ${sum(c or 0 for c in cost):.4f}"
            if calls and None not in cost
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
