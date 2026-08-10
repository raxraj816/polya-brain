"""Raw-input composition boundary for the general cognitive kernel."""

from __future__ import annotations

from app.cognition.capabilities import CapabilityRegistry
from app.cognition.controller import CognitiveController
from app.cognition.kernel import CognitiveKernel, CognitiveRunResult
from app.graph.state import create_initial_state
from app.models.contracts import EvidenceItem


class CognitiveRuntime:
    """Start one bounded cognitive run from raw user input."""

    def __init__(
        self,
        registry: CapabilityRegistry,
        *,
        controller: CognitiveController | None = None,
    ) -> None:
        self._kernel = CognitiveKernel(registry, controller=controller)

    def run_problem(
        self,
        raw_input: str,
        *,
        session_id: str | None = None,
        max_cycles: int = 12,
        seed_evidence: list[EvidenceItem] | None = None,
    ) -> CognitiveRunResult:
        """Create explicit initial state, then run observe-decide-act-update."""
        state = create_initial_state(
            raw_input,
            session_id=session_id,
            max_iterations=max_cycles,
        )
        state["evidence"] = list(seed_evidence or [])
        return self._kernel.run(state, max_cycles=max_cycles)
