# Vector upload normalization contract

Status: accepted contract intent; implementation conformance pending. ADR-0145
and the exact dependency graph are accepted subject to the mandatory owned
preflight. Original-upload and failed-attempt retention are required project
artifacts under the rules below.

## Scope and authority

Roads, AgFields, Omni contrasts (run and dry-run), and Batch Runner accept their
existing GeoJSON variants plus single-dataset Shapefile ZIP and single-file
GeoParquet after qualification. Culvert API and D-Tale are excluded. All binary
parsing occurs in shape-converter through format-specific short-lived Rust CLIs.
Every receiving workflow revalidates normalized GeoJSON before persistence.
Converter success cannot authorize a workflow mutation.

## Admission and normalization

Filename extensions and MIME are admission hints, never format proof. Reject
content mismatches. GeoParquet admits versions 1.0/1.1, one root primary WKB
geometry column, and scalar JSON-compatible properties. Reject datasets, remote
resources, external column references, encryption, unsupported encodings and
codecs, nested properties and extension semantics. Do not deserialize Arrow
extension metadata. Missing CRS means CRS84; explicit null means unknown and is
rejected. Known CRS transformation must operate offline.

Normalized output is a UTF-8 GeoJSON FeatureCollection in WGS84 longitude/latitude
order with finite coordinates and JSON-compatible finite property values.
Preserve feature order and property names. Recompute bounds and geometry types;
metadata claims cannot substitute for decoding. Parse the emitted artifact back
and reconcile feature count, bounds, types and hash before success.

## Workflow semantics

Roads accepts LineString/MultiLineString. AgFields requires Polygon/MultiPolygon and retains `field_id`
validation. Omni requires Polygon/MultiPolygon for user-defined areas and retains
existing run/dry-run behavior. These geometry checks must be explicit: current
AgFields attribute-only reading and Omni loading do not establish them. Batch Runner accepts only Polygon/MultiPolygon for new uploads in all
formats, as explicitly selected by the operator on 2026-11-16. Reject points,
lines, geometry collections, null geometries and mixed unsupported collections
before replacing a resource. The decision aligns admission with watershed-area
semantics; retaining legacy point admission was rejected. Existing saved projects
are not migrated or deleted.

## Lifecycle and compatibility

Stage binary bytes first as a bounded private project attempt artifact, then send
an immutable snapshot to shape-converter's private request scratch. The project
copy is provenance/evidence and is never an accepted workflow input or automatic
retry source. Shape-converter scratch cleanup follows success, rejection, timeout
and cancellation; repeated cancellation must not release process ownership before
descendants are drained. Retry creates a fresh attempt and scratch tree.
Conversion and receiving validation must finish before accepted artifacts or
workflow state are replaced. Preserve existing authentication, CSRF, run scope,
locking and error response schemas.

Preserve current endpoint upload policies: Roads and AgFields 10 MiB, Omni
100 MiB, Batch Runner 30 MiB with its existing configured override. These are
existing receiving caps, not approved parser allocation or normalized-output
ceilings. An ADR must resolve expansion and resource budgets before code.

## Acceptance gate

Prove each supported format through the actual receiving boundary, reload state,
and parse downstream artifacts. Test failed replacement against an already
accepted resource. Include malformed metadata, allocation/decompression expansion,
geometry bombs, nonfinite values, unknown CRS, timeout, repeated cancellation,
descendants, scratch cleanup, concurrency and converter bypass. Mocks and file
existence alone do not establish acceptance.

## Bounded format profile

GeoParquet versions are exactly `1.0.0` or `1.1.0`. Require one `geo` metadata
entry, a single root BYTE_ARRAY primary geometry column encoded as WKB, and
unique column names. Admit required/optional scalar boolean, integer, finite
float and UTF-8 string properties plus null. Reject repeated/nested columns,
binary properties, decimal/timestamp semantics, encrypted metadata/columns,
external column paths and native GeoArrow encodings. Ignore no executable
extension semantics: reject extension metadata; never deserialize `ARROW:schema`.
Reject nonplanar edges and coordinate epochs rather than silently changing their
meaning. Bounds and geometry-type declarations are informational; decoded data
must agree with admitted geometry structure and all output bounds are recomputed.

