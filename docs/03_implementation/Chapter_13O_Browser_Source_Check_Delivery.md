# Chapter 13-O: Browser source/check delivery

The local Investigator now admits a user-selected Python source file and a
regression check through the browser, runs the existing bounded source/check
workflow, and returns an inspectable candidate diff. This closes the browser
transport gap in Chapter 13-N; it does not establish broad technical quality or
complete the independent product-value gate.

## Workflow and permission boundary

1. The user describes the issue, enables the experimental source/check workflow,
   and chooses two UTF-8 Python files. The check defines `verify(implementation)`
   and uses assertions. Only the standard library is available in this sandbox.
2. The UI checks backend availability. The backend must enable
   `CODE_EXECUTION_ENABLED`, have a configured provider, and have access to Docker
   and the pinned sandbox image. The general Compose API intentionally has no
   Docker socket access. Use a local host backend for this workflow.
3. The user explicitly consents to submitting the selected files to the provider
   and executing the check. Both API consent fields require literal JSON `true`;
   numbers, strings, false, and missing fields are rejected.
4. Admission validates size/content and stores exact snapshots plus SHA-256
   hashes in one private application artifact. Known secret-like content is
   refused instead of silently editing executable input. The local database
   retains these snapshots; production retention and tenant controls remain open.
5. The normal created-session run claim selects the source/check runner. It
   validates the stored bytes and consent again, writes private temporary files,
   and invokes the same runtime and before/after sandbox capability as the CLI.
   Temporary files are deleted on exit. Original user files are never edited.
6. The report uses measured verification outcome, medium confidence, explicit
   checks, and open questions. The proposed diagnosis remains qualified; matching
   identifiers is a lexical check, not causal proof.
7. The candidate panel exports a unified diff and shows the original/check hashes.
   For a passed candidate, it verifies the source, check, and patched hashes against
   recorded execution before allowing that diff to be presented as checked. A
   changed plan or stored snapshot is refused. Unverified proposals are labeled.

Canonical evidence excerpts now preserve leading/trailing whitespace, while
rejecting blank excerpts, so executable evidence survives validation unchanged.
The admission and execution tests include leading and trailing blank lines.

## Verification evidence

API tests exercise a valid correction, an incorrect edit, a vacuous passing
check, disabled execution, missing/non-boolean consent, oversized/blank/secret-like
input, changed input hashes, changed candidate plans, temporary-file cleanup,
byte-preserving evidence, and report confidence/scope.

A live browser integration run used the existing configured provider on a small
synthetic `total(count, unit_price)` defect. It made one model call (1,057 input
and 1,114 output tokens), recorded 13.76 seconds of active runtime, observed the
original fail and the candidate pass, and preserved the downloadable diff after
reload. The live check is opt-in and is not run automatically in CI. This was a
known synthetic defect for integration verification, not a blind evaluation or
competitive quality claim. Private local screenshots are in `runs/workbench/`.

The final backend suite passed 459 tests against migrated Postgres, including
the source/check cases with the pinned Docker sandbox. Frontend type checking,
two unit tests, and the production build passed. Five ordinary browser tests
passed; the sixth live-provider case passed separately with explicit opt-in.

The ordinary browser suite also verifies disabled-source messaging and prevents
submission without consent. Database CI pulls the pinned Docker image and runs
positive/negative source/check integration tests with a scripted model response.
This separates deterministic transport/verifier coverage from live provider use.

## Run locally

With migrated Postgres, the existing provider configuration, and Docker running:

```sh
docker pull python:3.14-alpine@sha256:a1321512d6a287428c50dcdf2ab3857761127e03a23b1f648e9c1c0de59288f8
CODE_EXECUTION_ENABLED=true make dev
make frontend-dev
```

Use a separate terminal for the frontend. The files must fit the combined
18,000-character escaped sandbox payload, and each browser-selected file is
limited to 18 KB. No automatic whole-repository execution or patch application is
provided. Source/check passing remains scoped to the supplied regression check;
adversarial code can tamper with the in-process Python harness, and no hostile-code
attestation or complete regression safety is claimed.
