# Live Direct-Model Baseline Audit — 2026-08-09

## Final conclusion

The configured direct model selected the correct safe investigation direction
on all five curated cases and usually supplied more concrete domain diagnostics
than the current deterministic PolyaBrain proof output. PolyaBrain's artifact
bundle is more explicit about confidence, evidence against, verification, open
questions, and audit trace, but that structural advantage does not yet prove
higher user value or lower workflow overhead.

Continue into Chapter 11 and the first real engine, but retain a hard product
gate: the real Polya loop must outperform or complement this direct baseline on
verified correctness, evidence quality, or user decision confidence—not merely
on report formatting.

## Confidence level

High for this five-case comparison. The cases cover deployment readiness,
database/cache latency, worker memory growth, search indexing, and billing
webhook idempotency. They remain curated synthetic investigations rather than
real user incidents with ground-truth artifacts.

## Configuration

- Provider: OpenRouter.
- Model: `nvidia/nemotron-3-ultra-550b-a55b:free`.
- Cases: 5.
- Total tokens: 3,418.
- Average tokens per case: 683.
- Average response latency: 26.684 seconds.
- Minimum/maximum latency: 14.187 / 40.521 seconds.
- Reported model cost: unavailable; the selected route is marked free.
- Reliability note: one response omitted a completion payload during the first
  sweep; one explicit retry succeeded.

No credential value is stored in these artifacts.

## Evidence used

- Live direct-model response for each curated case.
- Each case's reference `recommended_next_action` and open questions.
- Generated PolyaBrain report, evidence, hypothesis, checklist, and trace
  artifacts for the same input.
- Provider-reported model, latency, response id, and token usage metadata.

## Case results

| Case | Direction aligned with reference | Concrete diagnostic checks | Explicit confidence/evidence-against | Relative observation |
| --- | --- | --- | --- | --- |
| Billing webhook duplicates | Yes | Strong | No | Direct answer was specific and immediately actionable. |
| Cache investigation | Yes | Strong | No | Direct answer gave richer query and tracing checks. |
| Deploy health-check regression | Yes | Strong | No | Direct answer aligned closely with rollback/isolation guidance. |
| Worker memory growth | Yes | Strong | No | Direct answer offered useful tooling but made some stack assumptions. |
| Search ranking drop | Yes | Strong | No | Direct answer supplied a concrete index-quality checklist. |

## Evidence against

- The automated `polya_artifact_more_auditable` result checks structural
  sections; it does not score correctness, usefulness, or overhead.
- PolyaBrain's current evidence items are deterministic metadata derived from
  the prompt, not independently gathered incident evidence.
- The direct model included verification-like checks and conditional decision
  rules despite not using PolyaBrain's exact section labels. Exact heading
  matching therefore understates baseline quality.
- No human user timed or rated the two workflows.
- No case included real logs, code, metrics, or a known resolved root cause.

## Checks performed

- Verified every live artifact bundle with
  `verify_pre_platform_proof.py --run-dir`.
- Confirmed all five direct answers chose the safer reference direction.
- Compared each direct answer with the curated reference action.
- Inspected direct answers for concrete checks, alternatives, irreversible-action
  gates, explicit confidence, source metadata, and contradiction handling.
- Aggregated latency and token metadata across all five responses.
- Confirmed the stored artifacts contain no OpenRouter credential pattern.

## Open questions

- Will real Problem Representation and Constraint Discovery engines improve
  decisions rather than add ceremony?
- Does explicit evidence-against and trace visibility increase user trust enough
  to justify the additional artifacts?
- Can PolyaBrain gather and verify real evidence that a direct answer lacks?
- Will a technical user choose PolyaBrain for a second real investigation?
- Is the current free model representative of the strongest baseline users
  would otherwise choose?

## Recommended next action

Implement Chapter 11 against the Chapter 12-A fake client, then use Chapter 13
golden examples to compare structured framing quality against these same direct
answers. Before further platform expansion, run at least three real technical
problems with human usefulness and overhead ratings.

## Audit trace

1. Safely detected and relocated the runtime credential into ignored `.env`.
2. Added an OpenRouter baseline path using the documented chat-completions API.
3. Verified the client contract against an offline local HTTP endpoint.
4. Ran all five curated cases with the configured live model.
5. Retried one provider response that omitted completion choices.
6. Verified each generated artifact bundle.
7. Compared live answers to reference actions and recorded limitations.
