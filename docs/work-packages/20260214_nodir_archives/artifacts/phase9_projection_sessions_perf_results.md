# Phase 9 Projection Sessions Perf Results

Date captured: 2026-02-18 (UTC)

## Scope

Phase 9E perf evidence verifies the Phase 9 contract target that projection-session reads materially reduce `WD/.nodir/cache` growth for path-heavy WEPP prep access patterns, compared with a Phase 8-style per-file materialization baseline.

## Method

Execution environment:
- Command runner: `wctl exec weppcloud bash -lc ...`
- Python runtime: `/opt/venv/bin/python`
- Locking: deterministic in-memory Redis lock stub (same lock API as NoDir tests) applied to `wepppy.nodir.materialize` and `wepppy.nodir.projections`

Synthetic workload:
- Archive-backed roots: `watershed.nodir`, `soils.nodir`, `landuse.nodir`
- Unique logical paths per iteration: `851`
  - `watershed` hillslope files: `300`
  - `watershed` flowpaths files: `150`
  - `watershed` channels file: `1`
  - `soils` files: `200`
  - `landuse` management files: `200`
- Iterations: `5` per scenario

Scenarios:
1. `phase8_style_materialize_baseline`
   - For each logical path, call `materialize_input_file(...)` then read one byte.
   - This models Phase 8-era high-fanout per-file materialization behavior.
2. `phase9_projection_sessions`
   - Acquire stage-scoped read projections for `watershed`, `soils`, and `landuse`.
   - Resolve each path via `with_input_file_path(..., use_projection=True, allow_materialize_fallback=False, tolerate_mixed=True, mixed_prefer="archive")` and read one byte.

Collected metrics:
- Wall-time per scenario run (mean/median/p95)
- `WD/.nodir/cache` growth per run:
  - file count delta
  - byte size delta

Method note:
- Phase 8 artifact `phase8_wepp_nodir_perf_results.md` quantified read-stage wrapper overhead, not cache-file growth directly. This Phase 9E run adds explicit cache-growth measurement while preserving a Phase 8-style materialization baseline behavior model.

## Results

| Metric | Phase 8-style materialize baseline | Phase 9 projection sessions | Delta |
|---|---:|---:|---:|
| Cache file growth (mean) | 1702 | 0 | -100.00% |
| Cache file growth (p95) | 1702 | 0 | -100.00% |
| Cache bytes growth (mean) | 424804 | 0 | -100.00% |
| Cache bytes growth (p95) | 424804 | 0 | -100.00% |
| Wall time mean (ms) | 3571.4984 | 4534.5083 | +26.96% |
| Wall time p95 (ms) | 3665.4961 | 4762.2321 | +29.92% |

Raw summary JSON:

```json
{
  "phase8_style_materialize_baseline": {
    "cache_bytes_growth": {
      "mean": 424804,
      "median": 424804,
      "p95": 424804
    },
    "cache_files_growth": {
      "mean": 1702,
      "median": 1702,
      "p95": 1702
    },
    "timing": {
      "mean_ms": 3571.4984,
      "median_ms": 3571.4237,
      "p95_ms": 3665.4961
    }
  },
  "phase9_projection_sessions": {
    "cache_bytes_growth": {
      "mean": 0,
      "median": 0,
      "p95": 0
    },
    "cache_files_growth": {
      "mean": 0,
      "median": 0,
      "p95": 0
    },
    "timing": {
      "mean_ms": 4534.5083,
      "median_ms": 4495.7815,
      "p95_ms": 4762.2321
    }
  },
  "workload": {
    "iterations": 5,
    "landuse_files": 200,
    "soils_files": 200,
    "unique_logical_paths": 851,
    "watershed_flowpaths": 150,
    "watershed_hillslopes": 300
  }
}
```

## Assessment

- Contract target met: `.nodir/cache` growth declines materially under projection sessions (`1702 -> 0` files; `424804 -> 0` bytes).
- Synthetic runtime in this measurement is not lower for projection sessions; this benchmark is used for cache-growth evidence, not end-to-end WEPP runtime ranking.

## Cross-Reference

- Phase 8 baseline context: `docs/work-packages/20260214_nodir_archives/artifacts/phase8_wepp_nodir_perf_results.md`
- Phase 8 read-touchpoint inventory: `docs/work-packages/20260214_nodir_archives/artifacts/wepp_nodir_read_touchpoints_phase8a.md`
