"""Lean-first differential verification for self-contained implementation tasks.

Stage A solves with one bounded tool loop. Stage B asks an independent oracle,
which never sees the candidate, for a brute-force reference, an input generator
and the problem's own examples. Stage C runs a deterministic differential harness
in the sandbox. Stage D adjudicates the smallest concrete disagreement against
quoted problem text and repairs the side judged wrong. Stage E certifies only what
was actually observed.
"""

from __future__ import annotations

import ast
import difflib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from time import perf_counter
from typing import Any, Protocol

from pydantic import ValidationError

from app.execution.sandbox import SandboxExecutionResult
from app.llm import (
    LLMClient,
    LLMClientError,
    LLMMessage,
    LLMRequest,
    LLMRequestOptions,
    LLMRole,
)
from app.memory.failure_patterns import FailurePatternStore
from app.models.contracts import ContractModel
from app.verified_coding.contracts import (
    Adjudication,
    Certificate,
    CertificateStatus,
    Finding,
    ModelCallRecord,
    OraclePackage,
    Proposal,
    Relaxation,
    SandboxRunRecord,
    Verdict,
)
from app.verified_coding.harness import (
    DifferentialResult,
    Example,
    HarnessConfig,
    Regression,
    build_program,
    parse_result,
    tools_source,
)
from app.verified_coding.prompts import (
    SOLVE_PROMPT,
    adjudicate_prompt,
    oracle_prompt,
    performance_prompt,
)

LIMITATIONS = [
    "The reference oracle is written by a model from the same problem text and can share a misreading.",
    "Randomized differential testing covers small generated inputs; it is not a proof of correctness.",
    "Scale timing is an observation in a constrained sandbox, not a complexity proof.",
    "Adjudication applies quoted problem text to one concrete input; it is a model judgment, re-checked by execution.",
]


class Sandbox(Protocol):
    @property
    def limits(self) -> Any: ...

    def execute(self, code: str, tests: Any = ()) -> SandboxExecutionResult: ...


@dataclass(frozen=True)
class PipelineLimits:
    solve_calls: int = 3
    solve_sandbox_calls: int = 3
    oracle_attempts: int = 2
    repair_rounds: int = 2
    per_request_output_tokens: int = 6_000
    request_timeout_seconds: float = 90.0
    max_retries: int = 2
    differential_budget_seconds: float = 6.0
    call_seconds: float = 1.0
    scale_seconds: float = 4.0


@dataclass
class SolveOutcome:
    proposal: Proposal | None = None
    passed: bool = False
    attempts: int = 0
    last_execution: SandboxExecutionResult | None = None
    failure: str | None = None


@dataclass
class VerifiedOutcome:
    problem: str
    solve: SolveOutcome
    certificate: Certificate
    code: str | None
    explanation: str
    oracle: OraclePackage | None = None
    model_calls: list[ModelCallRecord] = field(default_factory=list)
    sandbox_runs: list[SandboxRunRecord] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    elapsed_ms: float = 0.0


class SandboxUnavailable(RuntimeError):
    """The execution infrastructure, not the code under test, failed."""


_INFRASTRUCTURE = re.compile(
    r"docker (api|daemon)|cannot connect to the docker|failed to connect to the docker"
    r"|error response from daemon|no such image|unable to find image",
    re.IGNORECASE,
)


def infrastructure_failure(result: SandboxExecutionResult) -> bool:
    """True when the container never ran the program (daemon or image unavailable)."""
    return bool(
        result.exit_code != 0
        and not result.test_results
        and not result.timed_out
        and "Traceback" not in result.stderr
        and _INFRASTRUCTURE.search(result.stderr)
    )


def _strip_fences(code: str) -> str:
    text = code.strip()
    match = re.fullmatch(r"```[a-zA-Z0-9_+-]*\n(.*?)\n?```", text, re.DOTALL)
    return (match.group(1) if match else text).strip() + "\n"


def _normalize(text: str) -> str:
    text = text.replace("’", "'").replace("‘", "'").replace('"', "'").replace("`", "'")
    return re.sub(r"\s+", " ", text).strip().lower()


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text.replace('"', "'"))


