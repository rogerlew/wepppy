# Features-export content identity checkpoint

Starting revision `dd5d09ca7` with reviewed runtime waves still in the working
tree. Owner authorized package execution and confirmed consumer fixes.
Canonical authorities: features_export/specification File-content cache identity
amendment and Cache Key Rules, file-dependency-freshness-contract,
rq-response-contract and artifact-observability-standard. No enqueue wiring or
new access authority; no numerical formula/default change.

## Confirmed failure and decision

`features_export_baseline_probe.py` exercises actual catalog planning,
materialization, ZIP writing, manifest and cache reuse on disposable GeoJSON/
parquet. Only catalog selection is injected, using the existing test catalog.
Revision2 evidence: source value25 becomes75 with equal byte size/restored mtime;
second export reports cache_hit=true and its real parquet member still contains25.
Retain the first probe's mistaken API-name failure as diagnostic evidence.

Service preparation will request existing sha256 mode. Low-level metadata mode
remains available explicitly, preserving its existing API default. Hash each
regular dependency with the shared verified helper; validate metadata around
the read. Fingerprint valid SHA entries using existing provenance/size/hash but
exclude diagnostic mtime. Never exclude metadata for malformed/incomplete hashes.
No new persisted entry keys or removed keys are required; mtime stays observable.

Add one bounded post-materialization snapshot comparison before cache-index
publication. On conflict/read error, retain the candidate artifact files and
artifact/job manifests marked by additive dependency_verification information,
raise changed_source409, and preserve all prior cache/artifact bindings. Existing
RQ worker exception/failed-job handling remains. Successful bundles include the
verified record. No silent retry, source repair or deletion.

## Compatibility and regression plan

- Newly content-keyed submissions miss old metadata cache keys and rebuild.
  Do not rewrite old manifests or infer accepted historical hashes.
- Existing job and published download bindings remain retrievable under their
  unchanged contracts. Cache-index version1 and manifest version remain.
- Present empty regular files hash normally; existing numeric/vector reader
  validation still determines whether they form valid source data.
- Absent optional entries stay explicit; absent required source fails the
  established materialization contract. A source disappearing during collection
  produces changed_source and no new reusable binding.
- Directory-backed dependencies keep their honest metadata-only record. Indirect
  vector/raster/directory closure remains a package blocker; this wave does not
  silently reject formats or claim that catalog main files are all native inputs.
- Same-byte touch/link/restore reuses the content cache. Equal-size/restored-time
  changed bytes yield a new ZIP with changed actual values. Settings, source
  path, catalog and Unitizer changes retain existing invalidation behavior.
- Concurrent source change during materialization fails before cache publication;
  prior exact artifact bytes/index survive. Retained failed candidate manifests
  are visibly rejected/error, browsable and archivable.

## Performance and evidence

This is submission/materialization work, not status polling. Reuse the already
reviewed file-digest cache; no new cache, watcher, dependency or datastore.
Measure the real representative existing export dependency set (24 entries,
9.3MB before deduplication) and compare cold/settled costs; require no settled
content rereads and cold cost within2x the sum of measured per-file hashing cost
plus existing resolver work. The real service probe measures correctness, not
large-export throughput. Large-source/full runtime and archive acceptance remain.

Regression checks cover actual generated ZIP values, cache miss/hit behavior,
legacy explicit metadata mode, malformed hash handling, complete manifest
propagation, failed publication retention and existing published retrieval.
Independent correctness/security reviews and docs-only ancestor commit precede
code/tests. Promote durable decisions in the canonical specification above.

## Review amendment: companion and publication bindings

Independent native OpenFileGDB probe confirmed old GeoPackage value25 is
converted and cached under current source75 identity, then reused with old25.
Include this second publication path in this wave. Before conversion require
verified producer content manifest plus artifact-matching cache binding equal
to the current GeoPackage request key (Unitizer/version inputs included), and
current companion snapshot equality. Compare normalized requests except format.
After conversion recheck snapshot/request identity before cache insertion.
Retain failed candidate files and a companion verification manifest. Missing
legacy proof fails changed_source409 without upgrading historical metadata.
Normal dual-format export creates the verified producer first; historical
job/published downloads retain their contracts. Canonical amendment records why
arbitrary historical key transformation is impossible from incomplete settings.

Publication registry entries instead take identity from the actual matching
artifact cache binding and validate format, never today's source observations.
No matching valid binding uses existing stale_publication error. Initial hash
read errors use changed_source409; no metadata fallback. Verdict precedes all
success manifests, README and ZIP packaging; failed artifact/job manifests share
the rejected/error verdict. Cache-hit job observations may differ from immutable
producer metadata while retaining accepted content identity (§11.3).

Regression adds actual native companion conversion after a source change,
normal same-source dual-format success, Unitizer/version mismatch, missing legacy
proof rejection, and publication identity after source changes. No existing
historical artifact/index entries are deleted or rewritten to manufacture proof.

Companion attempts use distinct artifact directories, preserving prior accepted
ZIPs and source manifests even on post-conversion rejection. Successful native
GDB ZIPs add companion manifest/README alongside the existing GDB tree; cache
and result manifest references point at companion provenance. This additive
packaging closes the existing companion provenance omission without changing
the GDB payload or its download filename.

For dual-profile publication, verify/create the companion before updating either
registry profile. A changed-source conversion failure preserves both previous
published bindings; no new cross-file transaction is introduced. Independent
ENOSPC retention probe reproduced deletion of the accepted9,760-byte ZIP under
the old same-directory retry; isolated candidate storage addresses that defect.

## Implementation evidence (checkpoint 90a8a3dc9)

Six actual export/native regressions pass; the affected service/planner/writer/
RQ/route set passes195 tests. A subsequent13-test native retention set also
passes, including failure inside the real converter's archive step. The old
synthetic companion fixture had no producer cache or manifest proof; it now
asserts legacy-proof rejection, while real dual-profile success/retention is
covered by `test_features_export_freshness.py`.

The first performance script compared full service preparation/recheck against
only the low-level dependency resolver and hashing, omitting existing catalog,
plan and Unitizer preparation. Retain its failed budget assertion. Revision2
measures the actual metadata-mode preparation through the same service with only
hash mode disabled:0.2141s. Cold content preparation plus verification is0.2745s,
within the ratified2x hashing-plus-existing-preparation budget0.4996s. Settled
preparation/recheck is0.2255s with zero digest misses across ten iterations.
Actual representative24 entries/14 unique files; no source mutation performed.
Native large/export runtime and archive acceptance remain open.
