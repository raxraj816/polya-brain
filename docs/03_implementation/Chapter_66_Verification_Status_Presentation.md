# Chapter 66: finished runs without verified conclusions

Verified locally on 2026-10-01, Asia/Kolkata. This is a presentation correction
within the existing report contract, not a new verification or completion rule.

## Failure and correction

Citation rejection correctly clears the canonical final answer and verified
reflection. The workbench previously rendered that persisted null answer as
“No conclusion recorded yet,” while the execution badge said “completed” and the
verification row always used a check-mark shield. These cues did not clearly
distinguish a finished unsuccessful run from a pending answer or verified success.

The screen and Markdown export now say “No verified conclusion is available.”
when the conclusion is absent. Completed execution is labelled “run finished” in
history and detail, with “Run finished” in the status filter. The separate verified
badge and check-mark shield require a passing verification. API statuses and
canonical null conclusions are unchanged. Failed checks, admitted evidence, trace
and recommended next action remain inspectable. No automatic retry is added.

## Verification

`backend/tests/fixtures/citation_reports.py` creates three isolated sessions using
scripted model outputs through the real kernel, verifier, PostgreSQL persistence,
and report service: an unadmitted source, a missing numbered section, and a
supported-locator control. Rejected cases retain no final answer, reflection, or
episodic memory. The fixture does not expose an application HTTP endpoint.

`frontend/tests/citation-reports.spec.ts` reads those saved sessions through the
production Next.js server and real API. The before-fix test failed on the misleading
conclusion text. After the fix, one browser test covering all three cases passes:
failed checks and recovery guidance appear; exports stay unverified; trace retains
the provenance failure; reload preserves it; 390-pixel mobile views have no
horizontal overflow. The passing control retains its correct source link and
verified badge. Both rejected mobile reports were captured; the missing-section
report was visually inspected.

The ordinary workbench suite also passes **seven cases**, with the live-provider
case explicitly skipped. **30 frontend unit/socket tests**, TypeScript and the
production build pass. Fixture Ruff validation passes. The unchanged backend
runtime suite was not repeated for this presentation-only increment; its latest
complete result remains 1,089 passing tests.

Artifacts, including the preserved before-fix failure trace, are under
`runs/launch-readiness/2026-09-30-report/`. Reproduce with an isolated migrated
database, `PYTHONPATH=backend:backend/tests` for the fixture, and
`POLYABRAIN_CITATION_CASES` pointing at its output JSON for Playwright. That browser
case skips explicitly when fixtures are not configured.

These are developer fixtures with zero live provider calls. They verify delivery
of already-rejected output, not general factual accuracy, semantic support,
automatic citation repair, hosted authentication, or real-user usability.


The later [backend-loss browser verification](Chapter_98_Browser_Process_Loss.md)
also corrects persisted running-state wording to “outcome pending” and supplies
recovery guidance for pending and operator-stopped reports without changing their
canonical execution/verification status.
