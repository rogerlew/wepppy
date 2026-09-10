# Production M1 upload and execution workflow

Status: proposed 2026-09-10 UTC; no runtime implementation or deployment.
Scope explicitly requested: NoDb state, prerequisite/freshness checks, dNBR
upload/publication, RQ execution, and a minimal control to upload and run M1.
Reports and interactive dashboard are deferred. Canonical UI proposal:
[Post-fire debris-flow control](../../../../../docs/ui-docs/contracts/postfire-debris-flow-control-contract.md).

## Authority and acceptance boundary

Reuse existing predictor, rainfall, dNBR, slope/SBS and scalar contracts. Preserve
legacy debris_flow.nodb and outputs. The new facade is PostfireDebrisFlow,
proposed file postfire_debris_flow.nodb. Existing project watershed/outlet is
exclusive assessment scope. Both upload and run enforce authorization and CSRF
at the proper session/token boundary through existing contracts.

Complete the contract-first checkpoint before any coupled runtime edits:
explicit operator approval of UI/data/state matrix, two independent read-only
reviews, all affected canonical amendments, and a standalone ancestor commit.
This draft and package are not that checkpoint. Security impact is high.

## Prerequisites and source ownership

M1 eligibility is WBT plus canonical effective CONUS locale. Resolve legacy us
and cross-boundary behavior through project-config authority before freezing
payloads; never infer geography from template/config names. A 10 m project is
the intended operator smoke test, not a new M1 10 m restriction. Respect accepted
area warnings outside inclusive 0.2–8 km² without rejecting on area alone.

Run prerequisites: completed delineation with valid raw DEM/grid/boundary/outlet,
readable built WEPP Soils inventory, prepared SBS, RUSLE Nomograph K with accepted
provenance, accepted normalized dNBR, and valid project Climate event parquet.
NOAA artifact is required only for requested NOAA design comparisons. Use K-
artifact readiness, not a successful unrelated full RUSLE factor build (ADR-0059).
No implicit upstream rebuild or NOAA acquisition. Readiness checks validate
actual artifacts and source ownership, not simply controller/file presence.

Owner-required live readiness: publish prerequisite/freshness and NOAA availability
through the existing Redis-backed preflight WebSocket flow. The control consumes
`preflight:update`, including initial hydration and reconnect reconciliation.
Integrate producer invalidations when upstream artifacts change; a historical
task-completion flag alone cannot establish current K/dNBR/NOAA readiness.
Freeze additive payload keys and producer ownership in the checkpoint. Keep raster
decoding/full hashing out of the preflight service and heartbeat path; model
submission and worker publication independently enforce current source checks.
Disable unavailable/stale NOAA immediately; do not silently switch rainfall sources.

Upload needs eligible project/grid/domain plus write access; it does not require
finished Soils, K or Climate. Read-only GET on a never-used module must show a
usable empty state without writing NoDb. First authorized mutation creates state
under normal lock/persistence rules; present-empty is not corruption.

## Durable state and immutable artifacts

Version the new facade state. Freeze exact public/property/serialized names at
checkpoint; record at minimum active dNBR artifact identity/metadata, current
upload attempt, current run/job identity, selected rainfall source, last accepted
run revision, dependency snapshot/freshness, and terminal failure details. Keep
large rasters/tables in artifacts, not NoDb JSON. Bind attempt IDs to published
artifacts so an old worker cannot replace a newer submission.

Layout under postfire_debris_flow/: hidden .staging/<id>/ contains immutable
source/normalized artifacts and unfinished predictor/results bundles. Only
accepted completed model files are exposed through fixed result links.
A completed accepted pointer in NoDb is the active authority; partial directories
are never active. Retain previously accepted artifacts on upload/run failure.
Specify retention/cleanup and orphan reconciliation before code; no destructive
cleanup of prior successful runs is implicit. Generated permissions must work
for web and worker identities on the actual target mounts.

Use short lock/refresh/allowlisted-state updates, not a NoDb lock across uploads,
normalization, hashing or model execution. Workers snapshot inputs, compute in
private attempt directories and finalize only after reacquiring fresh state and
checking attempt/dependency identities. Readbacks refresh cached NoDb using the
canonical persistence contract. No whole-object merging or stale mutation retry.

## Upload transport and publication

