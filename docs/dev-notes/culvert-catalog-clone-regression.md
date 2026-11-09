# Culvert catalog clone regression (2026-11-09)

## Scope and acceptance

Operator request: patch on forest and replay the production payload from batch
`4a867e98-870d-458b-863d-3e45e4a23b1b`. Production remains unchanged.
This is a conformance fix to the unchanged lifecycle requirements in
`docs/schemas/query-engine-catalog-refresh-contract.md`, especially Scope identity
and Lifecycle integration: copies must not inherit executable coordination.
The production finalizer reported 33 failures at 2026-11-09 19:41:12 UTC;
all 33 child tracebacks rejected the template's copied catalog identity.

Compatibility plan: retain payload, NoDb, scientific inputs, queue topology and
output schemas. Rotate only copied catalog lifecycle metadata using the existing
helper, retaining old receipts as historical evidence. Never relax scope checks.
Test absent legacy metadata, initialized managed metadata, pending receipts,
source preservation, distinct destination identities and repeated existing-run
setup. Existing malformed/symlink metadata rejection remains required.

Acceptance requires the exact production ZIP (SHA-256
`d679299ebcfd12cde4a20a6b14479d21ee63ce21bcd59435049678db5a74f392`)
through forest HTTP admission and real batch workers. Read back each run's scope,
metadata, terrain/model outputs and the downloadable skeleton archive; distinguish
legitimate skipped outlets from failures. Job success alone is insufficient.

## Failure-class assessment

The bounded search covers project copy sites in CulvertsRunner and BatchRunner,
plus existing fork/restore lifecycle handling. Both CulvertsRunner copy sites
(`_ensure_base_project`, `create_run_if_missing`) omit identity rotation and are
confirmed affected. BatchRunner's child copy and project fork/restore already
call `invalidate_catalog_incarnation`; source inspection alone is not runtime
verification of those unrelated workflows. No global scope-validation change is
needed. Existing failed production trees require separate recovery; the forest
replay uses a fresh batch.

## Validation results

The managed filesystem regression reproduced the production `CatalogRefreshConflict`
before the patch. After the patch, `wctl run-pytest
tests/culverts/test_culverts_runner.py tests/query_engine/test_catalog_refresh.py
tests/rq/test_culvert_rq_pipeline.py --maxfail=1 -q` passed all 53 tests. The tests
use the real catalog lifecycle helper and RedisPrep consumer with real copied
files. Coverage includes absent, initialized and pending source metadata,
distinct base/sibling identities, retained historical receipts, unchanged source
JSON bytes and stable identities on repeated setup. Existing lifecycle tests
exercise stale-publication fencing and symlink rejection.

Independent correctness review found no blocking findings. Broad-exception
changed-file enforcement and stub completeness passed. Documentation lint passed;
code-quality telemetry was retained under `/tmp/culvert-catalog-regression-20261109/`.
The broad suite stopped after 13,227 passed, 424 skipped and 15 passed subtests
(3,710.24 seconds). Its only failure was
`tests/weppcloud/test_usersum_template_wiring.py::test_runs_template_uses_the_ttl_deletion_usersum_doc_id`:
`runs2.html` lacks `runsTtlDeletionHelpUrl`. Both that test and template match
HEAD and are untouched by this patch. This is an unrelated baseline limitation;
the full suite is not green. Final artifact acceptance passed as recorded below.

## Forest replay record

Forest's batch workers run as UID 1000, GID 993, umask 0022 with the normal
`/wc1` mounts and managed catalog roots. The original forest template lacked the
production incarnation marker; the direct managed filesystem regression covers
that source state. No production files or jobs were changed.

The forest public HTTPS listener was unreachable from the container. Admission
used the existing Caddy ingress at `http://caddy:8080` with its configured forest
Host and forwarded HTTPS headers, retaining normal JWT and feature-access checks.
An unregistered diagnostic subject was denied before admission; the existing
registered `culvert-batch-submit-90d` service identity was used for acceptance.
Credentials are retained only in mode-0600 temporary files, never this record.

Initial replay `9293af11-4867-454e-9172-0833bdd4cd64` (root
`35489f0f-bd4b-4de4-8456-024204ec2cdc`) exposed worker module preloading: source
bytes were patched, but the runtime still created an unrotated `_base`.
It is not patch-acceptance evidence. Its 29 queued children and deferred finalizer
were canceled. The four active jobs were initially drained, then canceled through
the normal authenticated cancellation API to avoid spending further execution
time on the superseded replay; their artifacts were retained. The forest
batch-worker container stopped cleanly and was started to reload the module.
No unrelated active batch jobs were present at the drain check.

Fresh acceptance batch: `cbdb8928-114f-4b8f-8c79-f46ecf354f24`, root job
`f2a4a615-d659-4d88-91cb-7ca41c7b4fdb`. HTTP admission returned 200 with the exact
ZIP hash above. A temporary monitor captures identities and prepared input hashes
before the existing skeletonization policy removes transient artifacts. Finalizer,
all-run output readback and authenticated download verification completed.
After worker restart, the new `_base` and first four child scopes
had five distinct non-initialization incarnations, and all four passed DEM setup.

Execution provenance: base revision
`f0ad8a1e281393b5a1177aa96c647f05441c3aac` with this uncommitted patch;
`culverts_runner.py` SHA-256
`02f1dc48467cec0b0dd4dd71958d992c971dd3d9460d7edb5231c6ec90692885`.
The forest template retains 51 simulation years and `wepp_dcc52a6` (binary SHA-256
`365d44d643f70c5eee54e0ea81e74a125003799df8c912bab9ff267c476308a8`).
The replay does not change those existing model settings or condition the supplied
DEM again.

