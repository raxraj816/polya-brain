# Chapter 13-P: citation provenance before completion

Verified locally on 2026-09-30 on `feature/launch-readiness`, based on
`ba51625096b522165fd7f8d7170eaa01a7e02a2e`. Changes are uncommitted.
The binding master plan was updated before implementation.

## Failure and implemented boundary

The saved HTTP CLI answer cited RFC 9110 §9.3.1 even though the retained
source excerpts contained §6.4.1 and a cross-reference to §9.3.1, not its heading.
An offline replay also accepted an invented source URL when paired with the
model's passing report. The separate saved workbench answer did not contain
that same wrong section; this finding must not be attributed to it.

`citation_provenance.py` now screens the final answer in both the ordinary model
verifier and fused conclusion checker after model review, before canonical
acceptance. It parses Markdown using `markdown-it-py` with linkification, checks
rendered web destinations against admitted source URIs with nonempty excerpts,
and requires numbered section headings in excerpts from the same source. A
cross-reference or a model-extracted claim cannot supply the missing heading.

URI matching preserves scheme, path and query. Host case, default ports and
percent-escape hex case receive syntax normalization. Other anchors must already
be present in an admitted source URI. No request follows redirects or fetches
sources during this check. Unsupported locators require document-level citation
or further evidence acquisition; the checker does not rewrite them.

A rejection replaces the proposed pass with failed verification and removes the
answer/reflection. Existing recovery receives a concrete failure and a route to
revise or acquire the missing passage before fresh verification. Existing trace
metadata retains bounded diagnostics, candidate text and its hash; model usage
remains charged. No extra provider request, canonical field or migration is added.

## Citation conventions and limits

Narrative HTTP(S) links, including reference links, autolinks, bare URLs and table
links, are references by default. Code spans and fenced/indented code remain
examples. Future research may use a standalone paragraph with only
`Unverified link (not evidence):` followed by one link and optional punctuation.
A later claim, second link or continued paragraph does not inherit that exception.
The model instructions explain these conventions.

This is a necessary provenance screen, not complete factual verification:

- A matching document/heading does not prove entailment or source reliability.
  A numbered line or table-of-contents entry can resemble a heading.
- Missing citations, disguised claims, unlinked bibliographic references, link
  labels and non-HTTP evidence still require independent semantic review.
- Raw HTML and images are outside the parsed-link check; the workbench disables
  raw HTML and image rendering. This is not a general Markdown sanitizer.
- Conservative URI/anchor matching can reject legitimate aliases or sections
  whose headings were omitted by extraction. Correct evidence acquisition or
  source-level citation is required; no source credit is inferred.
- Limits bound accepted input sizes and link counts, not a measured worst-case
  CPU deadline. Oversize checked content fails closed.

## Evidence

Historical inputs and original failed evaluations remain unchanged under
`runs/core-value/` and `runs/launch-readiness/2026-09-30/`. New replay artifacts
are separate in `runs/launch-readiness/2026-09-30-citations/` (ignored local files).
The replay reconstructs typed output from saved state; it is not the original
raw provider response or a whole-run replay.

| Injected output | Before | After |
| --- | --- | --- |
| Saved CLI answer with absent section | Accepted | Failed; answer removed |
| Manually corrected section locator | Accepted | Accepted by provenance check |
| Unadmitted-domain control | Accepted | Failed; answer removed |

All three use a fake provider. No live model/search calls occurred. A corrected
locator passing is not independent evidence of the answer's truth.

The regression suite covers both verifier adapters, URI/source boundaries,
Markdown forms and examples, exemptions, input ceilings, CLI report truthfulness,
and a real PostgreSQL API run/report reload. That integration check confirms no
final answer or reflection survives rejection and no success episode is learned.
The initial focused run reproduced four failures before the implementation.

Full backend verification with migrated disposable PostgreSQL and the pinned
Docker sandbox passed **1,016 tests with zero skips** in 76.62 seconds. JUnit output
is `runs/launch-readiness/2026-09-30-citations/backend-results.xml`. Dependency
deprecation warnings remain (841). These are developer regressions, not an
independent holdout, live-model improvement or public-launch certificate.

After adding two explicit non-HTTP fixture compatibility cases, all **48 focused
tests** passed with PostgreSQL, zero skips (`citation-results.xml`). The earlier
full suite contains the first 46 of these tests; do not report a full 1,018-test
run. Ruff lint/format and strict mypy (140 source files) passed. Formatting-only
cleanup followed; no further behavior change was made. The disposable database
was stopped after verification. No unchanged frontend suite was rerun.

The readiness ledger records remaining gates and subsequent verification.
