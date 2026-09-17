"""Deterministic, domain-independent next-action controller."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from typing import Protocol

from app.cognition.capabilities import CapabilityRegistry
from app.cognition.contracts import (
    CapabilityDefinition,
    CognitiveActionCandidate,
    CognitiveActionDecision,
    CognitiveActionType,
    LearnedActionPreference,
    RejectedCognitiveAction,
)
from app.cognition.epistemic_control import derive_epistemic_status
from app.cognition.evidence_closure import deterministic_evidence_attestation_available
from app.cognition.performance import AdaptiveActionEstimate
from app.cognition.task_model import (
    accumulated_usage,
    budget_rejection_reason,
    configured_budget,
    reservation_fits,
)
from app.cognition.verification_factory import deterministic_verification_available
from app.graph.state import PolyaState
from app.models.contracts import KnowledgeGap, PriorityLevel, RiskLevel

POLICY_VERSION = "cognitive-controller-v0.5.0"
CONTROLLER_CAPABILITY = "cognitive_controller"

_PRIORITY_USEFULNESS = {
    PriorityLevel.CRITICAL: 0.98,
    PriorityLevel.HIGH: 0.88,
    PriorityLevel.MEDIUM: 0.68,
    PriorityLevel.LOW: 0.42,
}
_RISK_PENALTY = {
    RiskLevel.LOW: 0.0,
    RiskLevel.MEDIUM: 0.12,
    RiskLevel.HIGH: 0.3,
}
_DEFAULT_CAPABILITY = {
    CognitiveActionType.INTERPRET: "problem_representation",
    CognitiveActionType.DISCOVER_CONSTRAINTS: "constraint_discovery",
    CognitiveActionType.DETECT_GAPS: "gap_detector",
    CognitiveActionType.CLARIFY: "human_input",
    CognitiveActionType.REFRAME: "reasoner",
    CognitiveActionType.DECOMPOSE: "reasoner",
    CognitiveActionType.RECALL: "memory",
    CognitiveActionType.RETRIEVE_MEMORY: "memory",
    CognitiveActionType.SEARCH: "web_search",
    CognitiveActionType.EVALUATE_EVIDENCE: "evidence_evaluator",
    CognitiveActionType.ASK_HUMAN: "human_input",
    CognitiveActionType.INSPECT: "inspector",
    CognitiveActionType.OBSERVE: "observer",
    CognitiveActionType.MEASURE: "measurement",
    CognitiveActionType.CALCULATE: "calculator",
    CognitiveActionType.COMPARE: "reasoner",
    CognitiveActionType.HYPOTHESIZE: "reasoner",
    CognitiveActionType.PLAN: "planner",
    CognitiveActionType.SIMULATE: "simulator",
    CognitiveActionType.EXPERIMENT: "experiment",
    CognitiveActionType.EXECUTE: "executor",
    CognitiveActionType.MONITOR: "monitor",
    CognitiveActionType.VERIFY: "verifier",
    CognitiveActionType.RETRY: "executor",
    CognitiveActionType.BACKTRACK: CONTROLLER_CAPABILITY,
    CognitiveActionType.REPLAN: "planner",
    CognitiveActionType.STOP: CONTROLLER_CAPABILITY,
    CognitiveActionType.REFLECT: "reflector",
}
_RECOVERY_ACTIONS = {
    CognitiveActionType.SEARCH: (
        CognitiveActionType.INSPECT,
        CognitiveActionType.ASK_HUMAN,
    ),
    CognitiveActionType.INSPECT: (
        CognitiveActionType.OBSERVE,
        CognitiveActionType.SEARCH,
        CognitiveActionType.ASK_HUMAN,
    ),
    CognitiveActionType.OBSERVE: (
        CognitiveActionType.INSPECT,
        CognitiveActionType.ASK_HUMAN,
    ),
    CognitiveActionType.CALCULATE: (
        CognitiveActionType.INSPECT,
        CognitiveActionType.ASK_HUMAN,
    ),
    CognitiveActionType.MEASURE: (
        CognitiveActionType.OBSERVE,
        CognitiveActionType.INSPECT,
    ),
    CognitiveActionType.EXPERIMENT: (
        CognitiveActionType.SIMULATE,
        CognitiveActionType.OBSERVE,
    ),
    CognitiveActionType.EXECUTE: (
        CognitiveActionType.REPLAN,
        CognitiveActionType.INSPECT,
    ),
    CognitiveActionType.VERIFY: (
        CognitiveActionType.COMPARE,
        CognitiveActionType.BACKTRACK,
    ),
}


class ProceduralPreferenceProvider(Protocol):
    """Minimal boundary used by the controller for verified strategy recall."""

    def preference(
        self,
        problem_type: str,
        gap_type: str,
    ) -> LearnedActionPreference | None:
        """Return a verified preference or no suggestion."""
        ...


class SemanticMemoryAvailabilityProvider(Protocol):
    """Attention boundary that reports whether governed memory has a likely match."""

    def has_relevant_memory(self, query: str, domain: str | None = None) -> bool:
        """Return whether retrieval is likely to reduce the current gap."""
        ...


class ActionPerformancePolicy(Protocol):
    """Bounded empirical adjustment applied only after controller hard gates."""

    policy_version: str

    def estimate(
        self,
        state: PolyaState,
        candidate: CognitiveActionCandidate,
        definition: CapabilityDefinition,
    ) -> AdaptiveActionEstimate:
        """Estimate version-scoped verified progress and marginal cost."""
        ...


def _unique(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _state_fingerprint(state: PolyaState) -> str:
    """Hash only canonical decision inputs, not volatile trace timing."""
    payload = {
        "session_id": state["session_id"],
        "raw_input": state["raw_input"],
        "structured_problem": (
            state["structured_problem"].model_dump(mode="json")
            if state["structured_problem"] is not None
            else None
        ),
        "gaps": [gap.model_dump(mode="json") for gap in state["gaps"]],
        "evidence": [item.model_dump(mode="json") for item in state["evidence"]],
        "hypotheses": [item.model_dump(mode="json") for item in state["hypotheses"]],
        "plan": [item.model_dump(mode="json") for item in state["plan"]],
        "execution_outputs": [item.model_dump(mode="json") for item in state["execution_outputs"]],
        "verification": (
            state["verification"].model_dump(mode="json")
            if state["verification"] is not None
            else None
        ),
        "reflection": (
            state["reflection"].model_dump(mode="json") if state["reflection"] is not None else None
        ),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()[:16]


def _preferred_action_for_gap(gap: KnowledgeGap) -> CognitiveActionType:
    """Map the nature of an obstacle to a general cognitive action."""
    typed = {
        "numeric_computation": CognitiveActionType.CALCULATE,
        "missing_measurement": CognitiveActionType.MEASURE,
        "missing_artifact_knowledge": CognitiveActionType.INSPECT,
        "controlled_experiment": CognitiveActionType.EXPERIMENT,
        "simulation": CognitiveActionType.SIMULATE,
        "current_external_fact": CognitiveActionType.SEARCH,
        "user_owned_information": CognitiveActionType.CLARIFY,
    }.get(gap.gap_type)
    if typed is not None:
        return typed
    text = " ".join(
        part for part in (gap.gap_type, gap.description, gap.suggested_source or "") if part
    ).lower()
    # Paths are data references, not instructions to ask their named users.
    text = re.sub(r"(?:file://)?(?:[A-Za-z]:)?[/\\][^\s]+", " ", text)

    def contains(terms: tuple[str, ...]) -> bool:
        return any(re.search(r"\b" + re.escape(term) + r"\w*\b", text) for term in terms)

    if contains(("ambiguous", "clarif", "user", "human input")):
        return CognitiveActionType.CLARIFY
    if contains(("contradiction", "wrong problem", "reframe")):
        return CognitiveActionType.REFRAME
    if contains(("calculator", "arithmetic", "compute", "numeric")):
        return CognitiveActionType.CALCULATE
    if contains(("experiment", "falsif", "controlled test")):
        return CognitiveActionType.EXPERIMENT
    if contains(("simulation", "simulate")):
        return CognitiveActionType.SIMULATE
    if contains(("measure", "metric", "baseline", "dataset")):
        return CognitiveActionType.MEASURE
    if contains(("code", "file", "log", "document", "repository", "artifact")):
        return CognitiveActionType.INSPECT
    if contains(("memory", "past case", "prior strategy")):
        return CognitiveActionType.RETRIEVE_MEMORY
    if contains(("web", "official", "public", "current", "source", "research", "api")):
        return CognitiveActionType.SEARCH
    return CognitiveActionType.OBSERVE


def _failure_history(
    state: PolyaState,
    target: str,
) -> set[CognitiveActionType]:
    failed: set[CognitiveActionType] = set()
    for event in state["events"]:
        if event.event_type != "capability_observation":
            continue
        if event.metadata.get("target") != target:
            continue
        if event.metadata.get("status") not in {"failed", "blocked", "inconclusive"}:
            continue
        raw_type = event.metadata.get("action_type")
        if isinstance(raw_type, str):
            try:
                failed.add(CognitiveActionType(raw_type))
            except ValueError:
                continue
    return failed


def _candidate_failed_before(
    state: PolyaState,
    candidate: CognitiveActionCandidate,
) -> bool:
    """Prevent an unchanged failed capability call from masquerading as progress."""
    return any(
        event.event_type == "capability_observation"
        and event.metadata.get("action_type") == candidate.action_type.value
        and event.metadata.get("target") == candidate.target
        and event.metadata.get("capability") == candidate.capability
        and event.metadata.get("status") in {"failed", "blocked", "inconclusive"}
        for event in state["events"]
    )


def _constraint_discovery_completed(state: PolyaState) -> bool:
    return any(
        event.engine_name == "constraint_discovery"
        and event.event_type == "completed"
        and event.metadata.get("status") == "ok"
        for event in state["events"]
    )


def _gap_detection_completed(state: PolyaState) -> bool:
    return any(
        event.event_type == "gap_detection_completed" and event.metadata.get("status") == "ok"
        for event in state["events"]
    )


def _capability_for_action(
    action_type: CognitiveActionType,
    registry: CapabilityRegistry,
) -> str:
    """Prefer compute-aware implementations while preserving legacy fallbacks."""
    preferences = {
        CognitiveActionType.DETECT_GAPS: ("task_gap_detector", "gap_detector"),
        CognitiveActionType.HYPOTHESIZE: ("deliberator", "reasoner"),
        CognitiveActionType.VERIFY: ("conclusion_checker", "verifier"),
    }
    for name in preferences.get(action_type, ()):
        if registry.supports(name, action_type):
            return name
    return _DEFAULT_CAPABILITY[action_type]


def _pending_evidence_acquisition(state: PolyaState) -> str | None:
    """Return the oldest acquired candidate batch not yet evaluated."""
    evaluated = {
        acquisition_id
        for event in state["events"]
        if event.event_type == "evidence_evaluation_completed"
        and isinstance((acquisition_id := event.metadata.get("acquisition_id")), str)
    }
    for event in state["events"]:
        acquisition_id = event.metadata.get("acquisition_id")
        if (
            event.event_type == "evidence_candidates_acquired"
            and isinstance(acquisition_id, str)
            and acquisition_id not in evaluated
        ):
            return acquisition_id
    return None


def _requires_sensitive_data_boundary(state: PolyaState) -> bool:
    """Detect an accepted privacy constraint without inventing a parallel contract."""
    problem = state["structured_problem"]
    if problem is None:
        return False
    constraint_text = " ".join(problem.constraints).casefold()
    return any(
        token in constraint_text
        for token in ("privacy", "private", "confidential", "sensitive data", "pii")
    )


class CognitiveController:
    """Choose the next action from explicit state and declared capabilities."""

    policy_version = POLICY_VERSION

    def __init__(
        self,
        procedural_memory: ProceduralPreferenceProvider | None = None,
        semantic_memory: SemanticMemoryAvailabilityProvider | None = None,
        performance_policy: ActionPerformancePolicy | None = None,
    ) -> None:
        self.procedural_memory = procedural_memory
        self.semantic_memory = semantic_memory
        self.performance_policy = performance_policy

    def generate_candidates(
        self,
        state: PolyaState,
        registry: CapabilityRegistry,
    ) -> list[CognitiveActionCandidate]:
        """Generate bounded candidates without asking a model to control the run."""
        problem = state["structured_problem"]
        if problem is None:
            from app.problem_understanding.fallbacks import deterministic_problem_understanding

            deterministic = (
                registry.supports(
                    "deterministic_problem_representation",
                    CognitiveActionType.INTERPRET,
                )
                and deterministic_problem_understanding(state) is not None
            )
            return [
                self._candidate(
                    CognitiveActionType.INTERPRET,
                    capability="deterministic_problem_representation"
                    if deterministic
                    else "problem_representation",
                    target="raw problem input",
                    purpose="Construct a validated initial problem representation.",
                    expected="A structured goal, knowns, unknowns, constraints, and success criteria.",
                    usefulness=0.99,
                    registry=registry,
                )
            ]

        if not _constraint_discovery_completed(state):
            return [
                self._candidate(
                    CognitiveActionType.DISCOVER_CONSTRAINTS,
                    target=problem.core_question,
                    purpose=(
                        "Identify explicit, implicit, and missing requirements before "
                        "choosing a solution path."
                    ),
                    expected=(
                        "A validated constraint set or a focused question for a missing "
                        "user-owned boundary."
                    ),
                    usefulness=0.97,
                    registry=registry,
                )
            ]

        gap_detector = _capability_for_action(CognitiveActionType.DETECT_GAPS, registry)
        if registry.supports(gap_detector, CognitiveActionType.DETECT_GAPS) and not (
            _gap_detection_completed(state)
        ):
            return [
                self._candidate(
                    CognitiveActionType.DETECT_GAPS,
                    target=problem.core_question,
                    purpose=("Identify only the missing knowledge that blocks a verified outcome."),
                    expected=(
                        "Prioritized gaps tied to an available source, tool, or focused "
                        "user question."
                    ),
                    usefulness=0.95,
                    registry=registry,
                    capability=gap_detector,
                )
            ]

        pending_acquisition = _pending_evidence_acquisition(state)
        if pending_acquisition is not None and registry.supports(
            "evidence_evaluator", CognitiveActionType.EVALUATE_EVIDENCE
        ):
            return [
                self._candidate(
                    CognitiveActionType.EVALUATE_EVIDENCE,
                    target=pending_acquisition,
                    purpose=(
                        "Evaluate provenance, quality, relevance, and source independence "
                        "before research results enter canonical evidence."
                    ),
                    expected="Accepted evidence plus explicit rejection and limitation details.",
                    usefulness=0.96,
                    registry=registry,
                )
            ]

        unresolved = sorted(
            (gap for gap in state["gaps"] if not gap.filled),
            key=lambda gap: _PRIORITY_USEFULNESS[gap.priority],
            reverse=True,
        )
        if unresolved:
            candidates: list[CognitiveActionCandidate] = []
            for gap in unresolved[:3]:
                epistemic_status = derive_epistemic_status(state, gap)
                preferred = _preferred_action_for_gap(gap)
                failed = _failure_history(state, gap.description)
                learned = (
                    self.procedural_memory.preference(problem.problem_type, gap.gap_type)
                    if self.procedural_memory is not None
                    else None
                )
                seen: set[tuple[CognitiveActionType, str]] = set()
                if learned is not None and learned.action_type not in failed:
                    candidates.append(
                        self._candidate(
                            learned.action_type,
                            target=gap.description,
                            purpose=(
                                f"Apply a strategy supported by {learned.verified_successes} "
                                "verified related run(s), then verify it in this case."
                            ),
                            expected=(
                                "An observation that tests whether the verified strategy "
                                "transfers to the current problem."
                            ),
                            usefulness=min(
                                0.99,
                                _PRIORITY_USEFULNESS[gap.priority] + 0.1,
                            ),
                            registry=registry,
                            capability=learned.capability,
                        )
                    )
                    seen.add((learned.action_type, learned.capability))
                memory_likely_relevant = (
                    self.semantic_memory.has_relevant_memory(
                        gap.description,
                        problem.domain,
                    )
                    if self.semantic_memory is not None
                    else False
                )
                if (
                    memory_likely_relevant
                    and CognitiveActionType.RETRIEVE_MEMORY not in failed
                    and registry.supports("memory", CognitiveActionType.RETRIEVE_MEMORY)
                    and (CognitiveActionType.RETRIEVE_MEMORY, "memory") not in seen
                ):
                    candidates.append(
                        self._candidate(
                            CognitiveActionType.RETRIEVE_MEMORY,
                            target=gap.description,
                            purpose=(
                                "Check governed long-term memory before paying for new "
                                "acquisition or asking the user."
                            ),
                            expected=(
                                "Current sourced knowledge relevant to the gap, or an "
                                "explicit no-match observation."
                            ),
                            usefulness=min(
                                0.97,
                                _PRIORITY_USEFULNESS[gap.priority] + 0.06,
                            ),
                            registry=registry,
                            capability="memory",
                        )
                    )
                    seen.add((CognitiveActionType.RETRIEVE_MEMORY, "memory"))
                action_options = (preferred, *_RECOVERY_ACTIONS.get(preferred, ()))
                for position, action_type in enumerate(_unique_actions(action_options)):
                    if action_type in failed:
                        continue
                    capability = _DEFAULT_CAPABILITY[action_type]
                    if (action_type, capability) in seen:
                        continue
                    candidates.append(
                        self._candidate(
                            action_type,
                            target=gap.description,
                            purpose=(
                                f"{gap.why_needed} Residual evidence need: "
                                f"{epistemic_status.rationale}"
                            ),
                            expected=(
                                "An observation that resolves or materially narrows "
                                f"the gap: {gap.description}"
                            ),
                            usefulness=max(
                                0.05,
                                _PRIORITY_USEFULNESS[gap.priority] - (position * 0.08),
                            ),
                            registry=registry,
                            capability=capability,
                        )
                    )
            return candidates or [self._stop_candidate(registry, "all gap actions failed")]

        if problem.unknowns:
            return [
                self._candidate(
                    CognitiveActionType.DECOMPOSE,
                    target=problem.unknowns[0],
                    purpose="Convert an unresolved unknown into an actionable knowledge gap.",
                    expected="A smaller unknown with an identifiable source or test.",
                    usefulness=0.78,
                    registry=registry,
                )
            ]

        if not state["hypotheses"]:
            hypothesis_candidates: list[CognitiveActionCandidate] = []
            if deterministic_evidence_attestation_available(state) and registry.supports(
                "attested_evidence_procedure",
                CognitiveActionType.HYPOTHESIZE,
            ):
                hypothesis_candidates.append(
                    self._candidate(
                        CognitiveActionType.HYPOTHESIZE,
                        target=problem.core_question,
                        purpose=(
                            "Close a fully attested deterministic result before spending "
                            "semantic compute."
                        ),
                        expected=(
                            "An integrity-bound candidate plus replayable deterministic check."
                        ),
                        usefulness=0.98,
                        registry=registry,
                        capability="attested_evidence_procedure",
                    )
                )
            hypothesis_capability = (
                "arithmetic_deliberator"
                if problem.problem_type == "simple_arithmetic"
                and registry.supports("arithmetic_deliberator", CognitiveActionType.HYPOTHESIZE)
                else "source_patch_investigator"
                if problem.problem_type
                in {"field_derived_technical_investigation", "source_patch_investigation"}
                and registry.supports(
                    "source_patch_investigator",
                    CognitiveActionType.HYPOTHESIZE,
                )
                else "artifact_lookup_procedure"
                if problem.problem_type == "explicit_artifact_lookup"
                and registry.supports(
                    "artifact_lookup_procedure",
                    CognitiveActionType.HYPOTHESIZE,
                )
                else None
            )
            hypothesis_candidates.append(
                self._candidate(
                    CognitiveActionType.HYPOTHESIZE,
                    target=problem.core_question,
                    purpose=(
                        "Propose one exact source edit for governed present-case execution."
                        if hypothesis_capability == "source_patch_investigator"
                        else "Generate testable explanations or solution paths from current evidence."
                    ),
                    expected=(
                        "One evidence-bound edit plus an independently executable check."
                        if hypothesis_capability == "source_patch_investigator"
                        else "Distinct candidates with expected signals and falsification criteria."
                    ),
                    usefulness=(
                        0.94 if hypothesis_capability == "source_patch_investigator" else 0.82
                    ),
                    registry=registry,
                    capability=hypothesis_capability,
                )
            )
            return hypothesis_candidates

        if not state["plan"]:
            return [
                self._candidate(
                    CognitiveActionType.PLAN,
                    target=problem.core_question,
                    purpose="Turn supported hypotheses into bounded executable checks.",
                    expected="An ordered plan whose tasks have observable outputs.",
                    usefulness=0.79,
                    registry=registry,
                )
            ]

        completed_task_ids = {item.task_id for item in state["execution_outputs"]}
        pending_tasks = [task for task in state["plan"] if task.id not in completed_task_ids]
        if pending_tasks:
            task = pending_tasks[0]
            capability = task.tool_name or _DEFAULT_CAPABILITY[CognitiveActionType.EXECUTE]
            return [
                self._candidate(
                    CognitiveActionType.EXECUTE,
                    target=task.id,
                    purpose=task.action,
                    expected=task.expected_output or "An inspectable execution result.",
                    usefulness=0.84,
                    registry=registry,
                    capability=capability,
                    risk=task.risk_level,
                )
            ]

        if state["verification"] is None:
            verification_candidates: list[CognitiveActionCandidate] = []
            if deterministic_evidence_attestation_available(state) and registry.supports(
                "attested_evidence_procedure",
                CognitiveActionType.VERIFY,
            ):
                verification_candidates.append(
                    self._candidate(
                        CognitiveActionType.VERIFY,
                        target=problem.core_question,
                        purpose=(
                            "Replay every trusted evidence binding before deterministic "
                            "finalization."
                        ),
                        expected=(
                            "A passing report only if producer, version, provenance, hash, "
                            "quality, and criterion coverage still match."
                        ),
                        usefulness=0.99,
                        registry=registry,
                        capability="attested_evidence_procedure",
                    )
                )
            verification_capability = (
                "arithmetic_conclusion_checker"
                if problem.problem_type == "simple_arithmetic"
                and registry.supports("arithmetic_conclusion_checker", CognitiveActionType.VERIFY)
                else "verifier_factory"
                if registry.supports(
                    "verifier_factory",
                    CognitiveActionType.VERIFY,
                )
                and deterministic_verification_available(state)
                else "artifact_lookup_procedure"
                if problem.problem_type == "explicit_artifact_lookup"
                and registry.supports(
                    "artifact_lookup_procedure",
                    CognitiveActionType.VERIFY,
                )
                else None
            )
            verification_candidates.append(
                self._candidate(
                    CognitiveActionType.VERIFY,
                    target=problem.core_question,
                    purpose="Try to disprove the candidate conclusion before accepting it.",
                    expected="Independent checks with pass, failure, or contradiction details.",
                    usefulness=0.96,
                    registry=registry,
                    capability=verification_capability,
                )
            )
            return verification_candidates

        if not state["verification"].passed:
            return [
                self._candidate(
                    CognitiveActionType.REPLAN,
                    target=problem.core_question,
                    purpose="Respond to failed verification with a materially different plan.",
                    expected="A revised plan targeting failed checks or contradictions.",
                    usefulness=0.9,
                    registry=registry,
                )
            ]

        if state["reflection"] is None:
            return [
                self._candidate(
                    CognitiveActionType.REFLECT,
                    target=problem.core_question,
                    purpose="Extract reusable lessons only after verification passes.",
                    expected="Specific successful, failed, and reusable strategy observations.",
                    usefulness=0.62,
                    registry=registry,
                )
            ]

        return [self._stop_candidate(registry, "verified outcome reflected")]

    def decide(
        self,
        state: PolyaState,
        registry: CapabilityRegistry,
    ) -> CognitiveActionDecision:
        """Select the highest-utility safe candidate with an available capability."""
        candidates = self.generate_candidates(state, registry)
        available: list[CognitiveActionCandidate] = []
        rejected: list[RejectedCognitiveAction] = []
        budget = configured_budget(state)
        usage = accumulated_usage(state)
        for candidate in candidates:
            if candidate.action_type is CognitiveActionType.STOP:
                available.append(candidate)
                continue
            if not registry.supports(candidate.capability, candidate.action_type):
                rejected.append(
                    RejectedCognitiveAction(
                        candidate_id=candidate.id,
                        rationale=(
                            f"Capability {candidate.capability} is unavailable or does not "
                            f"support {candidate.action_type.value}."
                        ),
                    )
                )
                continue
            if _candidate_failed_before(state, candidate):
                rejected.append(
                    RejectedCognitiveAction(
                        candidate_id=candidate.id,
                        rationale=(
                            "The same capability action already failed without a material "
                            "state change; repeating it would not create progress."
                        ),
                    )
                )
                continue
            capability = registry.get(candidate.capability)
            if (
                budget is not None
                and capability is not None
                and not reservation_fits(capability.definition, budget, usage)
            ):
                rejected.append(
                    RejectedCognitiveAction(
                        candidate_id=candidate.id,
                        rationale=(
                            f"Capability {candidate.capability} cannot fit the remaining "
                            "hard cognitive budget: "
                            f"{budget_rejection_reason(capability.definition, budget, usage)}."
                        ),
                    )
                )
                continue
            if (
                _requires_sensitive_data_boundary(state)
                and capability is not None
                and not capability.definition.approved_for_sensitive_data
            ):
                rejected.append(
                    RejectedCognitiveAction(
                        candidate_id=candidate.id,
                        rationale=(
                            f"Capability {candidate.capability} is not approved for sensitive "
                            "data required by an accepted privacy constraint."
                        ),
                    )
                )
                continue
            available.append(candidate)

        if not available:
            selected = self._stop_candidate(registry, "no safe supported action")
        else:
            selected = max(
                available,
                key=lambda candidate: self._utility(state, registry, candidate)[0],
            )

        selected_utility, selected_estimate = self._utility(state, registry, selected)

        for candidate in available:
            if candidate.id == selected.id:
                continue
            candidate_utility, candidate_estimate = self._utility(
                state,
                registry,
                candidate,
            )
            rejected.append(
                RejectedCognitiveAction(
                    candidate_id=candidate.id,
                    rationale=(
                        f"Lower bounded utility ({candidate_utility:.3f}) than selected "
                        f"action ({selected_utility:.3f}). "
                        f"Adaptive estimate: {self._estimate_rationale(candidate_estimate)}"
                    ),
                )
            )

        return CognitiveActionDecision(
            policy_version=self.policy_version,
            state_fingerprint=_state_fingerprint(state),
            selected=selected,
            rejected=rejected,
            rationale=(
                f"Selected {selected.action_type.value} for {selected.target} from "
                f"explicit state using expected verified progress per marginal cost, "
                f"risk, failure history, remaining budget, and declared capability "
                f"availability. Selected bounded utility {selected_utility:.3f}. "
                f"Adaptive estimate: {self._estimate_rationale(selected_estimate)}"
            ),
        )

    def _candidate(
        self,
        action_type: CognitiveActionType,
        *,
        target: str,
        purpose: str,
        expected: str,
        usefulness: float,
        registry: CapabilityRegistry,
        capability: str | None = None,
        risk: RiskLevel = RiskLevel.LOW,
    ) -> CognitiveActionCandidate:
        capability_name = capability or _capability_for_action(action_type, registry)
        definition = registry.get(capability_name)
        estimated_cost = definition.definition.estimated_cost if definition is not None else 1.0
        identity = hashlib.sha256(
            f"{action_type.value}|{target}|{capability_name}".encode()
        ).hexdigest()[:12]
        return CognitiveActionCandidate(
            id=f"action-{identity}",
            action_type=action_type,
            target=target,
            purpose=purpose,
            expected_observation=expected,
            expected_usefulness=usefulness,
            estimated_cost=estimated_cost,
            risk_level=risk,
            capability=capability_name,
            success_condition="The expected observation is produced with inspectable provenance.",
            failure_condition="The capability fails, is blocked, or does not reduce the target obstacle.",
        )

    def _stop_candidate(
        self,
        registry: CapabilityRegistry,
        reason: str,
    ) -> CognitiveActionCandidate:
        return self._candidate(
            CognitiveActionType.STOP,
            target="current run",
            purpose=f"Stop safely because {reason}.",
            expected="A truthful terminal status without a forced conclusion.",
            usefulness=0.05,
            registry=registry,
            capability=CONTROLLER_CAPABILITY,
        )

    def _utility(
        self,
        state: PolyaState,
        registry: CapabilityRegistry,
        candidate: CognitiveActionCandidate,
    ) -> tuple[float, AdaptiveActionEstimate | None]:
        progress = candidate.expected_usefulness
        effective_cost = candidate.estimated_cost
        estimate: AdaptiveActionEstimate | None = None
        capability = registry.get(candidate.capability)
        if self.performance_policy is not None and capability is not None:
            estimate = self.performance_policy.estimate(
                state,
                candidate,
                capability.definition,
            )
            progress *= estimate.progress_multiplier
            effective_cost += estimate.extra_effective_cost
        verified_progress_per_cost = progress / (0.1 + effective_cost)
        return (
            verified_progress_per_cost - _RISK_PENALTY[candidate.risk_level],
            estimate,
        )

    @staticmethod
    def _estimate_rationale(estimate: AdaptiveActionEstimate | None) -> str:
        if estimate is None:
            return "disabled; used declared estimates only."
        return (
            f"{estimate.policy_version}, samples={estimate.sample_count}, "
            f"confidence={estimate.sample_confidence:.3f}, progress multiplier="
            f"{estimate.progress_multiplier:.3f}, extra cost="
            f"{estimate.extra_effective_cost:.3f}. {estimate.rationale}"
        )


def _unique_actions(
    actions: Iterable[CognitiveActionType],
) -> list[CognitiveActionType]:
    return list(dict.fromkeys(actions))
