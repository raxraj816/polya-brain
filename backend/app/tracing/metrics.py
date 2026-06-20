"""Lightweight in-process trace persistence metrics."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class TraceMetricsSnapshot:
    """Point-in-time trace metrics used by tests and future observability adapters."""

    append_attempts: int = 0
    append_successes: int = 0
    append_failures: int = 0
    persisted_events: int = 0
    route_decision_events: int = 0
    redactions: int = 0
    append_duration_ms_total: float = 0.0


class TraceMetrics:
    """Thread-safe counters for the current backend process."""

    def __init__(self) -> None:
        self._lock = Lock()
        # Immutable snapshots keep Phase 1 metrics simple; later observability can replace this.
        self._snapshot = TraceMetricsSnapshot()

    def reset(self) -> None:
        """Reset counters for isolated tests."""
        with self._lock:
            self._snapshot = TraceMetricsSnapshot()

    def snapshot(self) -> TraceMetricsSnapshot:
        """Return current metric values."""
        with self._lock:
            return self._snapshot

    def record_append_attempt(self) -> None:
        """Record one call that attempted to append trace events."""
        with self._lock:
            self._snapshot = TraceMetricsSnapshot(
                append_attempts=self._snapshot.append_attempts + 1,
                append_successes=self._snapshot.append_successes,
                append_failures=self._snapshot.append_failures,
                persisted_events=self._snapshot.persisted_events,
                route_decision_events=self._snapshot.route_decision_events,
                redactions=self._snapshot.redactions,
                append_duration_ms_total=self._snapshot.append_duration_ms_total,
            )

    def record_append_success(
        self,
        *,
        persisted_events: int,
        route_decision_events: int,
        redactions: int,
        duration_ms: float,
    ) -> None:
        """Record a successful trace append."""
        with self._lock:
            self._snapshot = TraceMetricsSnapshot(
                append_attempts=self._snapshot.append_attempts,
                append_successes=self._snapshot.append_successes + 1,
                append_failures=self._snapshot.append_failures,
                persisted_events=self._snapshot.persisted_events + persisted_events,
                route_decision_events=self._snapshot.route_decision_events + route_decision_events,
                redactions=self._snapshot.redactions + redactions,
                append_duration_ms_total=self._snapshot.append_duration_ms_total + duration_ms,
            )

    def record_append_failure(self, *, duration_ms: float) -> None:
        """Record a failed trace append."""
        with self._lock:
            self._snapshot = TraceMetricsSnapshot(
                append_attempts=self._snapshot.append_attempts,
                append_successes=self._snapshot.append_successes,
                append_failures=self._snapshot.append_failures + 1,
                persisted_events=self._snapshot.persisted_events,
                route_decision_events=self._snapshot.route_decision_events,
                redactions=self._snapshot.redactions,
                append_duration_ms_total=self._snapshot.append_duration_ms_total + duration_ms,
            )


trace_metrics = TraceMetrics()