def _passed(result: SandboxExecutionResult, count: int) -> bool:
    return bool(
        count > 0
        and result.exit_code == 0
        and not result.timed_out
        and not result.output_truncated
        and result.tests_run == count
        and [test.index for test in result.test_results] == list(range(1, count + 1))
        and all(test.passed for test in result.test_results)
    )


def _split_assertions(text: str) -> list[str]:
    """Split a newline-joined block of assertions into individual statements."""
    tests: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        if line.lstrip().startswith("assert") or not tests:
            tests.append(line.strip())
        else:
            tests[-1] += "\n" + line
    return tests


def parse_proposal(text: str) -> Proposal:
    """Validate a solver proposal, tolerating one common shape slip: tests as one string."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return Proposal.model_validate_json(text)
    if isinstance(payload, dict) and isinstance(payload.get("tests"), str):
        payload = {**payload, "tests": _split_assertions(payload["tests"])}
    return Proposal.model_validate(payload)


def schema_feedback(error: ValidationError) -> str:
    details = "; ".join(
        f"{'.'.join(str(part) for part in item['loc']) or 'response'}: {item['msg']}"
        for item in error.errors()[:5]
    )
    return (
        "Invalid schema (" + details + "). Return only the requested JSON object: "
        '{"code": string, "tests": [string, ...], "explanation": string}.'
    )


def sourced_examples(problem: str, examples: list[Example]) -> tuple[list[Example], int]:
    """Keep examples whose call (or its arguments) and expected value appear in the problem."""
    compact = _compact(problem)
    kept: list[Example] = []
    for example in examples:
        call = _compact(example.call)
        args = call[call.find("(") + 1 : call.rfind(")")] if "(" in call else call
        expected = _compact(example.expected)
        call_ok = call in compact or (len(args) >= 3 and args in compact)
        if call_ok and expected and expected in compact:
            kept.append(example)
    return kept, len(examples) - len(kept)


def quote_supported(problem: str, quote: str) -> bool:
    """A governing requirement must be (nearly) verbatim problem text."""
    needle = _normalize(quote).strip(" .;:,'")
    if len(needle) < 8:
        return False
    haystack = _normalize(problem)
    if needle in haystack:
        return True
    match = difflib.SequenceMatcher(None, haystack, needle, autojunk=False).find_longest_match(
        0, len(haystack), 0, len(needle)
    )
    return match.size >= 0.9 * len(needle)


def _literal(text: str) -> tuple[bool, Any]:
    try:
        return True, ast.literal_eval(text.strip())
    except ValueError, SyntaxError, TypeError, MemoryError, RecursionError:
        return False, None


def _same_value(left: Any, right: Any) -> bool:
    try:
        return bool(left == right)
    except Exception:  # noqa: BLE001 - arbitrary literal comparison
        return False


class VerifiedCodingPipeline:
    """Bounded solve-verify-repair loop over one LLM client and one sandbox."""

    def __init__(
        self,
        client: LLMClient,
        model: str,
        sandbox: Sandbox,
        *,
        limits: PipelineLimits | None = None,
        progress: Callable[[dict[str, Any]], None] | None = None,
        patterns: FailurePatternStore | None = None,
        source: str = "",
    ) -> None:
        self.client = client
        self.model = model
        self.sandbox = sandbox
        self.limits = limits or PipelineLimits()
        self.patterns, self.source = patterns, source
        self._progress = progress
        self.model_calls: list[ModelCallRecord] = []
        self.sandbox_runs: list[SandboxRunRecord] = []
        self.events: list[dict[str, Any]] = []
        self._solve_sandbox_calls = 0

    # ----- recording -------------------------------------------------------
    def _event(self, event_type: str, mode: str, summary: str, **metadata: Any) -> None:
        event = {
            "engine_name": "verified_coding",
            "event_type": event_type,
            "reasoning_mode": mode,
            "summary": summary,
            "metadata": metadata,
        }
        self.events.append(event)
        if self._progress is not None:
            self._progress(event)

    def _complete(self, role: str, content: str) -> str:
        return self._chat(role, [LLMMessage(role=LLMRole.USER, content=content)])

    def _chat(self, role: str, messages: list[LLMMessage]) -> str:
        request = LLMRequest(
            model=self.model,
            messages=messages,
            options=LLMRequestOptions(
                max_output_tokens=self.limits.per_request_output_tokens,
                json_mode=True,
                timeout_seconds=self.limits.request_timeout_seconds,
                total_timeout_seconds=self.limits.request_timeout_seconds,
                max_retries=self.limits.max_retries,
            ),
        )
        started = perf_counter()
        try:
            response = self.client.complete(request)
        except Exception as exc:
            self.model_calls.append(
                ModelCallRecord(
                    role=role,
                    model=self.model,
                    duration_ms=(perf_counter() - started) * 1000,
                    outcome=type(exc).__name__,
                )
            )
            self._event(
                "verified_coding_model_failed",
                "execute",
                f"The {role} model call failed ({type(exc).__name__}).",
                role=role,
            )
            raise
        record = ModelCallRecord(
            role=role,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cost_usd=response.usage.estimated_cost_usd,
            duration_ms=(perf_counter() - started) * 1000,
        )
        self.model_calls.append(record)
        self._event(
            "cognitive_resource_usage",
            "execute",
            f"Recorded resources used by the {role} model call.",
            capability=f"verified_coding.{role}",
            capability_kind="model",
            action_type="execute" if role in {"solver", "performance_repair"} else "verify",
            model_calls=1,
            external_calls=0,
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            normalized_cost=0.0,
            duration_ms=round(record.duration_ms, 3),
        )
        return response.text

    def _execute(
        self, purpose: str, code: str, tests: list[str] | tuple[()] = ()
    ) -> SandboxExecutionResult:
        result = self.sandbox.execute(code, tests)
        if infrastructure_failure(result):
            self._event(
                "verified_coding_sandbox_unavailable",
                "execute",
                "The isolated execution sandbox is unavailable; stopping instead of treating it as a code failure.",
                purpose=purpose,
            )
            raise SandboxUnavailable(result.stderr.strip().splitlines()[0][:200])
        self.sandbox_runs.append(
            SandboxRunRecord(
                purpose=purpose,
                runtime_ms=round(result.runtime_ms, 3),
                timed_out=result.timed_out,
                exit_code=result.exit_code,
            )
        )
        return result

    # ----- stage A: lean solve --------------------------------------------
    def solve(self, problem: str) -> SolveOutcome:
        outcome = SolveOutcome()
        messages = [LLMMessage(role=LLMRole.USER, content=SOLVE_PROMPT + problem)]
        for _ in range(self.limits.solve_calls):
            try:
                text = self._chat("solver", messages)
            except LLMClientError as exc:
                outcome.failure = f"solver model call failed: {exc.code.value}"
                break
            except Exception as exc:  # noqa: BLE001 - metered clients raise budget errors
                outcome.failure = f"solver model call failed: {type(exc).__name__}"
                break
            outcome.attempts += 1
            messages.append(LLMMessage(role=LLMRole.ASSISTANT, content=text))
            try:
                proposal = parse_proposal(text)
            except ValidationError as exc:
                messages.append(LLMMessage(role=LLMRole.USER, content=schema_feedback(exc)))
                continue
            outcome.proposal = proposal
            if self._solve_sandbox_calls >= self.limits.solve_sandbox_calls:
                outcome.failure = "solver sandbox allowance exhausted"
                break
            self._solve_sandbox_calls += 1
            try:
                result = self._execute("solver_self_tests", proposal.code, proposal.tests)
            except ValueError as exc:
                messages.append(
                    LLMMessage(
                        role=LLMRole.USER,
                        content=f"The sandbox rejected the proposal: {exc}. Repair and resend.",
                    )
                )
                continue
            outcome.last_execution = result
            if _passed(result, len(proposal.tests)):
                outcome.passed = True
                break
            messages.append(
                LLMMessage(
                    role=LLMRole.USER,
                    content="Observed sandbox result; repair and rerun: "
                    + result.model_dump_json(),
                )
            )
        self._event(
            "verified_coding_solved" if outcome.passed else "verified_coding_solve_incomplete",
            "execute",
            (
                f"Lean solver produced code that passed its own {len(outcome.proposal.tests)} assertions."
                if outcome.passed and outcome.proposal
                else "Lean solver did not produce code that passes its own assertions."
            ),
            attempts=outcome.attempts,
            own_tests=len(outcome.proposal.tests) if outcome.proposal else 0,
            failure=outcome.failure,
        )
        return outcome

    # ----- stage B: independent oracle ------------------------------------
    def _oracle(self, problem: str, feedback: str | None = None) -> OraclePackage | None:
        content = oracle_prompt(problem)
        if self.patterns is not None:
            # Hints shape generated inputs; they never become requirements.
            content += self.patterns.prompt_hints("coding", problem)
        if feedback:
            content += (
                "\nYOUR PREVIOUS ORACLE COULD NOT BE USED: "
                + feedback
                + "\nReturn a corrected complete JSON object."
            )
        try:
            text = self._complete("oracle", content)
        except Exception:  # noqa: BLE001 - failure already recorded
            return None
        try:
            package = OraclePackage.model_validate_json(text)
        except ValidationError as exc:
            self._event(
                "verified_coding_oracle_rejected",
                "verify",
                "The oracle response did not match its schema.",
                errors=len(exc.errors()),
            )
            return None
        return package.model_copy(
            update={
                "reference_code": _strip_fences(package.reference_code),
                "generator_code": _strip_fences(package.generator_code),
                "scale_code": _strip_fences(package.scale_code)
                if package.scale_code.strip()
                else "",
                "same_code": _strip_fences(package.same_code) if package.same_code.strip() else "",
            }
        )

    # ----- stage C: differential execution --------------------------------
    def _differential(
        self,
        *,
        candidate: str,
        oracle: OraclePackage,
        reference: str,
        examples: list[Example],
        regressions: list[Regression],
        relaxations: list[str],
    ) -> DifferentialResult:
        config = HarnessConfig(
            entrypoint=oracle.entrypoint.harness(),
            examples=examples,
            regressions=regressions,
            budget_seconds=self.limits.differential_budget_seconds,
            call_seconds=self.limits.call_seconds,
            scale_seconds=self.limits.scale_seconds,
            relaxations=relaxations,
        )
        try:
            program = build_program(
                candidate=candidate,
                reference=reference,
                tools=tools_source(oracle.generator_code, oracle.same_code, oracle.scale_code),
                config=config,
            )
        except ValueError as exc:
            return DifferentialResult(setup_error=f"harness: {exc}")
        needed = (
            self.limits.differential_budget_seconds
            + 3 * self.limits.scale_seconds
            + 4 * self.limits.call_seconds
            + 8
        )
        original_limits = self.sandbox.limits
        extended = getattr(original_limits, "timeout_seconds", needed) < needed
        try:
            if extended:
                self.sandbox.limits = replace(original_limits, timeout_seconds=needed)  # type: ignore[misc]
            execution = self._execute("differential", program)
        except ValueError as exc:
            return DifferentialResult(setup_error=f"harness: {exc}")
        finally:
            if extended:
                self.sandbox.limits = original_limits  # type: ignore[misc]
        result = parse_result(execution)
        self._event(
            "verified_coding_differential",
            "compare",
            (
                f"Compared candidate with the independent reference on {result.cases_compared} "
                f"generated inputs; {result.disagreements} disagreements."
                if result.setup_error is None
                else f"Differential run could not start: {result.setup_error}"
            ),
            result=result.model_dump(mode="json"),
        )
        return result

    # ----- stage D: adjudication ------------------------------------------
    def _adjudicate(
        self,
        problem: str,
        *,
        source: str,
        args: str,
        candidate_output: str,
        reference_output: str,
        candidate: str,
        reference: str,
    ) -> Adjudication | None:
        try:
            text = self._complete(
                "adjudicator",
                adjudicate_prompt(
                    problem=problem,
                    source=source,
                    args=args,
                    candidate_output=candidate_output,
                    reference_output=reference_output,
                    candidate_code=candidate,
                    reference_code=reference,
                ),
            )
        except Exception:  # noqa: BLE001 - failure already recorded
            return None
        try:
            ruling = Adjudication.model_validate_json(text)
        except ValidationError:
            self._event(
                "verified_coding_adjudication_rejected",
                "verify",
                "The adjudication response did not match its schema.",
            )
            return None
        return ruling.model_copy(
            update={
                "repaired_candidate_code": _strip_fences(ruling.repaired_candidate_code)
                if ruling.repaired_candidate_code.strip()
                else "",
                "repaired_reference_code": _strip_fences(ruling.repaired_reference_code)
                if ruling.repaired_reference_code.strip()
                else "",
            }
        )

    @staticmethod
    def _consistency_failure(
        ruling: Adjudication,
        *,
        candidate_output: str,
        reference_output: str,
        stated_expected: str | None,
    ) -> str | None:
        """Reject rulings whose expected value contradicts the side they select."""
        verdict = ruling.verdict
        if verdict in {Verdict.AMBIGUOUS, Verdict.BOTH_ACCEPTABLE}:
            return None
        ok, expected = _literal(ruling.expected)
        if not ok:
            return "expected value is not a Python literal"
        if stated_expected is not None:
            stated_ok, stated = _literal(stated_expected)
            if stated_ok and not _same_value(expected, stated):
                return "expected value contradicts the example stated in the problem"
        cand_ok, cand = _literal(candidate_output)
        ref_ok, ref = _literal(reference_output)
        if verdict is Verdict.CANDIDATE_WRONG:
            if cand_ok and _same_value(expected, cand):
                return "ruled the candidate wrong but expects the candidate's output"
            if ref_ok and stated_expected is None and not _same_value(expected, ref):
                return "ruled only the candidate wrong but expects a value the reference did not return"
        if verdict is Verdict.REFERENCE_WRONG:
            if ref_ok and _same_value(expected, ref):
                return "ruled the reference wrong but expects the reference's output"
            if cand_ok and not _same_value(expected, cand):
                return "ruled only the reference wrong but expects a value the candidate did not return"
        if verdict is Verdict.BOTH_WRONG and (
            (cand_ok and _same_value(expected, cand)) or (ref_ok and _same_value(expected, ref))
        ):
            return "ruled both wrong but expects one side's output"
        return None

    # ----- orchestration ---------------------------------------------------
    def verify(self, problem: str, solved: SolveOutcome) -> VerifiedOutcome:
        started = perf_counter()
        proposal = solved.proposal
        certificate = Certificate(status=CertificateStatus.NO_CANDIDATE, limitations=LIMITATIONS)
        if proposal is None:
            return self._finish(problem, solved, certificate, None, "", None, started)
        certificate.own_tests_passed = solved.passed
        certificate.own_test_count = len(proposal.tests)
        candidate = _strip_fences(proposal.code)
        explanation = proposal.explanation

        oracle: OraclePackage | None = None
        examples: list[Example] = []
        result: DifferentialResult | None = None
        last_result: DifferentialResult | None = None
        feedback: str | None = None
        for _ in range(self.limits.oracle_attempts):
            oracle = self._oracle(problem, feedback)
            if oracle is None:
                feedback = "the response was not a valid JSON object with the required keys"
                continue
            examples, dropped = sourced_examples(
                problem, [item.harness() for item in oracle.examples]
            )
            certificate.examples_sourced, certificate.examples_dropped = len(examples), dropped
            result = self._differential(
                candidate=candidate,
                oracle=oracle,
                reference=oracle.reference_code,
                examples=examples,
                regressions=[],
                relaxations=[],
            )
            failure = self._oracle_defect(result)
            last_result = result
            if failure is None:
                break
            feedback = failure
            result = None
        if oracle is None or result is None:
            certificate.status = CertificateStatus.UNVERIFIED
            if last_result is not None:
                certificate.final_differential = last_result
                certificate.cases_compared = last_result.cases_compared
                certificate.sizes_covered = last_result.sizes_covered
            certificate.limitations = [
                "No usable independent oracle was produced; only the solver's own assertions ran.",
                f"Independent checking stopped: {feedback or 'no usable result'}"[:600],
                *LIMITATIONS,
            ]
            self._event(
                "verified_coding_unverified",
                "verify",
                "Independent verification could not be established; delivering with an explicit warning.",
                reason=feedback,
            )
            return self._finish(
                problem, solved, certificate, candidate, explanation, oracle, started
            )

        certificate.entrypoint = oracle.entrypoint.harness().label()
        certificate.assumptions = list(oracle.assumptions)
        reference = oracle.reference_code
        regressions: list[Regression] = []
        relaxations: list[str] = []
        repaired_candidate = False
        status: CertificateStatus | None = None
        for round_number in range(1, self.limits.repair_rounds + 1):
            finding = self._next_finding(result)
            if finding is None:
                break
            source, args, cand_out, ref_out, stated = finding
            if source == "scale":
                repaired = self._repair_performance(
                    problem, candidate, result, certificate, round_number
                )
                if repaired is None:
                    status = CertificateStatus.DISPUTED
                    break
                candidate = repaired
                repaired_candidate = True
            else:
                ruling = self._adjudicate(
                    problem,
                    source=source
                    if stated is None
                    else f"{source}; the problem states the expected output is {stated}",
                    args=args,
                    candidate_output=cand_out,
                    reference_output=ref_out,
                    candidate=candidate,
                    reference=reference,
                )
                record = Finding(
                    round=round_number,
                    source=source,
                    args=args,
                    candidate_output=cand_out,
                    reference_output=ref_out,
                    verdict=ruling.verdict.value if ruling else "no_ruling",
                    expected=ruling.expected if ruling else "",
                    governing_requirement=ruling.governing_requirement if ruling else "",
                    explanation=ruling.explanation if ruling else "",
                )
                certificate.findings.append(record)
                rejection = self._ruling_rejection(
                    problem,
                    ruling,
                    source=source,
                    cand_out=cand_out,
                    ref_out=ref_out,
                    stated=stated,
                )
                if rejection is not None:
                    self._event(
                        "verified_coding_ruling_rejected",
                        "verify",
                        f"Adjudication was not applied: {rejection}.",
                        round=round_number,
                    )
                    status = CertificateStatus.DISPUTED
                    break
                assert ruling is not None
                self._event(
                    "verified_coding_ruling",
                    "verify",
                    f"Adjudicated {source}: {ruling.verdict.value}.",
                    round=round_number,
                    verdict=ruling.verdict.value,
                    governing_requirement=ruling.governing_requirement,
                )
                if ruling.verdict is Verdict.AMBIGUOUS:
                    certificate.open_question = ruling.question or (
                        f"The problem does not determine the output for input {args}."
                    )
                    status = CertificateStatus.AMBIGUOUS
                    break
                if ruling.verdict is Verdict.BOTH_ACCEPTABLE:
                    relaxations.append(ruling.relaxation.value)
                else:
                    if ruling.verdict in {Verdict.CANDIDATE_WRONG, Verdict.BOTH_WRONG}:
                        candidate = ruling.repaired_candidate_code
                        repaired_candidate = True
                    if ruling.verdict in {Verdict.REFERENCE_WRONG, Verdict.BOTH_WRONG}:
                        reference = ruling.repaired_reference_code
                    if source in {"differential", "regression"}:
                        regressions.append(Regression(args=args, expected=ruling.expected.strip()))
                record.resolved = True
            result = self._differential(
                candidate=candidate,
                oracle=oracle,
                reference=reference,
                examples=examples,
                regressions=regressions,
                relaxations=relaxations,
            )
            if result.setup_error is not None:
                status = CertificateStatus.DISPUTED
                break
        if status is None:
            pending = self._next_finding(result)
            if pending is None and result.coverage_failure is not None:
                status = CertificateStatus.UNVERIFIED
            elif pending is None:
                status = (
                    CertificateStatus.REPAIRED if repaired_candidate else CertificateStatus.VERIFIED
                )
            else:
                status = CertificateStatus.DISPUTED
                if not any(not item.resolved for item in certificate.findings):
                    source, args, cand_out, ref_out, _ = pending
                    certificate.findings.append(
                        Finding(
                            round=self.limits.repair_rounds + 1,
                            source=source,
                            args=args,
                            candidate_output=cand_out,
                            reference_output=ref_out,
                            verdict="unresolved_after_repair_budget",
                        )
                    )
        certificate.status = status
        if result.coverage_failure is not None:
            certificate.limitations.insert(0, result.coverage_failure)
        certificate.cases_compared = result.cases_compared
        certificate.sizes_covered = result.sizes_covered
        certificate.scale_seconds = [
            item.seconds for item in result.scale if item.seconds is not None
        ]
        certificate.scale_timeouts = sum(1 for item in result.scale if item.timed_out)
        certificate.final_differential = result
        certificate.regressions = regressions
        if repaired_candidate:
            explanation = (
                explanation
                + "\n\nPolyaBrain repaired this implementation after independent verification found "
                "a concrete input where it contradicted the problem statement (see findings)."
            )
        return self._finish(problem, solved, certificate, candidate, explanation, oracle, started)

    def _repair_performance(
        self,
        problem: str,
        candidate: str,
        result: DifferentialResult,
        certificate: Certificate,
        round_number: int,
    ) -> str | None:
        try:
            text = self._complete(
                "performance_repair",
                performance_prompt(
                    problem=problem,
                    candidate_code=candidate,
                    result=result,
                    seconds=self.limits.scale_seconds,
                ),
            )
            payload = json.loads(text)
            code = payload.get("repaired_candidate_code") if isinstance(payload, dict) else None
        except Exception:  # noqa: BLE001 - malformed repair is a dispute, not a crash
            code = None
        certificate.findings.append(
            Finding(
                round=round_number,
                source="scale",
                args="; ".join(item.input_summary for item in result.scale_failures),
                candidate_output="exceeded time limit",
                reference_output="not run at scale",
                verdict="performance_repair" if code else "no_repair",
                resolved=bool(code),
            )
        )
        if not isinstance(code, str) or not code.strip():
            return None
        return _strip_fences(code)

    @staticmethod
    def _oracle_defect(result: DifferentialResult) -> str | None:
        if result.setup_error is not None:
            if result.setup_error.startswith("harness:"):
                return result.setup_error
            return f"the oracle code failed to load or run: {result.setup_error}"
        if result.cases_compared == 0:
            return (
                "no generated input could be compared "
                f"(generator errors {result.generator_errors}, reference timeouts {result.reference_skipped}); "
                "generate(rng, size) must return a tuple of valid arguments and the reference must be fast on them"
            )
        # A concrete counterexample remains useful even if another sample failed.
        # Final certification rechecks coverage after any applied repair.
        if VerifiedCodingPipeline._next_finding(result) is not None:
            return None
        return result.coverage_failure

    @staticmethod
    def _next_finding(
        result: DifferentialResult,
    ) -> tuple[str, str, str, str, str | None] | None:
        """Pick the most decisive unresolved finding: stated examples first."""
        for example in result.examples:
            if not example.candidate_ok or not example.reference_ok:
                return (
                    "stated_example",
                    example.call,
                    example.candidate,
                    example.reference,
                    example.expected,
                )
        if result.regressions_failed:
            item = result.regressions_failed[0]
            return ("regression", item.args, item.candidate, item.reference, item.reference)
        for item in result.counterexamples:
            if item.kind == "input_mutated":
                return ("mutation", item.args, item.candidate, item.reference, None)
        if result.counterexamples:
            item = result.counterexamples[0]
            return ("differential", item.args, item.candidate, item.reference, None)
        if result.scale_failures:
            return ("scale", "", "", "", None)
        return None

    def _ruling_rejection(
        self,
        problem: str,
        ruling: Adjudication | None,
        *,
        source: str,
        cand_out: str,
        ref_out: str,
        stated: str | None,
    ) -> str | None:
        if ruling is None:
            return "no valid ruling was returned"
        if ruling.verdict is Verdict.AMBIGUOUS:
            return None
        if not quote_supported(problem, ruling.governing_requirement):
            return "the governing requirement is not verbatim problem text"
        if ruling.verdict is Verdict.BOTH_ACCEPTABLE:
            if ruling.relaxation is Relaxation.NONE:
                return "both outputs were accepted without a supported equivalence"
            return None
        if (
            ruling.verdict in {Verdict.CANDIDATE_WRONG, Verdict.BOTH_WRONG}
            and not ruling.repaired_candidate_code
        ):
            return "the candidate was ruled wrong without a repair"
        if (
            ruling.verdict in {Verdict.REFERENCE_WRONG, Verdict.BOTH_WRONG}
            and not ruling.repaired_reference_code
        ):
            return "the reference was ruled wrong without a repair"
        if source == "mutation":
            return None
        return self._consistency_failure(
            ruling,
            candidate_output=cand_out,
            reference_output=ref_out,
            stated_expected=stated,
        )

    def _finish(
        self,
        problem: str,
        solved: SolveOutcome,
        certificate: Certificate,
        code: str | None,
        explanation: str,
        oracle: OraclePackage | None,
        started: float,
    ) -> VerifiedOutcome:
        if self.patterns is not None:
            recorded: set[str] = set()
            for finding in certificate.findings:
                if not finding.resolved or finding.verdict not in {"candidate_wrong", "both_wrong"}:
                    continue
                key = finding.explanation or finding.governing_requirement
                if key in recorded:
                    continue  # one confirmation per pattern per run
                recorded.add(key)
                self.patterns.record(
                    "coding",
                    finding.explanation
                    or finding.governing_requirement
                    or "Draft contradicted the problem",
                    trigger=f"input {finding.args}: draft {finding.candidate_output}, correct {finding.expected}",
                    evidence=finding.governing_requirement,
                    source=self.source,
                )
        self._event(
            "verified_coding_certified",
            "verify",
            f"Verification status: {certificate.status.value}.",
            status=certificate.status.value,
            cases_compared=certificate.cases_compared,
            findings=len(certificate.findings),
        )
        return VerifiedOutcome(
            problem=problem,
            solve=solved,
            certificate=certificate,
            code=code,
            explanation=explanation,
            oracle=oracle,
            model_calls=list(self.model_calls),
            sandbox_runs=list(self.sandbox_runs),
            events=list(self.events),
            elapsed_ms=(perf_counter() - started) * 1000,
        )

    def run(self, problem: str) -> VerifiedOutcome:
        started = perf_counter()
        outcome = self.verify(problem, self.solve(problem))
        outcome.elapsed_ms = (perf_counter() - started) * 1000
        return outcome


class OutcomeSummary(ContractModel):
    """Compact JSON summary used by evaluations and exports."""

    status: str
    model_calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: float | None
    sandbox_runs: int
    findings: int


def summarize(outcome: VerifiedOutcome) -> OutcomeSummary:
    costs = [call.cost_usd for call in outcome.model_calls]
    return OutcomeSummary(
        status=outcome.certificate.status.value,
        model_calls=len(outcome.model_calls),
        input_tokens=sum(call.input_tokens for call in outcome.model_calls),
        output_tokens=sum(call.output_tokens for call in outcome.model_calls),
        cost_usd=None
        if any(cost is None for cost in costs)
        else round(sum(c or 0 for c in costs), 8),
        sandbox_runs=len(outcome.sandbox_runs),
        findings=len(outcome.certificate.findings),
    )
