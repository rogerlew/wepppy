# weppcloud-wbt UnnestBasins Migration Guide
> Migrate Culvert_web_app nested watershed delineation to `weppcloud-wbt` `UnnestBasins` with sidecar-driven hierarchy.
> Updated: 2026-02-17

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

## Appendix: Big O analysis — SnapPourPoints single call vs iterative

This analysis applies equally to `SnapPourPoints` and `JensonSnapPourPoints`; the algorithms differ only in the comparison criterion (max flow accumulation vs nearest stream cell) but have identical control flow and I/O structure.

Source files:

- `whitebox-tools-app/src/tools/hydro_analysis/snap_pour_points.rs` (lines 278-310)
- `whitebox-tools-app/src/tools/hydro_analysis/jenson_snap_pour_points.rs` (lines 280-317)

### Variables

| Symbol | Meaning |
|---|---|
| P | Number of pour points |
| D | Search radius in cells = `floor(snap_dist / resolution / 2)` |
| R × C | Raster dimensions (rows × columns) |

### Core algorithm

Both tools iterate over every pour-point record and scan a `(2D+1) × (2D+1)` cell window in the raster:

```rust
for record_num in 0..pourpts.num_records {                        // P iterations
    row = flow_accum.get_row_from_y(record.points[0].y);          // O(1)
    col = flow_accum.get_column_from_x(record.points[0].x);       // O(1)
    for x in (col - snap_dist_int)..(col + snap_dist_int + 1) {   // 2D+1
        for y in (row - snap_dist_int)..(row + snap_dist_int + 1) { // 2D+1
            zn = flow_accum.get_value(y, x);                      // O(1)
        }
    }
}
```

Per-point computation: **O(D²)**. The raster is already in memory, and `get_value` is an array index lookup.

### Single call (all P points in one shapefile)

| Phase | Cost |
|---|---|
| Process spawn (`Popen` in `whitebox_tools.py`) | 1 subprocess |
| Read pour-points shapefile | O(P) |
| Read raster into memory | O(R·C) — **once** |
| Core search loop | O(P · D²) |
| Write output shapefile | O(P) |
| **Total** | **O(R·C + P·D²)** |

### Iterative (one `run_tool` call per pour point)

Each of the P invocations spawns a new subprocess via `Popen` (`whitebox_tools.py` lines 329-407), which re-initializes the tool binary and re-reads the raster from disk:

| Phase | Cost per call | × P calls |
|---|---|---|
| Process spawn (fork+exec+arg parse) | k₁ | P · k₁ |
| Read pour-points shapefile (1 point) | O(1) | O(P) |
| Read raster into memory | O(R·C) | **O(P · R·C)** |
| Core search loop | O(D²) | O(P · D²) |
| Write output shapefile (1 point) | O(1) | O(P) |
| **Total** | | **O(P · R·C + P · D²) = O(P · (R·C + D²))** |

### Side-by-side

| | Single call | Iterative |
|---|---|---|
| Computation | O(P · D²) | O(P · D²) |
| Raster I/O | **O(R·C)** | **O(P · R·C)** |
| Process spawns | 1 | P |
| Overall | **O(R·C + P·D²)** | **O(P · (R·C + D²))** |

The raster reload dominates. In the typical regime where `R·C >> D²`, iterative invocation is **~P× slower** than a single call.

### Concrete example (Santee dataset)

R×C = 833×789 ≈ 657K cells, D = 15 cells, P = 36 pour points:

| | Single | Iterative | Ratio |
|---|---|---|---|
| Raster cell reads (I/O) | 657K × 1 = 657K | 657K × 36 = 23.7M | **36×** |
| Search cell comparisons | 36 × 961 = 34.6K | 36 × 961 = 34.6K | 1× |
| Subprocess spawns | 1 | 36 | 36× |

For Tallulah (R×C = 14315×26768 ≈ 383M cells, P = 49):

| | Single | Iterative | Ratio |
|---|---|---|---|
| Raster cell reads (I/O) | 383M × 1 = 383M | 383M × 49 = 18.8B | **49×** |

### Relevance to migration

The current `Culvert_web_app` code in `nested_basin_delineation` calls `wbt.watershed()` (and implicitly snap) per pour point. The `UnnestBasins` migration replaces this with a single call that processes all pour points at once, eliminating the P× raster reload penalty — the same asymptotic improvement documented here for snap pour points.

Any future snap-then-delineate workflow should always batch all pour points into a single shapefile and make one tool call rather than iterating.

## Appendix: Hydro-enforcement — breakline approach vs `BurnStreamsAtRoads`

### Lindsay 2016 guidance

