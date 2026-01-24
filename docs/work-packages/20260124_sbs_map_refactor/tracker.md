# Tracker – SBS Map Refactor (Rust Acceleration)

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-01-24  
**Current phase**: Closed  
**Last updated**: 2026-01-24  
**Next milestone**: Closed

## Task Board

### Ready / Backlog
_None._

### In Progress
- [ ] None

### Blocked
- [ ] None

### Done
- [x] Add large fixtures + baseline expectations (2026-01-24).
- [x] Add gated regression tests for fixtures (2026-01-24).
- [x] Create work package spec + multi-phase plan (2026-01-24).
- [x] Capture large-fixture expectations for `SoilBurnSeverityMap` (2026-01-24).
- [x] Add benchmark harness + baseline timings (2026-01-24).
- [x] Implement `wepppyo3.sbs_map.summarize_sbs_raster` (2026-01-24).
- [x] Wire `sbs_map_sanity_check` to Rust summary (fallback to Python) (2026-01-24).
- [x] Consolidate raster scanning in `get_sbs_color_table`/`SoilBurnSeverityMap` (2026-01-24).
- [x] Run large-fixture tests + partial benchmarks (2026-01-24).
- [x] Implement Rust reclassification helper for `SoilBurnSeverityMap.data` (2026-01-24).
- [x] Implement Rust export helper for `export_4class_map` (2026-01-24).
- [x] Capture Rust benchmark run + artifacts (2026-01-24).
- [x] Confirm `wepppyo3` default import via `.pth` in container (2026-01-24).

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Rust GDAL bindings diverge from Python GDAL behavior | Medium | Medium | Validate against fixture expectations + parity tests | Open |
| Large raster scans still slow if we re-read bands | High | Medium | Require one-pass scan + streaming | Open |
| CI unable to run GDAL-backed tests | Medium | Medium | Keep Python fallback + env-gated tests | Open |

## Decisions Log

### 2026-01-24: Color map source of truth lives in repo JSON
**Context**: We want to update SBS severity color mappings without recompiling Rust.

**Options considered**:
1. Hard-code in Rust (fast, but requires rebuild)
2. Env var path to JSON (opaque/less observable)
3. Explicit arg to JSON file in repo (transparent + editable)

**Decision**: Store `sbs_color_map.json` under `wepppy/nodb/mods/baer/data/` and pass the file path explicitly to Rust helpers.

**Impact**: Rust defaults can exist, but Python and Rust can share a visible, editable source of truth without env configuration.

## Progress Notes

### 2026-01-24: Fixture + spec setup
**Agent/Contributor**: Codex

**Work completed**:
- Added large SBS fixtures and baseline summary JSON.
- Added gated slow regression tests (env `SBS_MAP_LARGE_FIXTURES=1`).
- Wrote package spec + multi-phase plan.
- Added `sbs_map_large_expectations.json` and expanded fixture tests.
- Added benchmark harness + captured timings under `notes/`.

**Files modified**:
- `tests/sbs_map/data/prediction_wgs84_merged.tif`
- `tests/sbs_map/data/Rattlesnake.tif`
- `tests/sbs_map/data/sbs_map_fixtures.json`
- `tests/sbs_map/data/sbs_map_large_expectations.json`
- `tests/sbs_map/data/README.large_fixtures.md`
- `tests/sbs_map/test_sbs_map_large_fixtures.py`
- `docs/work-packages/20260124_sbs_map_refactor/package.md`
- `docs/work-packages/20260124_sbs_map_refactor/tracker.md`
- `docs/work-packages/20260124_sbs_map_refactor/notes/benchmarks.json`
- `docs/work-packages/20260124_sbs_map_refactor/notes/benchmarks.md`
- `tools/benchmarks/bench_sbs_map.py`

**Blockers encountered**: None

**Next steps**:
1. Implement Rust summary function (`summarize_sbs_raster`).
2. Wire `sbs_map_sanity_check` to use Rust summary.
3. Add reclassification/export helpers.

**Test results**: Not run (fixtures only; tests gated).

### 2026-01-24: Summary reuse + test/bench run
**Agent/Contributor**: Codex

**Work completed**:
- Added summary caching + reuse to avoid repeated full raster scans.
- Wired `get_sbs_color_table` and `SoilBurnSeverityMap.__init__` to reuse summary output.
- Updated stubs for the new optional `summary` parameter.
- Ran gated large-fixture tests in-container (10 passed).
- Ran partial benchmarks (skip data/export) to validate summary path.

**Files modified**:
- `wepppy/nodb/mods/baer/sbs_map.py`
- `wepppy/nodb/mods/baer/sbs_map.pyi`
- `stubs/wepppy/nodb/mods/baer/sbs_map.pyi`

**Blockers encountered**:
- Full benchmark (data/export) exceeded 10 minutes and 40 minutes; stopped to avoid runaway CPU.

**Next steps**:
1. Implement Rust reclassification for `SoilBurnSeverityMap.data`.
2. Implement Rust export for `export_4class_map`.
3. Re-run full benchmark after Rust paths land.

**Test results**:
- `pytest tests/sbs_map/test_sbs_map_large_fixtures.py -v` (SBS_MAP_LARGE_FIXTURES=1): 14 passed, 2 warnings (pytz/pyparsing deprecations).

### 2026-01-24: Rust reclass/export integration + full benchmarks
**Agent/Contributor**: Codex

**Work completed**:
- Wired Rust reclassification/export helpers into `SoilBurnSeverityMap.data` and `export_4class_map`.
- Added Rust color-table helpers to `get_sbs_color_table`/`sbs_map_sanity_check`.
- Added regression tests for the Rust helper APIs.
- Ran full benchmark with Rust paths and saved JSON artifact.

**Files modified**:
- `wepppy/nodb/mods/baer/sbs_map.py`
- `tests/sbs_map/test_sbs_map_large_fixtures.py`
- `docs/work-packages/20260124_sbs_map_refactor/notes/benchmarks.md`
- `docs/work-packages/20260124_sbs_map_refactor/notes/benchmarks_rust.json`

**Blockers encountered**: None

**Next steps**:
1. Re-run large-fixture tests after Rust helper wiring (done).
2. Compare Rust vs Python benchmark deltas in `benchmarks.md`.

**Test results**:
- `pytest tests/sbs_map/test_sbs_map_large_fixtures.py -v` (SBS_MAP_LARGE_FIXTURES=1): 14 passed, 2 warnings (pytz/pyparsing deprecations).

### 2026-01-24: Rust u8 summary fast path benchmark refresh
**Agent/Contributor**: Codex

**Work completed**:
- Reran Rust benchmarks after u8 scan optimization in `summarize_sbs_raster`.
- Updated benchmark artifacts/notes.

**Files modified**:
- `docs/work-packages/20260124_sbs_map_refactor/notes/benchmarks_rust.json`
- `docs/work-packages/20260124_sbs_map_refactor/notes/benchmarks.md`

**Blockers encountered**: None

**Test results**: Not run (bench refresh only).

### 2026-01-24: Close-out
**Agent/Contributor**: Codex

**Work completed**:
- Confirmed `wepppyo3` loads without extra env vars (via `/opt/venv/lib/python3.12/site-packages/wepppyo3.pth` pointing to `/workdir/wepppyo3/release/linux/py312`).
- Accepted sanity-check latency as success and closed the work package.

**Files modified**:
- `docs/work-packages/20260124_sbs_map_refactor/package.md`
- `docs/work-packages/20260124_sbs_map_refactor/tracker.md`

**Blockers encountered**: None

**Test results**: Not run (close-out doc update).
