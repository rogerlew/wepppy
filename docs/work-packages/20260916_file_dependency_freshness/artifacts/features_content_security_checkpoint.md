# Features export content identity security checkpoint

Independent review by `freshness_security`, 2026-09-17 UTC. Reviewed the proposed
`features_content_contract_decision.md`, the canonical features-export
specification and current service/dependency/manifest/download implementations.
No production or test files were changed by this reviewer.

## Findings and disposition

**PASS for the revised bounded checkpoint, including companion/publication
identity.** Reviewed the final working-tree amendment after `edff4db5a`.
Implementation and runtime approval remain pending. Confirmed defects below
require implementation closure; this pass accepts their specified remedies.

- **FE-S01, Low, resolved in contract:** section 11.3 originally allowed cache-hit
  job manifests to differ only in `cache_hit`/`source_job_id`. The revised clause
  explicitly separates new selection observations from immutable producer
  provenance, preserving same-byte reuse without rewriting original ZIP/README
  diagnostics. The final amendment also settles the verification verdict before
  success manifests, README and ZIP packaging and defines matching failure
  verdicts in artifact/job manifests.
- **FE-C01, High, implementation OPEN:** the correctness review's native probe
  confirms old GeoPackage data is attributed to today's different input key.
  The revised checkpoint requires accepted producer proof, matching request
  identity and before/after verification; see the companion section below.
- **FE-S02, Medium, implementation OPEN:** repeated companion conversion removes
  an accepted ZIP before the native call. An injected converter failure leaves
  the previous cache entry pointing at a missing file. The revised contract
  requires distinct visible candidate directories and forbids prior-artifact
  overwrite/deletion. The independent real-file probe below establishes this
  retention defect and supplies the implementation regression condition.

## Confirmed failure and bounded correction

`features_export_baseline_probe.py` and its `revision2.json` result exercise the
actual planner, materializer, ZIP writer, manifest and cache. Only catalog
selection uses an existing test fixture. A valid parquet value changes from
25 to 75 with equal size and restored mtime. Both submissions produce the same
cache key; the second returns `cache_hit=true`, the original artifact ID, and
an actual ZIP parquet member still containing 25. The initial mistaken API-name
probe failure remains retained separately. No named project was changed.

Today `prepare_export_submission` uses `build_dependency_snapshot` without
SHA mode. `dependency_fingerprint` serializes all entry mappings, including
mtime. Opting the service into its existing SHA mode and excluding mtime only
for valid SHA entries repairs the demonstrated false-current path and permits
same-byte restoration/touch reuse. Keep path, role, layer/output-layer and
dependency identifiers, presence, size and catalog signature in identity.
Request normalization, concrete SWAT selection, conversion/export versions and
project Unitizer preferences remain independent cache inputs.

The metadata-only low-level default remains available. Existing missing entries
and directories must retain their explicit metadata representation; no synthetic
empty digest, blanket regular-file restriction or inferred historical hash is
authorized. Malformed/incomplete hashes cannot qualify for metadata omission.
New keys may miss old metadata keys and generate new artifacts, while old index
entries and historical artifact bindings remain readable.

## Access, errors and coherence

`dependency_tracker._normalize_relpath` enforces the existing run/allowed parent
run roots. Preserve valid canonical Omni child dependencies and allowed ordinary
symlinks. The shared helper follows ordinary filesystem semantics and checks
current read access even on admitted cache hits; it is not a replacement path
authorization mechanism. No new source writes, permissions, source preparation,
fallback dependency resolution or network access is part of this checkpoint.

Capture dependency metadata around the verified read; a precheck alone cannot
bind a returned digest to the recorded metadata. A disappearance or read error
during collection must become explicit `changed_source` failure rather than a
metadata-only fallback. An initially absent optional input retains its existing
state; a required absent input still fails the existing materialization rules.
Do not silently substitute a previous digest, retry an export, or repair inputs.

Recollect the same resolved catalog/plan dependency set after materialization.
On mismatch or read failure, preserve prior reusable/publication bindings,
retain the candidate records, and raise the specified 409 service error through
the existing RQ exception boundary. A before/after comparison is observation of
agreement, not a multi-file transaction or isolation from arbitrary writers.
The already reviewed helper's timestamp/coherent-filesystem assumptions still
apply. The proposal correctly leaves nested raster/vector/directory closure
open; main-file SHA alone cannot certify all bytes consumed by native readers.

## Retention and historical retrieval

`_run_cache_miss_export` already allocates visible unique artifact directories
under `export/features/artifacts/<artifact_id>`, with job metadata under
`export/features/jobs/<job_id>`. Retain useful failed payloads and manifests in
those established locations and clearly label the verdict. Do not remove the
only useful writer output while reporting a verification conflict.

