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

## Quick Start

1. Build a payload from Culvert_web_app outputs (or use a pre-built test payload)
2. POST to `https://{host}/rq-engine/api/culverts-wepp-batch/`
3. Poll `status_url` until job completes
4. Browse results at `https://{host}/weppcloud/culverts/{batch_uuid}/browse/`

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
| Culvert_web_app Output | Payload Path | Notes |
|------------------------|--------------|-------|
| `WS_deln/breached_filled_DEM_UTM.tif` | `topo/hydro-enforced-dem.tif` | Hydro-conditioned DEM |
| `hydrogeo_vuln/main_stream_raster_UTM.tif` | `topo/streams.tif` | Binary stream raster |
| `WS_deln/all_ws_polygon_UTM.shp` | `culverts/watersheds.geojson` | Nested watershed polygons |
| `WS_deln/pour_points_snapped_to_RSCS_UTM.shp` | `culverts/culvert_points.geojson` | Pour points snapped to road-stream crossings |

**Note:** We use RSCS-snapped pour points (snapped to Road-Stream Crossing Sites) rather than
the original `Pour_Point_UTM.shp`. This ensures culvert points are on the stream network,
improving outlet detection fidelity in wepp.cloud.

## CRITICAL: Watershed Simplification Issue

**45% of culverts may be skipped** if you provide simplified watershed polygons.

wepp.cloud validates that each culvert's pour point is inside its associated watershed polygon
(with a configurable buffer, default 30m). Culvert_web_app applies 1.0m polygon simplification
by default, which can move polygon boundaries enough to exclude the pour point.

### Impact (Hubbard Brook dataset example)
| Metric | Unsimplified | Simplified (1.0m) |
|--------|-------------:|------------------:|
| Pour points inside watershed | 208 / 210 | **116 / 210** |
| Culverts skipped by wepp.cloud | 2 | **94** |

### Recommendation

Preserve unsimplified polygons before calling `simplify_geometry()` in
`subroutine_nested_watershed_delineation.py`:

```python
# Save unsimplified polygons BEFORE simplification
ws_polygon_unsimplified_path = os.path.join(output_path, "ws_polygon_unsimplified_UTM.shp")
watershed_poly_gdf_merged.to_file(ws_polygon_unsimplified_path)

# Then apply simplification for the standard output
watershed_poly_gdf_merged = simplify_geometry(watershed_poly_gdf_merged, tolerance=1.0)
```

Use `ws_polygon_unsimplified_UTM.shp` when building payloads for wepp.cloud.

### Culvert_web_app files deleted during processing

These files are created but deleted after processing:
- `ws_raster_UTM.tif` - Watershed raster (cell values = pour point FID)
- `ws_polygon_UTM.shp` - Unsimplified polygons before simplification

Consider retaining the unsimplified polygons if you need full culvert coverage.

## Nested vs Partitioned Watersheds

Culvert_web_app has two watershed delineation functions. **Use nested watersheds for wepp.cloud.**

| Method | Polygon Overlap | Pour Point Inside Watershed | wepp.cloud Behavior |
|--------|-----------------|----------------------------|---------------------|
| Nested (`nested_basin_delineation`) | Yes | Always (by construction) | Runs all culverts |
| Partitioned (`delineate_watersheds_for_pour_points`) | No | Maybe (simplification can move boundaries) | May skip culverts |

**Current Culvert_web_app uses nested delineation** (see `watershed_delineation_task.py` lines 2477-2498).

Check your watershed shapefile:
```python
import fiona
with fiona.open("all_ws_polygon_UTM.shp") as src:
    cols = list(src.schema["properties"].keys())
    if "is_nested" in cols or "child_ids" in cols:
        print("Nested processing - OK for wepp.cloud")
    else:
        print("Partitioned processing - may skip culverts")
```

## Contract notes
- CRS must match across rasters and GeoJSON; record `crs.proj4` in `metadata.json`.
- `Point_ID` is required in both GeoJSON files.
- `watersheds.geojson` polygons are simplified (1.0m tolerance) unless you modify the source.
- Streams are pre-computed; no `mcl`/`csa` parameters in `model-parameters.json`.
- `flow_accum_threshold` is extracted from `user_ws_deln_responses.txt` and included in `model-parameters.json`; it only drives order-reduction pass mapping when `order_reduction_mode=map` and does not trigger stream extraction.
- `order_reduction_passes` can be added to `model-parameters.json` to override the mapped/default pass count.
- Payload hash/size are computed by wepp.cloud at upload time (optional request params).
- `source.project_id` uses a sanitized project name (non-alphanumeric -> underscore, trimmed).

