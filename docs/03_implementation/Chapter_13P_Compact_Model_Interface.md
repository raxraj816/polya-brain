# Chapter 13-P: reduce avoidable model overhead

The preceding build completed both signed-array and directed-walk attempts, but
required four provider calls per attempt and roughly 26–34k total tokens. The lean
baseline passed the same independent checks with one call. This follow-up targets
unnecessary request content and proposal repair while preserving verification.

## Implemented behavior

- Typed request state omits default nulls and empty collections. Scalar status,
  risk, priority and Boolean defaults remain explicit. Raw input, arbitrary tool
  parameters/results, code/tests, source excerpts, failures and non-default values
  are retained. Canonical state and stored reports are unchanged.
- Request schemas omit display titles while keeping all property names,
  descriptions, defaults and validation constraints. A repair includes one copy
  of its schema and retains the original capability rules and full input.
- Before evidence exists, proposal schemas advertise only candidate/deferred/
  rejected hypothesis statuses. Validation rejects unsupported selected/verified/
  falsified statuses on initial and repair responses, even with invented support
  strings or otherwise harmless extra fields. Returned hypotheses are never
  silently relabeled. Existing evidence enables the original selection contract.
- Generated-check instructions now match admission exactly: all additional
  call/literal expected-result assertions are rejected, including apparently
  obvious answers. Additional cases should compare with an independently derived
  executable reference or check a separately justified property. Exact supplied
  examples and already admitted checks stay unchanged.

Versions: gateway `cognitive_capability@0.10.0`, fused deliberator `0.10.0`,
planner `0.6.0`. No new persisted contract field or database migration is needed.

## Mechanical request-size audit

`runs/coding-readiness/model-wire-audit-v1.json` replays saved gateway responses
from all four preceding successes without remote calls. At the same saved state
and response, initial plus repair request messages shrink from 251,246 to 231,690
UTF-8 bytes (**7.78%**). Framing is excluded. This is a byte comparison, not a token
estimate, paid live run, or claim about outcome quality. The audit uses original
capability instructions to isolate transport changes from the later instruction
clarification.

This preserved audit predates structural edit repair (gateway `0.9.0`). Running
the command below against the current gateway also includes the changed repair
protocol, so it will not reproduce the original isolated byte delta exactly.

```sh
PYTHONPATH=backend:. .venv/bin/python -m evals.chapter_13p.coding_execution.wire_audit \
  runs/coding-readiness/matched-check-admission-transfer-v2/shortest_span-0-polya \
  runs/coding-readiness/matched-check-admission-transfer-v2/shortest_span-1-polya \
  runs/coding-readiness/matched-check-admission-graph-v1/finite_routes-0-polya \
  runs/coding-readiness/matched-check-admission-graph-v1/finite_routes-1-polya \
  --output runs/coding-readiness/NEW-wire-audit.json
```

## Preserved live attempts

All live attempts use the existing matched runner, unchanged problem text,
withheld checks, model and budgets. Both arms execute real sandbox checks.
Choose a new output directory for each run. Latencies are local observations,
not controlled performance estimates; backend regression tests overlap part of
the signed-array experiments. The graph experiment runs after these complete.

| Experiment | Polya completed and checked | Lean checked | Polya calls / total tokens | Lean calls / total tokens |
| --- | --- | --- | --- | --- |
| `matched-compact-wire-transfer-v1` | 2/2 | 2/2 | 4 / 24,439; 4 / 24,959 | 1 / 2,868; 1 / 2,740 |
| `matched-compact-wire-transfer-v2` | 2/2 | 2/2 | 4 / 25,327; 4 / 25,919 | 2 / 6,516; 1 / 2,384 |

The first compact-interface experiment takes 57.89 / 67.99 seconds for Polya,
versus lean's 17.69 / 14.27. Both Polya proposals avoid unsupported selection but
still need a repair for additional literal tests. Inspection identifies the
instruction mismatch: "do not guess" did not clearly state that even correct
invented literal expectations are rejected. The explicit instruction follows
this observation; original proposals and their full cost remain preserved.

