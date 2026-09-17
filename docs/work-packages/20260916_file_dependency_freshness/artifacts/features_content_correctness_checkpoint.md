# Features content identity correctness checkpoint

Independent correctness reviewer: `freshness_correctness`, 2026-09-17 UTC.
Reviewed `features_content_contract_decision.md` and specification amendment
against actual service, dependency tracker, cache, manifest, native companion
conversion and download callers. Production code/tests were not edited.

**Current disposition: PASS for the revised bounded checkpoint.** The canonical
amendment and section 11.3 now resolve FE-C01/FE-C02 at the design boundary. The
original findings and native reproduction below remain retained. Implementation,
performance and runtime evidence are still required; this is not package closure.

## Findings

### FE-C01 — High: companion conversion attributes old output to current inputs

`service.py:co_create_post_wepp_geodatabase_artifact` converts an already completed
GeoPackage, then calls `prepare_export_submission` against today's sources and
passes that key into `_upsert_co_created_published_cache_entry` (near line 618).
A post-materialization check confined to `_run_cache_miss_export` cannot protect
this other reusable cache publication. Even checking sources immediately before
and after conversion would miss the source change between original export and
conversion: the converted data came from the older artifact.

Retained `features_companion_baseline_probe.py`, JSON and log execute the actual
service, GeoPackage writer, GDAL OpenFileGDB conversion, cache writer/lookup and
OGR read against disposable files. Only catalog/profile selection is injected.
Source value 25 is exported, source becomes 75, and the old/new source keys are
confirmed different. Companion conversion then inserts value-25 output under
the value-75 key. A subsequent geodatabase export returns `cache_hit=true` and
OGR reads 25 while the actual parquet source contains 75. The probe exits 0.
This is not a speculative metadata-collision limitation; ordinary newer source
metadata reproduces the defect. SHA keys alone retain the attribution error.

The smallest defensible treatment binds companion cache identity to the accepted
source artifact's dependency snapshot and corresponding request/settings, with
explicit compatibility for historical artifacts lacking content provenance.
Alternatively, reject a companion reuse/publication that cannot establish this
association. Do not compute current hashes and attach them to old converted
bytes. If the parent deliberately splits this path, narrow the canonical promise
to primary materialization and retain companion publication as an OPEN package
blocker; do not mark C02 complete.

`publish_profile_artifact` also recomputes current submission identity when
labeling a historical artifact (near line 529). Existing published resolution
repairs its registry identity from the artifact's actual cache entry. Preserve
historical download behavior while making new publication provenance honest;
do not add today's-source matching as a requirement for historical downloads.

The companion currently shares the source artifact directory, deletes an existing
`features_export.gdb.zip` before conversion, and points its manifest binding at
the source GeoPackage job manifest. A rejected new conversion must preserve any
prior accepted companion ZIP and the source artifact's successful manifest.
Stage a candidate independently or otherwise avoid these destructive collisions.
Native conversion currently packages only the `.gdb` tree: the new promise that
successful bundles contain verification metadata must explicitly cover companion
propagation or retain an honest, separate conformance obligation.

### FE-C02 — Medium: cache-hit manifest difference rule needs explicit precision

Specification section 11.3 currently permits cache-hit job manifests to differ
only in `cache_hit`/`source_job_id` context. The amendment intentionally makes
same-byte, different-mtime submissions cache hits while retaining diagnostic
mtime. `_finalize_cache_hit` builds the job manifest from the latest submission,
whereas the immutable ZIP manifest/README contain the earlier artifact snapshot.
Both observations can be correct, but the literal section 11.3 rule cannot hold.

Amend that clause to distinguish immutable artifact-build provenance from
job-scoped selection observations, including timestamps and diagnostic metadata.
Specify what the new verification member means on hits: it must not falsely
claim that an old artifact was materialized again or that current source metadata
is its historical build metadata. Keep artifact ZIP/README bytes immutable.

## Accepted core direction and implementation constraints

- The original actual parquet/ZIP baseline proves 25-to-75 source replacement
  with equal size/restored time returns stale 25. Service opt-in to existing SHA
  mode, metadata-bound verified reads and excluding only valid SHA-entry mtime
  are the smallest plausible main-file correction. Preserve explicit low-level
  `none` mode, all existing provenance/settings selectors and directory states.
- For primary exports, compare the same resolved dependency snapshot after all
  source-consuming materialization and before reusable publication. Prefer
  deciding verified/rejected status before packaging so the artifact manifest,
  job manifest, ZIP member and generated README cannot disagree. Retain failed
  candidates and before/after diagnostics; do not silently retry or overwrite
  prior artifact/index bindings.
