"""Differential verification of one changed function against the change's stated intent.

The old version is the reference and the changed version the candidate. A model only
writes the input generator and, when the intent is not behavior-preserving, classifies
concrete differences against quoted intent. The harness decides what changed.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from enum import StrEnum
from time import perf_counter
from typing import Any

from pydantic import Field, ValidationError

from app.llm import LLMClient, LLMMessage, LLMRequest, LLMRequestOptions, LLMRole
from app.llm.errors import provider_failure_reason
from app.memory.failure_patterns import FailurePatternStore
from app.models.contracts import ContractModel
from app.verified_change.source import FunctionChange, ModuleVersions
from app.verified_coding.contracts import CODE_LIMIT, ModelCallRecord, ModelOutput
from app.verified_coding.harness import (
    DifferentialResult,
    Entrypoint,
    HarnessConfig,
    build_program,
    parse_result,
    tools_source,
)
from app.verified_coding.pipeline import (
    Sandbox,
    SandboxUnavailable,
    _strip_fences,
    infrastructure_failure,
    quote_supported,
)

PROMPT_VERSION = "verified_change@0.3.0"

GENERATOR_PROMPT = """You are PolyaBrain's change-verification input generator (prompt {version}).
A developer changed the Python function {qualified} in module {module_path}. PolyaBrain
will call the OLD and NEW versions on the same inputs and report every difference.
Your only job is to write inputs that are likely to expose behavior differences.

Return exactly one JSON object:
- "generator_code": defines generate(rng, size) returning a TUPLE of positional
  arguments for one call of {qualified}{method_note}. rng is a random.Random;
  size is an int from 0 to 8 controlling input scale (0 = smallest valid input).
  Inputs must be valid for the OLD function's contract (types, preconditions in its
  docstring, signature and code). Concentrate on the region the diff touches and
  on edge cases: empty and single-element inputs, duplicates, ties, boundaries,
  zero, negative values, unusual but valid strings, None where allowed. Keep each
  input small enough that either version finishes well under a second. Return
  fresh objects on every call. Standard library only, no files or network.
- "same_code": "" unless the function's documented contract allows several correct
  results (for example any ordering); only then define same(args, got, want).
- "input_notes": short strings describing the input space you covered.

Do not include Markdown fences. Code at most 6000 characters.

STATED INTENT OF THE CHANGE:
{intent}

OLD MODULE (context: documentation, helpers and types the function relies on):
{module}

OLD FUNCTION:
{old}

NEW FUNCTION:
{new}

DIFF:
{diff}
"""

CLASSIFY_PROMPT = """You are PolyaBrain's change reviewer (prompt {version}).
Running the OLD and NEW versions of {qualified} on the same inputs produced the
behavior differences below. Judge each NEW output against the stated intent AND the
documented contract (docstrings, comments) of the function. Check two things for
every difference: is this input's new treatment called for, and is the exact new
output value correct? An input the intent says to newly accept is still a
regression if the value returned contradicts the contract or "everything else stays
the same" style statements.
- "intended": the stated intent explicitly calls for this new behavior AND the new
  output is exactly what the contract implies. Quote the deciding phrase VERBATIM
  from the intent.
- "regression": the new behavior is not called for, or the new output value is wrong.
  When the correct output can be derived, give it in "expected_output".
- "unclear": the intent is genuinely ambiguous for this input (for example it names
  lowercase but says nothing about mixed case).

Return exactly one JSON object {{"items": [{{"index": <int>, "verdict": <str>,
"intent_quote": <verbatim phrase or "">, "expected_output": <Python literal or "">,
"explanation": <at most two sentences>}}]}} covering every difference.

STATED INTENT:
{intent}

OLD FUNCTION:
{old}

NEW FUNCTION:
{new}

