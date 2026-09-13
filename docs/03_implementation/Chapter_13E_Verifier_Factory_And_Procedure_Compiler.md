# Chapter 13-E: Verifier Factory and Procedure Compiler

Status: experimental implementation, offline structural gates, and repeated
held-out live verifier gate complete; real procedure-transfer and safe
deployed-reuse gates remain open.

## Product Problem

Before this chapter, PolyaBrain could ask a model or a narrow hard-coded pack to
produce a `VerificationReport`, and procedural memory could prefer one action
that had succeeded for a related gap. Those are useful foundations, but neither
is the mechanism required by the product vision:

- A report is not an executable verifier.
- One recalled action is not a compiled problem-solving procedure.
- A successful source case is not proof that transfer is safe.

Chapter 13-E introduces experimental mechanisms that close those gaps without
promoting new fields into canonical `PolyaState`.

## Implemented Verifier Factory

`backend/app/cognition/verification_factory.py` defines:

- criterion-bound verifier specifications;
- allowlisted exact-evidence and structured-output operations;
- explicit input bindings and independence levels;
- proposed, validated, passed, failed, and inconclusive lifecycle states;
- deterministic suite execution and canonical `VerificationReport` output;
- complete specification and result traces;
- a capability-registry adapter selected only when every criterion has a known
  deterministic procedure.

The structured verifier is a declarative language, not generated code. It can
check exact equality or inequality, numeric upper and lower bounds, string/list
containment, non-empty all-true result sets, and empty error fields. It resolves
only bounded paths in existing execution output. It cannot call functions,
evaluate expressions, access attributes, or execute model-produced code.
The declaration set and success criteria must also match a system-generated
fingerprint event from trusted task specification. Plan metadata alone—such as
thresholds proposed by the same model that generated a candidate—cannot make a
verifier executable.

Exact artifact verification independently requires:

1. one eligible admitted evidence item;
2. explicit source URI and source-visible excerpt;
3. minimum reliability and relevance;
4. the admitted claim to occur in the excerpt; and
5. the candidate conclusion to match the admitted claim.

If a criterion has no known deterministic procedure, the factory emits a
non-executable semantic-review proposal. The controller then uses the existing
bounded conclusion checker rather than misrepresenting the criterion as
mechanically verified.

## Implemented Procedure Compiler

`backend/app/cognition/procedure_compiler.py` compiles only completed, reflected,
verified runs that contain an executable verifier-suite trace. Its artifact
contains:

- structural task family and gap types;
- generalized target roles rather than task-specific target literals;
- ordered cognitive actions and expected postconditions;
- pinned capability versions;
- source and safety preconditions;
- the complete executable verifier suite;
- source-session provenance and resource profile;
- known failure modes, regression cases, lifecycle, and invalidation rules;
- a content-integrity hash over every trust-relevant field.

The default lifecycle is `proposed`. A proposal is not executable memory. Two
distinct independently verified replay cases are required for `verified`
promotion, except for an explicitly invoked mechanically proven narrow
exact-artifact procedure. The mechanical-proof path rejects every other task or
verifier family. Even a verified procedure must pass present-case applicability
and the embedded verifier suite.

The applicability checker returns applicable, inapplicable, or inconclusive. It
rejects or defers transfer when integrity, lifecycle, task family, safety
constraints, gap shape, evidence-source boundary, capability availability, or
capability version does not match.

## Runtime And Persistence Boundary

The production-composed runtime automatically compiles eligible completed runs
after the kernel stops and appends the proposal to the audit trace. It does not
admit that proposal into executable memory.

The existing long-term-memory repository validates the artifact and its
integrity hash before storing it inside existing procedural-strategy metadata.
A proposed artifact is persisted with zero verified successes and cannot be
returned as a verified action preference. This deliberately avoids a core
contract or database migration before transfer value is proven.

The runtime also exposes an explicit governed executor for verified procedures.
It rechecks integrity, lifecycle, applicability, safety constraints, capability
versions, current risk and approval, sensitive-data permission, and remaining
cognitive budget. Each step is rebound to the present task and executed through
the capability registry; observations pass through the same typed state-update
boundary as ordinary kernel work. Completion still requires the embedded
present-case verifier, reflection, and final answer.