## Stream Network Scaling for High-Resolution DEMs

`flow_accum_threshold` in Culvert_web_app is cell-count based (default 100). For high-resolution
DEMs, this yields a much denser stream network than coarser DEMs, which can explode hillslope
counts and runtime.

### Scaling guidance

Target area: `A_target_m2 = flow_accum_threshold * (cellsize_m^2)`

To match the 30m/100-cell baseline (~90,000 m^2):
| DEM Resolution | Recommended `flow_accum_threshold` |
|----------------|-----------------------------------|
| 30m | 100 (default) |
| 10m | 900 |
| 1m | 90,000 |

### Mitigations

1. **Re-run `extract_streams`** in Culvert_web_app with a scaled threshold (best fidelity)
2. **Use `order_reduction_passes`** in `model-parameters.json` as a heuristic simplifier
   - 1m DEM: 3 passes
   - 4m DEM: 2 passes
   - 10m DEM: 1 pass (default)

### Baseline fixture
Use the `Santee_10m_no_hydroenforcement` project as the canonical dev payload:
`/wc1/culvert_app_instance_dir/user_data/1_outputs/Santee_10m_no_hydroenforcement`.

### Pre-built test payloads
Ready-to-use payloads are available in the test fixtures:
```
tests/culverts/test_payloads/santee_mini_4culverts/payload.zip  (~1.3 MB, 4 culverts, 9.33m)
tests/culverts/test_payloads/santee_10m_no_hydroenforcement/payload.zip  (~1.5 MB, 63 culverts, 9.33m)
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

# Large payload (49 culverts, 0.82m high-res LiDAR)
WEPPCLOUD_HOST=wc.bearhive.duckdns.org python scripts/submit_payload.py \
  --payload /workdir/wepppy/tests/culverts/test_payloads/Tallulah_River_Demo/payload.zip
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

## API Reference

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/rq-engine/api/culverts-wepp-batch/` | Submit a payload and start batch processing |
| POST | `/rq-engine/api/culverts-wepp-batch/{batch_uuid}/retry/{point_id}` | Retry a single failed run |
| GET | `/rq-engine/api/jobstatus/{job_id}` | Poll job status |
| GET | `/rq-engine/api/jobinfo/{job_id}` | Get detailed job info |
| GET | `/weppcloud/culverts/{batch_uuid}/browse/` | Browse batch artifacts |

### POST `/rq-engine/api/culverts-wepp-batch/`

Submit a culvert batch payload.

**Request:** `multipart/form-data`
- `file`: `payload.zip` (required)
- `zip_sha256`: SHA256 hash of payload (optional, for verification)
- `total_bytes`: Payload size in bytes (optional)

**Response (200 OK):**
```json
{
  "success": true,
  "job_id": "abc123-def456-...",
  "culvert_batch_uuid": "xyz789-uvw012-...",
  "status_url": "/rq-engine/api/jobstatus/abc123-def456-..."
}
```

**Response (400 Bad Request):**
```json
{
  "success": false,
  "error": "Validation failed",
  "error_code": "VALIDATION_ERROR",
  "error_detail": "Missing required file: topo/hydro-enforced-dem.tif"
}
```

### POST `/rq-engine/api/culverts-wepp-batch/{batch_uuid}/retry/{point_id}`

Retry a single culvert run within an existing batch (for flake-checking or after transient failures).

**Response (200 OK):**
```json
{
  "success": true,
  "job_id": "new-job-id-...",
  "culvert_batch_uuid": "xyz789-uvw012-...",
  "point_id": "42",
  "status_url": "/rq-engine/api/jobstatus/new-job-id-..."
}
```

### GET `/rq-engine/api/jobstatus/{job_id}`

Poll job status until completion.

**Response:**
```json
{
  "job_id": "abc123-def456-...",
  "status": "started",
  "queued_at": "2026-01-05T10:30:00+00:00",
  "started_at": "2026-01-05T10:30:05+00:00"
}
```

**Status values:**
| Status | Description |
|--------|-------------|
| `queued` | Job is waiting in the queue |
| `started` | Job is currently running |
| `finished` | Job completed successfully |
| `failed` | Job failed (check `error_code`, `error_detail`) |
| `deferred` | Job is deferred |
| `scheduled` | Job is scheduled for later |
| `canceled` | Job was canceled |

