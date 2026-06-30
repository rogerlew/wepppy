# wepp1 Exception Evidence - Batch Runner Durability

**Captured**: 2026-06-30 19:56 UTC
**Host**: `wepp1`
**Repo path checked**: `/workdir/wepppy`
**Batch**: `nasa-roses-202606-psbs`

## Summary

The production batch was restarted after observed climate years were set, but the failed-run evidence shows why the Batch Runner needs durable retry selection. Per-watershed RQ jobs catch exceptions and return `(False, elapsed)`, so RQ records the job as `finished` with empty `exc_info`. The durable failure signal is currently `runs/<leaf>/run_metadata.json`, but success metadata is not written today.

At the scoping sample, the batch was still active. No production mutations were performed.

## Commands Run

- `ssh wepp1 'hostname; pwd; cd /workdir/wepppy && git rev-parse --show-toplevel'`
- `ssh wepp1 'cd /workdir/wepppy && wctl run-python -c ... Job.fetch(...) ...'`
- `ssh wepp1 'python3 - <<PY ... scan /geodata/wc1/batch/nasa-roses-202606-psbs/runs/*/run_metadata.json ... PY'`
- `ssh wepp1 'cd /workdir/wepppy && wctl run-python -c ... BatchRunner/RedisPrep summary ...'`

## RQ Job Evidence

The provided RQ job IDs all fetched successfully from Redis. Each one had:

- `status`: `finished`
- `func_name`: `wepppy.rq.batch_rq.run_batch_watershed_rq`
- `result`: `(False, <elapsed_seconds>)`
- `exc_info`: empty string
- `meta.runid`: `nasa-roses-202606-psbs`

Sample rows:

| Job ID | Result | Notes |
| --- | --- | --- |
| `0b38b2f6-df11-4b6f-bb80-10f45f6e2b47` | `(False, 1437.7817513942719)` | User-provided `WA-38` failure. |
| `8e065d69-29c1-46ef-85ec-ed5d6f7a36ca` | `(False, 1556.1093962192535)` | User-provided `WA-36` failure. |
| `e657ab3c-cf0a-4889-8d73-eabc90342456` | `(False, 1555.7719593048096)` | User-provided `WA-39` failure. |
| `33fcc0ca-349b-490d-a82d-a20a94f3190d` | `(False, 1589.6421339511871)` | User-provided `OR-16` failure. |
| `df4af169-9b29-4591-a6e4-162504ae198d` | `(False, 1804.9941821098328)` | User-provided `OR-17` failure. |
| `7ca13c88-bcef-458b-82b0-ab763e71d4af` | `(False, 1699.8658702373505)` | User-provided `OR-20` failure. |
| `7b5d89c3-1b7a-4948-9275-da7aa777f456` | `(False, 1884.2216084003448)` | User-provided `OR-184` failure. |

## Run Metadata Failure Counts

Scanning `/geodata/wc1/batch/nasa-roses-202606-psbs/runs/*/run_metadata.json` found `36` failed metadata files:

- `19` climate configuration failures with `ValueError: observed_start_year must be an integer year, got empty string`.
- `7` NoDir lock failures with `NODIR_LOCKED`, mostly watershed or soils maintenance locks after cancellation/restart pressure.
- `10` WEPP hillslope failures with `returncode=-8`.

WEPP hillslope `returncode=-8` leaves in the sample:

| Leaf | Error summary |
| --- | --- |
| `OR-16` | `wepp_id=372`, `p372.run`, `returncode=-8` |
| `OR-17` | `wepp_id=759`, `p759.run`, `returncode=-8` |
| `OR-184` | `wepp_id=3`, `p3.run`, `returncode=-8` |
| `OR-19` | `wepp_id=1193`, `p1193.run`, `returncode=-8` |
| `OR-20` | `wepp_id=112`, `p112.run`, `returncode=-8` |
| `OR-21` | `wepp_id=724`, `p724.run`, `returncode=-8` |
| `WA-36` | `wepp_id=16`, `p16.run`, `returncode=-8` |
| `WA-37` | `wepp_id=1369`, `p1369.run`, `returncode=-8` |
| `WA-38` | `wepp_id=11`, `p11.run`, `returncode=-8` |
| `WA-39` | `wepp_id=11`, `p11.run`, `returncode=-8` |

## Live Batch State Sample

At the sample time, `_active_batch_job_summaries("nasa-roses-202606-psbs")` returned `25` queued `run_batch_watershed_rq` jobs.

`BatchRunner` plus `RedisPrep` summary:

- Total watershed features: `93`
- Complete by enabled task timestamps: `0`
- Incomplete by enabled task timestamps: `93`
- Missing run directories: `50`
- Failed metadata files: `36`
- Stale failed metadata with complete enabled tasks: `0`

Missing enabled task counts:

| Task | Missing count |
| --- | ---: |
| `abstract_watershed` | 4 |
| `build_landuse` | 4 |
| `build_soils` | 8 |
| `build_climate` | 27 |
| `build_rap_ts` | 27 |
| `run_wepp_hillslopes` | 38 |
| `run_wepp_watershed` | 43 |
| `run_omni_scenarios` | 43 |

## Implementation Implications

- RQ `failed` registries and `job.exc_info` are insufficient for retry selection because watershed jobs intentionally finish with `(False, elapsed)`.
- Existing `run_metadata.json` failure records are useful evidence but cannot be the only source of truth after a later successful rerun, because the current success path does not overwrite them.
- The retry filter should combine enabled `RedisPrep` task completion with terminal metadata, then start writing success metadata so future status is explicit.
- Run Batch should reject overlapping active batch work before enqueueing another parent job.