`export_routes.export_features_download` checks access, job/run association and
`status == finished` before resolving artifact manifests. The RQ worker reraises
service failures and does not stamp completion on failure. Therefore retaining
failed candidate manifests does not authorize them as completed exports;
project browsing/archive visibility remains required. Historical job and
published artifact retrieval must not acquire a current-source freshness gate.
Cache-hit selection uses the initial verified dependency observation and the
existing immutable artifact, with later changes handled by later submissions.

## Companion and publication scope review

The correctness review's `features_companion_baseline_probe.py/.json/.log`
uses real GeoPackage and OpenFileGDB writers, conversion, cache lookup and OGR
readback. Source value 25 is exported, then changed to 75 with a different key.
Current `co_create_post_wepp_geodatabase_artifact` converts old 25 and inserts it
under today's 75 key; a later export hits that entry and reads 25. Hashing more
accurately cannot fix this attribution error. The companion cache writer must
participate in this wave or remain an explicit unresolved package blocker.

The final amendment binds conversion to the artifact's accepted verified
manifest and matching cache entry. It checks the corresponding current source
GeoPackage request key, including Unitizer and version inputs, and requires
normalized producer/companion requests to agree except format. Both plans use
the same catalog. Current companion dependencies must equal accepted producer
dependencies; request and dependency identity are checked again after conversion.
These checks address the demonstrated failure without recertifying old payloads
using new hashes. Directory and optional absence representations remain governed
by the earlier main-file scope; a verified content manifest is not a claim of
recursive native dependency closure.

Legacy conversion without sufficient producer proof now fails `changed_source`.
This is an explicit scoped compatibility decision: old manifests lack the full
Unitizer/version inputs needed to honestly derive another-format cache key.
Ordinary dual-format execution first creates a newly verified GeoPackage and
remains supported. Existing historical job/published downloads remain available
even when today's sources have changed or disappeared. Do not require a rebuild
just to retrieve an old artifact.

Independent command and evidence:

```text
wctl exec weppcloud python docs/work-packages/20260916_file_dependency_freshness/artifacts/features_companion_retention_probe.py
```

`features_companion_retention_probe.log` exits 0. The first conversion is real
GDAL OpenFileGDB and creates a 9,760-byte accepted archive. Only the second
converter call injects `OSError(ENOSPC)`; catalog/profile selection uses the
existing test fixture. Current orchestration deletes the accepted ZIP, then
propagates the injected failure, leaving the cache index byte-identical and its
accepted path absent. This is a failure-path characterization, not a natural
ENOSPC measurement or arbitrary-writer exploit. All data is disposable.

Distinct candidate directories directly address this failure and post-conversion
verification rejection. Successful companion ZIPs must carry their own manifest
and README next to the existing GDB tree; result/cache references must point to
companion provenance. The source manifest and old companion ZIP remain intact.
Retain useful partial conversions with their rejected/error verification record.
Do not replace an original job's source manifest with a companion failure.

The final canonical amendment also requires dual-profile orchestration to finish
companion conversion/verification before either profile-registry write.
Otherwise today's `publish_profile_execution_artifacts`
updates `prep-wepp` first and a subsequent companion rejection contradicts the
promise to preserve previous publication bindings. A successful primary artifact
and its valid cache entry can remain retained; no rollback/delete of valid work
or new multi-file transaction is required by this observation.

`publish_profile_artifact` must select the actual artifact-matching cache entry
and validate format, deriving request/dependency identity from its key instead
of calling `prepare_export_submission` against today's inputs. That preserves
historical selection semantics and avoids writing misleading current provenance.
Missing/incompatible bindings use existing `stale_publication` behavior. This
does not authorize a new current-source gate in published download resolution.

## Required implementation and runtime evidence

Verify actual generated ZIP values after a restored-time rewrite, same-byte
reuse with retained old bundle provenance, all manifest/README verdict copies,
and unchanged historical published retrieval. Exercise final-read failure,
observable source change, initial disappearance, invalid hash metadata and
directory/parent-run compatibility. Rejecting an attempt must preserve the
prior index and artifact bytes and retain its useful candidate files.

Extend the real native companion probe for same-source success, changed-source
rejection before and during conversion, request/Unitizer/version mismatch,
missing legacy proof and all companion manifest copies. Exercise conversion
failure after an accepted companion already exists and assert exact prior ZIP,
source manifest, cache and publication binding preservation. A later new-source
export must materialize that source rather than hit old converted payload.

Use the canonical archive/restore implementation to prove success and failed
candidate paths survive byte-for-byte, then exercise browser/download behavior
under the normal service identity. These are implementation/closeout gates,
not evidence already supplied by the baseline probe. Measure the actual full
dependency preparation/recheck path and settled read counts, including repeated
entries, against the checkpoint's representative workload and stated budget.
No package security approval follows from this checkpoint alone.