**Failed job response:**
```json
{
  "job_id": "abc123-def456-...",
  "status": "failed",
  "error_code": "EXECUTION_ERROR",
  "error_detail": "Run 42 failed: NoOutletFoundError - No valid outlet found"
}
```

### Artifact Access

After job completion, browse results at:
```
https://{host}/weppcloud/culverts/{batch_uuid}/browse/
```

Key artifacts:
| Path | Description |
|------|-------------|
| `runs_manifest.md` | Human-readable summary of all runs |
| `culverts_runner.nodb` | Machine-readable batch state (JSON) |
| `weppcloud_run_skeletons.zip` | Archive of skeletonized run outputs |
| `runs/{point_id}/run_metadata.json` | Per-run status and metrics |
| `runs/{point_id}/wepp/output/interchange/` | WEPP model outputs |

### Error Codes

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Payload validation failed (missing files, CRS mismatch, etc.) |
| `EXECUTION_ERROR` | Run-level error during processing |
| `CulvertPointOutsideWatershedError` | Culvert point is outside its watershed polygon |
| `WatershedAreaBelowMinimumError` | Watershed area below configured minimum |
| `NoOutletFoundError` | Could not find outlet for watershed |

### Limits

| Limit | Value |
|-------|-------|
| Max payload size | 2 GB |
| Max culverts per batch | 300 |
| Job timeout | 12 hours |

## Output Artifact Details

### `batch_summary.json`

High-level batch outcome:
```json
{
  "culvert_batch_uuid": "249b77e9-3ff0-49cc-8bc7-d94aa847a9dc",
  "total": 36,
  "succeeded": 35,
  "failed": 1,
  "skipped_no_outlet": 0
}
```

### `run_metadata.json` (per run)

**Successful run:**
```json
{
  "runid": "culvert;;249b77e9-3ff0-49cc-8bc7-d94aa847a9dc;;1040",
  "point_id": "1040",
  "culvert_batch_uuid": "249b77e9-3ff0-49cc-8bc7-d94aa847a9dc",
  "config": "culvert.cfg",
  "status": "success",
  "started_at": "2026-01-11T19:43:41.683179+00:00",
  "completed_at": "2026-01-11T20:16:36.332627+00:00",
  "duration_seconds": 1974.649448
}
```

**Failed run:**
```json
{
  "runid": "culvert;;249b77e9-3ff0-49cc-8bc7-d94aa847a9dc;;2901",
  "point_id": "2901",
  "culvert_batch_uuid": "249b77e9-3ff0-49cc-8bc7-d94aa847a9dc",
  "config": "culvert.cfg",
  "status": "failed",
  "started_at": "2026-01-11T20:16:29.235729+00:00",
  "completed_at": "2026-01-11T20:16:29.366055+00:00",
  "duration_seconds": 0.130326,
  "error": {
    "type": "RuntimeError",
    "message": "ClipRasterToRaster failed (...)"
  }
}
```

### `runs_manifest.md`

Human-readable markdown with:
- Source metadata (system, project_id, user_id, created_at)
- Batch summary (total, succeeded, failed, skipped)
- Table of all runs with:
  - `Point_ID` and watershed label
  - Subcatchment/channel counts (when available)
  - Job status and timing
  - Validation metrics (culvert/outlet coordinates, distance, area)

### `culverts_runner.nodb`

Machine-readable JSON (jsonpickle format) containing:
- Batch metadata and configuration
- Per-run records with:
  - `status`: `"success"` | `"failed"`
  - `error`: `{type, message}` when failed
  - `validation_metrics`: coordinates, distances, areas
  - `job_status`, `job_created` (when available)

### Validation Metrics

Each run includes validation metrics for QA:

| Metric | Description |
|--------|-------------|
| `culvert_easting` | Culvert point X coordinate (UTM) |
| `culvert_northing` | Culvert point Y coordinate (UTM) |
| `outlet_easting` | Detected outlet X coordinate (UTM) |
| `outlet_northing` | Detected outlet Y coordinate (UTM) |
| `culvert_outlet_distance_m` | Distance between culvert and outlet (meters) |
| `target_watershed_area_m2` | Rasterized watershed area (m^2) |
| `bounds_area_m2` | Watershed bounds area (m^2) |

Large `culvert_outlet_distance_m` values (>30m) may indicate outlet snapping issues.

## References
- `docs/culvert-at-risk-integration/weppcloud-integration.spec.md`
- `docs/culvert-at-risk-integration/weppcloud-integration.plan.md`
