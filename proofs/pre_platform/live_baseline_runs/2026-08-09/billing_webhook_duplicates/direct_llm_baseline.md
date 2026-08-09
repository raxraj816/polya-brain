**Verify idempotency handling first.** Disabling retries is a blunt fix that breaks the provider's intended reliability model and will cause missed payments during future transient failures.

**Why idempotency first:**
- Webhook retries are *expected* behavior for at-least-once delivery; the bug is in your handler, not the retry mechanism
- Idempotency keys (or deduplication via event IDs) are the standard solution—most providers (Stripe, Paddle, etc.) already send unique event IDs you can use
- Disabling retries shifts the burden to manual reconciliation and increases support load when inevitable network hiccups occur

**Immediate steps:**
1. **Audit the webhook handler** – confirm it checks for duplicate event IDs before processing charges
2. **Add idempotency** – store processed event IDs (with TTL) and return 2xx immediately on duplicates
3. **Replay the duplicate events** – verify they're now safely ignored
4. **Only then consider retry config** – if the provider's retry storm is genuinely excessive (e.g., hundreds of retries in seconds), tune backoff/max-retries, but don't disable

**Rollback plan if idempotency is hard:** Temporarily disable retries *while* you build proper idempotency, with a hard deadline to re-enable. But treat that as a band-aid, not the fix.
