**Recommendation: Find the root cause first.** Don't just double memory.

## Why

| Approach | Risk |
|----------|------|
| **Double memory now** | Buys ~6 more hours before OOM. Leak continues. You'll be back here in days with 6GB pods. Masks the real bug (unbounded cache? connection pool? job payloads accumulating?). |
| **Root cause first** | Fixes it permanently. Usually takes 1-4 hours with the right tools. |

## Immediate Triage (30 min)

```bash
# 1. Grab a heap dump before OOM (add to pod spec)
#    -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/tmp/heap.hprof

# 2. Check what's growing - RSS vs heap
kubectl exec <pod> -- cat /proc/<pid>/smaps | grep -E "^(Size|Rss|Pss)" | head -20

# 3. Quick language-specific checks:
#    - Go: pprof --inuse_space http://localhost:6060/debug/pprof/heap
#    - Java: jcmd <pid> GC.class_histogram | head -30
#    - Python: objgraph / tracemalloc / memray
#    - Ruby: heap_analyzer / derailed_benchmarks
#    - Node: clinic.js / heap snapshots in Chrome DevTools
```

## Most Likely Culprits (by frequency)

1. **Unbounded in-memory queue/cache** — jobs batching with no TTL or max size
2. **Connection/pool leak** — DB/HTTP clients not returned, growing goroutine/thread count
3. **Job payload accumulation** — deserialized messages held in memory after processing
4. **Metrics cardinality explosion** — Prometheus labels with unbounded values (request IDs, user IDs)
5. **Library bug** — known issues in sidekiq, celery, temporal, bullmq, etc.

## Decision Rule

> **If you can't identify the leak in 2 hours → add memory alert + automated restart + schedule root-cause sprint.**
> Never double memory without a ticket to investigate.

## What to Do Right Now

1. Add OOM heap dump + memory limit alert (e.g., >2.5GB)
2. Schedule 2-hour investigation block today
3. If critical path: restart pod every 4h via `livenessProbe` + `restartPolicy: OnFailure` as temporary band-aid

---

**Bottom line:** Doubling memory is technical debt with compounding interest. Spend the 2 hours now.
