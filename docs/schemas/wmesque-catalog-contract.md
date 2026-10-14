# WMesque Catalog and Retrieval Contract

Status: accepted for M1–M5 implementation by operator instruction on 2026-10-14;
implementation conformance pending. Governance: [catalog policy](../infrastructure/wmesque-catalog-governance.md).

## Client Routing and Compatibility

V2 resolves an explicit endpoint argument first, otherwise the ordered JSON URL
array in `WMESQUE_ENDPOINTS`, otherwise `https://wepp.cloud/webservices/wmesque2/`.
Unset/blank deployment configuration uses that default; an empty array, non-HTTP(S)
URL, credentials, query, fragment, or malformed value is an explicit config error.
Do not append implicit servers. V1 behavior and integer success return remain.

Use at most one attempt per configured endpoint and a 300-second total network
budget, sharing remaining time among remaining candidates. Retry HTTP 404, 409,
429, 500, 502, 503, 504, network timeout/disconnection, and invalid/truncated raster
responses. Do not retry other HTTP errors or local filesystem failures. Record
attempts in logs and successful metadata. No persistent endpoint health state.

Requests may specify `expected_revision` (a SHA-256 hex digest). A mismatch or
missing revision cannot satisfy that request. Unpinned requests may use a verified
lagging replica. Old servers without revision metadata remain usable for unpinned
requests; they must not be represented as verified revisions. Validate raster
readability before replacing the output. Failed downloads preserve the prior
output. Publish the metadata and raster as a rollback-protected operation; no
claim of cross-file atomic visibility is made to concurrent readers. The normal
caller consumes them after successful return. Keep provenance additive.

## Published Resources

An optional `/geodata/.wmesque/catalog.json` contains schema version 1 and a
`datasets` mapping from logical ID to revision. Its absence means no managed
resources; legacy paths continue to work. An explicitly empty mapping is valid.
Malformed catalogs fail explicitly rather than masquerading as absence.

Each immutable `.wmesque/releases/<revision>/manifest.json` contains schema
version 1, dataset ID, entrypoint, files (relative path, size, SHA-256), and
revision. Revision is the SHA-256 of UTF-8 JSON of the other manifest fields,
with sorted keys, compact separators, ASCII escaping, and files sorted by path.
The entrypoint is `data/<dataset>/.vrt`; manifest file paths are release-root
relative, without `..`. No symlinks are allowed in a published release. VRT
SourceFilename paths are relative to their containing VRT; `..` is permitted
only when the resolved target remains inside the release and is inventoried.
The publisher snapshots the VRT dependency closure rooted in the configured
geodata directory, rewrites VRT filenames to contained VRT-relative paths, includes
adjacent metadata, and verifies before publication. External/virtual/network VRT
sources must be materialized by the operator before publication; never advertise
their mutable URL as a verified data revision. Legacy retrieval remains available.

Publish a verified release directory first, then atomically replace the catalog
JSON under a shared publisher/sync filesystem lock. Re-read the destination
catalog under this lock before merging updates so local extension publications
are not lost. A request resolves the catalog once and reads that
immutable release throughout processing. Retain old releases; garbage collection
is outside this contract. Original legacy directories remain untouched, allowing
local extensions and code rollback. Master adoption changes the managed catalog
mapping through the ordinary sync path, without renaming the logical resource.

Keep `/catalog` list compatibility, adding logical `/geodata/<dataset>/.vrt`
entries (not physical release paths), deduplicated against legacy entries.
Add `/catalog/manifest` for the versioned managed mapping. Retrieval
returns dataset revision as `wmesque.revision` in `WMesque-Meta`; expected revision mismatch is HTTP 409.
Missing resource is 404; invalid IDs are 400. No bulk download API is introduced.

## Synchronization and Scheduling

`publish_dataset(geodata_dir, dataset)` creates a managed snapshot.
`sync_catalog(source, destination, *, dry_run=False)` pulls the master's managed
catalog and referenced immutable releases. Source is an absolute local root for
fixtures or an administrator-configured `user@tailnet-host:/absolute/root` over
SSH. Reuse rsync with argument protection and noninteractive SSH; source config
is never browser input. Require host-key verification and existing authorized
credentials; never auto-accept unknown host keys. Validate transferred paths,
VRT dependency containment, and hashes before asking GDAL to open them, then raster readability
before publishing any catalog changes. No delete or reverse-sync operation.

One destination-scoped OS lock prevents overlapping sync; process exit releases
it. Verify copied releases even if previously present; never trust matching names
alone. Resources absent from master remain unchanged. A failed transfer preserves
the previous catalog; dry run reports proposed updates without publishing. Retain
a bounded last-attempt/last-success JSON status record with revision results.

`sync_wmesque_rq()` reads `WMESQUE_SYNC_SOURCE` and `WMESQUE_SYNC_DESTINATION`
(default `/geodata`) and delegates to the helper. Scheduling is disabled unless
`WMESQUE_SYNC_ENABLED=true`, and uses the existing batch queue and scheduler.
An enqueue helper coalesces queued/started work by destination using Redis
transactions and job state; OS locking also protects manual execution. Default
interval is 86400 seconds and job timeout 3600 seconds. Sync subprocesses have
bounded timeouts and interrupted work never advances the catalog.

## State and Acceptance Matrix

Absent managed catalog: legacy retrieval and first publication work. Empty
catalog: no-op sync. Populated catalog: verified revision retrieval and update.
Legacy dataset: unpinned retrieval works and local publication is explicit.
Hostile paths, symlinks, corrupt manifest, or unavailable pinned revision: explicit
failure without destination escape or replacement. Configuration combinations
are tested independently from these resource states.

Tests must parse real rasters, exercise interruption and adoption, and prove
actual RQ/scheduler behavior under forest identities. Forest tests use isolated
resources and test servers for failure injection. Production and Kubernetes
activation remain M6/M7; tailnet connectivity and writable receiver placement
must be validated there, not assumed from forest fixture success.