Lindsay (2016) identifies four fundamental problems with traditional stream burning (*FillBurn*):

1. **Elevation offset choice** — a constant offset either distorts terrain attributes (too large) or fails to survive depression filling (too small). More sophisticated methods (Expocurv, TribBurn) reduce but do not eliminate this trade-off.
2. **Parallel stream artifacts** — where mapped streams are misaligned with DEM drainage lines, burning creates erroneous parallel channels.
3. **Topological errors from rasterization** — line thinning forces nearby streams into the same grid cell, causing stream piracy (artifact capture) and collisions. These errors worsen as the mismatch between vector hydrography scale and DEM resolution increases.
4. **Manual vector editing required** — wide streams, lakes, braided channels, loops, and discontinuous streams all need pre-processing before traditional burning.

Lindsay's `TopologicalBreachBurn` method addresses these by:
- Pruning the vector network to match DEM resolution using Total Upstream Channel Length (TUCL)
- Rasterizing streams with link ID values (not boolean) to track topology
- Using a modified priority-flood that integrates depression removal into flow-direction assignment
- Performing a breach-burn that lowers cells by **only the minimum amount needed** (0.001 elevation units) for monotonic drainage

A critical design point: the priority-flood operation produces the flow-direction raster directly — **no separate depression removal step is needed** (Lindsay, 2016, p. 663). The breach-burned DEM is a secondary output "only useful for visualization and in cases where the user wishes to apply an alternative flow algorithm to D8."

For LiDAR DEMs with road crossings, Lindsay recommends a more conservative approach:

> "One of the main issues with LiDAR DEM based drainage modeling... is that culverts are not present in surface models and so road and rail embankments can result in large artifact dams at road-stream crossings. Thus, an alternative, conservative method, may be to only burn a LiDAR DEM for a short distance upstream/downstream of road crossings, with the intent of removing road embankments while preserving the DEM's representation of drainage features elsewhere. This approach has been implemented as Whitebox GAT plugin tool called *Burn Streams At Roads*." (Lindsay, 2016, p. 667)

### Current Culvert_web_app approach (steps 8-11)

The current hydro-enforcement pipeline in `subroutine_nested_watershed_delineation.py` uses four steps:

1. **`create_breaklines`** (line 424) — For each pour point snapped to a road, project onto the nearest road segment and generate a perpendicular line segment of length `road_width + offset`. Requires shapely, geopandas, numpy.
2. **`adjust_dem_along_polyline`** with `burn=False` (line 2269) — Buffer road polylines by `road_fill_Dem_buffer_m`, rasterize via shapely `.buffer()` + rasterstats `rasterize`, add `+dy` to DEM under the mask. Creates road embankments. Requires rasterio, fiona, shapely, rasterstats.
3. **`adjust_dem_along_polyline`** with `burn=True` (line 2300) — Buffer breakline segments, subtract `-dy` from DEM under the mask. Punches holes through embankments at culvert locations.
4. **`wbt.breach_depressions(max_depth=None, max_length=None, fill_pits=True)`** (line 2328) — Unconstrained global breach to remove all depressions created by steps 2-3.

### Problems with this approach

**The unconstrained breach negates the spatial control.** The entire point of breaklines is to say "water should only cross roads at these specific culvert locations." But `BreachDepressions` with no `max_depth` or `max_length` constraints can carve channels anywhere — including through road embankments at locations where there is no culvert. The controlled enforcement from steps 2-3 is undone by the global breach in step 4. Lindsay (2016) explicitly designs `TopologicalBreachBurn` to avoid this problem by integrating depression removal into the priority-flood so that stream topology governs where breaching occurs.

**Fixed-depth burn is elevation-unaware.** `adjust_dem_along_polyline` adds or subtracts a constant `dy` regardless of surrounding terrain. If the stream bed is 5m below the road surface and `dy=2m`, the burn doesn't reach the stream. If the road is only 0.5m above the stream and `dy=2m`, the burn creates a 1.5m artificial depression. Both cases require `BreachDepressions` to fix, further eroding spatial control. By contrast, Lindsay's breach-burn lowers cells by the minimum decrement needed for monotonic drainage (Lindsay, 2016, p. 663).

**Heavy Python dependency chain.** The two `adjust_dem_along_polyline` calls require rasterio, fiona, shapely, rasterstats, and numpy — all for an operation that is fundamentally "modify raster cells near vector features." The `create_breaklines` function adds geopandas. These are runtime dependencies that must be installed and maintained on the server.

**Intermediate I/O.** The pipeline writes and reads three intermediate rasters (`Road_elevated_DEM`, `breaklines_burned_DEM`, `breached_filled_DEM`), each a full R×C GeoTIFF write-read cycle.