The codec allowlist is UNCOMPRESSED and SNAPPY; admitted encodings are PLAIN, RLE,
PLAIN_DICTIONARY and RLE_DICTIONARY. Admit DATA_PAGE (V1), DATA_PAGE_V2 and
DICTIONARY_PAGE only, with matching required headers; reject index/unknown page
types and repeated or out-of-order dictionary pages. V2 level-byte counts must
fit the compressed/uncompressed body before decoding. Owned bounded
Compact-Thrift/footer, page, dictionary and schema preflight is mandatory before
the upstream reader. Preflight and decode must use the same opened immutable
regular-file descriptor, with identity and size rechecked before decode. Direct
`SerializedFileReader` use on unpreflighted hostile bytes is forbidden. Count
actual decoded rows and bytes as well as declarations; mismatches reject.
Resource ceilings and reasons are in
[ADR-0145](../adrs/ADR-0145-geoparquet-upload-resource-bounds.md).

WKB supports finite 2D/3D simple geometries. Reject M/SRID extensions, invalid
nesting, trailing bytes, wrong multipart child types and malformed coordinate
counts. A collection may be decoded only within bounded converter semantics;
the four receiving workflows reject collections and null/empty geometries.
The CLI may represent an optional null geometry as JSON null, preserving row
cardinality. It rejects empty geometries and files with no nonnull geometry
because a finite observed bounding box is required. Receiving workflows reject
any null geometry before publication, even when other rows are valid.
No winding-order repair, geometry simplification or automatic validity repair
is added. Property ordering is not semantic, but feature order is preserved.

## CRS and receiving handoff

The CLI validates bounded metadata structure and emits CRS84 for absence or a
bounded PROJJSON object for an explicit known CRS. Existing shape-converter
PyProj resolves CRS and reprojects offline with longitude/latitude axis order;
no new Rust CRS dependency is proposed. Explicit null, malformed CRS, unavailable
grids or unsupported dynamic/edge semantics fail. Offline mode alone does not
prove this: binary normalization must reject ballpark transformations and missing
best-operation grids explicitly, with a regression fixture for each. Binary-source CRS is never
inferred from coordinate magnitudes. Canonical GeoJSON carries explicit EPSG:4326
at the internal receiving boundary so existing Roads inference cannot reinterpret
projected-looking longitude/latitude values. Existing direct GeoJSON CRS handling
is unchanged except the explicitly authorized receiving geometry restrictions.

## Transport and error mapping

Retain receiving URLs, multipart field names and existing response envelopes.
Add `.zip`, `.parquet`, `.geoparquet` to each existing extension allowlist. A
trusted receiving service submits bytes to the existing shape-converter HTTP
boundary; it never passes a client URL, arbitrary target path or parser options.
Shape-converter inspect/convert retain existing fields and JSON envelopes, adding
format dispatch by admitted content. Conversion for these workflows requests
GeoJSON and EPSG:4326. Existing Shapefile archive checks remain mandatory.

Stable internal failure categories are `invalid_vector`, `unsupported_vector`,
`vector_limit_exceeded`, `vector_crs_invalid`, `vector_converter_unavailable`
and `vector_conversion_timeout`. Receiving endpoints translate these into their
existing validation/unavailable envelopes and status conventions; no new RQ
response shape or auth challenge is introduced. Error messages name the failed
requirement and export action without quoting raw metadata, filesystem paths,
server exception text or submitted secrets. Invalid files must not become 500s.
An unavailable converter must not make existing direct GeoJSON uploads unavailable.

| Failure | Converter HTTP / code | Receiving HTTP |
| --- | --- | --- |
| Malformed or unsupported vector | 400 / `invalid_vector` or `unsupported_vector` | 400 in existing endpoint envelope |
| Input, decoded or output byte/count cap | 413 / `vector_limit_exceeded` | 413 in existing endpoint envelope |
| Unknown/invalid/untransformable CRS | 400 / `vector_crs_invalid` | 400 in existing endpoint envelope |
| Missing/unready parser or unreachable converter | 503 / `vector_converter_unavailable` | 503 in existing endpoint envelope |
| Parser/service deadline | 408 / existing `request_timeout` | 408 in existing endpoint envelope |
| Converter/project source digest mismatch | 502 / `vector_source_integrity_error` | 502 in existing endpoint envelope |
| Retained-attempt count/byte/free-space quota | receiving boundary does not invoke converter | 507 / `vector_retention_quota_exceeded` |

Internal `vector_conversion_timeout` maps to existing `request_timeout`; it is
not a replacement public converter code. Existing auth, scope, active-job and
multipart errors retain their existing status/code. Connection errors must be
caught narrowly; malformed converter output fails as unavailable, never as a
successful workflow upload.

## Publication, provenance and retained records

