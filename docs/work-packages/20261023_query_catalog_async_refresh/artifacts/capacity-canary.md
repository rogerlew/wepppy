# Two-host catalog service canary under one owner

**PASS for this bounded service/convergence canary.** Executed on
2026-10-27 approximately 01:15:30–01:19:33 UTC, within the 15-minute task bound.
This is controlled service evidence, not full-fleet capacity certification or
production rollout approval.

## Isolation and workload

Two normal forking RQ Workers ran in the existing wepp1/wepp2 batch containers as
uid 1002/gid 130, supplementary group 130. Their only queue was the unique
`qcat-capacity-20261027-fff52a3f` validation queue. The subclass overrides worker
registration only to advertise the exact candidate configuration; execution uses
RQ's normal workhorse. Both advertised before the controller admitted work, and
both waited for a controller barrier before consuming jobs. Each executed four.

The owned scope is
`/wc1/query-catalog-validation/20261026/qcat-capacity-20261027-fff52a3f`.
Eight projects lie under `batches/owner/scopes/`; only the child projects receive
`wepp.nodb` markers containing `{}`. There is no top-owner project marker and no
NoDb hydration. The explicit batch-layout namespace gives eight distinct scope
identities but one shared canonical owner guard, outside the replaceable trees.
Exactly one stable guard file was observed; none was deleted or replaced.

Each child exposes the same 79 immutable Parquets, 73,328,103 bytes, from the
retained owned `rollout-cycle-2355/runs/representative` fixture. Hardlinks were
supported, so no fallback copies were needed. Hardlink creation changes inode
link counts; source file bytes were hashed before/after and are unchanged. This
is repeated shared data with potential cache benefits, not eight independent
production datasets.

Candidate `query_catalog_rq.py` and `_query_catalog_inventory.py` were staged in
private temporary directories and exec-compiled only in the canary interpreters.
Exact SHA256 values (still matching local source at verification):

- query_catalog_rq: `839bafc4efa1b1f4161b3d7fec1b7f0a4c0c7e0b3652727f70bd6363404c0cac`
- _query_catalog_inventory: `d39f056e243b7889b0dd50c2030c518b822f3d54e4263fb6f16a4b5e8cc86791`

Only process-local root/enabled/default-queue configuration changes were made.
No live service/configuration, real project, production namespace or existing
batch job was modified. The private queue and its normal retained RQ job records
are canary evidence. No default batch job was consumed. Scripts/source manifests
and per-role stdout/stderr remain in `capacity-canary-logs/` and
`capacity-canary-{probe,driver,readback}.py`.

## Service results

| Measurement | Minimum | Median | Maximum |
| --- | --- | --- | --- |
| Enqueue-to-start | 5.204 s | 35.887 s | 69.048 s |
| Start-to-end service | 14.513 s | 20.686 s | 24.039 s |

First start to last completion: **83.286 s**. First admission to last completion:
**89.162 s**. Queue wait includes the deliberate all-jobs-admitted start barrier
and the eight-job cohort behind two workers; it is not live shared-batch delay.
These are eight observations, so no tail percentile or sustained-throughput
promise is inferred. Service includes metadata discovery/publication and any
ownership wait; individual lock waits were not instrumented in this run.

Each of the eight jobs finished successfully and published **80 catalog entries**,
including every selected Parquet. Raw catalog entry/size checks and zero-pending
checks occurred before calling the actual required-path freshness barrier, so a
repairing read cannot hide a failed job. Required-path verification then passed
for all 79 paths in every scope; pending receipts remained zero.

Sixteen actual DuckDB consumer queries additionally read two retained artifacts
per child: `watershed/channels.parquet` has 19 rows and
`wepp/output/interchange/H.pass.parquet` has 280,512 rows, matching the source.
Per-scope sample hashes and inode sharing are recorded. The complete source
Parquet manifest is retained; all source content hashes remain unchanged.

At completion the unique queue and its started registry were empty, compatible
active consumers were zero, and read-only `/proc` checks found no owned probe
process on either host. Normal workers exited and registered death; no forced
cleanup was needed. There were no failed jobs/attempts in this canary. Scratch,
private overlays, stable guard and bounded-retention RQ evidence remain intact.

## Disposition and limits

The result demonstrates that two compatible production-identity workers can
converge eight nested scopes sharing one owner under the actual NFS/guard path.
Receipts were explicitly recorded and admitted; this does **not** exercise a
fleet-wide inventory traversal or prove the inventory helper's behavior merely
because its candidate source was loaded. It also does not measure competition
with the busy production batch queue, independent-project variability, oldest
unreconciled age or the 24-hour target. Keep those parent-owned gates separate.

Summary: `capacity-canary-summary.json`. Full job timing and file/sample proof:
`capacity-canary-readback.json`. Process cleanup: `capacity-canary-cleanup.json`.
