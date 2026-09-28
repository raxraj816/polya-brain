"""Compact model requests without changing canonical contracts or tool data."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy

from app.models.contracts import ContractModel

PROPOSAL_STATUSES = ("candidate", "deferred", "rejected")


def compact_record(record: ContractModel) -> dict[str, object]:
    """Elide empty defaults only; explicit scalar status/risk/flags stay visible."""
    full = record.model_dump(mode="json")
    compact = record.model_dump(mode="json", exclude_defaults=True)
    for name, value in full.items():
        if name not in compact and value is not None and value != [] and value != {}:
            compact[name] = value
    return compact


def compact_schema(output_type: type[ContractModel], *, unselected_only: bool) -> dict[str, object]:
    """Drop display titles only; keep descriptions, defaults and validation rules."""
    schema = deepcopy(output_type.model_json_schema())

    def walk(node: object) -> None:
        if not isinstance(node, dict):
            return
        node.pop("title", None)
        # These maps contain names, not schema keywords. Never drop a property
        # named 'title' or change arbitrary JSON inside examples/defaults.
        for key in ("$defs", "definitions", "properties", "patternProperties", "dependentSchemas"):
            children = node.get(key)
            if isinstance(children, dict):
                for child in children.values():
                    walk(child)
        for key in (
            "items",
            "additionalProperties",
            "contains",
            "not",
            "if",
            "then",
            "else",
            "propertyNames",
            "unevaluatedProperties",
        ):
            walk(node.get(key))
        for key in ("allOf", "anyOf", "oneOf", "prefixItems"):
            children = node.get(key)
            if isinstance(children, list):
                for child in children:
                    walk(child)

    walk(schema)
    if unselected_only:
        definition = schema.get("$defs", {}).get("HypothesisStatus")
        if isinstance(definition, dict):
            definition["enum"] = list(PROPOSAL_STATUSES)
            definition["description"] = (
                "No admitted evidence yet: propose candidates, defer, or reject alternatives. "
                "Selection and verification require later evidence; do not invent it."
            )
    return schema


def proposal_status_error(payload: dict[str, object], context: object) -> str | None:
    """A schema hint must also be enforced when a provider ignores it."""
    if not isinstance(context, Mapping) or context.get("unselected_hypotheses_only") is not True:
        return None
    hypotheses = payload.get("hypotheses")
    if isinstance(hypotheses, list) and any(
        isinstance(item, dict) and item.get("status", "candidate") not in PROPOSAL_STATUSES
        for item in hypotheses
    ):
        return (
            "No admitted evidence exists. Hypothesis status must be candidate, deferred or "
            "rejected; selected, verified and falsified require evidence from the runtime. "
            "Do not invent supporting evidence or observed test results."
        )
    return None
