# SBS Map Refactor (Rust Acceleration)

**Status**: Closed (2026-01-24)

## Overview
`wepppy/nodb/mods/baer/sbs_map.py` is dominated by Python loops and repeated full-raster scans that
make uploads and validation painfully slow. The goal is to move the heavy raster analysis and
classification work into a Rust + GDAL extension (wepppyo3) while preserving existing behavior
and outputs across multiple hot paths.

## Objectives
- Reduce `sbs_map_sanity_check` latency on real SBS rasters from minutes to seconds.
- Eliminate repeated full-raster scans in `get_sbs_color_table`, `SoilBurnSeverityMap`, and export helpers.
- Replace Python pixel loops in `SoilBurnSeverityMap.data` and `export_4class_map` with Rust-backed routines.
- Preserve existing classification semantics, messages, and outputs.
- Add regression fixtures/tests tied to real SBS maps and document the performance target.

## Scope
### Included
- Rust/PyO3 module in `/workdir/wepppyo3` for SBS raster analysis + classification.
- Python wrapper updates in `wepppy/nodb/mods/baer/sbs_map.py`.
- New regression fixtures + tests for the large SBS maps.
- Work package docs and plan.

### Explicitly Out of Scope
- Changing SBS classification rules or severity color mapping.
- UI or batch-runner workflow changes beyond faster response times.
- Replacing GDAL with an alternate raster stack.

## Stakeholders
- **Primary**: WEPPcloud core maintainers (Roger)
- **Reviewers**: wepppy owners, wepppyo3 maintainers
- **Informed**: Ops (timeout/HAProxy tuning)

## Success Criteria
- [x] `sbs_map_sanity_check` acceptable latency on fixtures (4.77s for `prediction_wgs84_merged.tif`, 0.02s for `Rattlesnake.tif`).
- [x] Rust summary output matches `tests/sbs_map/data/sbs_map_fixtures.json`.
- [x] `SoilBurnSeverityMap.data` and `export_4class_map` outputs match current Python behavior.
- [x] New tests pass in docker (large fixtures gated by `SBS_MAP_LARGE_FIXTURES=1`).
- [x] Python fallbacks remain available if Rust module is missing.

## Dependencies
- wepppyo3 build pipeline with GDAL headers available.
- Docker dev stack for test execution.

## References
- `wepppy/nodb/mods/baer/sbs_map.py` — current implementation.
- `tests/sbs_map/data/README.large_fixtures.md` — fixture provenance.
- `/workdir/wepppyo3/raster` — existing GDAL-backed Rust helpers.

## Rust API Spec (Proposed)
> Module name: `wepppyo3.sbs_map`

Color map source of truth (editable without recompiling):
- `wepppy/nodb/mods/baer/data/sbs_color_map.json`
- Rust should accept this file path explicitly; no env vars required.

### 1) `summarize_sbs_raster(path: str, *, color_map_path: str | None = None) -> dict`
Returns a summary used by `sbs_map_sanity_check` and regression tests.

Expected fields:
- `srs_valid: bool`
- `class_count: int`
- `unique_classes: list[int | float]` (include all if `class_count <= 512`, otherwise empty list)
- `class_counts: list[tuple[int | float, int]]` (value, count) when `class_count <= 512`
- `has_non_integer: bool`
- `has_color_table: bool`
- `color_table_severities: list[str]` (subset of `unburned|low|mod|high`)
- `color_table_valid: bool`
- `sanity_status: int`
- `sanity_message: str`
- `size_bytes: int`

Notes:
- Must use the same severity color map as Python (`sbs_map.py` default).
- Must not allocate entire raster more than once.
- Single-pass scan must feed downstream needs (class_count, unique_classes, class_counts).
- Callers should reuse summary output instead of re-scanning.

### 2) `reclassify_sbs_raster(path: str, *, breaks: list[float] | None, ct: dict | None, nodata: list[float], offset: int, color_map_path: str | None = None) -> numpy.ndarray`
Rust-accelerated equivalent of `SoilBurnSeverityMap.data`.

### 3) `export_sbs_4class(path: str, dst_path: str, *, breaks: list[float] | None, ct: dict | None, nodata: list[float], color_map_path: str | None = None) -> None`
Rust-accelerated equivalent of `export_4class_map` (with GDAL palette).

### 4) Optional helpers
- `read_color_table(path: str) -> dict` (color index map + severity labels)
- `unique_values(path: str) -> list[int | float]` (only if needed outside summary)
- `summarize_color_table(path: str) -> dict` (counts + severity map without scanning pixels)

## Implementation Plan (Multi-phase)
### Phase 0 — Fixtures + Baseline
- [x] Add real-world fixtures under `tests/sbs_map/data`.
- [x] Capture baseline summary in `sbs_map_fixtures.json`.
- [x] Add slow regression tests gated by `SBS_MAP_LARGE_FIXTURES=1`.

### Phase 1 — Rust Summary
- Implement `summarize_sbs_raster` in wepppyo3 using GDAL raster IO.
- Ensure one-pass scan and color table inspection.
- Add Python fallback when module import fails.
- Wire Python call sites to reuse summary output instead of re-reading the raster.

### Phase 2 — Sanity Check Refactor
- Replace Python `sbs_map_sanity_check` internals with Rust summary call.
- Preserve exact messages and return codes.
- Keep Python-only fallback for environments without the Rust module.
- Remove redundant `get_sbs_color_table` scans where summary already has counts.

### Phase 3 — Classification Path
- Implement Rust reclassification for `SoilBurnSeverityMap.data` and `export_4class_map`.
- Validate output parity using existing tests + new fixture tests.

### Phase 4 — Performance + Cleanup
- Bench with the large fixtures and document results.
- Remove redundant Python loops if Rust is available.
- Update docs and README notes for new performance characteristics.

## Deliverables
- New `wepppyo3.sbs_map` module + bindings.
- Updated `wepppy/nodb/mods/baer/sbs_map.py`.
- Regression tests + fixture metadata.
- Benchmarks captured in package notes.
