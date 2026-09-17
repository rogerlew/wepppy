# File dependency freshness contract

Status: implemented bounded contracts (2026-09-17 UTC); full runtime acceptance is tracked in the file-dependency-freshness work package.

## Identity obligations

A consumer must distinguish content equivalence, source/configuration provenance,
cache revalidation hints, completion order and coherent read/publication identity.
For content-equivalence decisions, unchanged raw bytes remain equivalent after
hard-link creation/removal, touch, chmod or same-byte replacement. Changed bytes
remain different after an equal-size rewrite with restored mtime. A digest never
authorizes a path or substitutes for coherent input acquisition or owner checks.
Raw bytes are the default only for the explicitly adopted consumers below;
SQLite logical snapshots retain their domain contract. This contract does not
retroactively change every timestamp-based cache or completion receipt.

## Post-fire adoption: first implementation wave

Applies to `production.sources`, accepted upload/result currentness,
`artifacts_current`, and the rq-engine accepted-file download. Paths, settings,
owner receipts, model/frequency selection, sidecar inventories, tool/engine
identity and M3 soil snapshot obligations retain their existing authority.
Only ordinary source-file and artifact content comparisons adopt this wave.

New source snapshots retain existing `files` stat records and add
`content_sha256`, keyed by exactly the same source names (null for absent input).
Currentness compares the complete inventory, relative paths, sizes, content
hashes and unchanged selections. It ignores timestamps only when both snapshots
carry complete valid hashes. Legacy snapshots without hashes remain subject to
exact stat comparison; metadata drift stays stale, never acquires a fabricated
acceptance-time digest. Malformed/incomplete new maps are stale. Empty and absent
optional dependencies remain distinct. New optional fields are additive.

Accepted artifacts retain `[relative_path, size, mtime_ns, ctime_ns, sha256]`.
Strong checks verify accepted path, size and digest; metadata churn alone does
not invalidate a hashed artifact. Cheap checks reuse a validated digest only
under the cache identity below. Hashless legacy records retain exact metadata
checks; they cannot gain content-equivalence treatment. Downloads require the
accepted SHA-256 and the same opened regular-file handle through verification
and streaming; use existing `rainfall_io.open_local` component-wise no-follow
admission (or equivalent), not a pathname check followed by ordinary open.
Old hashless records are unavailable for download.

The `strong=False` artifact check currently serves both state and locked
finalizers. Implementation must distinguish these callers explicitly: changing
accepted-currentness equality must not silently broaden finalizer acceptance.
Locked finalizers retain strict recorded stat/generation checks, and execution
boundary full hashes remain uncached.

Workers still compare strict snapshots at admission and locked publication and
perform full before/after hashes outside the lock. Metadata churn during a build
may supersede that attempt; this conservative coherent-publication rule is
separate from the content-currentness of already accepted output. Never strip
metadata from rollback ownership, SQLite main/WAL or descriptor race guards.

## Cached digest and read coherence

Reuse the existing bounded in-process digest cache with a 512-entry bound
(two measured representative M3 working sets exceed the old 64-entry bound). Cache keys include absolute
path, device, inode, size, nanosecond mtime and ctime. A cache miss hashes one
opened regular-file descriptor and checks descriptor and pathname identity
before and after reading. Observable descriptor/path generation or byte-count drift fails explicitly;
a failed read is never cached. A complete uncached read observes bytes at a
point during the call; a same-quantum write after its last byte may leave that
coherent earlier observation valid. The next observation rehashes during the
admission interval. This is not arbitrary-writer snapshot isolation: existing
immutable accepted-artifact and worker locking/before-after content checks
remain the publication boundary. Validate containment using the existing domain
path checks on every access. Access loss must fail even on a cached hash.

These cache hints assume normal filesystem metadata semantics, not a hostile
privileged writer capable of restoring ctime/inode identity. Filesystem trust
and existing path authorization remain unchanged. The initial assumption that every equal-size restored-mtime write changes
ctime was refuted during execution; the timestamp-quantum admission amendment
below is required.
Ordinary warm reads must not reread unchanged raster bytes; cache eviction or
metadata changes permit revalidation. No watcher or persistent hash database.