Freeze exact route/multipart fields, size limits and error contract in checkpoint.
Accept the backend's format family and integer/float single bands. The browser
offers Auto (default), standard scale presets and Custom with factor/offset
fields. Resolve Auto to explicit factor/offset before calling the unchanged
normalizer; distribution-based detection and ambiguity retry are specified in the
UI contract. Record encoding evidence and prevent double scaling. Default GDAL
identity metadata does not establish encoding. Auto examines robust valid-value
distributions, with metadata as evidence; numerical selection rules require
fixture evaluation under ADR-0063. Dtype or a single extreme is insufficient. An unresolved
candidate is not published; an authorized bounded retry can reuse its staged
files after the user selects a scale. Freeze candidate access/expiry and metadata
validation in the checkpoint. No user-entered imagery dates or date prerequisite;
retain available source metadata without inheriting dates from a replaced map.
Preserve original filename as escaped display metadata across reloads; generate
server-owned paths. Show accepted filename separately from a pending replacement.
Publish upload details and applied scale in a persistent two-column table inside
`wc-control__panel-summary`, using the exact UI-contract rows. Permit scale
correction from retained source through the existing upload action; re-normalize
and publish as a new attempt, invalidating results only on accepted replacement.
Always display accepted raster formats and integer/floating-point datatype help.
Require actual valid-data watershed overlap; partial dNBR is accepted with coverage.

Bound streamed upload size before decoder access; `.vrt` source references map
only to explicitly uploaded companion file(s) within this attempt. No arbitrary
server/network paths, traversal, symlinks, derived VRT execution, external HFA
resources or archive extraction. Preserve strict dNBR backend behavior rather
than exposing its trusted-path assumptions to browser input. Specify overall
request cap as well as per-file cap; use SBS precedent without importing its
categorical-value limits. Do not write final inputs into a shared public path.

Proposed upload route stages validated transport, enqueues normalization and
returns canonical job identity. Queued worker uses normalize_dnbr with current
project grid/domain, verifies source hashes and publishes only on complete
success with unchanged grid and current attempt. Failed replacement preserves
previous accepted map and results. New accepted dNBR invalidates derived results.
Grid/outlet changes invalidate normalized dNBR; re-normalization of stored source
must be an explicit documented action, not an unnoticed source change.

## RQ model execution and freshness

Proposed one model job prepares an immutable snapshot, invokes the completed
build_m1_predictors and build_m1_results sequentially, then finalizes the active
run pointer. Use existing rq-engine submission/auth/job/status conventions;
freeze retry/timeout/idempotency and response states before code. Do not invent
a separate scheduler or fan out tasks absent a measured need. Never copy a
partially built predictor/result directory into active output.

The run route refuses missing/stale prerequisites and attaches to an already
active matching attempt on duplicate clicks. Worker rechecks source association
and hashes at start and before publication. Inputs changed during computation
produce a superseded/not-current result, never a current pointer. Upload/run
races and queued retries use explicit attempt ownership. No automatic M3 switch.
Incomplete scientific support can produce a successful diagnostic result with
null probabilities under accepted backend contracts; this is distinct from a
failed worker or an invalid request.

Dependency snapshot includes DEM/grid/domain/resolved outlet, Soils build/source
inventory, SBS artifact/class mapping/assessment, named K and its provenance,
dNBR source/normalization/assessment, CLI parquet/mode/date semantics, selected
frequency source/NOAA or CLI parity artifact, engine/tool identity and scientific
parameters. Hashes establish content identity, not association with current
controllers; record and revalidate relevant owner revision/config identities.
Do not rerun terrain because only climate changed when validated predictor reuse
is possible; reuse policy must verify all predictor dependencies, not timestamps.
Unitizer changes never stale scientific results. Freeze exact invalidation matrix
at checkpoint, including source deletion and legacy missing provenance.

## UI parameters and output boundary

Proposed first-control defaults: frequency source project climate, all 15/30/60
minute event/design durations, 1/2/5/10-year design intervals and 50% inverse
threshold. These are proposed UI/workflow defaults requiring explicit approval
and ADR; backend contracts remain explicit-argument APIs. No M3 selector or
algorithm/coverage knobs. Dates/encoding are upload metadata, not model tuning.

