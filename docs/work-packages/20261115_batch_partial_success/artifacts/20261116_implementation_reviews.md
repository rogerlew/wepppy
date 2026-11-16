# Implementation reviews — 2026-11-16

Independent read-only reviewers: `contract_correctness` (reviewer),
`contract_security` (security_reviewer), and `implementation_qa` (qa_reviewer).
Final verdict: no open high/medium correctness or security findings; no blocking
QA findings. Security verdict is limited to local implementation, not deployment.

## Findings and disposition

- Exact enrollment/finalizer/source identity, non-expiring RQ records, retry-aware
  terminal settlement and guarded foreign Omni graph traversal: fixed and covered.
- Artifact disclosure through full member paths, symlinks/source replacement and
  untrusted summaries: fixed; validated contained reads, digest checks before ZIP
  writes, safe working files and reconstructed public fields have regressions.
- SEC-IMP-04 (High), cancellation blocked by archive construction: closed. Build
  outside the resource lease; recheck cancellation and source states at short commit.
  Cancel authorization uses observational job-tree lookup; shared dispatch locks
  cover enqueue/linkage. Cancellation refreshes stale parent metadata after lock
  acquisition. Tests cover the actual route and registration/enqueue race.
- Concurrent publication overwrote manifest evidence: fixed by committing the
  sidecar under the same lease after the immutable-summary check. Poll failures
  also commit matching failed-member manifests. Tested concurrent publishers and
  cancellation plus polling during packaging.
- Malformed Culvert diagnostic receipts/outlet objects aborted valid siblings:
  fixed with logged, narrow parsing and shape checks. Actual production finalizer
  regression retains the two valid sibling IDs; rejected outputs log run/attempt.
- Single-storm H.pass versus continuous H.loss producer compatibility: reviewed
  and ratified in checkpoint `0aec93f1c`; owned producer schemas drive validation.
- External consumer origin/redirect safety and identical metrics/geometry cohort:
  reviewed; pinned URL and manifest membership/readback tests pass.

## Receipts and limitations

Correctness rereview at 2026-11-16T07:23:07Z accepted the final terminal-manifest
and dispatch changes. Security rereview at 2026-11-16T07:21:22Z closed SEC-IMP-04;
subsequent terminal-manifest and metadata-lock changes also passed security
rereview at 2026-11-16T07:25:35Z, with the final 63-test receipt inspected. QA reviewed malformed input handling and immutable manifest commit.
The final boundary suite passed 63 tests after these fixes.

Local signed-JWT download/foreign denial uses real HTTP handlers; feature grants
and cancellation identity have fixtures. Synthetic Parquet/GeoJSON proves reader
and orchestration behavior, not scientific model parity or deployed Celery behavior.
Production-equivalent workflow acceptance is a rollout gate.

## Final source hashes

- `wepppy/rq/batch_outcome.py`: `c9d3ad2369bccb8d5824c6d217936db7460274c37d42c2c9c861913f3481e688`
- `wepppy/rq/batch_rq.py`: `9d35b30e6d15382f63db90badcdd160e9e9573343aaf49664a6710eb32f19023`
- `wepppy/rq/cancel_job.py`: `b61a84765c9659323a565ab08fd23e251ed5916216e80b80e0e623ec6a8a4028`
- `wepppy/rq/culvert_rq.py`: `ca0b616dba73b964b37ffe6f2df8c8eb3b36ba546daa2d557eaec9115f33843c`
- `wepppy/rq/culvert_rq_pipeline.py`: `fa07d2f620d94cae1f89261a00771185dd8d889e7d3d26a1fbabe9af6118daf6`
- `wepppy/rq/omni_rq.py`: `f2d50a39639e3523974992917bcea93bde9b1535395a48e8e7f6ac3431d7f025`
- `wepppy/rq/job_info.py`: `37ea0bbe0b0ed0b19246489f935ea401a0e57f3049bf49bbc6362b21c9293e2c`