Use existing workflow staging and mutation locks. Validate the entire canonical
candidate, including workflow geometry/attributes, before changing the accepted
resource or selected input path. Never overwrite a prior accepted file merely to
learn whether a replacement is valid. After success, reload and downstream
consumers use the same canonical GeoJSON resource as before; original binary
suffixes must not leak into parser selection. No queue edges are added.

Retain normalized accepted GeoJSON in existing visible module upload/resources
paths, plus every complete within-limit original upload and a bounded
normalization receipt. Failed and hostile attempts retain the complete submitted
bytes when the receiving boundary obtained the whole file within its existing
endpoint limit. They never replace the accepted resource. Receipt paths are
`roads/vector_upload_attempts/<uuid>/normalization.json`,
`ag_fields/vector_upload_attempts/<uuid>/normalization.json`,
`_pups/omni/contrasts/vector_upload_attempts/<uuid>/normalization.json`, and
Batch `resources/vector_upload_attempts/<uuid>/normalization.json`, relative to
the owning run/batch root. These four roots and all descendants are sensitive
paths. Successful canonical paths remain `roads/roads.uploaded.geojson`,
`ag_fields/fields.WGS.geojson`, Omni's UUID upload directory with a `.geojson`
basename, and Batch's registered `resources/<safe-basename>.geojson`. Receipts
use schema `vector-normalization-v1`, server-generated attempt UUID and status
`receiving`, `source_stored`, `prepared`, `accepted`, `accepted_recovered`,
`rejected`, or `incomplete`. Each complete original is stored beside the receipt under
`original/<safe-submitted-basename>.upload`; use the canonical upload helper's
Werkzeug `secure_filename` result, limit the retained basename to 120 ASCII
bytes without splitting its extension, and reject an empty result. The terminal
`.upload` suffix
prevents established project tools from selecting a parser by the attacker-
controlled extension. The receipt preserves a bounded sanitized submitted name
and detected format so users can identify and recover their file.

Under the project-scope retention lock, create the mode-`0700` UUID directory and
atomically publish a `status=receiving` receipt with its quota reservation before
reading any source byte. Stream into an exclusive no-follow mode-`0600` partial
file while computing SHA-256 and enforcing all byte/quota/free-space limits.
Verify containment/regular-file identity, flush and fsync file/directory, rename
the complete original atomically to its `.upload` path, then atomically replace
the receipt with `status=source_stored`, complete size and SHA-256 before converter
invocation. Device/inode identity is an in-process immutability check, not portable
receipt provenance. Omit client media type rather than retaining attacker-
controlled text. A receipt cannot claim a source hash until the whole within-
limit file is stored. If the upload exceeds its endpoint limit,
remove the partial file and retain only an `oversize_not_retained` receipt with
the measured lower-bound byte count; never label a prefix digest as the original
SHA-256. Authentication, multipart or routing failures before an authorized
project attempt exists remain ordinary request/security logs rather than project
artifacts.

The receipt contains only bounded data fields: attempt ID and UTC timestamps;
workflow and run/batch identity; outcome and enforcement stage; source relative
path, sanitized submitted name, detected format, complete byte size and SHA-256;
canonical relative path, size and SHA-256 when
present; converter request/correlation ID; stable error ID/code; parser binary
name/version/SHA-256, exact Cargo.lock SHA-256 and source revision; and a
server-authoritative actor object. For a human actor, record only `kind=human`
and the canonical positive account user ID resolved after authentication. For a
registered service/MCP actor, record its bounded verified subject and kind. Do
not persist tokens, cookies, session IDs, roles, raw JWT claims, submitted paths,
untrusted metadata values or client IP addresses in project artifacts.

Shape-converter computes `source_size` and `source_sha256` from its own complete
request snapshot and returns them in the strict response. The receiver streams
from its already-open verified project descriptor, rechecks descriptor identity
and size before and after transfer, and rejects with a stable converter-integrity
error unless converter size/digest exactly match the project original. Digest
comparison occurs before receiving validation, accepted publication or terminal
accepted receipt.

If parsing/normalization fails before canonical output, there is no canonical
hash/size. If normalization succeeds but receiving validation fails, retain the
bounded normalized work product as
`candidate.geojson` beside the attempt receipt, with its hash/size and rejection
code. It remains inspectable/archivable but must never replace the accepted
resource or be reused automatically.