Show status, upload coverage, actionable errors and completion/download access
only. Generated event/design/inverse files exist and can be inspected by the
operator through existing authorized run-file access. No report tables/charts,
new report renderer, public query API or dashboard. Prefer an existing protected
file listing with allowlisted bundle links; do not add a general archive service.

## Validation and deployment distinction

Exercise valid absent/empty/populated/read-only/legacy states separately from
malformed/hostile requests. Require actual upload → normalization/publication →
run → generated files → reload under production-equivalent web/worker identities,
groups, mounts, umask and orchestration. Include failed replacement, stale inputs,
source mutation mid-job, duplicate submit and competing upload/run finalizers.
UI tests must prove user labels/status/action outcomes, not only payload shapes.

Update RQ dependency catalog/graph and verify actual job trees. Confirm installed
WBT binary capability/hash through real worker execution before rollout. Local
Rust build evidence alone does not prove worker availability. Build a concrete
release/preflight/rollback plan through canonical deployment tooling; installation
or deployment requires existing explicit target authority, not inference from
this scaffold. Operator's later 10 m project is the final upload/run smoke case.

## Execution contract (2026-09-10)

This section supersedes preceding provisional implementation details and pending
choice language. Its exact decisions are normative for the checkpoint; the
earlier sections describe scope/rationale. Runtime conformance remains pending.

The owner's instruction to execute this package authorizes implementation of the
reviewed UI and the following bounded engineering choices, including its required
standalone contract commit. Conformance is pending. No deployment or push is implied.

### Transport and admission

Use rq-engine `/api/runs/{runid}/{config}/postfire-debris-flow/state` (GET),
`upload-dnbr` (POST multipart), `retry-dnbr` (POST JSON), and `run-m1` (POST JSON)
under that same `postfire-debris-flow/` prefix. GET requires `rq:status`; mutations
require `rq:enqueue`. All use canonical JWT and run authorization. Before any
mutation, require normalized URL config (strip optional .cfg suffix) equals current Ron.config_stem and reject readonly
projects. Feature must be enabled; runtime locale and WBT requirements are server
checks. Session-token browser requests retain existing CSRF/token contracts.

Upload fields: `file`, optional `companion` only for VRT, `scale_mode` default
`auto` (`auto`, `scaled_1000`, `normalized`, `custom`), and `scale_factor`/
`add_offset` only for custom. Custom requires finite positive factor and finite
offset. Reject unknown/duplicate fields, multiple file values and empty files.
At most two files and three text fields; cap actual streamed request bytes before
multipart parsing at 201 MiB, each raster at 100 MiB, VRT at 64 KiB, each text
field at 256 bytes. Enforce actual streaming limits even without Content-Length;
close parser files on success/failure. Reject remote/absolute/traversal VRT sources;
only one simple basename referring to the explicitly uploaded companion is
allowed. Preserve validated basenames inside an exclusive server-owned attempt
directory so the VRT identity is preserved. Basenames are not storage authority.

Retry fields: `candidate_id`, `scale_mode`, optional custom factor/offset; the ID
is a server-issued 32-character lowercase hex UUID, bound to this run's recorded
latest candidate or active accepted source. No browser paths. Pending candidates
expire after 24 hours; accepted sources remain available for correction. Retrying
creates a new attempt; never change accepted files in place. Reauthorize every
retry. Concurrent upload normalization rejects a second distinct upload with 409;
model execution may coexist with an upload, subject to publication freshness.

JSON retry/run bodies are capped at 4 KiB actual streamed bytes before decoding.
Require object JSON and reject duplicate/unknown keys, nonfinite values and
non-JSON bodies; Content-Length does not substitute for counted bytes.

Run fields: `frequency_source` (`cli` default or `noaa`), no other parameters.
Always evaluate 15/30/60-minute wet events and design storms at 1/2/5/10 years,
with inverse target 0.5. No optional CLI frequency CSV is supplied: calculate CLI
frequencies directly from parquet, avoiding stale CSV parity artifacts. NOAA is
required only when selected. Defaults are recorded with ADR-0063's workflow scope.

POST success returns `job_id`, `result: {attempt_id}`; matching active model
submissions return the same job ID. Distinct active model requests return 409.
Use existing tracked submission/lifecycle lease and enqueue-recovery helpers;
record attempt receipt before enqueue and reconcile unknown enqueue outcomes
before admitting another attempt. Enqueue failure must not strand a ready-looking
job or overwrite accepted output. Terminal RQ state is authoritative for orphan
reconciliation; GET may report reconciliation needs but does not persist state.
Use the configured RQ timeout and existing status-stream job lifecycle. No
unbounded automatic retries; explicit user retry starts a new attempt.

