"""Shared source/check report language grounded in the measured verifier outcome."""

from collections.abc import Mapping
from typing import Any


def source_patch_conclusion(params: Mapping[str, Any]) -> str:
    """Call only after the source/check verifier has passed."""
    return (
        "The supplied regression check failed on the original source and passed on the candidate edit.\n\n"
        f"Proposed diagnosis: {params.get('diagnosis', 'Not supplied.')}\n"
        f"Candidate edit: replace {params.get('old_text')!r} with {params.get('new_text')!r}.\n"
        "Scope: supplied-check coverage only. Causal correctness, other regressions, and hostile-code attestation remain unproven. "
        "The hypothesis artifact preserves the original proposal and its uncertainties before execution."
    )


def source_patch_checks() -> list[str]:
    return [
        "Matched the source and check to their complete admitted snapshots.",
        "Observed the original source fail the supplied regression check.",
        "Observed the candidate edit pass the same supplied regression check.",
        "Matched proposed diagnosis identifiers to the edited identifiers (lexical check only).",
    ]