Attempt publication is recoverable state, not a cross-file transaction. After
conversion and receiving validation, atomically write `status=prepared` with all
source/candidate/provenance hashes
before accepted-resource mutation. Recheck lock ownership, perform the existing
workflow mutation, then atomically replace the receipt with terminal `accepted`.
Rejections atomically become terminal `rejected` without workflow mutation. On
recovery, a receiving/source_stored/prepared receipt is never parsed or retried.
A receiving receipt found after acquiring the expired/released scope lock is
stale: retain its partial file under the sensitive root, mark it `incomplete` with
`source_complete=false`, measured partial size and no source SHA-256, and release
its reservation. An unexpected UUID directory without a valid receipt is counted
against quota, classified `incomplete/corrupt_attempt`, and never parsed; root
repair must create a bounded terminal receipt or remove the entire directory.
If receipt creation failed before any source byte was read, remove the empty UUID
directory. For source_stored/prepared recovery, compare exact canonical hashes
and authoritative state under the lock. Mark unambiguous committed state
`accepted_recovered`, otherwise `incomplete`, retaining all evidence and reporting
uncertainty. A workflow without a read-only authoritative recovery adapter must
take the conservative branch directly and retain `incomplete`; canonical file
existence or hash alone is never acceptance evidence. Any
original/source_stored/prepared receipt persistence failure stops
before accepted-resource mutation.

Retention uses the accepted count/byte/free-space limits and 600-second project-
scope lock in ADR-0145. One run-scope lock covers all three run workflows; Batch
uses its project scope. Quota accounting includes working reservations, originals,
receipts, candidates and private sensitive archives. Exhaustion returns
`507 vector_retention_quota_exceeded` before converter work and preserves older
evidence and accepted state. No automatic expiry or eviction is allowed. Omni contrast clear/rebuild/stale-run
cleanup preserves both `_uploads` and `vector_upload_attempts` byte-for-byte;
retained attempts are project records, never generated contrast workspaces. A root
operator may export then remove only an entire terminal attempt/private archive
under the same lock; deletion is explicitly audited and partial provenance
deletion is forbidden.

Before that project lock and before any source/archive byte is read, acquire an
owner-bound 600-second reservation from ADR-0145's existing-Redis filesystem
ledger. The atomic reservation composes committed and worst-case reserved bytes
across every run and Batch project, the verified actor or shared-unattributed
bucket, and the in-flight ceiling. It is keyed by an operator-configured canonical
run-filesystem ID rather than container-local device numbers. Missing/mismatched
configuration, Redis failure, corrupt accounting or inability to verify free
space fails closed. Commit exact descriptor-verified bytes atomically at terminal
publication; release pre-write failures atomically; retain uncertain charges
until receipt/file recovery reconciles them. The ledger stores only bounded
aggregate counters, opaque reservation UUIDs and verified account/service IDs;
the unattributed bucket is shared and creates no anonymous identity record.

Reservation records do not expire while their aggregate charge remains active.
The operator reconciliation command takes a filesystem-wide owner lock that
blocks new reservations, bounds reservation and receipt scans to 10,000 entries,
and never parses retained payloads. Stale pre-write reservations are released
only when no attempt was bound. Bound attempts are terminalized from receipt and
descriptor/hash readback as `accepted_recovered`, `incomplete`, or
`corrupt_attempt`, then charged by measured regular-file bytes. Audit is the
default; mutation requires `--apply`. The same command can rebuild committed
totals from terminal `vector-normalization-v1` receipts after Redis loss or
project deletion. A rebuild snapshots and preserves unrelated active
reservation/principal charges while recomputing committed bytes; it refuses
unverifiable active state, symlinks, corrupt or nonterminal receipts, and
over-bound inventories. Only the exact configured filesystem root may rebuild
the global ledger.

Before run or whole-Batch project deletion, private-archive deletion, or
destructive private archive restoration, validate the configured identity and
exact filesystem root before changing project state. Reject symlink deletion
targets and obligation directories. Acquire global maintenance before project
scopes; whole-Batch deletion also fences its generated child-run upload scopes.
Persist a deterministic mode-private rebuild obligation
under the configured filesystem root and mirror its identity in the existing
Redis ledger. New reservations and activation readiness fail closed while any
obligation is pending. Perform deletion/restoration and the exact-root rebuild
under the project scope, verify ledger readback, then fsync removal of the file
marker before clearing the Redis marker. Retry uses the identical operation and
globally qualified target identity even when the target is already absent.
An absent retry still fsyncs the target parent before accounting repair. Recheck
all owned leases after reconciliation and before clearing obligations. An unrelated
destructive operation must wait for every pending repair, so parent deletion cannot
remove the workspace required by an earlier archive/child retry. Identical
operation/target retries remain admitted from either marker authority; failures
retain repair authority. A failed obligation write may have already replaced its
file, so it never rolls back the Redis obligation on a persistence error.
Operators must never edit Redis counters or remove only part of an
attempt/private archive.