Errors follow canonical RQ envelope: invalid payload/format/encoding/overlap 400,
auth 401/403, missing candidate 404, stale/busy/config mismatch 409, size 413,
missing prerequisites/ineligible project 422, dependency/service failure 503.
Worker expected errors persist a sanitized code/message; detailed exceptions
remain in protected logs, not open preflight or job-result payloads.

### State, sources and publication

NoDb `_state` is schema version 1 with `active_dnbr`, `upload_attempt`,
`run_attempt`, `frequency_source` and `last_successful_run`, initially null except
frequency source `cli`. Attempt records include ID, job key/ID, phase, timestamp,
source snapshot and safe error. Successful dNBR record includes immutable attempt
ID, relative artifact references, source display filename, summary and snapshot;
run record includes ID, source snapshot and completed result bundle references.
GET returns a sanitized projection: eligibility/readonly, required-data readiness,
NOAA availability, selected source, upload/run status, accepted dNBR summary,
previous/current result state and fixed file links. Never serialize raw controller
objects or arbitrary manifests to the browser.

Store sources and unfinished computation under `postfire_debris_flow/.staging/`
with exclusive attempt directories. Do not expose hidden data through browsing.
Retain immutable accepted sources/normalization in hidden storage as well; expose
only verified completed model bundle files via fixed accepted-result links.
All paths must remain within nonsymlink project-owned directories. Use group-
compatible web/worker permissions and validate them under actual identities.
No automatic deletion in this increment: reject expired retry candidates; cleanup
is an operator task limited to verified unreferenced attempt directories.

RunCapabilityAuthority.locale_profile must resolve to `conus`; missing/invalid or
other locale authority is unavailable. Existing authority handles legacy `us`.
No new rectangular/geographic cutoff is inferred. Western US guidance remains
visible; scientific area warnings do not block execution.

Read current Ron.dem_fn, Watershed.wbt_wd/bound.tif and outlet.geojson, current
built Soils inventory, Disturbed.sbs_4class_path, rusle/k_polaris_nomograph.tif
and rusle/manifest.json, Climate's climate/wepp_cli.parquet and selected
climate/atlas14_intensity_pds_mean_metric.csv. Confirm artifact ownership and
current controller selections, not arbitrary file presence. SBS is already 0–3;
retain classes/masks and use accepted nearest alignment. Use raw DEM, never
conditioned relief/fvslop. Initial raster admission retains the existing local
M1 supported formats/limits; unsupported raw DEM representation produces an
explicit prerequisite error, not an implicit terrain substitution.

Snapshot relevant input selections and actual source signatures for cheap live
freshness; SHA-256 all consumed inputs before/after computation. Exclude unrelated
NoDb metadata, Unitizer and unselected NOAA/CLI CSV from scientific identity.
Normalize source/grid into immutable attempt inputs while preserving recorded
lineage. Model worker builds predictors then results, validates complete manifests,
and publishes only after fresh locked rehydration confirms attempt and dependency
identity. Changed input or newer attempt yields superseded, preserving prior
accepted output. Avoid broad cache clearing; clear only postfire_debris_flow.nodb
immediately before mutable RQ hydration and refresh while locked before mutation.

### Live preflight and control

Keep the existing boolean preflight wire contract. On initial hydration and each
`preflight:update`, fetch authenticated state; debounce/coalesce requests and
ignore out-of-order responses. Upstream RedisPrep changes trigger refresh even
when checklist booleans remain the same; ensure the stream emits these events.
Publish a domain revision notification on upload/run transitions. Reconcile on
socket reconnect and expose connection state using the existing preflight status;
do not create another socket or an expensive raster scan in the Go service.
Live state inspects owner selections and file signatures, while workers perform
full validation. A prerequisite row means input available for model validation,
not a guarantee that every watershed cell has valid scientific support.

Use the exact control fields/table/copy in the UI contract. Register
`postfire_debris_flow` as a preview feature, user role, WBT, requires disturbed,
enable dependency rusle (which already enables polaris); enabling features never
builds owner data. Render eligible absent-controller state. Feature metadata
cannot define locale; run capability authority controls locale availability.

