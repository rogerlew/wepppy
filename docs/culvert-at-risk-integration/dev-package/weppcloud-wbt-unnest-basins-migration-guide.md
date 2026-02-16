# weppcloud-wbt UnnestBasins Migration Guide
> Migrate Culvert_web_app nested watershed delineation to `weppcloud-wbt` `UnnestBasins` with sidecar-driven hierarchy.
> Updated: 2026-02-16

## Purpose

This guide documents how to replace the current Python nested delineation/hierarchy workflow in `Culvert_web_app` with the revised Rust `UnnestBasins` implementation in `weppcloud-wbt`.

Target Python code paths:

- `culvert_app/utils/subroutine_nested_watershed_delineation.py::nested_basin_delineation(...)`
- `culvert_app/utils/subroutine_nested_watershed_delineation.py::establish_nesting_hierarchy(...)`

Target Rust tool:

- `whitebox-tools-app/src/tools/hydro_analysis/unnest_basins.rs`

## Why migrate

The current Python approach does two expensive operations:

1. Per-pour-point watershed delineation plus raster-to-vector conversion inside a loop.
2. Pairwise polygon overlap checks in `establish_nesting_hierarchy` (`O(n^2)` geometry operations).

`UnnestBasins` now provides:

- One-pass flow assignment with per-order remapping (no per-order full-grid retracing).
- A hierarchy sidecar CSV with parent/child bookkeeping.
- Regression tests validating remap parity with legacy tracing logic.

## Sidecar contract

`UnnestBasins` writes:

- Order rasters: `<output_stem>_1.tif`, `<output_stem>_2.tif`, ..., `<output_stem>_<max_order>.tif`
- Hierarchy CSV: `<output_stem>_hierarchy.csv`

Hierarchy CSV schema:

| Field | Type | Meaning |
|---|---|---|
| `outlet_id` | int | 1-based outlet ID from pour-point record order |
| `parent_outlet_id` | int | Immediate downstream outlet (`0` = root) |
| `child_count` | int | Number of immediate upstream child outlets |
| `child_ids` | string | Semicolon-separated child outlet IDs |
| `nesting_order` | int | Order raster index that contains this outlet's full basin |
| `hierarchy_level` | int | `0` at root, increasing upstream |
| `is_root` | bool | `true` when `parent_outlet_id == 0` |
| `row` | int | Outlet row index in D8 grid |
| `column` | int | Outlet column index in D8 grid |

Mapping to current Culvert fields:

| Current Culvert field | Sidecar source | Transform |
|---|---|---|
| `parent_watershed` / `parent_wat` | `parent_outlet_id` | Convert `0` to null |
| `child_count` / `child_coun` | `child_count` | Direct |
| `child_ids` | `child_ids` | Convert `;` delimiter to `,` if current downstream code expects commas |
| `hierarchy_level` / `hierarchy_` | `hierarchy_level` | Direct |
| `is_nested` | `is_root` | `is_nested = not is_root` |
| `watershed_id` / `watershed_` | `outlet_id` | Use `outlet_id - 1` if zero-based ID is required |

## Benchmarks and expected gains

Measured during `weppcloud-wbt` implementation/validation:

| Case | Pour points | D8 grid | Current Culvert Python | UnnestBasins (pre-opt) | UnnestBasins (revised) | Improvement |
|---|---:|---:|---:|---:|---:|---:|
| `Santee_10m_no_hydroenforcement` | 36 | `833 x 789` | `58.876s` | `3.070s` | `2.883s` | `20.4x` vs current Python |
| `Tallulah River Demo` | 49 | `14315 x 26768` | not directly measured | `1033.087s` | `886.748s` | `14.2%` faster vs pre-opt Rust |

Interpretation:

- Component-level migration target (`nested_basin_delineation` + hierarchy) is expected to be roughly `20x` faster based on Santee.
- Tallulah current-Python runtime is estimated at about `5.0h` by scaling the Santee factor (`886.748s * 20.4`); this is an inference, not a direct measurement.

Expected whole-task speedup by Amdahl's law (`s = 20.4x` for the migrated component):

| Fraction of total runtime spent in nested delineation (`f`) | End-to-end speedup |
|---:|---:|
| `0.50` | `1.9x` |
| `0.70` | `3.0x` |
| `0.80` | `4.2x` |
| `0.90` | `6.9x` |

## Refactor plan (Culvert_web_app)

### 1) Keep preprocessing and snapping unchanged

Do not change:

- road/breakline hydro-enforcement logic
- `D8flow_dir_UTM.tif` generation
- RSCS snapping pipeline (`pour_points_snapped_to_RSCS_UTM.shp`)

Only replace nested watershed extraction and hierarchy bookkeeping.

### 2) Replace per-point delineation with one `UnnestBasins` call

