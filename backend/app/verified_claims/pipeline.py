"""Answer a data question lean, then prove or refute every quantitative claim."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from enum import StrEnum
from time import perf_counter
from typing import Any

from pydantic import Field, ValidationError

from app.execution.sandbox import SandboxExecutionResult
from app.llm import LLMClient, LLMMessage, LLMRequest, LLMRequestOptions, LLMRole
from app.llm.errors import provider_failure_reason
from app.memory.failure_patterns import FailurePatternStore
from app.models.contracts import ContractModel
from app.verified_claims.runner import ClaimRunReport, build_program, parse, same, stated_tolerance
from app.verified_claims.tables import Table, schema_text
from app.verified_coding.contracts import ModelCallRecord, ModelOutput
from app.verified_coding.pipeline import SandboxUnavailable, _strip_fences, infrastructure_failure

PROMPT_VERSION = "verified_claims@0.1.0"

ANSWER_PROMPT = """You are answering a question about the user's data (prompt {version}).
Return exactly one JSON object:
- "answer": a concise answer for the user that states every number it relies on.
- "claims": at most 10 objects {{"id": "c1", "statement": <one precise sentence that
  defines a single checkable quantity, including every filter, grouping, unit and
  rounding rule>, "value": <the value exactly as stated in the answer: number,
  string, boolean or list>}}. Every number in the answer must be one claim.
- "code": Python standard-library code (no pandas or numpy) defining
  compute(tables) that returns a dict mapping each claim id to its computed value.
  tables is a dict mapping table name to a list of row dicts. CSV values are the
  raw strings from the file (convert types yourself; handle blank or invalid cells
  as the question implies). JSON tables keep their parsed values.
No Markdown fences.

TABLES:
{schema}

QUESTION:
{question}
"""

ORACLE_PROMPT = """You are PolyaBrain's independent claim verifier (prompt {version}).
Another analyst answered the QUESTION below. You will NOT see their numbers or code.
For each claim definition, write your own computation of exactly that quantity, and
check whether each definition really answers the QUESTION.

Return exactly one JSON object:
- "code": Python standard-library code defining compute(tables) that returns a dict
  mapping every claim id to your computed value. tables is a dict mapping table name
  to a list of row dicts (CSV values are raw strings; JSON keeps parsed values).
  Use a DIFFERENT method from a straightforward loop where practical: load the rows
  into an in-memory sqlite3 database and compute with SQL. Convert types explicitly
  and treat blank or invalid cells exactly as the question and definition imply.
- "definition_issues": [{{"id": <claim id>, "issue": <how the definition fails to
  answer the question, e.g. a filter or rounding the question requires is missing>}}];
  [] when every definition matches the question.
- "assumptions": short strings for any interpretation you had to choose.
No Markdown fences.

TABLES:
{schema}

QUESTION:
{question}

CLAIM DEFINITIONS:
{claims}
"""

ADJUDICATE_PROMPT = """You are PolyaBrain's claim adjudicator (prompt {version}).
Two independent computations of the same claims disagree. Decide from the QUESTION,
the claim definition and the data description which computation is right.

Return exactly one JSON object {{"items": [{{"id": <claim id>, "verdict":
"answer_correct" | "verifier_correct" | "both_wrong" | "ambiguous", "correct_value":
<value on the ORIGINAL data, or null>, "explanation": <at most two sentences>}}]}}.

TABLES:
{schema}

QUESTION:
{question}

DISAGREEMENTS:
{items}

ANSWER CODE:
{answer_code}