Upload summary remains visible through reload/failed replacement; scale correction
uses the existing upload action. Completed model files are status/download access,
not a new report. No probability table or dashboard is included.

Auto decoding must reuse dnbr._identity_vrt and bounded detached dnbr._raster
validation before reading values. Never open an uploaded pathname directly with
GDAL outside that boundary, including during distribution detection.

### State serialization and notification details

The authenticated GET `result` has exactly these top-level keys:
`schema_version` (1), `eligible` (bool), `readonly` (bool), `unavailable_reason`
(string or null), `required` (records below), `noaa_available` (bool),
`frequency_source` (`cli` or `noaa`), `upload_ready`/`run_ready` (bool),
`upload`/`run` (attempt or null), `dnbr` (accepted summary or null),
`results` (accepted result or null), `freshness` (`absent`, `current`, `stale`).
Readiness records have `key` (`watershed`, `soils`, `sbs`, `k`, `climate`, `dnbr`),
`ready` (bool), `reason` (safe code or null), `message` and `control` (fixed anchor).
The five upstream rows are visible; dNBR readiness belongs to its upload section.

Public attempts have `id`, `job_id` (nullable until reconciled), `phase`,
`created_at` (UTC ISO), `error` (null or `{code,message}`), `retryable` (bool).
Phases: `staged`, `queued`, `running`, `needs_scale`, `complete`, `failed`,
`superseded`, `enqueue_unknown`. `needs_scale` is successful job processing with
unresolved encoding, not accepted publication. Terminal outcomes survive reload.
Public dNBR has `id` (also valid for correction), `filename`, `format`, `dtype`,
`cell_size_m` (two numbers), `coverage_fraction`, `source_range`, `prepared_range`
(two numbers each), `scale_mode`, `scale_factor`, `add_offset`, `scale_method`
(`distribution`, `metadata`, `selected`), `completed_at`, `current` (bool).
Result has `id`, `completed_at`, `current` (bool), `partial` (bool), `files`
(list of `{name,url}` for events.parquet, design.parquet, inverse.parquet and
manifest.json only). Never include hidden source paths or candidate tokens in
preflight/job results. UUID is an identifier, not authorization.

Private attempts additionally store `snapshot`, `source_id`, `encoding`,
`filename` and `job_key`; schema allows absent optional values only in a freshly
created/empty state. Reject malformed populated records; do not interpret them
as a ready/empty controller. Public projections explicitly select fields.

Preflight notification choice: emit on every Redis keyspace update, even if
checklist/locks/whole-second last_modified compare equal. Do not invent a new
revision payload. Existing RedisPrep timestamp/clear/config methods notify the
run hash; add an opaque `postfire_debris_flow:revision` value on domain changes.
Managed artifact mutations must notify on publication and invalidation: watershed
DEM/domain/outlet, Soils builds, Disturbed SBS validation, RUSLE K publication,
Climate export and postfire upload/run transitions. Add notification at any such
owner path not already touching the run preflight hash. The browser emits a
`preflight:connection` event with `connected` boolean on open/close/error; this
control rehydrates on open and marks cached readiness non-live on close/error.
Existing per-run authorization remains on the detailed state endpoint. No
filesystem watcher is introduced: unmanaged operator file edits are checked at
next state request/submission and are outside realtime producer notifications.

### Fixed completed-file access (publication review clarification)

Keep completed bundles under hidden attempt storage. Copying to a generic public
run folder before committing NoDb would expose unaccepted or partially published
work. Instead use authenticated rq-engine GET
`postfire-debris-flow/files/{attempt_id}/{name}` with `rq:export`, run/config
checks, ID equality with the last accepted result and the four-name allowlist.
Resolve only the recorded attempt's hidden results directory; verify its published
file signature before serving. This is a fixed-file adapter, not a generic path
or archive endpoint. Browser downloads use the existing session-token request
helper and a temporary blob link. Stale previous results remain downloadable
when their own files match the accepted record; missing/changed files return 409.
No generic browseable publication directory is created. NoDb commit is the sole
publication boundary, eliminating a two-store atomicity gap.

Open each validated regular file once, compare its accepted signature using that
open handle and stream the same handle; do not reopen by pathname after validation.
