# Benchmark Results (Milestone 4)

## Execution Scope

Executed benchmark cases in this draft:

- `BW-01` DEM reprojection / warp
- `BW-02` Raster clipping

Deferred (not executed in this draft):

- `BW-03` rasterization
- `BW-04` terrain derivatives
- `BW-05` extent-window raster intersection

Harness and raw evidence:

- Harness script: `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/benchmark_harness_bw01_bw02.py`
- Raw run JSON: `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/benchmark_runs_bw01_bw02.json`
- Timestamped raw run JSON: `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/benchmark_runs_bw01_bw02_20260304T044701Z.json`
- Host metadata: `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/benchmark_host_metadata.txt`

## Environment Snapshot

- Host: `forest`
- Kernel: `Linux 6.8.0-90-generic x86_64 GNU/Linux`
- CPU: `48 vCPU` (`Intel Xeon E5-2697 v2 @ 2.70GHz`)
- Memory: `125 GiB`
- System Python (current stack runs): `3.12.3`, `rasterio 1.4.4`, `gdal 3.11.4`
- Candidate venv Python (`raster_tools` runs): `3.12.3`, `rasterio 1.5.0`, `raster_tools 0.9.11`
- Initial host snapshot timestamp (UTC): `2026-03-04T04:18:58Z`
- Final rerun ID: `20260304T044701Z`
- Final rerun output timestamp (UTC): `2026-03-04T04:47:01.917777+00:00`

## Runtime Summary (1 warmup + 3 measured runs)

| Case | Current median / p95 (s) | Candidate median / p95 (s) | Relative runtime (candidate/current, median) |
|---|---:|---:|---:|
| `BW-01` reprojection | `0.293 / 0.320` | `14.579 / 14.628` | `49.73x` slower |
| `BW-02` clipping | `0.926 / 0.939` | `15.674 / 15.754` | `16.92x` slower |

## Supplemental Zonal Comparison (Curiosity, Out of Shortlist)

This package also captured a supplemental zonal-style timing comparison for curiosity only.
It is explicitly outside Milestone 2 shortlist gating and does not change shortlist completion status.

Evidence:

- `wepppyo3` + `oxidized-rasterstats`: `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/zonal_benchmark_wepppyo3_oxidized_rasterstats.json` (`run_id=20260304T050046Z`)
- `raster_tools`: `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/zonal_benchmark_raster_tools.json` (`run_id=20260304T051038Z`)

Runtime summary (median seconds):

| Dataset | `wepppyo3` | `oxidized-rasterstats` | `raster_tools` | `oxidized/wepppyo3` | `raster_tools/wepppyo3` | `raster_tools/oxidized` |
|---|---:|---:|---:|---:|---:|---:|
| `small` | `0.0465` | `0.2669` | `2.9007` | `5.75x` | `62.44x` | `10.87x` |
| `large_local` | `0.1057` | `2.7439` | `34.1748` | `25.95x` | `323.23x` | `12.46x` |

Supplemental diagnostic parity context from `zonal_benchmark_wepppyo3_oxidized_rasterstats.json`:

- `small` majority match ratio: `0.9264`
- `large_local` majority match ratio: `0.9177`

Notes:

- Semantics are not identical across tools (`wepppyo3` raster key/value mode vs polygon zonal stats surfaces).
- `raster_tools` zonal run used `zonal_stats(..., stats=['count','mode'], features_field='TopazID')` and returns grouped rows (`399` for `small`, `5422` for `large_local`) rather than one row per feature.
- These results are directional telemetry only and are not treated as decision-grade parity evidence.

## Parity Outcomes

| Case | Parity check | Outcome | Notes |
|---|---|---|---|
| `BW-01` | Comparable-grid precondition (`same projection + shape + geotransform`), then RMSE `<= 1.0` on non-nodata cells | `non-comparable` | Projection matched, but grid mismatch remained (`122x121` vs `125x124`, different geotransforms), so RMSE was intentionally skipped |
| `BW-02` | Comparable-grid precondition (`same projection + shape + geotransform`), then non-zero footprint ratio `>= 0.85` | `non-comparable` | Nodata-aware footprint ratio was `0.9870` (`732,422` vs `742,073` valid cells), but grid mismatch remained (`2561x2243` vs `2563x2245`, different geotransforms), so ratio was treated as diagnostic only |

## Warnings and Deviations

- Candidate runs emitted repeated stderr text: `Error in sys.excepthook: Original exception was:` despite `returncode=0` and valid output files.
- Current runs emitted GDAL FutureWarning about `UseExceptions()` default behavior changes.
- Current and candidate commands were run in different Python environments to satisfy dependency constraints (`raster_tools` required a dedicated venv). This reduces direct runtime fairness and should be treated as a confounder.
- Timings include subprocess startup/import overhead because each measured run invokes `python -c ...` in a fresh process.

## Non-Comparable / Deferred Cases

- `BW-03`, `BW-04`, and `BW-05` remain deferred in this draft and are not included in performance comparison totals.
- `BW-01` and `BW-02` were executed but are non-comparable under the stricter grid-equivalence contract, so performance deltas are diagnostic only.
- This result set is therefore partial and should be treated as directional evidence only, not a full final benchmark suite.
