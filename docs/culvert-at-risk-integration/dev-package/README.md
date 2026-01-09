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

## Payload preparation for wepp.cloud

### Required layout
```
payload.zip
  topo/hydro-enforced-dem.tif
  topo/streams.tif
  topo/watersheds.tif              # Watershed raster (recreated by build_payload.py)
  culverts/culvert_points.geojson
  culverts/watersheds.geojson      # Unsimplified polygons (recreated by build_payload.py)
  metadata.json
  model-parameters.json
```

### Source mapping (Culvert_web_app outputs)
- DEM: `WS_deln/breached_filled_DEM_UTM.tif` -> `topo/hydro-enforced-dem.tif`
- Streams raster: `hydrogeo_vuln/main_stream_raster_UTM.tif` -> `topo/streams.tif`
- D8 flow direction: `WS_deln/D8flow_dir_UTM.tif` -> used to recreate watershed raster
- Watersheds polygons: `WS_deln/all_ws_polygon_UTM.shp` -> properties source (simplified)
- Culvert points: `WS_deln/Pour_Point_UTM.shp` -> `culverts/culvert_points.geojson`

## Culvert_web_app Data Deficiency

### Problem: Deleted intermediate files

Culvert_web_app's watershed delineation pipeline creates two valuable intermediate files
that are **deleted** after processing completes:

1. **`ws_raster_UTM.tif`** - Watershed raster where each cell's value is the FID of its
   associated pour point. This raster is essential for:
   - Spatial queries (which watershed does this pixel belong to?)
   - Accurate area calculations
   - Linking raster analysis results back to culverts

2. **`ws_polygon_UTM.shp`** - Unsimplified watershed polygons direct from raster-to-vector
   conversion. The saved version (`all_ws_polygon_UTM.shp`) has been simplified with a
   1.0m tolerance, losing significant geometric detail.

### Why this matters

The simplification reduces vertices by **30-300x** per watershed:

| Point_ID | Unsimplified | Simplified | Reduction |
|---------:|-------------:|-----------:|----------:|
| 130 | 3,958 | 62 | 64x |
| 162 | 5,608 | 49 | 114x |
| 112 | 1,575 | 5 | 315x |

Meanwhile, Culvert_web_app saves **44 other TIF files** (~5.5 GB) including duplicates
and categorized versions of PRISM, NLCD, slope, and soil data - but deletes the one
raster that uniquely identifies watershed membership.

### Code locations

The deletion occurs in `subroutine_nested_watershed_delineation.py`:

```python
# Line 1198: Creates unsimplified polygons (temporary)
wbt.raster_to_vector_polygons(i=output_watershed_raster_path, output=watershed_polygon_path)

# Line 1213: Simplifies with 1.0m tolerance before saving
watershed_poly_gdf_merged = simplify_geometry(watershed_poly_gdf_merged, tolerance=1.0)
```

The temp directory containing `ws_raster_UTM.tif` and `ws_polygon_UTM.shp` is deleted
after the task completes.

### How build_payload.py compensates

The `build_payload.py` script **reconstructs** these deleted resources:

1. **Checks for existing `ws_raster_UTM.tif`** - uses it if present (future-proofing
   for when Culvert_web_app is fixed)

2. **Recreates watershed raster** using WhiteboxTools:
   ```python
   wbt.watershed(
       d8_pntr=d8_pointer_path,      # WS_deln/D8flow_dir_UTM.tif
       pour_pts=pour_points_path,     # WS_deln/Pour_Point_UTM.shp
       output=output_raster_path      # topo/watersheds.tif
   )
   ```

3. **Converts to unsimplified vector polygons**:
   ```python
   wbt.raster_to_vector_polygons(i=ws_raster, output=ws_vector_shp)
   ```

4. **Merges properties** from the simplified source (`all_ws_polygon_UTM.shp`) into
   the unsimplified polygons, preserving `Point_ID` and all calculated attributes
   (area, slope, time of concentration, etc.)

### Recommended fix for Culvert_web_app

Modify `watershed_delineation_task.py` to preserve these files:

```python
# Add to output paths (around line 120):
ws_raster_UTM_path = os.path.join(user_output_WS_deln_path, "ws_raster_UTM.tif")
ws_polygon_unsimplified_path = os.path.join(user_output_WS_deln_path, "ws_polygon_unsimplified_UTM.shp")

# Copy from temp before cleanup (around line 570):
shutil.copy2(ws_raster_temporary_path, ws_raster_UTM_path)
# Save unsimplified polygons before simplification in subroutine
```

### Contract notes
- CRS must match across rasters and GeoJSON; record `crs.proj4` in `metadata.json`.
- `Point_ID` is required in both GeoJSON files.
- `watersheds.geojson` contains unsimplified polygons with full vertex detail.
- `watersheds.tif` cell values correspond to pour point FID (link via Point_ID).
- Streams are pre-computed; no `mcl`/`csa` parameters in `model-parameters.json`.
- Payload hash/size are computed by wepp.cloud at upload time (optional request params).
- `source.project_id` uses a sanitized project name (non-alphanumeric -> underscore, trimmed).

### Baseline fixture
Use the `Santee_10m_no_hydroenforcement` project as the canonical dev payload:
`/wc1/culvert_app_instance_dir/user_data/1_outputs/Santee_10m_no_hydroenforcement`.

### Pre-built test payloads
Ready-to-use payloads are available in the test fixtures:
```
tests/culverts/test_payloads/santee_10m_no_hydroenforcement/payload.zip  (~1.5 MB)
tests/culverts/test_payloads/Hubbard_Brook_Experimental_Forest/payload.zip  (~117 MB)
```

Use for quick testing without rebuilding:
```bash
# Small test payload
WEPPCLOUD_HOST=wc.bearhive.duckdns.org python scripts/submit_payload.py \
  --payload /workdir/wepppy/tests/culverts/test_payloads/santee_10m_no_hydroenforcement/payload.zip

# Larger payload with unsimplified watersheds
WEPPCLOUD_HOST=wc.bearhive.duckdns.org python scripts/submit_payload.py \
  --payload /workdir/wepppy/tests/culverts/test_payloads/Hubbard_Brook_Experimental_Forest/payload.zip
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