Binary activation is independent of direct GeoJSON admission.
`VECTOR_UPLOAD_BINARY_ENABLED` defaults false; when false the server rejects
ZIP/Parquet before converter work and browser file pickers advertise only
GeoJSON. Disabling this flag is the immediate binary rollback and leaves direct
GeoJSON receiving, provenance, and validation intact.

## Sharing, copies, and existing workspace resets

Operator decision (2026-11-17): making a project public or granting team access
permits users admitted by the existing fork/copy workflow to inherit its upload
originals, rejected/failed attempts, receipts, and private archives. The source
owner is responsible for that sharing choice. Preserve ordinary public/team
forking and destination ownership; do not remove these records from copies or
add a separate source-owner approval. This is an explicit copy-boundary exception
to the direct sensitive-download restrictions below, which remain unchanged.
The rejected alternative was source-only evidence with restricted copies; it
would contradict the operator's intended project-sharing semantics.

Copies preserve original bytes, source SHA-256, upload actor and attempt identity.
A copied normalization receipt remains provenance of the source upload, not a new
receiving/conversion event. Preserve source project identity in that receipt;
existing fork/Batch metadata identifies the derived project. Copies count their
physical retained bytes against the configured run-filesystem ledger and the
verified copying principal's bucket (the existing unattributed bucket for an
automated/legacy caller without a verified principal). Original upload `actor`
remains immutable provenance; additive `retention_actor` identifies who incurs
the new storage charge. A bounded copy-source receipt/hash records inheritance
without presenting it as a new upload. No synthetic upload event or new identity
store is required. Before a managed copy, measure complete terminal source
receipts under source/destination scopes and enforce the existing byte/free-space
ceilings including active reservations. Admit new physical bytes before copying;
verify exact ledger totals after the copy. Nonterminal/corrupt source evidence
requires reconciliation rather than silently omitting it. A reconciled terminal
`incomplete` attempt remains a valid retained record and can be copied.

Existing explicit whole-workspace replacement/reset operations retain their
established semantics, including selected Batch reruns and generated-child
removal. They use the same global-before-project fence and durable repair
obligation as deletion, then reconcile actual retained bytes, including renamed
stale workspaces left by deferred cleanup. Interrupted copy/reset blocks new
admission until its exact identity is repaired. Normal generated cleanup must
still preserve the owning project's retained-attempt roots.

The ledger governs only its exact configured run-filesystem root. Operator-owned
profile data-repository promotion and offline exports outside that root remain
ordinary byte-preserving exports governed by their storage owner; they are not
charged as bytes on the run filesystem. Established profile execution/fork roots outside the configured ledger root
likewise remain on their existing storage. Both configured root and identity
must be present to establish that boundary; missing settings are not evidence
of external storage. Copying records back into a run/sandbox within the ledger
root is a managed admission and must pass the same accounting boundary.
This distinction does not change mounts, roots, service identities, or profile
execution configuration. The known offline-export call sites explicitly identify
their export boundary; missing retention configuration must never silently
classify a managed destination as an export. Legacy projects with no retained
evidence remain valid.

Replacement admission includes all currently committed and reserved bytes plus
the incoming copy, without speculative credit for destination deletion. Deferred
cleanup can retain the old workspace, so peak retained storage must fit the same
existing ceilings. The exact retry carries known tombstone/stale paths into
configuration checks even when the original destination is absent. Ordinary
model symlinks may remain links, but copies cannot materialize retained evidence
through a symlink ancestor. Missing copied receipts leave a repair obligation.

An Omni workflow that already owns its renewable project scope may lend that
scope to the helper. Global maintenance acquisition is nonblocking; contention
fails before filesystem work, avoiding a lock-order wait cycle. Borrowed scopes
remain owned by their original workflow and active reservations survive rebuild.

Parent copies, resets, deletion and archive restoration fence existing child
upload reservations as well as the named parent scope. While holding global
maintenance, discover reservation scopes by composite project identity and bound
attempt path; this covers the interval before an attempt directory is created.
An active child upload blocks the parent mutation before any original is removed.
Copies also include outstanding reserved bytes in the free-space check.