VERIFIER CODE:
{oracle_code}
"""


class ClaimStatus(StrEnum):
    PROVEN = "proven"
    CORRECTED = "corrected"
    REVIEWED = "supported_after_review"
    DISPUTED = "disputed"
    UNVERIFIED = "unverified"


class AnswerStatus(StrEnum):
    VERIFIED = "verified"
    CORRECTED = "corrected_and_verified"
    NEEDS_REVIEW = "needs_review"
    UNVERIFIED = "unverified"


class ClaimSpec(ModelOutput):
    id: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9_]+$")
    statement: str = Field(min_length=1, max_length=600)
    value: Any = None


class AnswerPackage(ModelOutput):
    answer: str = Field(min_length=1, max_length=4_000)
    claims: list[ClaimSpec] = Field(default_factory=list, max_length=10)
    code: str = Field(min_length=1, max_length=9_000)


class DefinitionIssue(ModelOutput):
    id: str
    issue: str = ""


class OraclePackage(ModelOutput):
    code: str = Field(min_length=1, max_length=9_000)
    definition_issues: list[DefinitionIssue] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list, max_length=12)


class Ruling(ModelOutput):
    id: str
    verdict: str
    correct_value: Any = None
    explanation: str = ""


class RulingSet(ModelOutput):
    items: list[Ruling] = Field(default_factory=list)


class ClaimResult(ContractModel):
    id: str
    statement: str
    stated_value: Any = None
    computed_value: Any = None
    verifier_value: Any = None
    final_value: Any = None
    status: ClaimStatus = ClaimStatus.UNVERIFIED
    variants_agreed: int = 0
    variants_total: int = 0
    reason: str = ""


class ClaimsCertificate(ContractModel):
    status: AnswerStatus
    question: str
    answer: str = ""
    tables: list[str] = Field(default_factory=list)
    claims: list[ClaimResult] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    reason: str = ""
    limitations: list[str] = Field(default_factory=list)


LIMITATIONS = [
    "Agreement between two independent derivations on the data and on perturbed copies is strong evidence, not proof.",
    "Both derivations are model-written from the same question; a shared misreading can survive, though the verifier is asked to flag definitions that do not answer the question.",
    "Only claims stated as checkable quantities are verified; narrative statements in the answer are not.",
    "Data runs in an isolated standard-library sandbox; nothing outside the supplied tables is consulted.",
]


@dataclass(frozen=True)
class ClaimLimits:
    answer_attempts: int = 2
    oracle_attempts: int = 2
    per_request_output_tokens: int = 6_000
    request_timeout_seconds: float = 90.0
    max_retries: int = 2
    variants: int = 4
    call_seconds: float = 5.0


@dataclass
class ClaimsOutcome:
    certificate: ClaimsCertificate
    answer_code: str = ""
    oracle_code: str = ""
    model_calls: list[ModelCallRecord] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    elapsed_ms: float = 0.0


class ClaimVerifier:
    def __init__(
        self,
        client: LLMClient,
        model: str,
        sandbox: Any,
        *,
        limits: ClaimLimits | None = None,
        progress: Callable[[dict[str, Any]], None] | None = None,
        patterns: FailurePatternStore | None = None,
        source: str = "",
    ) -> None:
        self.client, self.model, self.sandbox = client, model, sandbox
        self.limits = limits or ClaimLimits()
        self.patterns, self.source = patterns, source
        self._progress = progress
        self.model_calls: list[ModelCallRecord] = []
        self.events: list[dict[str, Any]] = []
        self.last_failure: str | None = None

    # ----- plumbing --------------------------------------------------------------
    def _event(self, event_type: str, mode: str, summary: str, **metadata: Any) -> None:
        event = {
            "engine_name": "verified_claims",
            "event_type": event_type,
            "reasoning_mode": mode,
            "summary": summary,
            "metadata": metadata,
        }
        self.events.append(event)
        if self._progress is not None:
            self._progress(event)

    def _complete(self, role: str, content: str) -> str | None:
        started = perf_counter()
        try:
            response = self.client.complete(
                LLMRequest(
                    model=self.model,
                    messages=[LLMMessage(role=LLMRole.USER, content=content)],
                    options=LLMRequestOptions(
                        max_output_tokens=self.limits.per_request_output_tokens,
                        json_mode=True,
                        timeout_seconds=self.limits.request_timeout_seconds,
                        total_timeout_seconds=self.limits.request_timeout_seconds,
                        max_retries=self.limits.max_retries,
                    ),
                )
            )
        except Exception as exc:  # noqa: BLE001 - recorded; the claim stays unverified
            self.model_calls.append(
                ModelCallRecord(role=role, model=self.model, outcome=type(exc).__name__)
            )
            self.last_failure = provider_failure_reason(exc)
            return None
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
            capability=f"verified_claims.{role}",
            capability_kind="model",
            action_type="execute" if role == "answer" else "verify",
            model_calls=1,
            external_calls=0,
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            normalized_cost=0.0,
            duration_ms=round(record.duration_ms, 3),
        )
        return response.text

    def _execute(
        self, tables: list[Table], candidate: str | None, oracle: str | None
    ) -> ClaimRunReport:
        program = build_program(
            tables=tables,
            candidate=candidate,
            oracle=oracle,
            variants=self.limits.variants,
            call_seconds=self.limits.call_seconds,
        )
        needed = (self.limits.variants + 1) * 2 * self.limits.call_seconds + 10
        original = self.sandbox.limits
        extended = getattr(original, "timeout_seconds", needed) < needed
        try:
            if extended:
                self.sandbox.limits = replace(original, timeout_seconds=needed)
            execution: SandboxExecutionResult = self.sandbox.execute_with_data(
                program, {table.name: table.data for table in tables}
            )
        finally:
            if extended:
                self.sandbox.limits = original
        if infrastructure_failure(execution):
            raise SandboxUnavailable(execution.stderr.strip().splitlines()[0][:200])
        return parse(execution)

    # ----- stages ----------------------------------------------------------------
    def _answer(
        self, question: str, tables: list[Table]
    ) -> tuple[AnswerPackage | None, ClaimRunReport | None]:
        prompt = ANSWER_PROMPT.format(
            version=PROMPT_VERSION, schema=schema_text(tables), question=question
        )
        feedback = ""
        for _ in range(self.limits.answer_attempts):
            text = self._complete("answer", prompt + feedback)
            if text is None:
                return None, None
            try:
                package = AnswerPackage.model_validate_json(text)
            except ValidationError as exc:
                feedback = f"\nYOUR PREVIOUS RESPONSE WAS INVALID ({exc.error_count()} schema errors). Return the JSON object exactly."
                continue
            package = package.model_copy(update={"code": _strip_fences(package.code)})
            report = self._execute(tables, package.code, None)
            first = report.runs[0].candidate if report.runs else None
            if report.failure is None and first is not None and first.ok:
                missing = [c.id for c in package.claims if c.id not in first.values]
                if not missing:
                    return package, report
                feedback = f"\nYOUR compute() DID NOT RETURN THESE CLAIM IDS: {missing}. Return the corrected JSON object."
                continue
            error = report.failure or (first.error if first else "no result")
            feedback = (
                f"\nYOUR compute() FAILED ON THE DATA: {error}. Return the corrected JSON object."
            )
        return None, None

    def _oracle(
        self, question: str, tables: list[Table], claims: list[ClaimSpec]
    ) -> OraclePackage | None:
        listing = "\n".join(f"{c.id}: {c.statement}" for c in claims)
        prompt = ORACLE_PROMPT.format(
            version=PROMPT_VERSION, schema=schema_text(tables), question=question, claims=listing
        )
        if self.patterns is not None:
            hints = self.patterns.prompt_hints("claims", f"{question}\n{schema_text(tables)}")
            if hints:
                prompt += hints
                self._event(
                    "failure_patterns_retrieved",
                    "explore",
                    "Retrieved previously confirmed analysis mistakes as verification hints.",
                    hints=hints,
                )
        feedback = ""
        for _ in range(self.limits.oracle_attempts):
            text = self._complete("verifier", prompt + feedback)
            if text is None:
                return None
            try:
                package = OraclePackage.model_validate_json(text)
            except ValidationError:
                feedback = (
                    "\nYOUR PREVIOUS RESPONSE WAS NOT THE REQUIRED JSON OBJECT. Return it exactly."
                )
                continue
            package = package.model_copy(update={"code": _strip_fences(package.code)})
            report = self._execute(tables, None, package.code)
            first = report.runs[0].oracle if report.runs else None
            if report.failure is None and first is not None and first.ok:
                return package
            error = report.failure or (first.error if first else "no result")
            feedback = (
                f"\nYOUR compute() FAILED ON THE DATA: {error}. Return the corrected JSON object."
            )
        return None

    # ----- orchestration ---------------------------------------------------------
    def verify(self, question: str, tables: list[Table]) -> ClaimsOutcome:
        started = perf_counter()
        certificate = ClaimsCertificate(
            status=AnswerStatus.UNVERIFIED,
            question=question,
            tables=[table.name for table in tables],
            limitations=LIMITATIONS,
        )
        package, _ = self._answer(question, tables)
        if package is None:
            certificate.reason = "No answer with executable claim computations was produced" + (
                f": {self.last_failure}." if self.last_failure else "."
            )
            return self._finish(certificate, "", "", started)
        certificate.answer = package.answer
        claims = [
            ClaimResult(id=c.id, statement=c.statement, stated_value=c.value)
            for c in package.claims
        ]
        certificate.claims = claims
        oracle = self._oracle(question, tables, package.claims) if package.claims else None
        if oracle is None:
            certificate.reason = (
                "The answer stated no checkable quantities."
                if not package.claims
                else "No independent derivation could be produced; claims are unverified"
                + (f": {self.last_failure}." if self.last_failure else ".")
            )
            return self._finish(certificate, package.code, "", started)
        certificate.assumptions = list(oracle.assumptions)
        report = self._execute(tables, package.code, oracle.code)
        if report.failure is not None or not report.runs:
            certificate.reason = f"The comparison run failed: {report.failure}"
            return self._finish(certificate, package.code, oracle.code, started)
        issues = {item.id: item.issue for item in oracle.definition_issues if item.issue.strip()}
        disputed: list[tuple[ClaimResult, dict[str, Any]]] = []
        original = report.runs[0]
        for claim in claims:
            computed = original.candidate.values.get(claim.id) if original.candidate.ok else None
            checked = original.oracle.values.get(claim.id) if original.oracle.ok else None
            claim.computed_value, claim.verifier_value = computed, checked
            agreements = []
            first_difference: dict[str, Any] | None = None
            for run in report.runs:
                a = (
                    run.candidate.values.get(claim.id, run.candidate.error)
                    if run.candidate.ok
                    else f"error: {run.candidate.error}"
                )
                b = (
                    run.oracle.values.get(claim.id, run.oracle.error)
                    if run.oracle.ok
                    else f"error: {run.oracle.error}"
                )
                agree = same(a, b)
                agreements.append(agree)
                if not agree and first_difference is None:
                    first_difference = {"data": run.label, "answer_value": a, "verifier_value": b}
            claim.variants_total = len(report.runs)
            claim.variants_agreed = sum(agreements)
            stated_ok = same(
                claim.stated_value, computed, absolute=stated_tolerance(claim.stated_value)
            )
            if claim.id in issues:
                claim.status = ClaimStatus.DISPUTED
                claim.reason = (
                    f"The verifier says this claim does not answer the question: {issues[claim.id]}"
                )
                claim.final_value = computed
            elif all(agreements):
                claim.final_value = computed
                if stated_ok:
                    claim.status = ClaimStatus.PROVEN
                    claim.reason = f"Independent derivations agreed on the data and {len(report.runs) - 1} perturbed copies."
                else:
                    claim.status = ClaimStatus.CORRECTED
                    claim.reason = (
                        f"The answer stated {claim.stated_value!r}, but its own computation and the "
                        f"independent one both give {computed!r}."
                    )
            else:
                disputed.append((claim, first_difference or {}))
        if disputed:
            self._adjudicate(question, tables, package.code, oracle.code, disputed)
        statuses = {claim.status for claim in claims}
        certificate.status = (
            AnswerStatus.NEEDS_REVIEW
            if statuses & {ClaimStatus.DISPUTED, ClaimStatus.REVIEWED, ClaimStatus.UNVERIFIED}
            else AnswerStatus.CORRECTED
            if ClaimStatus.CORRECTED in statuses
            else AnswerStatus.VERIFIED
        )
        return self._finish(certificate, package.code, oracle.code, started)

    def _adjudicate(
        self,
        question: str,
        tables: list[Table],
        answer_code: str,
        oracle_code: str,
        disputed: list[tuple[ClaimResult, dict[str, Any]]],
    ) -> None:
        items = "\n".join(
            json.dumps(
                {
                    "id": claim.id,
                    "definition": claim.statement,
                    "original_data": {
                        "answer_value": claim.computed_value,
                        "verifier_value": claim.verifier_value,
                    },
                    "first_difference": difference,
                },
                default=str,
            )
            for claim, difference in disputed
        )
        text = self._complete(
            "adjudicator",
            ADJUDICATE_PROMPT.format(
                version=PROMPT_VERSION,
                schema=schema_text(tables),
                question=question,
                items=items,
                answer_code=answer_code,
                oracle_code=oracle_code,
            ),
        )
        rulings: dict[str, Ruling] = {}
        if text is not None:
            try:
                rulings = {item.id: item for item in RulingSet.model_validate_json(text).items}
            except ValidationError:
                rulings = {}
        for claim, _ in disputed:
            ruling = rulings.get(claim.id)
            claim.final_value = claim.computed_value
            if ruling is None:
                claim.status = ClaimStatus.DISPUTED
                claim.reason = "The two derivations disagree and no valid ruling was returned."
            elif ruling.verdict == "verifier_correct" and same(
                ruling.correct_value, claim.verifier_value
            ):
                claim.status = ClaimStatus.CORRECTED
                claim.final_value = claim.verifier_value
                claim.reason = f"Corrected after review: {ruling.explanation}"
            elif ruling.verdict == "answer_correct" and same(
                ruling.correct_value, claim.computed_value
            ):
                claim.status = (
                    ClaimStatus.REVIEWED
                    if same(
                        claim.stated_value,
                        claim.computed_value,
                        absolute=stated_tolerance(claim.stated_value),
                    )
                    else ClaimStatus.CORRECTED
                )
                claim.reason = f"The verifier's derivation was judged wrong: {ruling.explanation}"
            else:
                claim.status = ClaimStatus.DISPUTED
                claim.reason = (
                    f"Unresolved ({ruling.verdict}): {ruling.explanation}"
                    if ruling.verdict in {"both_wrong", "ambiguous"}
                    else "The ruling's value contradicts the derivation it selected."
                )
        self._event(
            "verified_claims_adjudicated",
            "verify",
            f"Adjudicated {len(disputed)} disagreeing claim(s).",
            claims=[claim.id for claim, _ in disputed],
        )

    def _finish(
        self, certificate: ClaimsCertificate, answer_code: str, oracle_code: str, started: float
    ) -> ClaimsOutcome:
        if self.patterns is not None:
            for claim in certificate.claims:
                if claim.status not in {ClaimStatus.CORRECTED, ClaimStatus.DISPUTED}:
                    continue
                self.patterns.record(
                    "claims",
                    f"{claim.statement} — {claim.reason[:200]}",
                    trigger=f"stated {claim.stated_value!r}; verified {claim.final_value!r}",
                    evidence=f"question: {certificate.question[:250]}",
                    source=self.source,
                )
        self._event(
            "verified_claims_certificate",
            "verify",
            f"Claim verification status: {certificate.status.value}.",
            certificate=certificate.model_dump(mode="json"),
        )
        return ClaimsOutcome(
            certificate=certificate,
            answer_code=answer_code,
            oracle_code=oracle_code,
            model_calls=list(self.model_calls),
            events=list(self.events),
            elapsed_ms=(perf_counter() - started) * 1000,
        )
