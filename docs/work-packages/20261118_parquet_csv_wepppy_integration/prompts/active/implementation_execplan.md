# Cut over WEPPpy CSV exports to the native converter


This active ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Keep
Progress, Surprises & Discoveries, Decision Log and Outcomes & Retrospective
current together with the package tracker. The operator authorized execution on
2026-11-18. Production deployment remains outside this request.

## Purpose / Big Picture


An authorized CSV download should produce the same contracted data through a
bounded Rust subprocess instead of building rows and a complete CSV buffer in
Python. The integrated release must use this path immediately for every supported
CSV request, without environment-facing configuration or a Python fallback.
Success is proven by actual downloaded CSV bytes, process/resource ownership and
negative security tests against the built service image.

## Progress


- [x] (2026-11-18 UTC) Inspect accepted standalone candidate and browse/download contracts.
- [x] (2026-11-18 UTC) Scaffold integration policy, package, tracker and checkpoint draft.
- [x] (2026-11-18 UTC) Validate six Markdown files, spelling previews and whitespace; no runtime tests.
- [x] M0: Inventory valid states/compatibility, resolve settings/errors and ratify contracts.
- [x] M0: Obtain independent contract reviews and commit checkpoint before code edits.
- [ ] M1: Package production CLI/harness and close native compatibility gaps.
- [ ] M2: Wire all supported CSV paths; implement serving ownership and remove old conversion.
- [ ] M3: Validate focused and exact-image workflows; then run the broad suite.
- [ ] M4: Close reviews, document release/rollback and hand off validated integration.

## Surprises & Discoveries


The current exporter already avoids pandas for CSV, but `_download.py` creates
Python rows and complete StringIO/bytes output. Filtered CSV first decodes a table
in the web process. Calling Rust only after that step would leave the untrusted
parsing and memory problem outside the child boundary.

An archive/file-like branch exists in source while the filesystem contract retires
virtual archive traversal. Establish reachability before implementing an adapter;
code presence alone is not authority to restore a retired feature.

The shared `pqf` contract explicitly depends on environment-backed enablement and
row caps. The operator's no-environment requirement therefore requires a scoped
CSV contract amendment, not merely avoiding a new backend-selection flag.
The wepp1 overlay starts eight workers; standalone two-slot admission is only
shared if every worker uses the same root. Worker/proxy timeout semantics and
parent-crash recovery also require integration evidence.

## Decision Log

2026-11-18, operator: approve temporary conversion storage. Delete staged input
copies, completed/partial CSVs and IPC files after serving, failure or crash
recovery; retain original Parquet and correlated service diagnostics. Rationale:
"the .csv could become stale but users wouldn't realize it". Generate a fresh
representation for each request rather than leaving a misleading project CSV.
The operator further clarified that retained CSVs would imply automatic generation
and cause users to ask why those outputs were absent. CSV remains an on-demand
representation, not an expected project artifact.


2026-11-18, operator: immediate native cutover, no environment-variable-facing
configuration, no fallback to Python. Record these as mandatory release behavior
in `docs/schemas/parquet-csv-integration-contract.md`; do not add staged routing,
compatibility backend switches or automatic failover. Rationale: one auditable
execution path after the standalone performance and correctness evaluation.

2026-11-18, Codex: preserve existing authorized CSV semantics across reachable
variants. Standalone exclusions are compatibility work, not an implicit scope
reduction. Extend native support where needed before cutover. Requests for an
intentional user-visible reduction require a concrete operator decision.

2026-11-18, operator/Codex: broad repository tests run after integration is wired.
Do not run them during this scaffold or repeatedly during standalone development.
Immediate cutover does not waive contract, exact-image or deployment safety gates.

## Outcomes & Retrospective


M0 execution in progress. No production code, image, route or running service has changed.
The accepted standalone implementation is a starting asset, not completed HTTP
integration. This package cannot close on an adapter stub or mocked route tests.

## Context and Orientation


Work in `/home/workdir/wepppy-parquet-csv-cli-package`, branch
`codex/parquet-csv-cli-package`, starting at
`392ee2299d8573e038b2e932fe3bdb7e044d1d35`. Preserve shared-master work and closed
package history. Read nearest instructions before touching each implementation
area: `wepppy/microservices/browse/AGENTS.md`, `docker/AGENTS.md`, `tests/AGENTS.md`
and any nested files discovered under the chosen runtime module.