In `nested_basin_delineation(...)`:

1. Keep `sort_points_by_flow_accumulation(...)`.
2. Write sorted pour points to a temporary shapefile (stable record order).
3. Run:
   - `wbt.unnest_basins(d8_pntr=flow_dir_path, pour_pts=sorted_pour_points_shp, output=unnest_output_base_tif)`
4. Read `<unnest_output_base_stem>_hierarchy.csv`.

Important ID rule:

- `outlet_id` is tied to the sorted pour-point record order used for the `UnnestBasins` call.
- Preserve a mapping table: `outlet_id -> Point_ID`.

### 3) Build per-outlet full watershed polygons from order rasters

For each unique `nesting_order` in sidecar:

1. Convert `<base>_<nesting_order>.tif` to polygons once.
2. Keep polygon records with `VALUE > 0`.
3. Treat `VALUE` as `outlet_id`.
4. Join sidecar attributes and `Point_ID`.
5. Append to combined watershed GeoDataFrame.

This replaces the current per-point `wbt.watershed(...)` loop and avoids repeated raster traversals.

### 4) Remove geometry-driven hierarchy inference

Replace:

- `nested_hierarchy = establish_nesting_hierarchy(combined_watersheds)`

With:

- sidecar join (`parent_outlet_id`, `child_ids`, `hierarchy_level`, `is_root`)

`establish_nesting_hierarchy(...)` can be retained temporarily as a fallback behind a feature flag during transition, then deleted after parity validation.

### 5) Update incremental-area logic to use outlet IDs (not row index)

Current `calculate_incremental_areas(...)` uses `child_ids` as positional indices via `iloc`, which is fragile.

Refactor to:

1. Key watersheds by `outlet_id` (or `Point_ID` after a deterministic mapping).
2. Parse `child_ids` as outlet IDs.
3. Look up child geometries by key, not row position.

This decouples area logic from DataFrame ordering and matches the sidecar contract.

### 6) Preserve downstream output compatibility

Keep writing:

- `all_ws_polygon_UTM.shp`

with expected columns used by later tasks (`Point_ID`, nested fields, area fields), even if internally generated from sidecar metadata.

If shapefile 10-character truncation remains required, continue emitting compatible aliases (`parent_wat`, `child_coun`, `hierarchy_`, etc.).

## Concrete change map

| File | Function | Change |
|---|---|---|
| `culvert_app/utils/subroutine_nested_watershed_delineation.py` | `nested_basin_delineation` | Replace per-point watershed loop with `UnnestBasins` call + sidecar join |
| `culvert_app/utils/subroutine_nested_watershed_delineation.py` | `establish_nesting_hierarchy` | Deprecate; keep as temporary fallback only |
| `culvert_app/utils/subroutine_nested_watershed_delineation.py` | `calculate_incremental_areas` | Use outlet-keyed lookup for `child_ids` |
| `culvert_app/tasks/watershed_delineation_task.py` | Step 18 call site | Keep signature stable; route through migrated `nested_basin_delineation` implementation |

## Validation checklist

For each test project (minimum: Santee + Tallulah):

1. Count parity:
   - Number of watershed polygons equals number of snapped pour points after filtering.
2. ID parity:
   - Every polygon has a valid `Point_ID`.
3. Hierarchy parity:
   - Parent/child relationships match sidecar.
4. Geometry sanity:
   - All geometries valid after final repair/simplification.
5. Area sanity:
   - `incremental_area_sqkm <= total_area_sqkm` for every outlet.
6. Runtime:
   - Record migrated step timing and compare against current production baseline.

## Suggested rollout

1. Phase 1 (dual run, non-production):
   - Run both current Python hierarchy and sidecar-driven hierarchy.
   - Compare parent/child, area, and geometry outputs.
2. Phase 2 (default to `UnnestBasins`):
   - Keep fallback flag for one release.
3. Phase 3 (cleanup):
   - Remove geometry-based hierarchy path after stability window.

## Repro benchmark commands

Rust `UnnestBasins` timing (example):

```bash
/usr/bin/time -f '%e' \
  /workdir/weppcloud-wbt/target/debug/whitebox_tools \
  -r=UnnestBasins -v=false \
  --d8_pntr=/wc1/culvert_app_instance_dir/user_data/1_outputs/Santee_10m_no_hydroenforcement/WS_deln/D8flow_dir_UTM.tif \
  --pour_pts=/wc1/culvert_app_instance_dir/user_data/1_outputs/Santee_10m_no_hydroenforcement/WS_deln/pour_points_snapped_to_RSCS_UTM.shp \
  -o=/tmp/unnest_santee.tif
```

Current Python baseline timing should target the same logical component (`nested_basin_delineation` plus hierarchy bookkeeping) using the same D8 and pour-point inputs.
