# Phase 7 Perf Targets And Results

Date captured: 2026-02-17 (UTC)

## Scope

Phase 7 required measurable before/after evidence for:
- browse listing p95 (`HTML` and `/files` JSON) on a large archived watershed run;
- download streaming throughput (no extraction);
- `materialize(file)` wall time;
- archive build time by root;
- inode reduction and NAS stat-pressure notes.

## Method

Benchmark harness (executed inside the `weppcloud` container) created two synthetic large runs under `/tmp/phase7_perf`:
- `phase7-before`: directory-form roots.
- `phase7-after`: same content, migrated with `python -m wepppy.tools.migrations.nodir_bulk` logic (`crawl_runs(...)`) and JSONL audit logging.

Dataset shape:
- `watershed`: 5,000 hillslope files, 400 channel files, and one 64 MiB random raster (`watershed/raster/big.tif`).
- `landuse`: 2,200 files.
- `soils`: 1,800 files.
- `climate`: 900 files.

Measurement details:
- Browse p95: 35 requests each via Starlette `TestClient` against `/browse/...` and `/files/...`.
- Download throughput: median of 5 raw downloads of the 64 MiB raster (`/download/...`), reported as MiB/s.
- Materialize wall time: `wepppy.nodir.materialize.materialize_file(...)` cache miss then cache hit.
- Archive build time by root:
  - baseline: direct `freeze()` per root;
  - Phase 7 path: per-root `duration_ms` from `nodir_bulk` audit log entries.
- Inodes: recursive file+directory entry counts via `rglob('*')` before/after.

## Targets

| Metric | Target |
|---|---|
| Browse HTML p95 (archived watershed listing) | <= 150 ms |
| `/files` JSON p95 (archived watershed listing) | <= 80 ms |
| Download throughput (archived stream) | >= 100 MiB/s |
| Materialize cache miss (`big.tif`) | <= 300 ms |
| Materialize cache hit (`big.tif`) | <= 10 ms |
| Archive build overhead (`nodir_bulk` vs direct `freeze`) | <= +15% per root |
| Inode reduction after archive migration | >= 95% |

## Results

### Browse / Files p95

| Metric | Before (dir) | After (archive) | Delta |
|---|---:|---:|---:|
| Browse HTML p95 | 183.27 ms | 97.06 ms | -47.04% |
| `/files` JSON p95 | 211.19 ms | 54.03 ms | -74.42% |

### Download Throughput

| Metric | Before (dir) | After (archive stream) | Delta |
|---|---:|---:|---:|
| Raster download throughput | 139.19 MiB/s | 137.73 MiB/s | -1.05% |

### Materialize(file) Wall Time (archive)

| Metric | Result |
|---|---:|
| Cache miss (`watershed/raster/big.tif`) | 191.78 ms |
| Cache hit (`watershed/raster/big.tif`) | 2.31 ms |

### Archive Build Time By Root

| Root | Direct `freeze` baseline | `nodir_bulk` duration | Delta |
|---|---:|---:|---:|
| `climate` | 310.19 ms | 304.00 ms | -1.99% |
| `landuse` | 753.61 ms | 734.00 ms | -2.60% |
| `soils` | 635.08 ms | 606.00 ms | -4.58% |
| `watershed` | 4229.39 ms | 4158.00 ms | -1.69% |

### Inodes

| Metric | Before | After |
|---|---:|---:|
| Total entries across run | 10,313 | 11 |
| Reduction | - | 99.89% |

Per-root before-entry counts:
- `watershed`: 5,404
- `landuse`: 2,201
- `soils`: 1,801
- `climate`: 901

## Target Evaluation

- Browse HTML p95: pass.
- `/files` JSON p95: pass.
- Download throughput: pass.
- Materialize miss/hit: pass.
- Archive build overhead: pass (no positive overhead observed).
- Inode reduction: pass.

## NAS Stat-Pressure Notes

- Evidence strongly supports reduced metadata pressure after migration because run entry count dropped from 10,313 to 11 (99.89% reduction).
- Browse/files timing improvements align with fewer filesystem metadata operations in archive form.
- Download throughput stayed near parity (streaming from archive central directory did not materially reduce throughput in this benchmark).