`tools/parquet_csv_cli/rust/` and `tools/parquet_csv_cli/harness/` contain the
accepted native executable and stdlib supervisor. The executable uses bounded
local input, strict JSON responses and OS limits; its caller owns private scratch
and file-lock admission until artifact cleanup. Its standalone API accepts a
regular source path; filters and file-like adapters are not implemented.

`wepppy/microservices/browse/_download.py` owns run, culvert and batch compatibility
download routes. `download_response_file` selects raw, filtered-Parquet and CSV
responses. `_parquet_to_csv_bytes_with_units`, `_parquet_fp_to_csv_bytes_with_units`,
`_table_to_csv_bytes_with_units` and their schema helpers form the legacy CSV
paths. `parquet_tables.py` also has consumers outside CSV export, so inspect its
callers before removing shared formatting/projection functions. `parquet_filters.py`
and the shared filter contract govern `pqf`; a zero-match filter is not the same
state as an empty unfiltered file.

The dedicated `download` service owns exact archive ZIP delivery and is not the
CSV owner. Existing routes and Caddy ownership should remain stable. The common
WEPPpy Docker build and Compose overlays must contain the required CLI artifact;
a binary built only in the shape-converter image cannot serve browse. Inspect
`scripts/deploy-production.sh` and current Docker documentation before writing
any rollout instructions. Do not invent a new image-publication workflow.

## Plan of Work


### M0: Commit a complete contract checkpoint


Use `artifacts/20261118_contract_decision.md` as the checklist, not as evidence of
completed approval. Inventory real schemas/codecs and every CSV route/input state,
including filtered, empty, legacy, malformed and any reachable file-like source.
Bind fixtures to immutable input identities. Record compatibility and regression
plans before editing serializers or schemas. Resolve duplicate labels, metadata
encoding, dates/decimals/binary/nested/extension fields and codecs required by actual
exports; do not build speculative type support for unobserved cases.

Specify exact code-owned constants and fixed binary/provenance/scratch paths.
Reconcile all CSV environment dependencies with the shared filter contract;
preserve non-CSV consumers. Specify finite HTTP error mappings and response
headers, startup/readiness failure policy, request cancellation, stream ownership,
shared capacity and crash recovery. Review resource ADR-0148 against actual service
budgets; write an integration ADR for changed defaults/thresholds before code.
Do not assume a 180-second child budget fits the current Gunicorn configuration.

Choose and record the minimal native filter/input extension needed for parity.
Python may parse bounded query syntax but must not decode Parquet in the request
worker. No arbitrary SQL or unversioned protocol may cross the boundary. Define
artifact visibility/retention and exact-image preflight requirements. Amend the
CLI, integration, filesystem and filter contracts where applicable. Retain two
independent read-only reviews, close findings and commit a standalone checkpoint
ancestor; record its full SHA in tracker before implementation.

### M1: Make the evaluated converter a required runtime artifact


Promote the harness into an appropriate production module, proposed
`wepppy/microservices/browse/parquet_csv.py`, with the exact ownership layout fixed
at M0. Avoid two drifting production implementations. Keep evaluation tests/oracle
separate from production imports. Extend the owned Rust crate only for required
compatibility, preserving preflight and process limits for every field, even
omitted indices. Apply dependency evaluation before changing the locked graph.

Build and install the executable/provenance using the actual WEPPpy image build,
with a compatible runtime ABI and complete source identity. Code owns paths and
limits; no environment override, auto-build/download or Python fallback. Validate
missing/tampered/incompatible artifacts through image preflight and request error
contracts. Passing --version alone is insufficient: convert a real fixture and
read back its bytes under the runtime identity.

### M2: Wire immediate cutover and complete response ownership


Replace every covered CSV branch with the async adapter in one accepted change.
Keep auth, containment, sensitive-original raw-byte and missing-file precedence.
Stage source bytes under the shared admission budget without web-worker decoding;
apply filters inside the bounded native boundary. Any file-like staging must also
bound decompression/input bytes and preserve source identity. Do not add an adapter
for a branch proven retired/unreachable.

Return a completed-file response, not Python CSV bytes. Own the artifact through
ASGI send completion, slow-client cancellation and disconnect; prove failure
cleanup and slot release when headers or body sends fail. Finalization and strict
IPC validation precede 200 headers. Use one admission root across workers, and
prove that worker restarts/death cannot silently overbook or delete active work.
Implement the M0 recovery policy without a new daemon or queue.

Delete superseded production CSV exporters/imports. Keep helpers used by preview
or other downloads only when they no longer provide a callable legacy export path.
Direct tests must make an attempted legacy invocation fail and still exercise all
successful native routes. Missing binary, bad IPC and exhausted limits must never
select the old code. Preserve existing raw and filtered-Parquet behavior.

