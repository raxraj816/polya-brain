# Chapters 61–70: Local Investigator workbench

Status: a usable local workbench is implemented. The full frontend integration
gate remains open for explicit mode overrides and fresh user investigations.
Browser source/check input and candidate edits are now delivered in Chapter 13-O. This work does not close Chapter
60 or the independent product-value requirements of Chapter 13-K.

## Delivered behavior

- Next.js, React, Tailwind, a shadcn-style button, Lucide icons, and TanStack Query.
- Actual persisted input/run/report flows, session URLs, search, status filters,
  paging, refresh recovery, clarification forms, loading and failure states.
- Capability checkpoint events committed through separate database transactions,
  visible before final canonical artifacts; final trace save excludes the already
  persisted event prefix. Resource summaries sum actual usage events.
- Evidence register with source filtering and excerpts, report evidence for and
  against, ranked hypotheses with checks and falsification criteria, expandable
  audit events, Markdown export, and print styling.
- Feedback types useful/wrong/incomplete/unsafe, optional correction, persisted
  history, and feedback-based session filters for manual review. Human input is
  not promoted into verified conclusions or memory.
- Localhost-only proxy, restricted backend paths, cross-origin mutation checks,
  JSON-only actions, bounded input, no automatic mutation retries, and no browser
  provider credentials. This is not a multi-tenant security boundary.
- Local Docker startup now includes the UI and runs migrations before the API
  starts. Published service ports bind to localhost and support overrides.

## Verification

Database integration tests cover literal search (including wildcard characters),
pagination, status filtering, artifacts, concurrent trace visibility, unique
trace sequencing, saved clarification questions, and feedback storage without
changing the report. Browser tests run three real deterministic sessions through
submission, verification, evidence, hypotheses, trace, reload, export, feedback,
keyboard tabs, and mobile layout. They also exercise backend-unavailable errors
and cross-origin / non-JSON action rejection. A fourth browser test pauses a
real investigation, reloads its questions, records clarification, and reloads
the new pending question and preserved trace. Images are private local artifacts
under `runs/workbench/`.

Verification recorded for this implementation: 445 backend tests passed against
migrated Postgres, strict Python lint/type checks passed, frontend type checking
and two unit tests passed, production builds passed locally and in Linux Docker,
and four Playwright tests passed against the complete Docker stack. Postgres,
Redis, backend, and frontend health checks all passed on isolated local ports.
The Linux build exposed and fixed a missing platform dependency in the npm lockfile.

These arithmetic runs verify application wiring. They do not establish technical
investigation quality or superiority over a direct model. Fresh technical cases
and actual repeat-use feedback remain required.

## Remaining chapter work

- Chapter 62: Compare/Review override propagation and optional structured inputs.
- Chapter 63: cursor-based streaming to replace bounded polling if throughput
  warrants it; explicit duration and combined-stage meanings already appear.
- Chapter 65: confidence history only after a reliable producer exists.
- Chapter 68: review status transitions, reviewer identity, and a governed path
  from reviewed corrections into future reflection.
- Chapter 70: fresh technical runs and user review following browser source/check
  and candidate edit delivery in Chapter 13-O. Three arithmetic runs are not a
  substitute for this technical product gate.
- Authentication, tenant isolation, cancellation/reconciliation, retention,
  and deployment operational gates remain before public cloud exposure.

## Demo script

1. Start with `What is 17 * 6?` and inspect the checked result and recorded usage.
2. Open Evidence, then Hypotheses, then Trace. Inspect source handles and metadata.
3. Reload the session URL and export the report. Search history for the problem.
4. Save an incomplete/wrong feedback item with a correction; locate it through
   the feedback review filter. Confirm the original report is unchanged.
5. Run an under-specified semantic problem with a configured provider. If the
   runtime requests clarification, reload before supplying the missing details.
6. Use the experimental source/check selector with an enabled local host backend
   for technical work. Review the candidate diff and scope; arithmetic screenshots
   and synthetic source checks are not independent debugging-quality evidence.
