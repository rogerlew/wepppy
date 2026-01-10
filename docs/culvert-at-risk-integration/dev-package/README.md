# Culvert_web_app dev package
> Handoff docs and scripts for building `payload.zip` files for wepp.cloud.

## Purpose
- Provide a readable, minimal payload builder for Culvert_web_app developers.
- Keep the payload contract aligned with `weppcloud-integration.spec.md`.
- Submit payloads over SSL and poll until completion.

## Layout
- `README.md` (this file)
- `scripts/` (payload builder and submission tools)
  - `build_payload.py` - Build payload.zip from Culvert_web_app outputs
  - `submit_payload.py` - Submit payload.zip to wepp.cloud over SSL

## CRITICAL: Watershed Processing Method Requirement

**Projects must be processed with `nested_basin_delineation()` to work with wepp.cloud.**

Culvert_web_app has two watershed delineation functions:

| Function | Watershed Type | wepp.cloud Compatible |
|----------|---------------|----------------------|
| `nested_basin_delineation()` | Overlapping/nested | **Yes** |
| `delineate_watersheds_for_pour_points()` | Non-overlapping/partitioned | **No** |

### Why partitioned watersheds fail

With **partitioned** watersheds, each raster cell is assigned to exactly one pour point (the
closest downstream). This creates non-overlapping polygons that touch but don't overlap.

When combined with the 1.0m simplification tolerance, polygon boundaries shift and pour points
may fall **outside** their associated watershed polygon. wepp.cloud validates that each culvert's
pour point is inside its watershed—culverts failing this check are skipped.

### How to identify the processing method

Check the watershed shapefile for hierarchy columns:
- **Nested**: Has `is_nested`, `child_ids`, `parent_wat`, `hierarchy_` columns
- **Partitioned**: Only has `Point_ID`, `FID`, `VALUE`, area attributes

Or run `generate_project_synopsis.py` which reports "Nested (N)" or "Partitioned" in the
WS Method column.

### Current code status

The **current Culvert_web_app code uses `nested_basin_delineation()`** (the legacy function is
commented out). However, older datasets processed before this change will have partitioned
watersheds and cannot be used with wepp.cloud without reprocessing.

---

## Payload preparation for wepp.cloud

### Required layout
```
payload.zip
  topo/hydro-enforced-dem.tif
  topo/streams.tif
  culverts/culvert_points.geojson
  culverts/watersheds.geojson
  metadata.json
  model-parameters.json
```

### Source mapping (Culvert_web_app outputs)
- DEM: `WS_deln/breached_filled_DEM_UTM.tif` -> `topo/hydro-enforced-dem.tif`
- Streams raster: `hydrogeo_vuln/main_stream_raster_UTM.tif` -> `topo/streams.tif`
- Watersheds polygons: `WS_deln/all_ws_polygon_UTM.shp` -> `culverts/watersheds.geojson`
- Culvert points: `WS_deln/Pour_Point_UTM.shp` -> `culverts/culvert_points.geojson`

## CRITICAL: Watershed Simplification Issue

### Problem: weppcloud skips culverts when pour point is outside watershed polygon

**weppcloud intentionally skips running WEPP models for culverts whose pour point falls
outside their associated watershed polygon.** This is a validation check to ensure
geometric consistency.

The Culvert_web_app applies a **1.0m simplification tolerance** to watershed polygons
before saving. This simplification can shift polygon boundaries enough that pour points
that were originally inside their watershed are now outside.

### Impact on Hubbard Brook dataset

Testing with the Hubbard Brook Experimental Forest dataset (210 culverts, 187 watersheds):

| Metric | Unsimplified | Simplified (1.0m) |
|--------|-------------:|------------------:|
| Pour points inside their watershed | 208 / 210 | **116 / 210** |
| Skipped by weppcloud | 2 | **94** |

**45% of culverts will be skipped** due to simplification moving boundaries.

### Why this happens

The simplification reduces vertices by 30-300x per watershed:

| Point_ID | Unsimplified | Simplified | Reduction |
|---------:|-------------:|-----------:|----------:|
| 130 | 3,958 | 62 | 64x |
| 162 | 5,608 | 49 | 114x |
| 112 | 1,575 | 5 | 315x |

When a polygon with 5,608 vertices is reduced to 49, the boundary changes significantly.

### Solution: Provide unsimplified watersheds

If you need all culverts to run (not just the 55% whose pour points remain inside after
simplification), you must provide **unsimplified watershed polygons** in the payload.

The `watersheds.geojson` in the payload should contain polygons direct from
`wbt.raster_to_vector_polygons()` without simplification applied.

## Culvert_web_app Deleted Resources

Culvert_web_app's watershed delineation pipeline creates intermediate files that are
**deleted** after processing, making it impossible to recover unsimplified polygons:

### Deleted files (in temp directory)

1. **`ws_raster_UTM.tif`** - Watershed raster where each cell's value is the FID of its
   associated pour point. Essential for:
   - Spatial queries (which watershed does this pixel belong to?)
   - Accurate area calculations
   - Linking raster analysis results back to culverts

