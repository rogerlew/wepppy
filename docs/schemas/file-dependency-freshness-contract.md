# File dependency freshness contract

Status: accepted first-wave checkpoint; implementation pending (2026-09-17 UTC).

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
before and after reading. Replacement or concurrent mutation fails explicitly;
a failed read is never cached. Validate containment using the existing domain
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

## Timestamp-quantum cache admission amendment (accepted; implementation pending)

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
