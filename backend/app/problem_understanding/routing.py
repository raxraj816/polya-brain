"""Provider-neutral routed problem-understanding contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.graph.state import PolyaState
from app.llm import LLMRouteAttemptTelemetry, LLMTokenUsage
from app.models.contracts import ProductMode
from app.problem_understanding.contracts import ProblemUnderstandingRunResult
from app.tracing.sanitization import sanitize_text


@dataclass(frozen=True)
class ProblemUnderstandingExecution:
    """Validated representation plus truthful cross-route resource telemetry."""

    result: ProblemUnderstandingRunResult
    usage: LLMTokenUsage
    model_calls: int
    route_attempts: tuple[LLMRouteAttemptTelemetry, ...] = ()


class ProblemUnderstandingProviderError(RuntimeError):
    """Safe routed failure that preserves non-content attempt accounting."""

    def __init__(
        self,
        summary: str,
        *,
        failure_kind: str,
        usage: LLMTokenUsage,
        model_calls: int,
        route_attempts: tuple[LLMRouteAttemptTelemetry, ...],
    ) -> None:
        self.safe_summary = sanitize_text(summary).strip() or "Representation route failed."
        self.failure_kind = sanitize_text(failure_kind).strip() or "representation_failure"
        self.usage = usage
        self.model_calls = max(0, model_calls)
        self.route_attempts = route_attempts[:2]
        super().__init__(self.safe_summary)


class ProblemUnderstandingProvider(Protocol):
    """Replaceable provider for contract-validated problem understanding."""

    @property
    def model_route(self) -> str:
        """Return a non-secret version identity for the configured route set."""
        ...

    @property
    def max_provider_attempts(self) -> int:
        """Return the hard worst-case provider-call reservation."""
        ...

    def generate(
        self,
        state: PolyaState,
        *,
        mode_hint: ProductMode | None,
        domain_hint: str | None,
        total_timeout_seconds: float,
        runtime_context: str | None = None,
    ) -> ProblemUnderstandingExecution:
        """Generate one validated representation inside the supplied deadline."""
        ...
