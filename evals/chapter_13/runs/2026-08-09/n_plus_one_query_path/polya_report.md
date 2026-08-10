# PolyaBrain Technical Investigation Report

## Final conclusion
**Query-path consolidation (JOIN) should be tested first.** The executable benchmark evidence demonstrates that the N+1 query pattern (51 queries) is the measured dominant bottleneck, with JOIN consolidation reducing median latency by ~5× (49.041 μs → 9.583 μs) and p95 latency by ~4.9× (56.833 μs → 11.709 μs) [query_metrics_summary]. Since the benchmark does not measure Redis at all, and constraints require targeting the measured bottleneck before adding infrastructure, the reversible, low-risk step is to consolidate the query path and verify whether that alone meets latency targets.

## Confidence level
High (90%). The benchmark directly measures the two query paths under identical conditions (in-memory SQLite, 50 accounts, 200 runs each) and shows a clear, large-magnitude difference attributable to query count. The only uncertainty is whether production latency targets are already met by the JOIN path—but that is exactly what should be verified next, before introducing Redis.

## Evidence used
- **Benchmark code** defines two strategies: N+1 (51 SELECTs) and JOIN (1 SELECT) on identical schema/data [query_measurement_code].
- **Summary metrics** (200 runs/strategy): N+1 median 49.041 μs, p95 56.833 μs, query_count=51; JOIN median 9.583 μs, p95 11.709 μs, query_count=1 [query_metrics_summary].
- **Raw CSV** confirms consistent per-run query counts (51 vs 1) and duration distributions [query_metrics_csv].
- **Problem constraints**: "Decision must be grounded in the provided benchmark evidence", "Avoid recommending infrastructure before measuring the dominant bottleneck", "Prefer reversible, low-risk checks first" [VALIDATED STRUCTURED PROBLEM].

## Evidence against
- None from the supplied artifacts. The benchmark does not include Redis, production network/disk latency, cache invalidation complexity, or dashboard query patterns beyond the measured accounts+details join. These are unknowns, not counter-evidence.

## Checks performed
1. Verified benchmark methodology: same in-memory SQLite DB, same 50 accounts, 200 runs per strategy, query counting via trace callback [query_measurement_code].
2. Confirmed summary statistics match raw CSV (median, p95, query_count, row_count) [query_metrics_summary, query_metrics_csv].
3. Computed speedup ratios: median 5.12×, p95 4.85× faster for JOIN vs N+1.
4. Checked constraints and success criteria against evidence: the measured dominant bottleneck is query count (51 vs 1); JOIN consolidation is a reversible code change; Redis is unmeasured infrastructure.

## Checks still needed (not performed)
- Run the JOIN path against a production-like database (network, disk, concurrency) to measure real-world latency.
- Define dashboard latency target (e.g., p95 < X ms) and verify whether JOIN alone meets it.
- Profile the full dashboard query set (beyond accounts+details) to confirm N+1 is the only hot path.
- Assess cache invalidation requirements and data freshness needs if Redis is later considered.
- Evaluate team operational capacity for Redis.

## Open questions
1. What is the production latency target for the account dashboard?
2. Does the JOIN path meet that target on a production database (not in-memory SQLite)?
3. Are there other N+1 patterns in the dashboard beyond the measured accounts+details query?
4. What are the data freshness requirements (would Redis caching require invalidation logic)?
5. If JOIN meets the target, is Redis still needed for other reasons (e.g., read scaling, downstream services)?

## Recommended next action
**Implement and deploy the JOIN consolidation (single query) to a staging environment that mirrors production database topology. Measure end-to-end dashboard latency (p50, p95) under realistic load. Only if the JOIN path fails to meet the latency target should Redis caching be prototyped and benchmarked against the consolidated query path.**

## Audit trace
- Artifacts ingested: query_measurement_code, query_metrics_summary, query_metrics_csv, VALIDATED STRUCTURED PROBLEM.
- No external data, logs, or measurements invented.
- All quantitative claims cite artifact IDs.
- Hypotheses considered: (A) test JOIN first (supported by evidence), (B) test Redis first (no supporting evidence in artifacts).
- Report structure follows required Markdown headings exactly.