## Compatibility, rollback and observability

Existing accepted values and attempt files are never rewritten by state reads.
Legacy metadata drift requires a normal explicit rerun; no migration can prove
historical content from current bytes alone. The current numerical-engine
fingerprint includes production code, so old results can be stale after this
release independently of the file-comparison fix. Reports/downloads retain
validated historical values. Do not rewrite engine identities to conceal this.

Old readers encounter additional source snapshot keys as a strict inequality,
so rollback conservatively marks new results stale. Four/five-element artifact
records remain readable. Retain attempt artifacts, diagnostics and original
NoDb snapshots in normal browse/archive paths; no archive exclusions or hidden
cache artifacts are introduced. Development acceptance must rebuild/restart,
exercise real UI/RQ/WEPP on disposable projects, and test archive restoration.

## Further consumers

The executing package inventories non-postfire consumers separately. Each needs
its own owner-contract amendment, compatibility decision, failing baseline and
reviewed checkpoint before adopting this behavior. Unresolved confirmed defects
block repository-wide package completion; first-wave completion is not closure.

## Timestamp-quantum cache admission amendment (implemented)

Real rapid rewrites demonstrated identical complete stat keys with different
bytes on the development filesystems. The immediate-reuse assumption above is
therefore insufficient. Per the
[cache-admission ADR](../adrs/20260917-file-digest-cache-admission.md), a newly
observed path/version must remain uncached for a one-second monotonic observation
interval. Afterward, admit only a freshly computed digest, never one retained
from the observation interval. Keep a bounded 512-entry observation LRU;
eviction restarts this interval and uncached verification. Warm zero-byte-read
acceptance applies after admission. The original rapid-rewrite probe must pass
without sleeps or mocked filesystem timestamps. Coherent metadata-on-open remains
a filesystem requirement; NFS acceptance must be measured on disposable runs.

## Controller bundle header identity (implemented)

The expected controller build ID is the `Build date:` value read from the
current on-disk bundle header, scanning at most the existing 80 lines. It MUST
NOT be reused solely because pathname, size and mtime match a prior read.
Missing, unreadable or headerless files retain the existing unknown (`None`)
behavior; unknown identity MUST NOT alone trigger the stale-client banner.
A complete earlier header observed during atomic replacement remains a valid
point-in-time read. The next lookup reads the current path again.

Read the small header on each lookup. A full-bundle digest or persistent cache
would cost more and provide no needed identity: the generated header is the
existing UI contract. Same-size/restored-time deployments must expose the new
header without restarting the reading process. Header format, asset path,
served-file alignment, client comparison and authorization remain unchanged.

## Shared ordinary-file digest reuse (implemented)

Ordinary local-file SHA-256 consumers MAY use one owned helper for verified,
bounded reads and the observation-guarded cache specified by the digest-cache
admission ADR. Cache reuse requires the complete device/inode/size/mtime/ctime
version, fresh read access and descriptor/path agreement on every call. A
changed version restarts admission; a failed read never supplies a digest.
Return the digest of actual bytes, not an empty substitute, and raise an explicit
`OSError` on observable read/version drift. Missing and access failures retain
their original filesystem exception. Reuse MUST NOT add path authority: existing
caller containment, symlink, execute-access and authorization policies still run.
This helper follows ordinary symlinks where callers already permit them; it is
not a replacement for post-fire's project-local no-follow opener.

Apply this to output-discovery export SHA-256 and project-config executable
identity. The former MUST NOT return an old digest after an equal-size/restored-
mtime export rewrite; caller-provided size/mtime are consistency expectations,
not permission to reuse a hash. Check those expectations against the verified
read observation or both before and after the helper call, so a wrapper precheck
cannot pair old advertised metadata with a new digest. A mismatch leaves the artifact unavailable via
its existing best-effort discovery boundary. Executable identity retains its
required read/execute checks and RegistryError translation. Same-content
metadata churn retains the same SHA-256. No persisted key, response schema,
executable selection or route access rule changes.