### M3: Prove the integrated workflow, then run broad regression


Use the exact built image and production-equivalent UID/GID, groups, mounts, umask,
secrets configuration and worker topology. Use authorized immutable project copies.
Retain request/filter intent, source/staged identity, binary/image/source hashes,
final CSV digest, parsed columns/rows/cells and HTTP-downloaded bytes. Cover run,
culvert and batch paths, accepted legacy/empty states and required filtered cases.
Do not replace the decoder, subprocess or response transport with mocks for the
artifact acceptance boundary.

Exercise real cross-process busy admission, large output, slow/disconnected
readers, repeated cancellation, resource exhaustion, malformed metadata/external
references, bad binary/provenance/IPC and worker crash/restart. Separately prove
unauthorized/path-escape/PII requests do no conversion work and raw bytes remain
available when CSV representation fails. Confirm route latency, memory and live
scratch remain within the M0 budgets and that Python never buffers the whole CSV.

Run focused gates while iterating. Only once wiring and focused/exact-image checks
are complete, run `wctl run-pytest --checkout "$PWD" -- tests --maxfail=1` with the
existing runtime preflight inputs if required. Record its source/runtime receipt
and disposition actual failures without weakening the no-fallback contract.

### M4: Review and hand off the release


Retain independent final correctness and security review artifacts and close
medium/high findings. Update browse developer/operator/user documentation with
fixed settings, error behavior, capacity/recovery procedures and supported inputs.
Write a concrete release and whole-release rollback procedure using canonical
Compose/wctl/deploy mechanics. A deployment authorization is separate from this
scaffold and from local implementation acceptance.

Record implemented, wired, locally validated, environment validated, remotely
integrated and deployed states separately. Archive the plan only after acceptance
for the authorized implementation scope; do not claim production repair without
production evidence. Promote durable rules outside the package and leave the
closed standalone evaluation unchanged.

## Concrete Steps


For this scaffold, run only documentation/whitespace checks from the task root:

    wctl --project-dir "$PWD" doc-lint --path docs/work-packages/20261118_parquet_csv_wepppy_integration
    wctl --project-dir "$PWD" doc-lint --path docs/schemas/parquet-csv-integration-contract.md
    wctl --project-dir "$PWD" doc-lint --path PROJECT_TRACKER.md
    git diff --check

During implementation, use actual source paths and the current container runtime:

    cargo test --locked --manifest-path tools/parquet_csv_cli/rust/Cargo.toml
    wctl run-pytest --checkout "$PWD" --profile python -- tools/parquet_csv_cli/tests -q
    wctl run-pytest --checkout "$PWD" -- tests/microservices/test_download.py tests/microservices/test_parquet_filters.py tests/microservices/test_browse_auth_routes.py tests/microservices/test_browse_security.py

Extend that list with the new integration/lifecycle tests and exact-image workflow
command at M0; update paths if the harness/crate is promoted. Record actual pass
counts and receipt identities, not historical counts. Run the broad suite only at
M3 after wiring. No runtime test or image build is required for this scaffold.

## Validation and Acceptance


A user follows the same CSV download link and receives the contracted bytes from
the required native executable. No environment setting changes that path, and a
failed converter produces an explicit failure rather than Python output. Healthy
raw downloads, previews, D-Tale and unrelated exports retain their behavior.
Acceptance requires real generated/served artifacts and all package gates; source
search, compilation and a passing mocked route test are supporting evidence only.

## Idempotence and Recovery


Use isolated test roots and immutable corpus copies. Clean only owned artifacts
after child/response ownership ends. Never delete another worker's active scratch.
Retry failed validation with a new evidence identity. Release rollback restores a
previous complete revision/image via the existing workflow; it is not a runtime
fallback. Reconcile orphan processes and scratch before reusing a crashed root.

## Artifacts and Interfaces


Retain the M0 matrix/ADR, contract review dispositions, checkpoint SHA, locked
binary/source/image identity, exact-image HTTP readback, lifecycle/resource and
no-fallback evidence, focused/broad receipts, final reviews and rollout handoff
under this package's artifacts. Keep large/private project data outside Git.
The durable integration contract controls behavior; the closed evaluation is
historical evidence. Runtime API/filter/error details must be complete at M0.

Revision note: 2026-11-18 scaffold created for the operator's immediate-cutover,
no-environment-configuration, no-Python-fallback implementation request.
