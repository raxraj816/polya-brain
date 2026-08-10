**Test query-path consolidation first.**

The data shows a clear N+1 problem: the current path executes **51 queries** (1 for accounts + 50 individual detail lookups) vs **1 query** for the join.

| Strategy | Queries | Median | P95 |
|----------|---------|--------|-----|
| N+1 | 51 | 49 µs | 57 µs |
| Join | 1 | 9.6 µs | 11.7 µs |

The join is **~5× faster** with a trivial SQL change. Adding Redis would introduce cache invalidation, consistency, and operational complexity for a problem that a single JOIN already solves. Fix the query path, re-measure, then evaluate if caching is still needed.