Initial finalization completed at approximately 2026-11-09 20:30:37 UTC with
30 successful runs, three failed runs and zero skips. All 34 base/child identities
were captured and distinct; none raised the original scope conflict. Points
2930, 581 and 2915 reported `BlockingIOError: [Errno 11] Resource temporarily
unavailable`, at different modeling stages. The historical traceback was not
retained, so no speculative runtime or resource-limit patch was made. Subsequent
diagnosis below narrows the likely cause to sibling catalog-lock contention.
Their original directories were retained in
`/tmp/culvert-catalog-regression-20261109/failed-runs-before-retry.tar.gz`
before normal API retries (the retry API replaces failed run directories).
Retries are sequential because the admission contract rejects concurrent batch
retries with HTTP 409. All three succeeded without further code changes:

| Point | Retry job | Domain result |
| --- | --- | --- |
| 2930 | `ee783d4a-17e0-4b01-8984-23032c84b066` | success |
| 581 | `0fb84086-eed1-4768-aa33-8df411cafab1` | success |
| 2915 | `2397594a-2958-476b-9cc3-047d859e55d8` | success |

Refreshed finalizer `e7374d9c-72d1-41a7-be80-b0424051786c` records
33 succeeded, zero failed and zero skipped. Archive completion and verification
passed. This is recovery after three retries, not a clean first-pass replay.
The original failures remain evidence; serial retry success does not establish
their resource cause.

Identity/input capture covers all 34 scopes on the initial attempt; the retry
monitor refreshed identity and prepared-input evidence for 581 and 2915. Retry
2930 finished before capture resumed, so its identity/input snapshot is from the
initial attempt. Final artifact readback covers its successful retry separately.
The focused managed-source regression, initial live scope evidence, and final
outputs are distinct evidence boundaries, not interchangeable claims.

## Final artifact acceptance

Readback completed at 2026-11-09 21:10:40 UTC. All 33 payload point IDs matched
the run directories and successful metadata. Across 2,364 hillslopes and 965
channels, hillslope IDs matched landuse and soil assignments; watershed areas
were positive and finite. Every run's `totalwatsed3.parquet` had 18,627 contiguous
simulation days for years 1–51. Checked water/sediment and outlet-event fields
were finite and non-null. All retained Parquet files had readable schemas and
row metadata. These are structural/semantic regression checks, not independent
scientific calibration or a physical-water closure study.

Normal batch browse and scoped-token download both returned HTTP 200 through
forest Caddy. The downloaded ZIP was 2,137,378,213 bytes with 2,877 unique members,
including metadata for all 33 runs. Every decompressed member's SHA-256 matched
its generated source file. The whole archive matched the server artifact with
SHA-256 `0070aaaf71135b8f3b3115fd19def168458f49762ee6eea40505c222f618e31a`.
Initial jobs, retry jobs and refreshed finalization were checked separately;
domain metadata and output readback, not RQ success alone, establish completion.

Detailed per-run schemas, output counts, member hashes, initial/retry identity
and input snapshots, probe scripts and test logs are retained under
`/tmp/culvert-catalog-regression-20261109/`. The normal user-facing artifacts
remain at `/wc1/culverts/cbdb8928-114f-4b8f-8c79-f46ecf354f24/`.
The implementation restores the clone identity contract on forest. Production
deployment/recovery was not requested or performed. Independent correctness
review found no blocking code issue and required the retry and broad-suite
qualifications retained here.

## Remaining sibling lock contention

A direct two-process reproduction in a disposable configured managed root used
two sibling culvert directories with distinct valid incarnations. Process A held
`catalog_lifecycle_guard(left)`; process B called
`RedisPrep.getInstance(right)`. Both scopes mapped to the same batch-owner lock.
The second call raised the exact `BlockingIOError(11, 'Resource temporarily
unavailable')` at `fcntl.lockf(... LOCK_NB)` in `catalog_refresh.py`, through
`RedisPrep._guard` and `redisprep_snapshot_guard`. No process/resource limits were
changed, and the fixture did not touch replay or production directories.

The original logged failure positions agree with RedisPrep access: point 2930
finished its hillslopes immediately before the completion timestamp; point 581
failed after entering `build_subcatchments`, before backend dispatch; point 2915
failed after edge-hillslope identification, before the subcatchment completion
timestamp. These consumers use RedisPrep. The handler only logged the exception
message, so the original syscall and lock holder cannot be conclusively recovered.
Sibling lock contention is reproducible and the leading explanation, not proof
of memory exhaustion. The nonblocking lifecycle acquisition avoids lock-order
deadlock, but its contention currently escapes as a culvert failure. This separate
concurrency defect remains unfixed by the bounded clone-identity patch; serial
retry success is not a concurrency repair. Future repair must preserve lifecycle
fencing and lock ordering, and retain full exception tracebacks at this boundary.


## Follow-through completed

The subsequent [catalog contention and stateless WBT repair](../work-packages/20261109_culvert_catalog_contention/package.md)
repairs the reproducible sibling coordination defect and shared WBT settings
race. Two fresh forest batches completed 33/33 without retries, with four
overlapping children, validated model outputs and authenticated archive readback.
The historical retry evidence above remains distinct from that clean acceptance.
Production remains unchanged.