**Uses deprecated depression removal.** The `BreachDepressions` tool used in step 4 is described in WBT's own docstring as "less satisfactory, higher impact" and "provided to users for legacy reasons." Lindsay recommends `BreachDepressionsLeastCost` instead — a cost-constrained algorithm with `--dist` (max search radius) and `--max_cost` (max cumulative breach cost) parameters, described as "particularly well suited to breaching through road embankments."

### `BurnStreamsAtRoads` approach

Lindsay's `BurnStreamsAtRoads` (`whitebox-tools-app/src/tools/hydro_analysis/burn_streams_at_roads.rs`) implements the conservative LiDAR approach recommended in Lindsay (2016, p. 667):

**Inputs:** DEM + vector streams + vector roads + road embankment width

**Algorithm:**
1. Rasterize streams (1px scan-line intersection)
2. Rasterize roads, detect stream/road intersection cells via pixel overlap and 8-neighbor adjacency
3. From each intersection, walk upstream and downstream along the rasterized stream for `width / 2` cells, record the minimum elevation encountered
4. Second traversal: lower any cell above the minimum down to it

**Key properties:**
- **Spatially controlled** — only modifies the DEM at stream/road crossings, nowhere else
- **Elevation-aware** — flattens to the local stream-bed minimum rather than subtracting a fixed depth, so it never creates artificial depressions
- **No follow-up breach needed for road crossings** — since it doesn't create depressions at crossings, it doesn't require `BreachDepressions` to clean up after it
- **No Python dependencies** — runs as a single WBT subprocess, no shapely/rasterio/rasterstats
- **No intermediate I/O** — reads inputs once, writes output once

### Side-by-side

| | Current (breaklines + burn + breach) | `BurnStreamsAtRoads` |
|---|---|---|
| Modifies DEM at | Everywhere within buffer of roads/breaklines | Only at stream/road intersections |
| Depth control | Fixed `dy`, elevation-unaware | Local minimum, depression-free |
| Spatial control | Negated by unconstrained `BreachDepressions` | Preserved — no global breach needed |
| Tool calls | 3 (fill roads, burn breaklines, breach) | 1 |
| Intermediate rasters | 2 full-grid writes | 0 |
| Python dependencies | rasterio, fiona, shapely, rasterstats, geopandas, numpy | None |
| WBT tool calls | 1 (`BreachDepressions`) | 1 (`BurnStreamsAtRoads`) |

### Recommended hydro-enforcement pipeline

Based on Lindsay (2016) and the WBT tool documentation:

| Step | Tool | Purpose |
|---|---|---|
| 1 | `BurnStreamsAtRoads(dem, streams, roads, width)` | Carve through road embankments at stream crossings using local minimum elevation (Lindsay, 2016, p. 667) |
| 2 | `BreachDepressionsLeastCost(dem, dist, max_cost, fill=true)` | Handle remaining natural depressions with cost-constrained breaching |

**Why `BreachDepressionsLeastCost` for step 2:** Lindsay's recommended depression removal tool uses least-cost path analysis with two constraint parameters:
- `--dist` — maximum search radius for breach paths
- `--max_cost` — maximum cumulative elevation change allowed along a breach path

These constraints prevent the algorithm from carving long channels through road embankments or other enforced features. Depressions that exceed the cost/distance thresholds are optionally filled (`--fill true`) rather than breached. The tool's own docstring describes it as "particularly well suited to breaching through road embankments" — meaning it is designed to work cooperatively with road-crossing enforcement rather than overriding it.

**Why not unconstrained `BreachDepressions`:** The legacy `BreachDepressions` tool (used in the current pipeline with `max_depth=None, max_length=None`) has no cost model. It will breach any depression regardless of how far or deep it must carve, potentially undoing road embankment enforcement. Lindsay's own WBT docstring calls it "less satisfactory, higher impact" and recommends `BreachDepressionsLeastCost` instead.

**Why not `FillDepressions` alone:** Filling (raising) is the most conservative option and preserves road embankments. However, filling can create extensive flat areas in low-relief landscapes, producing ambiguous flow directions. Lindsay (2016, p. 663) notes that "depression breaching has an advantage over filling methods in that the flow-direction information contained within depressions are preserved; filling methods replace the interior of depressions with flat areas raised to the level of their outlets." The least-cost breach approach combines the advantages of both: it breaches where cheap to do so and fills the rest.

## References

Lindsay JB. 2016. The practice of DEM stream burning revisited. *Earth Surface Processes and Landforms*, 41(5): 658-668. DOI: 10.1002/esp.3888
