# Pre-Platform Proof Report: Investigate whether Redis caching is the right latency fix

## Final conclusion
Do not add Redis as the first fix yet. First run a query-shape experiment for the likely N+1 pattern, then reassess whether caching is still needed.

## Confidence level
Moderate-high (0.74). The dominant latency evidence is strong, but the final answer still depends on running the before/after experiment.

## Evidence used
- `ev_query_log` (artifact:fixtures/query-log-summary.txt): The dashboard request performs 51 account detail queries after one initial account list query.
- `ev_profile` (artifact:fixtures/profile-summary.txt): Database time dominates request latency while external API time is low.

## Evidence against
- `ev_cache_estimate` (analysis:fixtures/cache-hit-estimate.md): A first Redis cache is estimated at only 30% hit rate because users often view distinct account sets.
- Redis may still be useful after the query-shape fix, especially if measured hit rate improves.

## Checks performed
- Final report includes all required audit sections.
- Every evidence item includes source_type, source_uri, claim, reliability_score, and relevance_score.
- Hypotheses do not use novelty_score as a core MVP field.
- Evidence against the selected action is explicitly listed before recommendation.
- New Redis infrastructure is not recommended before bottleneck verification.

## Open questions
- What is p95 latency after replacing repeated account detail queries with a batch/eager-load query?
- Does a larger traffic sample confirm the 30% cache-hit estimate?
- Which invalidation paths are required to preserve the five-minute dashboard freshness constraint?

## Recommended next action
Run a reversible query-shape experiment: add a query-count assertion, batch/eager-load account details, replay representative dashboard requests, and compare p95 latency before introducing Redis.

## Audit trace
- `explore` / `problem_representation`: Parsed the raw latency question into a technical investigation about whether caching is the right first fix.
- `reframe` / `problem_representation`: Reframed 'Should we add Redis?' into 'What verified bottleneck should we address first?'
- `compare` / `evidence_evaluation`: Compared query logs, profile data, cache hit estimate, freshness constraint, and an analogical pattern.
- `compare` / `hypothesis_reasoning`: Generated 3 candidate explanations and selected h_n_plus_one as the best-supported next path.
- `verify` / `verification`: Created a technical investigation checklist with contradiction and architecture-change checks.
- `reflect` / `reflection_memory`: Recorded that infrastructure should follow bottleneck evidence, not precede it.

## Hypotheses considered
- `h_n_plus_one` [selected] confidence=0.74: The main bottleneck is an N+1 query pattern, so query consolidation should be tested before Redis.
- `h_cache_first` [deferred] confidence=0.38: Redis caching should be the first fix because repeated reads are causing avoidable database load.
- `h_external_api` [rejected] confidence=0.14: External API calls are the dominant bottleneck.