The explicit-instruction rerun still needs one repair per Polya attempt. The first
proposal supplies new literal expectations for large uniform arrays despite the
instruction. Both runs complete and pass independent checks, taking 50.27 / 81.77
seconds versus lean's 28.79 / 13.35. This preserves a failed efficiency hypothesis:
more precise wording did not reliably remove the repair call.

## Bounded response edits

`structured_response_edits@0.1.0` lets the existing repair request return up to
16 explicit path/value edits, with paths at most 12 components and a 64,000-byte
encoded edit limit. Object fields can be set and existing list elements replaced.
Root replacement, implicit parent creation, list insertion/deletion, overlapping
paths and coercion of Boolean/string indices are rejected. Application deep-copies
the original unadmitted response and preserves every unmentioned value.

The reconstructed response passes the full original schema, no-evidence status
policy and generated-check admission. An invalid edit response fails within the
same attempt allowance. Truncated/invalid original JSON retains full-response
repair. Full-response provider compatibility remains supported. This edits the
model's pending response; it does not modify canonical state or admitted checks.

Existing capability observation metadata records response form, protocol version,
before/after hashes and bounded sanitized paths, without repaired values. The
semantic broker preserves this metadata. Eval artifacts retain the raw provider
response so the transformation can be inspected. Hashes establish consistency,
not signatures or a defense against rewriting every artifact.

## Latest matched outcomes

| Experiment | Polya completed and checked | Lean checked | Polya calls / total tokens | Lean calls / total tokens |
| --- | --- | --- | --- | --- |
| `matched-edit-repair-transfer-v1` | 2/2 | 2/2 | 3 / 16,832; 3 / 17,309 | 1 / 2,575; 2 / 6,570 |
| `matched-edit-repair-graph-v1` | 2/2 | 2/2 | 4 / 30,863; 4 / 30,723 | 1 / 4,581; 1 / 4,554 |

All directories are under `runs/coding-readiness/`. The signed-array runs take
35.02 / 42.25 seconds for Polya versus 14.72 / 23.77 for lean. Neither Polya
attempt requires repair, so its observed savings cannot be attributed to applying
edits. Both graph attempts actually repair `tasks[1].params.tests` while retaining
the complete implementation unchanged. They take 66.16 / 59.11 seconds versus
lean's 30.64 / 29.21. Repair responses still consume 2,371 / 3,292 output tokens,
including provider-reported reasoning tokens; small edits do not imply tiny bills.

Relative to the preceding check-admission build, average total tokens fall about
37% on signed arrays and 9% on graphs. These are observations from two repetitions
per task, not causal estimates or stable performance guarantees. Both arms pass
all four latest attempts. Polya remains slower and more expensive in tokens here.
No external holdout, independent user preference or competitive win is established.

## Workbench delivery and verification

Long requests now use bounded titles and an expandable exact original problem.
Reports render headings, lists, tables and code with a copy action. Code keeps its
indentation and scrolls within its block. Raw HTML, remote images and unsafe links
are not rendered. Report export retains the exact full input and Markdown answer.
History search is bounded to the API's 200-character limit, including change events.

The production browser submitted the frozen graph problem as session
`d6fbd74c-c8d8-456c-94a6-21d1bf6496e9`. It completed with four provider calls,
30,769 recorded tokens and 70.86 seconds of recorded active time. Reload restored
the result. A real keyboard copy/paste preserved the entire rendered code,
including indentation. The full 1,237-character request remained available, the
trace exposed the repair path and hashes, and the downloaded 7,494-byte Markdown
report matched `reportMarkdown(session, report)` exactly.

Saved public API responses and read-only persisted plan records are in
`runs/coding-readiness/browser-edit-repair-graph-v1`. `state.json` is an audit
reconstruction from those records, not an original in-memory checkpoint. The
current acceptance checker confirms executed/delivered code identity. Independent
Docker replay passes 600 random multigraphs and eight boundary/scale checks. This
extra browser run is separate from the matched comparison and adds no baseline
sample. Its loopback test-mode backend does not validate hosted authentication.

Verification at this checkpoint: 970 backend tests pass with PostgreSQL enabled
and Docker checks; Ruff and mypy (139 production files) pass. All six frontend
unit tests, TypeScript, formatting and production build pass. Browser verification
uses actual persisted data and preserves every provider attempt. No commit or
push is made.
