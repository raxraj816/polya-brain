# PolyaBrain Technical Investigation Report

## Final conclusion
The free model `nvidia/nemotron-3-ultra-550b-a55b:free` cannot satisfy `data_collection=deny` because its endpoint logs session data for security and model improvement, causing a 404 when the deny policy is enforced. A viable configuration requires **two distinct routing paths**: (1) an evaluation-only path that explicitly sets `data_collection=allow` for the free model, and (2) a production path that uses a paid model/endpoint supporting `data_collection=deny` or `ZDR=true`. The current single-client configuration cannot achieve this without code changes to support per-request policy overrides or segmented clients.

## Confidence level
**High** for the finding that the free model is incompatible with `data_collection=deny`. **Medium** for the feasibility of per-request overrides (not confirmed in artifacts). **Low** for specific paid model recommendations (catalog not yet consulted).

## Evidence used
- **[openrouter_env_template]**: Shows current configuration: `OPENROUTER_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free`, `OPENROUTER_DATA_COLLECTION=deny`, `OPENROUTER_ZDR=false`, `OPENROUTER_REQUIRE_PARAMETERS_FOR_JSON=true`. The comment explicitly states the free endpoint "cannot satisfy the fail-closed privacy and strict JSON routing defaults below."
- **[openrouter_official_sources]**: Documents that `provider.data_collection` accepts `allow` or `deny`; `deny` restricts routing to providers that do not collect user data. Confirms the free endpoint warns against sending confidential data and logs session data for security and model improvement. Also notes `provider.require_parameters=true` for structured outputs.
- **[openrouter_policy_probe]**: Live probe result: HTTP 404 with error `"No endpoints found matching your data policy (Free model training)"` when requesting the free model with `requested_data_collection: "deny"`.

## Evidence against
- No evidence in the supplied artifacts that OpenRouter supports per-request `data_collection` override via `provider.parameters` or similar mechanism. The official sources only document the parameter at the provider routing level, not per-request.
- No evidence of any paid model/endpoint that supports `data_collection=deny` or `ZDR=true` (catalog not provided).
- No evidence of current PolyaBrain router implementation (code not supplied) to assess whether segmented clients or per-request overrides are already implemented.

## Checks performed
1. **Policy probe execution** – Ran a live request against the free model with `data_collection=deny`; captured 404 response ([openrouter_policy_probe]).
2. **Configuration review** – Examined `.env.example` for current privacy and routing defaults ([openrouter_env_template]).
3. **Documentation review** – Consulted OpenRouter official sources for data-collection and structured-output routing behavior ([openrouter_official_sources]).

## Open questions
1. Which paid models/endpoints in the OpenRouter catalog support `data_collection=deny` or `ZDR=true`?
2. Does OpenRouter allow per-request override of `data_collection` (e.g., via `provider.parameters` in the chat completion request)?
3. What is the current PolyaBrain production request routing architecture (single client vs. segmented evaluation/production clients)?
4. What are the cost and latency constraints for selecting a production model?
5. Is there an existing mechanism in the PolyaBrain codebase to enforce routing isolation between evaluation and production traffic?

## Recommended next action
1. **Obtain OpenRouter model catalog** with data_collection/ZDR support matrix (required data source per problem statement).
2. **Review OpenRouter routing documentation** for per-request `provider.parameters` capability (especially `data_collection` override).
3. **Audit current PolyaBrain router implementation** to determine if segmented clients or request-level policy injection are feasible.
4. **Prototype a dual-client configuration**: one client with `data_collection=allow` for evaluation (free model), another with `data_collection=deny` for production (paid ZDR-capable model), ensuring no code path allows production prompts to reach the free endpoint.

## Audit trace
- Artifacts consulted: `openrouter_env_template`, `openrouter_official_sources`, `openrouter_policy_probe`.
- No external searches, API calls, or code inspections beyond the supplied artifacts were performed.
- All citations reference the provided artifact IDs exactly.
