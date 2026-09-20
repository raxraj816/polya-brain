"""Necessary consistency check for explicit source-linked time uncertainties.

This intentionally narrow parser is not a general measurement or truth verifier.
"""

import re
from decimal import Decimal

from app.graph.state import PolyaState

VERSION = "time_uncertainty_consistency@0.1.0"
_NUMBER = r"[-+−–]?\d+(?:\.\d+)?"
_UNIT = r"(?:seconds?|secs?|s|minutes?|mins?|min|hours?|hrs?|h)\b"
_PAIR = re.compile(
    rf"(?<![\w.])(?P<value>{_NUMBER})\s*(?P<unit>{_UNIT})?\s*"
    rf"(?:±|\+\s*/\s*-|plus\s+or\s+minus)\s*"
    rf"(?P<error>{_NUMBER})\s*(?P<error_unit>{_UNIT})",
    re.IGNORECASE,
)


def _seconds(value: str, unit: str) -> Decimal:
    multiplier = 3600 if unit.lower().startswith("h") else 60 if unit.lower().startswith("m") else 1
    return abs(Decimal(value.replace("−", "-").replace("–", "-"))) * multiplier


def _measurements(text: str) -> list[tuple[Decimal, Decimal, str]]:
    return [
        (
            _seconds(match["value"], match["unit"] or match["error_unit"]),
            _seconds(match["error"], match["error_unit"]),
            match.group(0),
        )
        for match in _PAIR.finditer(text)
    ]


def uncertainty_failures(state: PolyaState, answer: str) -> list[str]:
    """Reject conflicting uncertainties only where a matching central value exists."""
    sources = [
        (measurement, item.source_uri or "admitted source")
        for item in state["evidence"]
        # Model-extracted claims may already contain the unit error. Only compare
        # against admitted source text, never let a generated claim corroborate itself.
        if item.raw_excerpt is not None
        for measurement in _measurements(item.raw_excerpt)
    ]
    failures = []
    for central, uncertainty, text in _measurements(answer):
        matching = [(measurement, uri) for measurement, uri in sources if measurement[0] == central]
        if matching and not any(measurement[1] == uncertainty for measurement, _ in matching):
            expected = "; ".join(dict.fromkeys(f"{m[2]} ({uri})" for m, uri in matching))
            failures.append(
                f"Time uncertainty mismatch: answer states {text}; admitted source states {expected}."
            )
    return list(dict.fromkeys(failures))