- Distinguish initially missing required sources and established data-validation
  errors from source drift/read failures during dependency observation. Narrow
  exception translation should preserve original causes and required-source
  errors; it must not relabel arbitrary materializer errors as changed source.
- Valid empty files can hash successfully but still fail the existing native
  reader's content validation. Directories and optional missing entries remain
  explicit metadata states. No implicit regular-file-only format narrowing.
- Old metadata keys naturally miss; old artifact/job/publication bindings remain
  readable. Do not infer historical hashes or rewrite old entries on download.
  Cache-index and manifest schema version retention is compatible with an
  additive verification member, provided absent legacy values remain readable.
- The public job download and output-discovery callers already require RQ
  `finished` status before resolving the manifest. Rejected job manifests must
  remain failed through that existing boundary; retention alone is not success.
  Direct synchronous profile publication occurs only after successful execution.

## Required validation and remaining limits

Retain actual ZIP value evidence after the change, equal-content touch/link hits,
same-size/restored-time replacement misses, malformed/incomplete SHA fallback,
low-level metadata mode, source disappearance/read error and absent/empty/directory
states. Inject source change during actual materialization and assert explicit
409, exact preservation of an existing cache/index and artifact bytes, retained
rejected artifact/job manifests, and no successful publication binding. Verify
successful and failed manifest propagation, plus unchanged historical published
retrieval after today's sources change or disappear. Extend the companion native
probe when that path is included; the existing companion unit test mocks both
submission identity and conversion and cannot establish source association.

The shared helper's bounded cache is suitable for this submission workload;
measure the stated representative dependency set through actual snapshot
resolution, including repeated logical references and post-materialization pass.
The one-second admission guard means immediate duplicate references can reread;
settled zero misses alone is not a cold/end-to-end submission benchmark. Keep
the checkpoint's cold budget and record unique versus total bytes. No new
cache/watcher/dependency is justified by the retained evidence.

Indirect vector/raster/directory closure, large-source/native runtime and archive
acceptance remain OPEN. Main catalog file hashes do not prove complete native
input closure or atomic multi-file reads. Package completion remains blocked
until the separately tracked obligations are met.

## Revised checkpoint follow-up

Reviewed the revised canonical File-content cache identity amendment, section
11.3, and decision artifact's Review amendment: companion and publication
bindings before production edits. No additional blocking design finding remains.

- **FE-C01 resolved in the proposed contract:** all reusable writers participate.
  Companion conversion requires the verified producer manifest and an actual
  artifact-matching cache binding equal to the corresponding current GeoPackage
  key, including Unitizer and version inputs. Plans share the catalog; normalized
  requests agree except format, dependency fingerprints agree, and the companion
  request/snapshot are rechecked after conversion. This prevents attributing old
  GeoPackage rows to current model sources, including when the source changed
  before conversion started. Distinct candidate directories preserve accepted
  companion ZIPs and source manifests on failure. A companion's own manifest and
  README reach its ZIP and cache/result binding. Publication uses the completed
  artifact's matching cache identity instead of later source observations.
- **FE-C02 resolved in the proposed contract:** section 11.3 now explicitly
  distinguishes immutable producer metadata from new job selection observations.
  Timestamp and diagnostic mtime differences are allowed while artifact identity
  and accepted content fingerprint remain fixed. No false rematerialization is
  implied by a cache hit.
- **Legacy decision is bounded and justified:** historical downloads remain
  readable. New conversion of an artifact lacking accepted content proof fails
  explicitly; normal dual-format generation creates a verified producer first.
  Existing manifests omit the Unitizer preference fingerprint and conversion/
  export request version inputs needed to transform every historical format key
  honestly. General historical reconstruction would require more behavior and
  persisted metadata than this compatible new-export path.

The implementation review must verify that source identity is validated before
conversion touches output, that post-conversion rejection preserves prior ZIP,
cache and source-manifest bytes, and that current request-key checks include the
version/Unitizer inputs rather than only normalized request text. Exercise both
ordinary same-source native dual-format success and the retained changed-source
native reproduction. A rejected candidate's diagnostic manifest must reference
that candidate, never relabel the successful producer manifest. Check the new
companion ZIP's native GDB contents and provenance members together.

The cold/settled representative-set budget remains an implementation acceptance
gate, and indirect closure/runtime/archive obligations remain OPEN as above.
This follow-up performs documentation and call-graph review only; it does not
claim that unimplemented changes or their tests have passed.