Proposed procedures may execute only through the replay-only path. That path
uses the same safety, capability, budget, state-update, and verification gates
but grants no deployment authority. It derives typed replay evidence from the
actual execution trace. Two distinct passing replay executions can then promote
the procedure; an ordinary unverified proposal executes zero production steps.
Replay-promotion events, unlike proposals, can update trusted persisted
procedure evidence.

## Verified Offline Behavior

Targeted tests establish that:

- three independent release rules are synthesized and executed with zero model
  calls and complete per-criterion trace coverage;
- an incorrect transferred result fails present-case verification;
- a model-authored or stale structured verifier declaration cannot authorize
  itself without a matching trusted task-specification fingerprint;
- a semantic criterion remains explicitly non-executable and inconclusive;
- an artifact candidate cannot pass when it disagrees with source evidence;
- a three-step inspect, execute, verify trace compiles without retaining its
  task-specific target literal;
- one source success remains only proposed;
- two distinct passing replays promote the artifact;
- unverified, stale-capability, missing-safety, failed-replay, and tampered
  procedures are rejected;
- general debugging procedures cannot use the mechanical-proof shortcut;
- a proposed three-step procedure executes in replay mode on two related cases,
  and actual present-case verification produces its promotion evidence;
- the promoted procedure executes through the runtime boundary and reruns every
  step and verifier on a new case;
- a failed transfer assertion makes the procedure executor fail with no final
  answer;
- a real production-composed exact-artifact run leaves one proposed compiled
  procedure in its trace.

## Repeated Live Verifier Gate

On 2026-08-22, the configured premium endpoint completed six fictional held-out
cases across multi-rule decision and structured-debugging families, repeated
three times with rotated condition order. The final artifact is:

`evals/chapter_13e/live_runs/2026-08-22/113616-3535a3e7/summary.json`

| Condition | Correct verdicts | False passes | Model calls | Tokens | Median latency |
|---|---:|---:|---:|---:|---:|
| Direct model with complete structured observation | 18/18 | 0 | 18 | 23,944 | 4,948 ms |
| Full context with observations and distractors | 18/18 | 0 | 18 | 26,978 | 13,446 ms |
| Fixed lexical top-two retrieval | 8/18 | 0 | 18 | 30,901 | 14,384 ms |
| Polya typed verifier factory | 18/18 | 0 | 0 | 0 | 2.2 ms |

Every condition received the same candidate and mandatory success criteria.
The direct model received the complete structured observation, full context
received every observation document plus distractors, retrieval received a
fixed lexical top two, and Polya received declarative bindings to the same
structured observation. The gate therefore isolates verification after
candidate generation and observation; it does not compare end-to-end problem
solving.

Strict OpenRouter parameter routing returned HTTP 404 for this model route, so
the successful run used `OPENROUTER_REQUIRE_PARAMETERS_FOR_JSON=false`. Typed
output parsing and scoring still failed closed. Two earlier full attempts were
provider-blocked, and the successful campaign used case-level resumability after
an interrupted long-running attempt. Provider availability and observed latency
must become scheduler inputs.

The narrow Chapter 13-E verifier gate passed. `general_intelligence_win_claimed`
remains false.

After the verifier trust guards, governed executor, replay evidence path, and
runtime integration were added, the full local suite passed 303 tests with 23
environment-gated tests skipped. Ruff lint and formatting, strict mypy over 98
source files, and `git diff --check` also passed.

## Remaining Gates

This chapter does not establish a general intelligence or product win. The
following remain open:

1. Extend the repeated comparison from fixed verification checkpoints to full
   acquisition, candidate generation, execution, and recovery outcomes.
2. Measure real procedure transfer accuracy and savings in addition to the
   completed verifier false-pass, coverage, call, token, and latency metrics.
3. Exercise the governed executor with production acquisition and execution
   capabilities rather than only bounded fictional fixtures.
4. Promote and persist a procedure after real held-out replay evidence, then monitor
   failures and retire it when its assumptions stop holding.
5. Prove transfer savings without reducing verification quality across at least
   two materially different task families.

Until these gates pass, the correct claim is: PolyaBrain now has the typed
mechanisms for verifier synthesis and guarded procedure compilation, and it has
won one narrow known-verifier quality-cost gate—not general problem solving.