DIFFERENCES:
{differences}
"""

PRESERVING_HINTS = (
    "no behavior change",
    "no behaviour change",
    "no functional change",
    "behavior-preserving",
    "behaviour-preserving",
    "behavior preserving",
    "same behavior",
    "same behaviour",
    "pure refactor",
)


class ChangeStatus(StrEnum):
    NO_DIFFERENCE = "no_behavior_change_found"
    INTENDED_ONLY = "only_intended_changes"
    REGRESSIONS = "regressions_found"
    UNCLEAR = "changes_need_review"
    UNVERIFIED = "unverified"


class GeneratorPackage(ModelOutput):
    generator_code: str = Field(min_length=1, max_length=CODE_LIMIT)
    same_code: str = Field(default="", max_length=CODE_LIMIT)
    input_notes: list[str] = Field(default_factory=list, max_length=12)


class Classification(ModelOutput):
    index: int
    verdict: str
    intent_quote: str = ""
    expected_output: str = ""
    explanation: str = ""


class ClassificationSet(ModelOutput):
    items: list[Classification] = Field(default_factory=list)


class BehaviorDifference(ContractModel):
    kind: str
    args: str
    old_output: str
    new_output: str
    verdict: str = "unclassified"
    intent_quote: str = ""
    expected_output: str = ""
    explanation: str = ""


class ChangeCertificate(ContractModel):
    status: ChangeStatus
    qualified_name: str
    module_path: str
    base_ref: str
    head: str
    intent: str
    behavior_preserving_intent: bool
    cases_compared: int = 0
    sizes_covered: list[int] = Field(default_factory=list)
    total_differences: int = 0
    differences: list[BehaviorDifference] = Field(default_factory=list)
    input_notes: list[str] = Field(default_factory=list)
    reason: str = ""
    function_diff: str = ""
    limitations: list[str] = Field(default_factory=list)


LIMITATIONS = [
    "Randomized differential testing on generated inputs is evidence, not proof; untested inputs may still differ.",
    "The input generator is model-written from the function and intent; it can miss the region where behavior differs.",
    "Intended/regression labels are a model reading of your stated intent; inspect the concrete inputs and outputs.",
    "The module runs in an isolated standard-library sandbox; behavior that depends on files, network, time or other modules is not exercised.",
]


@dataclass(frozen=True)
class ChangeLimits:
    generator_attempts: int = 2
    per_request_output_tokens: int = 6_000
    request_timeout_seconds: float = 90.0
    max_retries: int = 2
    differential_budget_seconds: float = 8.0
    call_seconds: float = 1.0


@dataclass
class ChangeOutcome:
    certificate: ChangeCertificate
    model_calls: list[ModelCallRecord] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    differential: DifferentialResult | None = None
    elapsed_ms: float = 0.0


def behavior_preserving(intent: str) -> bool:
    lowered = " ".join(intent.lower().split())
    return any(hint in lowered for hint in PRESERVING_HINTS)


class ChangeVerifier:
    def __init__(
        self,
        client: LLMClient,
        model: str,
        sandbox: Sandbox,
        *,
        limits: ChangeLimits | None = None,
        progress: Callable[[dict[str, Any]], None] | None = None,
        patterns: FailurePatternStore | None = None,
        source: str = "",
    ) -> None:
        self.client, self.model, self.sandbox = client, model, sandbox
        self.limits = limits or ChangeLimits()
        self.patterns, self.source = patterns, source
        self._progress = progress
        self.model_calls: list[ModelCallRecord] = []
        self.events: list[dict[str, Any]] = []
        self.last_failure: str | None = None

    def _event(self, event_type: str, mode: str, summary: str, **metadata: Any) -> None:
        event = {
            "engine_name": "verified_change",
            "event_type": event_type,
            "reasoning_mode": mode,
            "summary": summary,
            "metadata": metadata,
        }
        self.events.append(event)
        if self._progress is not None:
            self._progress(event)

    def _complete(self, role: str, content: str) -> str | None:
        request = LLMRequest(
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
        started = perf_counter()
        try:
            response = self.client.complete(request)
        except Exception as exc:  # noqa: BLE001 - recorded and reported as unverified
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
            capability=f"verified_change.{role}",
            capability_kind="model",
            action_type="verify",
            model_calls=1,
            external_calls=0,
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            normalized_cost=0.0,
            duration_ms=round(record.duration_ms, 3),
        )
        return response.text

    def _differential(
        self, versions: ModuleVersions, change: FunctionChange, package: GeneratorPackage
    ) -> DifferentialResult:
        config = HarnessConfig(
            entrypoint=Entrypoint(name=change.name, class_name=change.class_name),
            budget_seconds=self.limits.differential_budget_seconds,
            call_seconds=self.limits.call_seconds,
            exhaustive=True,
            keep=6,
            mutation_mode="relative",
        )
        try:
            program = build_program(
                candidate=versions.new_source,
                reference=versions.old_source,
                tools=tools_source(package.generator_code, package.same_code),
                config=config,
            )
        except ValueError as exc:
            return DifferentialResult(setup_error=f"harness: {exc}")
        needed = self.limits.differential_budget_seconds + 4 * self.limits.call_seconds + 8
        original = self.sandbox.limits
        extended = getattr(original, "timeout_seconds", needed) < needed
        try:
            if extended:
                self.sandbox.limits = replace(original, timeout_seconds=needed)  # type: ignore[misc]
            execution = self.sandbox.execute(program, ())
        finally:
            if extended:
                self.sandbox.limits = original  # type: ignore[misc]
        if infrastructure_failure(execution):
            raise SandboxUnavailable(execution.stderr.strip().splitlines()[0][:200])
        result = parse_result(execution)
        self._event(
            "verified_change_differential",
            "compare",
            (
                f"Ran old and new {change.name} on {result.cases_compared} generated inputs; "
                f"{result.disagreements} behavior differences."
                if result.setup_error is None
                else f"Differential run could not start: {result.setup_error}"
            ),
            result=result.model_dump(mode="json"),
        )
        return result

    def verify(
        self, versions: ModuleVersions, change: FunctionChange, intent: str
    ) -> ChangeOutcome:
        started = perf_counter()
        qualified = f"{change.class_name}.{change.name}" if change.class_name else change.name
        preserving = behavior_preserving(intent)
        certificate = ChangeCertificate(
            status=ChangeStatus.UNVERIFIED,
            qualified_name=qualified,
            module_path=versions.module_path,
            base_ref=versions.base_ref,
            head=versions.head_label,
            intent=intent,
            behavior_preserving_intent=preserving,
            function_diff=change.function_diff,
            limitations=LIMITATIONS,
        )
        if versions.old_source == versions.new_source:
            certificate.status = ChangeStatus.NO_DIFFERENCE
            certificate.reason = "The module is identical in both versions; nothing changed."
            return self._finish(certificate, None, started)
        result: DifferentialResult | None = None
        last_result: DifferentialResult | None = None
        package: GeneratorPackage | None = None
        feedback = ""
        hints = (
            self.patterns.prompt_hints(
                "change", f"{change.old_function}\n{change.new_function}\n{intent}"
            )
            if self.patterns is not None
            else ""
        )
        if hints:
            self._event(
                "failure_patterns_retrieved",
                "explore",
                "Retrieved previously confirmed defect patterns as input-generation hints.",
                hints=hints,
            )
        for _ in range(self.limits.generator_attempts):
            text = self._complete(
                "input_generator",
                GENERATOR_PROMPT.format(
                    version=PROMPT_VERSION,
                    qualified=qualified,
                    module_path=versions.module_path,
                    method_note=(
                        f" (the harness calls it on a fresh {change.class_name}() instance)"
                        if change.class_name
                        else ""
                    ),
                    intent=intent or "(not stated)",
                    module=versions.old_source[:8_000],
                    old=change.old_function,
                    new=change.new_function,
                    diff=change.function_diff
                    or "(function text unchanged; other module code changed)",
                )
                + hints
                + feedback,
            )
            if text is None:
                break
            try:
                parsed = GeneratorPackage.model_validate_json(text)
            except ValidationError:
                feedback = (
                    "\nYOUR PREVIOUS RESPONSE WAS NOT THE REQUIRED JSON OBJECT. Return it exactly."
                )
                continue
            package = parsed.model_copy(
                update={
                    "generator_code": _strip_fences(parsed.generator_code),
                    "same_code": _strip_fences(parsed.same_code)
                    if parsed.same_code.strip()
                    else "",
                }
            )
            result = self._differential(versions, change, package)
            last_result = result
            if (
                result.setup_error is None
                and result.cases_compared > 0
                and (result.coverage_failure is None or result.counterexamples)
            ):
                break
            reason = result.coverage_failure or (
                f"no input could be compared (generator errors {result.generator_errors}, "
                f"old-version timeouts {result.reference_skipped})"
            )
            feedback = (
                f"\nYOUR PREVIOUS GENERATOR COULD NOT BE USED: {reason}. generate(rng, size) must "
                "return a tuple of valid arguments. Return a corrected JSON object."
            )
            result = None
        if result is None or package is None:
            certificate.reason = feedback.strip() or (
                f"No usable input generator was produced: {self.last_failure}."
                if self.last_failure
                else "No usable input generator was produced."
            )
            if result is None and package is not None and feedback:
                certificate.reason = feedback.strip()
            if last_result is not None:
                certificate.cases_compared = last_result.cases_compared
                certificate.sizes_covered = last_result.sizes_covered
            return self._finish(certificate, last_result, started)
        certificate.input_notes = list(package.input_notes)
        certificate.cases_compared = result.cases_compared
        certificate.sizes_covered = result.sizes_covered
        if result.coverage_failure is not None:
            certificate.limitations.insert(0, result.coverage_failure)
        certificate.total_differences = result.disagreements + int(result.mutation_detected)
        differences = [
            BehaviorDifference(
                kind=item.kind,
                args=item.args,
                old_output=item.reference,
                new_output=item.candidate,
            )
            for item in result.counterexamples
        ]
        if not differences:
            certificate.status = ChangeStatus.NO_DIFFERENCE
            return self._finish(certificate, result, started)
        if preserving:
            for item in differences:
                item.verdict = "regression"
                item.explanation = "The stated intent says behavior should not change."
        else:
            self._classify(qualified, intent, change, differences)
        certificate.differences = differences
        verdicts = {item.verdict for item in differences}
        certificate.status = (
            ChangeStatus.REGRESSIONS
            if "regression" in verdicts
            else ChangeStatus.UNCLEAR
            if verdicts - {"intended"}
            else ChangeStatus.INTENDED_ONLY
        )
        if certificate.status is ChangeStatus.INTENDED_ONLY and result.coverage_failure:
            certificate.status = ChangeStatus.UNVERIFIED
            certificate.reason = result.coverage_failure
        if certificate.status is ChangeStatus.INTENDED_ONLY and result.disagreements > len(
            differences
        ):
            certificate.reason = (
                f"{result.disagreements} differing inputs were observed; the smallest "
                f"{len(differences)} were classified. Review that the rest follow the same intended pattern."
            )
        return self._finish(certificate, result, started)

    def _classify(
        self,
        qualified: str,
        intent: str,
        change: FunctionChange,
        differences: list[BehaviorDifference],
    ) -> None:
        if not intent.strip():
            for item in differences:
                item.verdict = "unclear"
                item.explanation = (
                    "No intent was stated, so PolyaBrain cannot tell whether this change is wanted."
                )
            return
        listing = "\n".join(
            f"[{index}] input {item.args}: old -> {item.old_output}; new -> {item.new_output}"
            for index, item in enumerate(differences)
        )
        text = self._complete(
            "change_reviewer",
            CLASSIFY_PROMPT.format(
                version=PROMPT_VERSION,
                qualified=qualified,
                intent=intent,
                old=change.old_function,
                new=change.new_function,
                differences=listing,
            ),
        )
        parsed: ClassificationSet | None = None
        if text is not None:
            try:
                parsed = ClassificationSet.model_validate_json(text)
            except ValidationError:
                parsed = None
        rulings = {item.index: item for item in parsed.items} if parsed else {}
        for index, item in enumerate(differences):
            ruling = rulings.get(index)
            if ruling is None or ruling.verdict not in {"intended", "regression", "unclear"}:
                item.verdict = "unclear"
                item.explanation = "No valid classification was returned for this difference."
                continue
            if ruling.verdict == "intended" and not quote_supported(intent, ruling.intent_quote):
                item.verdict = "unclear"
                item.explanation = (
                    "Labelled intended without a verbatim quote from the stated intent."
                )
                continue
            item.verdict = ruling.verdict
            item.intent_quote = ruling.intent_quote if ruling.verdict == "intended" else ""
            item.expected_output = (
                ruling.expected_output[:400] if ruling.verdict == "regression" else ""
            )
            item.explanation = ruling.explanation[:400]

    def _finish(
        self, certificate: ChangeCertificate, result: DifferentialResult | None, started: float
    ) -> ChangeOutcome:
        if self.patterns is not None:
            recorded: set[str] = set()
            for item in certificate.differences:
                if item.verdict != "regression":
                    continue
                signature = (
                    item.explanation
                    if item.explanation and not certificate.behavior_preserving_intent
                    else f"A 'no behavior change' edit to {certificate.qualified_name} changed its results"
                )
                if signature in recorded:
                    continue  # one confirmation per pattern per run
                recorded.add(signature)
                self.patterns.record(
                    "change",
                    signature,
                    trigger=f"input {item.args}: old {item.old_output} -> new {item.new_output}",
                    evidence=item.expected_output
                    and f"expected {item.expected_output}"
                    or certificate.intent[:300],
                    source=self.source,
                )
        self._event(
            "verified_change_certificate",
            "verify",
            f"Change verification status: {certificate.status.value}.",
            certificate=certificate.model_dump(mode="json"),
            model_calls=[call.model_dump(mode="json") for call in self.model_calls],
        )
        return ChangeOutcome(
            certificate=certificate,
            model_calls=list(self.model_calls),
            events=list(self.events),
            differential=result,
            elapsed_ms=(perf_counter() - started) * 1000,
        )


def summary_json(outcome: ChangeOutcome) -> str:
    return json.dumps(outcome.certificate.model_dump(mode="json"), indent=2)
