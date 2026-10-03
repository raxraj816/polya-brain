# Chapter 173 — Verified changes

Status: implemented as a CLI command with deterministic tests, two live development
demonstrations and a QuixBugs real-bug evaluation (38/38 caught, 0/37 false alarms).
Binding decision: master plan, "Chapter 173: Verified changes".

## What it does

```bash
./polyabrain verify-change --repo . --module pkg/billing.py --function parse_size \
  --base main --head feature --intent "Accept lowercase units. Everything else stays the same."
```

1. `source.py` reads the base and changed module text through read-only `git show`
   (or the working-tree file), refuses paths outside the repository, non-`.py`
   files, option-like revisions, modules over 24,000 characters, async functions,
   and modules importing anything outside the standard library, each with a reason.
2. One model call (`input_generator`, prompt `verified_change@0.2.0`) sees both
   function versions, the diff and the stated intent, and writes an adversarial
   `generate(rng, size)`. One feedback retry is allowed.
3. The verified-coding harness runs the old version as reference and the new one as
   candidate in the networkless sandbox, in a new exhaustive mode: it compares for
   the whole budget across all sizes (up to 3,000 inputs) and returns up to six
   differences, one per distinct outcome shape first (raised vs value and result type),
   never the same input twice.
4. If the intent says behavior is preserved ("no behavior change" and similar), every
   difference is a regression without a model call. Otherwise one `change_reviewer`
   call sees both versions, the intent and the concrete differences, checks whether
   each input's new treatment is called for and whether the exact new value matches
   the documented contract, and returns intended / regression / unclear with an
   expected output for regressions. "Intended" requires a verbatim quote from the
   intent or it is downgraded to unclear.
5. Output: `report.md`, `certificate.json`, `trace.json`; exit 0 (no change found or
   only intended changes), 3 (regression or review needed), 4 (unverified), 1 (setup).

The repository is never modified. `image_available` (shared with Source Check)
now also accepts the pinned image when Docker answers only the local digest listing.

## Live development demonstrations (not an evaluation)

Agent-constructed changes in a scratch repository, `google/gemini-3.7-flash`:

- `prorate` rewritten as `round(amount * days / days_in_month)` under the intent "No
  behavior change": regression found on 3,000 inputs, e.g. `(1, 2, 2, 2)` old 1, new
  0 (banker's rounding of an exact half). One model call, 0.0077 USD.
- `parse_size` "accept lowercase units; everything else stays the same", where the
  change also switched KB/MB to 1024-based: after the reviewer prompt was tightened
  (0.1.0 labelled `'30kb' -> 30720` intended), the report separates the intended
  `'0mb' -> 0` from regressions `'9KB' 9000 -> 9216`, `'3MB'`, and newly accepted but
  wrongly valued `'6kb' -> 6144` (expected 6000). Two model calls, about 0.011 USD.

These were built and the prompt was adjusted on them, so they show the mechanism,
not a catch rate.

## QuixBugs evaluation (real bugs)

Data: QuixBugs (github.com/jkoppel/QuixBugs, commit 4257f44, shallow clone in
gitignored `runs/external/`), 40 standard-library Python programs, each with a real
one-line bug and its fix. Runner: `evals/verified_change/quixbugs.py`; summaries:
`evals/verified_change/summarize.py`; artifacts under `runs/verified-change/`.

Protocol, fixed before running: for each program the **bug arm** treats
correct (plus the program's spec docstring) -> buggy as a change claimed to be
"Refactor for readability. No behavior change."; the **control arm** treats the same
correct module -> its `ast.unparse` reformatting (identical behavior) with the same
claim. A regression on the bug arm is a catch; on the control arm, a false alarm.
QuixBugs' own tests are never shown to PolyaBrain. Model `google/gemini-3.7-flash`,
zero retries, local spend guard.

| Run | Bug arm caught | Missed | Control false alarms | Not run |
| --- | ---: | ---: | ---: | --- |
| v1 (original harness) | 38/38 | 0 | **7/37** | 2 programs (shard budget), 1 control unverified |
| v2 (fixed harness, combined reruns) | **38/38** | **0** | **0/37** | quicksort, rpn_eval; powerset control (provider failures) |

v1 false alarms came from harness defects the control arm exposed, so v1's catches
on those programs were not trustworthy: objects without value equality (QuixBugs
`Node` graphs) compared by identity, a generator result compared by identity
(`kheapsort`), and input mutation flagged even when the old version mutated the same
way (`next_palindrome`). Fixes: address-free structural snapshots for objects without
`__eq__`, bounded materialization of generator results inside the timed call, and
relative mutation comparison for change verification. Regression tests:
`test_generator_results_are_compared_by_what_they_yield`,
`test_objects_compare_structurally_and_mutation_is_relative`.

v2 ran under four directories because provider-side `LLMClientError` failures (one
during a session interruption, three later) blocked shards via the spend guard;
affected programs were rerun in fresh directories (`quixbugs-v2b/c/d`) with the same
code and protocol, and infrastructure-failed arms were excluded rather than scored.
Combined: 77 model calls, 0.319 USD provider-reported (about 0.008 USD per program for
both arms). `runs/verified-change/quixbugs-v2-combined.json` holds every record.

What this shows: on 38 real, classic one-line bugs presented as behavior-preserving
refactors, verify-change flagged every one with a concrete input, and it raised no
false alarm on 37 behavior-identical reformattings. What it does not show: QuixBugs is
public and old, so the model may know these programs; the bugs are single-line
algorithm defects, not AI-written changes; the generator sees the diff (as the product
does); and intent classification for non-preserving changes is not measured here.
Next evidence: real repository fix commits and AI-generated pull requests.

## Verification

`backend/tests/test_verified_change.py` (10 tests): read-only versions and repository
status, path containment, option-like revision rejection, non-stdlib refusal,
true refactor (no difference), preserving intent (regressions, no review call,
distinct inputs), intended-change quote enforcement, and the CLI writing
certificate and report with exit 3. `backend/tests/test_sandbox_image.py` covers the
image reference fallback and digest listing.

## Limits and next evidence

- Standard-library-only modules, module-level functions or classes constructible
  without arguments; no files, network, time or cross-module state.
- Random inputs can miss the differing region; the generator is model-written.
- Classification is a model reading of the intent, shown with concrete evidence.
- Next: measure on real changes that later needed fixes (public bug datasets or
  repository histories with fix commits), with the fix commit's tests withheld, and
  report catch rate, false alarms and cost. This needs an approved data source.
- Then: API session type and workbench view; multi-function changes; pytest-aware
  module loading for packages with third-party dependencies.
