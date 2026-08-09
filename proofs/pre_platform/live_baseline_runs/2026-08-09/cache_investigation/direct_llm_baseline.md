**Don't add caching yet.** 2.4s p95 is high enough that you should understand the breakdown first—caching often masks the real problem and adds operational complexity (invalidation, staleness, memory pressure, cold starts).

**Do this instead (1-2 hours max):**

1. **Get a flame graph or trace** of the endpoint (datadog, honeycomb, py-spy, async-profiler, etc.). Look for:
   - Single slow query vs. N+1 queries
   - External API calls (auth, billing, feature flags)
   - Serialization / JSON dumping large payloads
   - Lock contention or thread pool exhaustion

2. **Check the query plan** for the slowest DB call. Missing indexes? Scanning partitions? `OR`/`IN` clauses killing index usage?

3. **Verify the p95 isn't a tail-latency artifact**—is p50 also bad (~1.5s+)? If p50 is fine but p95 spikes, it's likely GC pauses, connection pool exhaustion, or a noisy neighbor query.

**Only cache if:**
- The hot path is genuinely expensive *and* cacheable (user-specific data that changes infrequently)
- You've fixed obvious N+1s / missing indexes first
- You have a clear invalidation strategy (TTL? event-driven? write-through?)

**Quick win checklist before caching:**
- [ ] `EXPLAIN ANALYZE` on top 3 queries
- [ ] Count DB round-trips per request
- [ ] Check payload size (are you serializing 50KB of unused relations?)
- [ ] Look at connection pool metrics (waiters, idle vs. active)

If after that the bottleneck is "complex aggregation that takes 800ms even when optimized," *then* cache with a short TTL and a background refresh job.

What does the endpoint actually do? (Aggregations? Joins? External calls?)
