# Chapter 13 Live Technical Investigations

This evaluation runs the production OpenRouter adapter and Chapter 13 Problem
Representation Engine against three reproducible technical cases:

1. Executable pagination code plus a genuine failing pytest log.
2. Executable SQLite query paths plus measured query counts and timings.
3. The configured OpenRouter model, the repository environment template,
   official provider-policy notes, and a genuine live policy-probe response.

The configured free model requires data-collection consent and does not declare
JSON-mode parameter support. Keep production defaults fail-closed. Run this
non-confidential benchmark with explicit process-local overrides:

```bash
OPENROUTER_DATA_COLLECTION=allow \
OPENROUTER_REQUIRE_PARAMETERS_FOR_JSON=false \
.venv/bin/python evals/chapter_13/run_live_investigations.py
```

Outputs include the artifact manifest and hashes, validated structured problem,
representation trace, Polya report, direct-model answer, per-case metrics, and
aggregate summary.

The `would_use_again_proxy` is a transparent rubric combining correctness,
evidence quality, actionability, and a latency penalty. It is not represented as
real human feedback; `human_user_feedback_collected` remains `false` until an
actual user reviews the cases.
