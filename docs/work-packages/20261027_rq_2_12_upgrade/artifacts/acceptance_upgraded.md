# Forest RQ 2.12.0 integrated acceptance

**Result:** PASS for this bounded actual-project/API/artifact acceptance scope.
**Executed:** 2026-10-27 19:39–19:54 UTC.
**Source:** `b5cac8166eaf067ac2ef79c440a82314c114111b`.
**Shared image:** `sha256:88a982e44d316824f493c99d0c3a9a3db3e4800feef86ff2c65693677039162b`.

Broader regression, historical-state/rollback and independent review gates are
separate; this artifact does not substitute for them. Runtime-wide identity,
mount, worker class and version evidence belongs to the package cutover records.

## Execution and receipts

The harness asserted `rq.__version__ == 2.12.0` inside the rebuilt weppcloud
container before mutation. It used the same existing dev-agent session and
actual HTTPS profile/CSRF token mint/API boundary as the 1.16.2 baseline.
Installed default and fork-archive worker pools executed the jobs against actual
Redis; no worker or API execution was mocked.

Fresh supported fork target `rq212-20261027-upgraded` came from unchanged source
`rlew-international-refuge`, configuration `disturbed-wbt-profile`. The baseline
project `rq212-20261027-baseline` was retained independently for exact content
comparison. Original historical binary rejection was reproduced before recovery:

| Stage | Job ID | Result |
| --- | --- | --- |
| Fresh fork | `b025aae4-91b4-4c26-9ae9-78b38d436fbe` | finished |
| Historical binary run | `36f3e436-8508-489a-a8b3-5273281f6a12` | expected preparation failure; strict descendants blocked |
| Normal API recovery | `1e457c34-5409-4576-bef0-1e4a1eebf75a` | all 18 graph nodes finished |
| Queued cancellation | `2eff2250-6e50-490f-b10c-40c4222d5655` | canceled before start |
| Same-target fork resubmission | `ae761d3b-9868-497c-b753-4b409ae83da0` | finished |
| Archive | `aa7d6a85-db4e-4336-a5f5-2b629a63ee13` | finished |
| Restore | `8bf53817-5400-4b97-9a2d-c7897f41ee9b` | finished |

The original `wepp_250915` provenance failure is identical to baseline. Selecting
`wepp_261026` through normal run-wepp payload resolved it without a provenance
bypass or source-project mutation. Resubmission canceled the 12 obsolete strict
descendants; the failed prerequisite and completed preparation remain retained.
The successful DAG includes parallel preparation, 28 hillslope model executions,
strict watershed stages, parallel postprocessing and final export/completion.
This supplies representative multistage and fan-out/fan-in acceptance.

Full requests, statuses, failed and successful trees and obsolete graph are in
`acceptance_upgraded.json`; polling transcript is `acceptance_upgraded_poll.log`.

## Cancellation and ownership

A uniquely identified, package-owned 90-second sleep job occupied only the
existing serial fork-archive worker. This made the actual API-created disposable
fork target `rq212-20261027-cancel` deterministically queued without pausing a
pool or interfering with unrelated work. Unauthenticated cancellation returned
401; a correctly signed service token scoped to unrelated
`rq212-20261027-unowned` returned 403. The job remained queued after both
rejections. Authorized cancellation returned 200; Redis state was canceled and
`started_at` remained null. The owned blocker finished naturally. Resubmission
to the same destination then finished through the real fork workflow.

## Exact generated-content comparison

`acceptance_baseline_readback.json` and `acceptance_upgraded_readback.json`
reload durable NoDb state, parse actual executable paths, and read all output
Parquets. `acceptance_paired_comparison.json` and its log establish:

- All 155 consumed inputs are byte-identical. Run-ID normalization was permitted
  by the comparator but was not needed for these inputs.
- The 29 `.err` diagnostic records differ in disposable run paths. They are
  execution diagnostics, not model inputs, and both sets remain inspectable.
- All 25 Parquets have identical decoded schemas, including all metadata, and
  exactly equal scientific values. No numeric tolerance or scientifically
  different result was accepted.
- Twenty-four Parquets have identical row order. The return-period rank table
  has only row-order differences; sorting on all columns yields exact equality.