2. **`ws_polygon_UTM.shp`** - Unsimplified watershed polygons direct from raster-to-vector
   conversion before simplification is applied.

### Source code locations

The deletion occurs in `subroutine_nested_watershed_delineation.py`:

```python
# Line ~1198: Creates unsimplified polygons (temporary)
wbt.raster_to_vector_polygons(i=output_watershed_raster_path, output=watershed_polygon_path)

# Line ~1213: Simplifies with 1.0m tolerance BEFORE saving
watershed_poly_gdf_merged = simplify_geometry(watershed_poly_gdf_merged, tolerance=1.0)
```

The temp directory containing both files is deleted after the task completes.

### Irony

Meanwhile, Culvert_web_app saves **44 other TIF files** (~5.5 GB) including:
- Duplicate slope rasters (167 MB x4)
- Duplicate precipitation rasters (1.3 MB x4)
- Categorized versions of everything

...but deletes the 2 MB shapefile and 167 MB raster that preserve watershed boundaries.

### Recommended fix for Culvert_web_app

Modify `watershed_delineation_task.py` to preserve these files:

```python
# Add to output paths (around line 120):
ws_raster_UTM_path = os.path.join(user_output_WS_deln_path, "ws_raster_UTM.tif")
ws_polygon_unsimplified_path = os.path.join(user_output_WS_deln_path, "ws_polygon_unsimplified_UTM.shp")

# Copy from temp before cleanup (around line 570):
shutil.copy2(ws_raster_temporary_path, ws_raster_UTM_path)
# Save unsimplified polygons BEFORE calling simplify_geometry()
```

## Contract notes
- CRS must match across rasters and GeoJSON; record `crs.proj4` in `metadata.json`.
- `Point_ID` is required in both GeoJSON files.
- `watersheds.geojson` polygons are simplified (1.0m tolerance) unless you modify the source.
- Streams are pre-computed; no `mcl`/`csa` parameters in `model-parameters.json`.
- Payload hash/size are computed by wepp.cloud at upload time (optional request params).
- `source.project_id` uses a sanitized project name (non-alphanumeric -> underscore, trimmed).

### Baseline fixture
Use the `Santee_10m_no_hydroenforcement` project as the canonical dev payload:
`/wc1/culvert_app_instance_dir/user_data/1_outputs/Santee_10m_no_hydroenforcement`.

### Pre-built test payloads
Ready-to-use payloads are available in the test fixtures:
```
tests/culverts/test_payloads/santee_mini_4culverts/payload.zip  (~1.3 MB, 4 culverts, 9.33m)
tests/culverts/test_payloads/santee_10m_no_hydroenforcement/payload.zip  (~1.5 MB, 63 culverts, 9.33m)
tests/culverts/test_payloads/Hubbard_Brook_Experimental_Forest/payload.zip  (~117 MB, 210 culverts, 1.0m)
tests/culverts/test_payloads/Tallulah_River/payload.zip  (~595 MB, 49 culverts, 0.82m)
```

Use for quick testing without rebuilding:
```bash
# Minimal payload (4 culverts, fastest for dev iteration)
WEPPCLOUD_HOST=wc.bearhive.duckdns.org python scripts/submit_payload.py \
  --payload /workdir/wepppy/tests/culverts/test_payloads/santee_mini_4culverts/payload.zip

# Small payload (63 culverts, 9.33m resolution)
WEPPCLOUD_HOST=wc.bearhive.duckdns.org python scripts/submit_payload.py \
  --payload /workdir/wepppy/tests/culverts/test_payloads/santee_10m_no_hydroenforcement/payload.zip

# Medium payload (210 culverts, 1.0m, ~45% skipped due to simplified watersheds)
WEPPCLOUD_HOST=wc.bearhive.duckdns.org python scripts/submit_payload.py \
  --payload /workdir/wepppy/tests/culverts/test_payloads/Hubbard_Brook_Experimental_Forest/payload.zip

# Large payload (49 culverts, 0.82m high-res LiDAR)
WEPPCLOUD_HOST=wc.bearhive.duckdns.org python scripts/submit_payload.py \
  --payload /workdir/wepppy/tests/culverts/test_payloads/Tallulah_River/payload.zip
```

## SSL Payload Submission

After building a payload, submit it over HTTPS:

```bash
# Submit to production (wepp.cloud)
python scripts/submit_payload.py --payload payload.zip

# Submit to test server (development)
WEPPCLOUD_HOST=wc.bearhive.duckdns.org python scripts/submit_payload.py --payload payload.zip
```

The `WEPPCLOUD_HOST` environment variable controls the target host:
- Default: `wepp.cloud` (production)
- Testing: `wc.bearhive.duckdns.org`

All connections use HTTPS (no HTTP fallback).

See `scripts/README.md` for full CLI options and observability output.

## References
- `docs/culvert-at-risk-integration/weppcloud-integration.spec.md`
- `docs/culvert-at-risk-integration/weppcloud-integration.plan.md`
