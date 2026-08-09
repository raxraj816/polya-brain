**Inspect indexing and sync quality first.**

Changing ranking weights on potentially corrupted data is like tuning a car engine that has the wrong fuel — you'll waste time optimizing symptoms instead of fixing the root cause.

## Immediate checks (run these before any ranking changes)

| Area | What to verify | How |
|------|----------------|-----|
| **Document count** | Total indexed products vs. source catalog | `SELECT COUNT(*) FROM products` vs. catalog export |
| **Field completeness** | Critical fields populated (title, category, price, availability, images) | Sample 100 docs: `SELECT * FROM products WHERE title IS NULL OR price IS NULL` |
| **Category/attribute drift** | Taxonomy changes, missing facets, new enum values | Diff yesterday's vs. day-before facet distributions |
| **Duplicate/near-duplicate docs** | Same SKU indexed multiple times, variant explosion | `GROUP BY sku HAVING COUNT(*) > 1` |
| **Stale inventory/availability** | Products marked in-stock but actually OOS | Cross-reference with inventory service for top 500 searched SKUs |
| **Embedding/vector freshness** | If using semantic search, were embeddings regenerated? | Check `updated_at` on vector column vs. sync timestamp |
| **Sync logs** | Errors, partial failures, skipped records | Search sync job logs for `ERROR`, `WARN`, `SKIPPED` |

## Quick smoke test
Run your top 20 converting queries against the index. If results look qualitatively wrong (irrelevant categories, missing bestsellers, obvious junk), **stop — the data is the problem**.

## Only if data checks pass
Then consider ranking tuning, but:
1. **A/B test** weight changes, don't ship blind
2. **Instrument** with conversion tracking per experiment
3. **Start small** — adjust one weight (e.g., `popularity_boost`) by ±10% and measure

## Escalation path
If sync quality checks reveal issues:
- **Roll back** to previous index snapshot if available
- **Re-run sync** with fix (missing field mapping, dedup logic, etc.)
- **Validate** with the same smoke test before re-enabling traffic

**Bottom line:** 30 minutes of data validation saves days of ranking thrashing. What does your sync log show?