- Physical Parquet hashes differ in 24 files. Embedded `ARROW:schema` metadata
  serialization order differs despite equal decoded key/value metadata. The
  rank-table row order also affects encoding. The retained
  `acceptance_parquet_encoding_differences.json` records raw metadata hashes and
  exact decoded-schema equality; representative writer remains parquet-rs 53.4.1.
- Actual authenticated outlet, hillslope and channel CSV responses returned 200
  and exactly match all baseline rows (9, 29 and 12 including headers).

Representative fresh content: 61,376 hillslope water-balance rows covering
28 hillslopes × 2,192 days in 2000–2005; 28 hillslope and 11 channel summaries;
2,192 watershed event/daily rows. Outlet stream discharge remains 4.069 in/year
and sediment discharge 4.52 ton/year. These are paired equivalence results,
not scientific calibration claims.

## Archive, download and restore

The canonical archive API and installed serial worker produced a 710-member ZIP.
All 417 files under `wepp/runs` and `wepp/output` were compared byte-for-byte
through before/archive/restored SHA256 readback. Actual authenticated download
returned HTTP 200 with 14,251,084 bytes and identical archive SHA256:
`209aa2117ce703b5d323b6162ac41f16e439da07ce1c42aecc84b4c9caf03b76`.

After canonical restore, all generated-file hashes matched. Normal NoDb,
executable-input and all 25 Parquet readers succeeded again; three fresh HTTP
CSV reports still matched the pre-restore rows. Evidence:
`acceptance_archive_restore.json`, `acceptance_upgraded_restored_readback.json`
and `acceptance_restored_comparison.json`.

The independent reviewer requested a destructive sentinel to exclude no-op
restoration. A later test removed only the package-owned
`wepp/output/interchange/loss_pw0.out.parquet`, proved absence and restored it
through the canonical API. Original, ZIP and recovered SHA256 are identical.
The first attempt exposed the existing retained-log NFS limitation; bounded
API/web process recovery preserved running pytest and RQ workers before retry.
See `acceptance_nfs_restore_recovery.md` and `acceptance_restore_repair.json`.
After successful retry, all 417 generated hashes were compared with the original
ZIP again, all 25 Parquets were opened, all 184 input/diagnostic files matched,
and three actual CSV reports matched pre-injection rows. Evidence:
`acceptance_final_repaired_manifest.json`,
`acceptance_upgraded_repaired_readback.json`, `acceptance_repaired_comparison.json`.

The first archive-download probe returned 401 because the harness supplied only
a Flask session cookie. The documented browse/download contract requires its JWT
cookie or bearer. Correcting the harness to send the already-minted profile
bearer made the request pass; no application/auth change was needed. Initial
probe evidence is retained. Two package-created archives remain in the disposable
upgraded project; no unrelated archive was changed.

## Execution IDs, metadata and webhooks

`acceptance_live_execution_tracking.json` captures a live owned preparation job:
raw started-registry member is `job_id:execution_id`, public registry output and
worker current-job value are plain application IDs, and the execution object's
job ID matches. It has no webhook configuration.

`acceptance_metadata_final.json` verifies all 44 owned API graph/fork/archive/restore jobs have
non-PII actor metadata for the expected existing user, a correlation ID, and zero
configured webhooks. The additional directly enqueued sleep blocker has no
actor/correlation metadata and zero webhooks, for 45 total owned jobs.
No owned job remained active at final inspection. This
actual workflow did not opt into profile recording; profile context/leakage and
instrumented outbound-webhook checks remain in the dedicated regression scope.
No native webhook configuration was exposed or enabled here.

## Reproduction and retained resources

Sanitized `acceptance_*_harness.py` files retain exact commands/requests; secrets
are minted/read only in process memory. Execute them through
`wctl docker compose exec -T weppcloud /opt/venv/bin/python -` with the script on
stdin. Fresh-clone harness refuses an existing upgraded destination.
For readback set `RQ212_PHASE=upgraded` and
`RQ212_TARGET=rq212-20261027-upgraded` using Compose exec `-e` options.

Retained package-owned resources: baseline, upgraded and cancellation-test
projects under `/wc1/runs/rq/`; their jobs/receipts and two upgraded archives.
The bounded blocker completed naturally. Existing unrelated jobs, queues, runs
and volumes were preserved. Production was not upgraded; native webhooks were
not enabled.