The helper's reusable cache and observation records each have the same bounded
512-entry capacity and 1-second admission interval already ratified in
`docs/adrs/20260917-file-digest-cache-admission.md`. Keep cold/changed reads
explicitly distinct from settled warm reads in validation. Introducing a
shared helper is justified by reproduced stale output digests and the existing
executable digest consumer using the same defective metadata shortcut; no
watcher, daemon, datastore, dependency or new deployment topology is authorized.

## D-Tale dataset generations (implemented)

D-Tale loader and GeoJSON registration fingerprints MUST identify current
ordinary-file bytes with the shared verified SHA-256 helper. Keep dataset IDs,
run/config/filter partitioning, authentication, containment, NoDir materialization,
limits, identifier aliases and supported readers unchanged. Same-byte metadata
changes may reuse a dataset; changed bytes require refresh even when size and
mtime are restored. Reuse also requires the same resolved source path; a
same-byte symlink retarget must rebuild the lazy reader against its new path.
No persisted cache or deployment topology is added.

Bind eager data, lazy schema/sample/count and registered GeoJSON to the observed
fingerprint by checking before and after acquisition. Observable content drift
or loss of read access must not publish a dataset tagged with an unrelated
fingerprint. Failed initialization removes partial dataset state; it does not
silently reuse old rows as current. An absent optional GeoJSON remains optional;
a later registration must not reuse a prior overlay after its file disappears.
Optional overlay parse/read failures, absent controller state and absent paths
retain table-launch availability: remove the affected old registration and map
choice/default references instead of blocking the table or retaining stale maps.
Already materialized eager datasets remain point-in-time views until relaunched.

A lazy Parquet instance retains the accepted content fingerprint. Check it before
and after each filesystem-backed count/page query, and before returning cached
counts or samples. If the current file differs or cannot be verified, fail
explicitly with `changed_source` and a message to reopen the dataset
from browse; do not mix an old schema/count with new rows, silently refresh a
schema under an existing grid, or load the entire file into pandas. Recheck observations on query failure as well as success: a detected generation
change takes the changed-source path even if the native query raised first. A
stable-generation parser/query failure retains its original error. The internal
loader returns HTTP409 with `error.code="changed_source"`, `error.message` and a
matching `description` on acquisition drift. The lazy grid endpoint follows
upstream D-Tale's HTTP200 error envelope: `success=false`, top-level string
`error` with reopen guidance, and `code="changed_source"`, without successful
row data. Upstream grid transport drops non-2xx bodies; this envelope preserves
visible error feedback without adding a frontend transport patch. Other reader/filter errors
retain their established contracts. The next normal launch rebuilds the same
stable dataset ID from current bytes. This explicit relaunch resets the shared
server dataset; other open tabs using that ID may also need to reopen. The
no-silent-refresh rule applies to lazy page reads, not per-browser generation
isolation or a new version-token protocol. Metadata-only changes remain harmless.
This is bounded before/after observation under existing producer assumptions,
not arbitrary concurrent-writer snapshot isolation.

The rationale for explicit lazy invalidation is that grid columns, filters,
counts and page queries share one schema generation, while the lazy backend
reopens its path per query. Reopening through browse recompiles filters and
rebuilds the shell consistently. Preserve the same `pqf` partition on relaunch
and recompile against the new schema; an invalidated field remains a422 filter
error, never silently drops the filter or reuses the old shell. Settled fingerprint checks must perform no
content rereads and meet the existing sub-millisecond per-file digest budget;
cold/changed loads may hash their source. Retain bounded DuckDB/PyArrow paging
and upstream non-lazy endpoint delegation. Verify launch/page error presentation
with the actual D-Tale UI, including same-schema and changed-schema source edits.
