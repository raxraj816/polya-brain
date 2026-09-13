"""Raw-input composition boundary for the general cognitive kernel."""

from __future__ import annotations

from app.cognition.capabilities import CapabilityRegistry
from app.cognition.controller import CognitiveController
from app.cognition.kernel import CognitiveKernel, CognitiveRunResult
from app.cognition.performance import CapabilityPerformanceLedger
from app.cognition.procedure_compiler import (
    CompiledProcedure,
    ProcedureCompiler,
    procedure_compiled_event,
)
from app.cognition.procedure_executor import (
    GovernedProcedureExecutor,
    ProcedureExecutionResult,
)
from app.cognition.task_model import CognitiveResourceBudget
from app.graph.state import PolyaState, append_state_events, create_initial_state
from app.models.contracts import EvidenceItem


class CognitiveRuntime:
    """Start one bounded cognitive run from raw user input."""

    def __init__(
        self,
        registry: CapabilityRegistry,
        *,
        controller: CognitiveController | None = None,
        budget: CognitiveResourceBudget | None = None,
        procedure_compiler: ProcedureCompiler | None = None,
        performance_ledger: CapabilityPerformanceLedger | None = None,
    ) -> None:
        self._registry = registry
        self._kernel = CognitiveKernel(registry, controller=controller)
        self._budget = budget
        self._procedure_compiler = procedure_compiler
        self._performance_ledger = performance_ledger

    def run_problem(
        self,
        raw_input: str,
        *,
        session_id: str | None = None,
        max_cycles: int = 12,
        seed_evidence: list[EvidenceItem] | None = None,
        budget: CognitiveResourceBudget | None = None,
    ) -> CognitiveRunResult:
        """Create explicit initial state, then run observe-decide-act-update."""
        state = create_initial_state(
            raw_input,
            session_id=session_id,
            max_iterations=max_cycles,
        )
        state["evidence"] = list(seed_evidence or [])
        result = self._kernel.run(
            state,
            max_cycles=max_cycles,
            budget=budget or self._budget,
        )
        if self._performance_ledger is not None:
            self._performance_ledger.observe_run(result)
        if self._procedure_compiler is None:
            return result
        try:
            procedure = self._procedure_compiler.compile(result)
        except ValueError:
            # Runs without executable verifier traces are not compilation-ready.
            return result
        next_state = dict(result.state)
        next_state["events"] = append_state_events(
            result.state["events"],
            procedure_compiled_event(procedure),
        )
        return CognitiveRunResult(
            status=result.status,
            state=next_state,  # type: ignore[arg-type]
            decisions=result.decisions,
            observations=result.observations,
            cycles=result.cycles,
        )

    def run_verified_procedure(
        self,
        procedure: CompiledProcedure,
        state: PolyaState,
        *,
        approved: bool = False,
    ) -> ProcedureExecutionResult:
        """Execute an explicitly selected verified procedure under runtime guards."""
        result = GovernedProcedureExecutor(self._registry).execute(
            procedure,
            state,
            approved=approved,
        )
        if self._performance_ledger is not None:
            self._performance_ledger.observe_procedure(result)
        return result
