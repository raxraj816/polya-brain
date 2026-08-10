# Chapters 22 and 26: Controlled Knowledge Acquisition

Status: complete for the current MVP contracts and production provider boundary.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## Product Behavior

When PolyaBrain detects a blocking fact it does not know, the cognitive
controller can select a registered source. The production web path is:

```text
knowledge gap
  -> bounded query tied to that gap
  -> provider-neutral search request
  -> untrusted evidence-candidate batch
  -> separate evidence-evaluation action
  -> accepted source-backed evidence or safe non-resolution
```

Search is a capability, not the controller. Provider output cannot directly
resolve a gap, create a hypothesis, or become a conclusion.

## Chapter 22: Available Data Source Registry

`app.acquisition.AvailableDataSourceRegistry` exposes only configured sources
to gap detection. Source metadata includes:

- source kind and description;
- executing capability;
- availability;
- sensitive-data approval;
- risk level.

The generic source taxonomy covers human input, local artifacts, web search,
APIs, databases, memory, measurement, calculators, code execution, and
experiments. The API composition currently advertises only capabilities it can
actually execute: calculator, focused human input, and web search when Brave is
configured.

## Chapter 26: Research Engine Interface

The provider-neutral boundary uses typed `SearchRequest`, `SearchResponse`, and
`SearchResultCandidate` contracts. `BraveSearchProvider` is the first real
adapter. It:

- sends the API key only through the server-side subscription-token header;
- enforces a maximum 400-character, 50-word query;
- normalizes ordinary web results without accepting a provider-generated
  answer;
- uses strict safe search and bounded result counts;
- sanitizes timeout, network, malformed-response, rate-limit, and HTTP errors.

The web-search capability enforces maximum queries, results per query, and
total candidates. Query usage is counted from the current trace and, on the API
path, from durable session events, so clarification/resume cannot reset the
external-query limit.

## Evidence Promotion Guard

Search results are stored in trace metadata as candidates. The deterministic
MVP evaluator checks valid provenance, unique hosts, baseline source quality,
and source independence. A web-derived gap requires at least two independent
accepted sources before it can be marked filled. The evaluation trace records
the explicit limitation that these checks do not establish factual truth;
hypothesis and final verification stages remain mandatory.

This is the initial Chapter 29 guard, not completion of the full evidence
evaluation chapter. Claim extraction, contradiction clustering, temporal
validity, stronger relevance evaluation, and cross-source factual agreement
remain open.

## Configuration

```text
SEARCH_PROVIDER=brave
SEARCH_API_KEY=<server-side secret>
SEARCH_BASE_URL=https://api.search.brave.com/res/v1/web/search
RESEARCH_MAX_QUERIES=3
RESEARCH_MAX_RESULTS_PER_QUERY=5
RESEARCH_MAX_TOTAL_CANDIDATES=15
```

Without a configured provider and key, web search is not registered and is not
advertised to the gap detector.

## Verification

The automated tests prove:

- source lookup excludes unavailable sources;
- the Brave credential stays out of the URL;
- results normalize into provider-neutral candidates;
- rate-limit details fail closed without leaking provider bodies;
- candidates do not enter canonical evidence before evaluation;
- two independent sources can resolve a web gap while retaining an explicit
  verification limitation;
- a durable prior query count blocks another provider request.

A live Brave request is not part of this gate because no search credential is
configured in the workspace. The real adapter is therefore integration-tested
with HTTP transport fixtures, not claimed as live-provider verified.

## Local Artifact Inspection

The same candidate/evaluation boundary now supports explicit local text
artifacts. `LocalArtifactInspector`:

- reads only a file explicitly referenced in the problem or selected gap;
- resolves the path and requires it to remain inside a configured allowed root;
- refuses directory scans, unsupported/binary formats, oversized files,
  `.env` files, common credential filenames, and private-key formats;
- extracts a bounded, line-numbered excerpt near gap terms;
- records that artifact text is untrusted evidence and is never executed as
  instructions.

One directly supplied local artifact can resolve a missing-artifact gap after
evaluation; final factual and outcome verification remain separate. Configure
the boundary with `ARTIFACT_ALLOWED_ROOTS` and `ARTIFACT_MAX_FILE_BYTES`.
