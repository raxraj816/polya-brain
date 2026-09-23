# Chapter 13-H: Semantic Capability Broker

Status: complete in the current working tree.

## Product Boundary

Polya owns semantic routing. A model endpoint is a replaceable processor, not
the intelligence controller. The broker may choose or fall back among only the
routes explicitly configured by the operator. It cannot change the cognitive
action, bypass evidence admission, approve risk, or accept its own conclusion.

## First Mechanism

- Capability-specific, model-route-specific bounded health profiles.
- Deterministic ordering with conservative priors.
- Circuit opening after repeated typed failures and bounded recovery probes.
- One total deadline partitioned across remaining routes.
- Actual provider-attempt accounting, including retry and repair calls.
- Trace-visible attempt metadata without prompts, credentials, or provider
  response bodies.

The first ledger is process-local and bounded. Durable routing memory and
cross-tenant policy require a separate promotion decision.

## Implemented

- `RoutedCognitiveModelGateway` owns deterministic ordering across one primary
  and at most one explicitly configured fallback route.
- `OPENROUTER_FALLBACK_MODELS` configures that optional fallback. Duplicate
  primary entries are removed, more than one distinct fallback is rejected,
  and the broker performs no model discovery.
- Route health is keyed by cognitive capability and a non-secret model-route
  fingerprint. Two consecutive failures open the first circuit; periodic
  probes allow recovery without permanently blacklisting a route.
- The first route receives only its partition of the hard total deadline, so a
  fallback retains execution time.
- Fallback is limited to rate-limit, timeout, unavailable, provider,
  malformed-response, and schema-validation failures. Authentication,
  permission, invalid-request, and unsupported-capability failures stop
  immediately and remain auditable.
- Every real provider invocation is counted, including transport retries and
  structured-output repair. Successful response usage and failed-route call
  counts are accumulated across the broker attempt.
- Capability observations and durable trace events expose only safe route,
  success, duration, attempt-count, and failure-kind metadata. Prompts,
  credentials, and raw provider bodies are not copied into route telemetry.
- The FastAPI process shares one bounded route-health ledger across session
  runners. The existing controller, risk, privacy, budget, evidence-admission,
  and present-case verification gates still sit above the broker.
- Initial problem representation and later model-backed cognitive capabilities
  now use the same route policy and shared health ledger. Representation
  reserves four calls for one route or eight for two, and its retry plus parser
  repair work shares the same route deadline.

## Verification

- Primary success completes in one route and one provider call.
- A primary timeout retries under its partition, then completes through the
  fallback with all three real calls charged.
- Invalid schema output can fall back; authentication failure cannot.
- Repeated primary degradation opens a circuit, later probe success restores
  it, and a changed model slug receives no stale health history.
- Exhausting both routes yields `insufficient_evidence`, no final answer, four
  charged provider attempts, and two safe route attempts in the decision trace.
- Bootstrap rejects more than one explicit fallback.
- Representation primary failure completes through the fallback with three
  actual calls, while four-call route exhaustion produces neither a structured
  problem nor a final answer. Parser repair cannot restart its total deadline.
- Current full repository suite: 338 passed, 23 skipped (361 collected).
- Ruff passes repository-wide; formatting passes across the 156 affected
  Python files; strict mypy passes over 102 application source files.

## Bounded Claim and Remaining Gap

This proves typed route resilience and truthful accounting across initial
representation and controller-registered model-backed cognitive capabilities.
It does not prove better reasoning quality, verified outcome superiority, or
general intelligence. Durable, tenant-aware health memory also remains
unimplemented, and provider diversity still depends on the operator explicitly
configuring routes that satisfy the same privacy and schema requirements.