After a failed fork worker copy, the authorized API replacement finishes the
exact destination's `fork_copy` cleanup/rebuild obligation before enqueueing a
new copy. It cannot consume an unrelated repair identity. Files, containing
directories, linking ancestors and retained stale trees are synced before the
ledger rebuild and marker clearance.
## Hostile-file quarantine and abuse review

Every rejected complete original is classified `quarantined` in its receipt.
Accepted originals remain `retained`; neither classification grants execution or
parser authority. Attempt directories are mode `0700` and original files mode
`0600` under the existing service identity. All attempt artifacts remain visible
only to an explicitly authorized project owner or root/operator through established
project browse and download tools and are included byte-for-byte with their modes
in the normal owner-authorized archive/restore workflow. Batch uses its existing
project/group membership authority. A registered service/MCP principal is allowed
only when its verified scope and existing governance confer that same run/Batch
sensitive-evidence authority.

The four exact `vector_upload_attempts` roots are protected by one shared path-
segment classifier that normalizes separators and Unicode, resolves containment
without following symlinks, and rejects case/encoding aliases. Apply it to HTML/
JSON browse trees, direct download, files/report/schema endpoints, D-Tale, GDAL
info, diff and other representations, `aria2c.spec`, Batch/group equivalents,
symlink/materialization helpers and future tool dispatch. Anonymous public
browsing, inventory, download and archive access must not expose a sensitive root
or descendant. Original `.upload`
files are download-only: serve `application/octet-stream` with attachment and
`X-Content-Type-Options: nosniff`; disable inline preview, schema inspection,
Parquet-to-CSV/filtering, D-Tale, GDAL information, archive expansion and every
other server-side interpretation. Restoration preserves quarantine state and
cannot enqueue, normalize or accept a retained file. A deliberate retry is a new
user upload/new attempt and runs every admission and parser control again.

After the shared sensitive-path classifier matches, every entry point invokes
one `authorize_sensitive_vector_artifact` predicate. For runs it requires the
verified current project owner or root and deliberately bypasses the ordinary
public-run branch that admits any authenticated user. For Batch it requires the
existing authorized project/group member or root. A generic logged-in identity,
knowledge of a public run ID, and ordinary public-read authorization are never
sufficient. Denial occurs before listing names, stat metadata, archive sidecars
or bytes. Tests use a valid non-owner account against a public run and require
denial across browse, direct download, files/report/schema, `aria2c.spec`, every
tool dispatch, symlink/materialization and `archives/private` paths.

An owner archive containing any sensitive root is stored under
`archives/private/`, accompanied by a mode-`0600` sensitivity sidecar that binds
the archive SHA-256 and `contains_vector_upload_attempts=true`. The shared
sensitive classifier denies that archive/sidecar to anonymous public-run access
even if live attempts are later removed or the archive is restored. Archive
creation uses the retention lock, aggregate archive/total-evidence quotas and
free-space preflight. Direct public archive downloads remain restricted. Authorized forks and copies
follow the explicit sharing exception above and retain the same project records.

Receipts support abuse investigation by correlating stable error/correlation IDs,
source SHA-256 and verified actor identity without opening the hostile file. For
each complete quarantined upload, emit one bounded structured operational event
`vector_upload_security_event_v1` containing only attempt ID, run/Batch identity,
verified actor kind/account ID or registered subject, source SHA-256/size, stable
error/correlation IDs and enforcement stage. Exclude filenames, tokens, sessions,
raw claims, roles, metadata and client IP. Operational event retention follows
existing logging policy; project evidence lasts only for the project/archive
lifetime. Neither is represented as permanent ban evidence.

These records provide evidence for a human operator to use existing account-
access governance. This package adds no automatic ban, IP blacklist, cross-
project surveillance store or authorization change. Any future automated
suspension or new ban mechanism requires a separate access-governance contract,
audit trail and operator authorization. Anonymous actors cannot be attributed to
an account; trusted-proxy operational logs remain the authority for network-abuse
review and must not be copied into project receipts.

Archive restoration must preserve original, candidate, canonical and receipt
bytes, modes and hashes. Browse/download tests must prove owner/root access,
public denial and download-only handling. Saved legacy projects remain readable
without new receipts.

## Specification references

Format details are checked against the [GeoParquet 1.1 specification](https://geoparquet.org/releases/v1.1.0/)
and [Apache Parquet file format](https://parquet.apache.org/docs/file-format/).
The bounded profile above is intentionally narrower than the full formats.
