<!-- AGENT DIRECTIVE: This documentation is for human developers integrating with wepp.cloud.
     DO NOT summarize, condense, or remove details from this file. All sections, examples,
     directory trees, and tables are intentionally comprehensive. Preserve all content,
     unless it is inaccurate. -->

# Culvert_web_app dev package
> Handoff doc for WEPPcloud's culverts API.

## Audience

Culvert_web_app developers and stakeholders integrating with the wepp.cloud culvert batch API.

## Purpose
- Provide a readable, minimal payload builder for Culvert_web_app developers.
- Keep the payload contract aligned with `weppcloud-integration.spec.md`.
- Submit payloads over SSL and poll until completion.

## Layout
- `README.md` (this file)
- `weppcloud-wbt-unnest-basins-migration-guide.md` (migration design for sidecar-driven nested watershed delineation)
- `scripts/` (payload builder and submission tools)
  - `build_payload.py` - Build payload.zip from Culvert_web_app outputs
  - `submit_payload.py` - Submit payload.zip to wepp.cloud over SSL

## Quick Start

1. Build a payload from Culvert_web_app outputs using `build_payload.py`
2. POST to `https://{host}/rq-engine/api/culverts-wepp-batch/`
3. Poll `status_url` until job completes
4. Download `weppcloud_run_skeletons.zip` from `https://{host}/weppcloud/culverts/{batch_uuid}/download/weppcloud_run_skeletons.zip`
5. (Optional) Browse results interactively at `https://{host}/weppcloud/culverts/{batch_uuid}/browse/`

## Authentication (JWT)

`/rq-engine/api/culverts-wepp-batch/*` now requires a bearer token. `jobstatus`/`jobinfo` remain open
for read-only polling.

Required scopes (service token): `culvert:batch:submit`, `culvert:batch:retry`,
`culvert:batch:read`, `rq:status`.

Recommended claims: `aud=<RQ_ENGINE_JWT_AUDIENCE>` (default `rq-engine`), `token_class=service`, `service_groups=culverts`,
`jti=<uuid>` (required for revocation).

TTL guidance: culvert service tokens should default to ~90 days. Rotate or revoke on compromise
using `wctl revoke-auth-token` (see `docs/dev-notes/auth-token.spec.md`).

The `scripts/submit_payload.py` helper reads `WEPPCLOUD_TOKEN` or `--token-file` when provided.

Example minting (host):
```bash
wctl issue-auth-token culvert-app \
  --audience rq-engine \
  --scope culvert:batch:submit \
  --scope culvert:batch:retry \
  --scope culvert:batch:read \
  --scope rq:status \
  --claim token_class=service \
  --claim service_groups=culverts \
  --claim jti=deadbeefdeadbeefdeadbeefdeadbeef \
  --expires-in 7776000 \
  --json
```

Send the token as `Authorization: Bearer <token>`.

## Artifacts access (browse/download)

Successful submissions return a short-lived, **batch-scoped** bearer token (currently 7-day TTL):
- `browse_token`
- `browse_token_expires_at` (JWT `exp`, Unix timestamp seconds)

Use `browse_token` as `Authorization: Bearer <browse_token>` for:
- `GET /weppcloud/culverts/{batch_uuid}/browse/*` (interactive browse)
- `GET /weppcloud/culverts/{batch_uuid}/download/{subpath}` (programmatic download via `browse_token`; WEPPcloud also allows privileged `user` tokens for admin browse/download workflows)

## Payload preparation for wepp.cloud

### Required layout
```
payload.zip
  topo/breached_filled_DEM_UTM.tif
  topo/streams.tif
  culverts/culvert_points.geojson
  culverts/watersheds.geojson
  metadata.json
  model-parameters.json
```

### Source mapping (Culvert_web_app outputs)
| Culvert_web_app Output | Payload Path | Notes |
|------------------------|--------------|-------|
| `WS_deln/breached_filled_DEM_UTM.tif` | `topo/breached_filled_DEM_UTM.tif` | Opttionally/Hydro-conditioned DEM |
| `hydrogeo_vuln/main_stream_raster_UTM.tif` | `topo/streams.tif` | Binary stream raster |
| `WS_deln/all_ws_polygon_UTM.shp` | `culverts/watersheds.geojson` | Nested watershed polygons |
| `WS_deln/pour_points_snapped_to_RSCS_UTM.shp` | `culverts/culvert_points.geojson` | Pour points snapped to road-stream crossings |

**Note:** We use RSCS-snapped pour points (snapped to Road-Stream Crossing Sites) rather than
the original `Pour_Point_UTM.shp`. This ensures culvert points are on the stream network,
improving outlet detection fidelity in wepp.cloud.

**Open Standards Preference:** wepp.cloud uses **GeoTIFF** (OGC) and **GeoJSON** (IETF RFC 7946)—open,
nonproprietary formats. This ensures compatibility with domestic and international open data
requirements:

| Organization | Scope | Relevant Standards |
|--------------|-------|-------------------|
| FGDC (US) | US Federal agencies | FGDC-endorsed formats (GeoTIFF, GeoJSON, OGC services) |
| INSPIRE (EU) | EU Member States | OGC/ISO-based (GML, WMS/WFS, ISO 191xx metadata) |
| USGS, EPA, NGA | US agencies | GeoTIFF, GeoJSON, OGC web services |
| National SDIs | India, UK, Australia, etc. | OGC/ISO, FAIR principles |

Shapefiles are converted to GeoJSON during payload creation to maintain open format compliance.

### `metadata.json` schema

```json
{
  "schema_version": "culvert-metadata-v1",
  "source": {
    "system": "Culvert_web_app",
    "project_id": "Santee_10m_no_hydroenforcement",
    "user_id": "1"
  },
  "created_at": "2026-01-11T10:30:00+00:00",
  "culvert_count": 63,
  "crs": {
    "proj4": "+proj=utm +zone=17 +datum=WGS84 +units=m +no_defs"
  },
  "dem": {
    "path": "topo/breached_filled_DEM_UTM.tif",
    "width": 833,
    "height": 789,
    "resolution_m": 9.33,
    "nodata": 0.0
  },
  "streams": {
    "path": "topo/streams.tif",
    "nodata": -32768.0,
    "value_semantics": "binary"
  },
  "culvert_points": {
    "path": "culverts/culvert_points.geojson",
    "feature_count": 63,
    "point_id_field": "Point_ID"
  },
  "watersheds": {
    "path": "culverts/watersheds.geojson",
    "feature_count": 36,
    "point_id_field": "Point_ID",
    "simplified": true,
    "simplification_tolerance_m": 1.0
  },
  "flow_accum_threshold": 100,
  "hydro_enforcement_select": "hydroenf_required"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | Yes | Schema version identifier (`culvert-metadata-v1`) |
| `source.system` | string | Yes | Source system name (`Culvert_web_app`) |
| `source.project_id` | string | Yes | Sanitized project name |
| `source.user_id` | string | No | User identifier from source system |
| `created_at` | string | Yes | ISO 8601 timestamp |
| `culvert_count` | integer | Yes | Number of culvert points |
| `crs.proj4` | string | Yes | Proj4 string for coordinate reference system |
| `dem.*` | object | Yes | DEM metadata (path, dimensions, resolution, nodata) |
| `streams.*` | object | Yes | Streams raster metadata |
| `culvert_points.*` | object | Yes | Culvert points metadata |
| `watersheds.*` | object | Yes | Watersheds metadata |
| `flow_accum_threshold` | integer | No | Flow accumulation threshold from Culvert_web_app |
| `hydro_enforcement_select` | string | No | Hydro-enforcement select value from `user_ws_deln_responses.txt` |

### `model-parameters.json` schema

```json
{
  "schema_version": "culvert-model-params-v1",
  "flow_accum_threshold": 100,
  "order_reduction_passes": 2
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | Yes | Schema version identifier (`culvert-model-params-v1`) |
| `flow_accum_threshold` | integer | No | Flow accumulation threshold (for order-reduction mapping) |
| `order_reduction_passes` | integer | No | Override stream network pruning passes |
| `base_project_runid` | string | No | Base project runid for template parameters |
| `nlcd_db` | string | No | NLCD database path override |

## Culvert Point Validation

wepp.cloud validates that each culvert's pour point is inside its associated watershed polygon
(with a 30m buffer to account for simplification and snapping tolerances). Culverts failing
this check are skipped to ensure the modeled watershed matches the intended catchment area.

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
- **CRS must be UTM.** wepp.cloud expects all rasters and GeoJSON files in a projected UTM coordinate
  system. The CRS must match across all files; record `crs.proj4` in `metadata.json`. Current
  Culvert_web_app enforces this constraint.
- **`Point_ID` is required** in both `culvert_points.geojson` and `watersheds.geojson`. The value
  can be integer or string in the source GeoJSON; wepp.cloud treats it as a string internally.
  Each watershed must have a matching culvert point by `Point_ID`.
- `watersheds.geojson` polygons are simplified (1.0m tolerance) unless you modify the source.
- Streams are pre-computed; no `mcl`/`csa` parameters in `model-parameters.json`.
- `flow_accum_threshold` is extracted from `user_ws_deln_responses.txt` and included in `model-parameters.json`; it only drives order-reduction pass mapping when `order_reduction_mode=map` and does not trigger stream extraction.
- `order_reduction_passes` can be added to `model-parameters.json` to override the mapped/default pass count.
- Payload hash/size are computed by wepp.cloud at upload time (optional request params).
- `source.project_id` uses a sanitized project name (non-alphanumeric -> underscore, trimmed).

## Minimum Watershed Size Filter

wepp.cloud skips culverts whose rasterized watershed area falls below a configurable threshold
(default: 100 m²). This filters out micro-catchments that are too small for meaningful WEPP
modeling and often result from snapping artifacts or DEM noise.

**Impact on small watersheds** (Hubbard Brook dataset, 127 culverts with <1 ha watersheds):

```
  ┌──────────────────┬─────────┬──────┬────────┐
  │  Min Threshold   │ Removed │ Kept │ % Kept │
  ├──────────────────┼─────────┼──────┼────────┤
  │ 10 m²            │      11 │  116 │    91% │
  ├──────────────────┼─────────┼──────┼────────┤
  │ 100 m² (0.01 ha) │      56 │   71 │    56% │  ← default
  ├──────────────────┼─────────┼──────┼────────┤
  │ 500 m² (0.05 ha) │      78 │   49 │    39% │
  ├──────────────────┼─────────┼──────┼────────┤
  │ 1000 m² (0.1 ha) │     100 │   27 │    21% │
  └──────────────────┴─────────┴──────┴────────┘
```

Culverts filtered by this threshold are marked `skipped_no_outlet` in batch results with
error `WatershedAreaBelowMinimumError`.

## Stream Network Handling

`flow_accum_threshold` in Culvert_web_app is cell-count based (default 100). For high-resolution
DEMs, this yields a much denser stream network than coarser DEMs.

wepp.cloud automatically simplifies the stream network at batch ingest using **Strahler stream
order pruning**. This process removes first-order (headwater) streams from the network, reducing
complexity while preserving the main drainage structure. Each pruning pass:
1. Computes Strahler order for all stream segments
2. Removes order-1 (smallest headwater) streams
3. Decrements the order of remaining streams

The number of pruning passes is determined by DEM resolution:
| DEM Resolution | Pruning passes | Effect |
|----------------|----------------|--------|
| 1m | 3 passes | Removes order 1, 2, and 3 streams |
| 4m | 2 passes | Removes order 1 and 2 streams |
| 10m+ | 1 pass | Removes order 1 streams only |

This keeps hillslope counts and runtimes manageable without requiring changes in Culvert_web_app.
You can override this by setting `order_reduction_passes` in `model-parameters.json` if needed.

## WEPPcloud Model Parameters

wepp.cloud uses the following data sources and configurations for culvert batch runs:

| Parameter | Value | Notes |
|-----------|-------|-------|
| Delineation backend | [weppcloud-wbt](https://github.com/rogerlew/weppcloud-wbt) | WhiteboxTools fork with TOPAZ-style hillslope identifiers |
| Land use | [NLCD 2024 Ever Forest](https://github.com/rogerlew/us-conus-nlcd-ever-forest) | NLCD with persistent forest classification |
| Soils | gNATSGO 2024 | Gridded National Soil Survey Geographic Database |
| Climate | PRISM stochastic | 51-year simulation using closest climate station |

### Outlet Finding Algorithm

wepp.cloud does not use the culvert point directly as the watershed outlet. Instead, it uses the
[FindOutlet](https://github.com/rogerlew/weppcloud-wbt) algorithm to locate a hydrologically valid
outlet on the stream network. This ensures the modeled watershed actually drains to a stream cell
rather than an arbitrary point.

**Why not use the exact culvert location?**
- The culvert point may be slightly off the stream centerline due to GPS error or snapping tolerances
- WEPP requires the outlet to be on a stream cell with proper junction topology
- The FindOutlet algorithm validates that flow actually reaches the outlet

**Algorithm overview:**
1. Build a raster mask from the watershed polygon
2. Compute the centroid and identify perimeter cells
3. Rank interior cells by distance from boundary (deepest interior first)
4. For each candidate, trace D8 flow downstream until reaching the watershed boundary
5. Accept the first boundary cell that is on a stream with junction count = 1

The outlet coordinates in `run_metadata.json` reflect the algorithmically determined outlet, which
may differ slightly from the input culvert point. The `culvert_outlet_distance_m` validation metric
captures this offset.

**Single-hillslope fallback for streamless watersheds:**

When a culvert watershed contains no stream pixels (common for very small catchments or areas where
the stream network was pruned), FindOutlet fails. wepp.cloud implements a fallback:

1. Parse the FindOutlet error to find where all flow candidates converge
2. If candidates converge to a single location, use that as a "seed" outlet
3. Mark the seed cell and one upstream neighbor as stream pixels
4. Retry FindOutlet with the seeded stream network
5. The result is a minimal single-channel watershed suitable for WEPP modeling

This fallback ensures small watersheds without mapped streams can still be processed, producing
valid erosion estimates based on the terrain and land cover even without explicit channel routing.

### Watershed Abstraction with Representative Flowpaths

For culvert batch processing, wepp.cloud uses **representative flowpath mode** to dramatically reduce
hillslope delineation time. This is implemented in [peridot](https://github.com/wepp-in-the-woods/peridot),
a Rust-based watershed abstraction tool.

**Standard mode** (used for interactive WEPPcloud runs):
- Traces a flowpath from every pixel in the hillslope boundary
- Aggregates all flowpaths into a weighted-average slope profile
- Produces detailed per-pixel flowpath metadata
- Processing time scales with watershed pixel count

**Representative flowpath mode** (used for culvert batches):
- Selects a single "seed" cell per hillslope using distance-to-channel analysis
- Traces one flowpath from the median-distance source cell
- Builds the hillslope slope profile from that single representative path
- Skips per-pixel flowpath generation entirely

This reduces hillslope abstraction time by 10-100x depending on watershed size, making batch
processing of hundreds of culverts feasible. The representative flowpath approach preserves
erosion modeling accuracy by selecting flowpaths that approximate median hillslope length,
avoiding bias toward longest or shortest paths.

## Building Payloads with `build_payload.py`

The `scripts/build_payload.py` script creates wepp.cloud-compatible payload.zip files from
Culvert_web_app project outputs. It uses only Python stdlib + GDAL/OGR command-line tools,
making it easy to integrate into Culvert_web_app.

### What it does

1. **Discovers** project directories from the Culvert_web_app user_data layout
2. **Validates** all required files exist and have correct attributes
3. **Extracts metadata** from rasters (gdalinfo) and vectors (ogrinfo)
4. **Validates alignment**:
   - CRS matches across all files (proj4 comparison)
   - DEM and streams have identical dimensions and resolution
   - Point_ID attribute exists in both culvert points and watersheds
   - All watershed Point_IDs map to culvert Point_IDs
5. **Converts** shapefiles to GeoJSON (ogr2ogr)
6. **Generates** `metadata.json` and `model-parameters.json`
7. **Creates** the final `payload.zip`

### Requirements

- Python 3.9+
- GDAL/OGR command-line tools: `gdalinfo`, `ogrinfo`, `ogr2ogr`, `gdalsrsinfo`

### CLI Usage

```bash
# Basic usage - auto-discovers project in user_data directories
python build_payload.py "MyProject"

# Specify user ID if project exists in multiple user directories
python build_payload.py "MyProject" --user-id 1

# Custom output path
python build_payload.py "MyProject" --output /path/to/payload.zip

# Dry run - validate without creating files
python build_payload.py "MyProject" --dry-run

# Extract payload contents for inspection
python build_payload.py "MyProject" --out-dir ./payload_contents

# With model parameter overrides
python build_payload.py "MyProject" \
    --nlcd-db custom_nlcd.db \
    --base-project-runid lt_wepp_template
```

### CLI Options

| Option | Description |
|--------|-------------|
| `project` | Project name (required) |
| `--base-dir` | Base user_data directory (default: `/wc1/culvert_app_instance_dir/user_data`) |
| `--user-id` | User ID to disambiguate projects |
| `--output`, `-o` | Output ZIP path (default: `payload.zip`) |
| `--out-dir` | Also extract payload to directory for inspection |
| `--dry-run`, `-n` | Validate only, don't create files |
| `--nlcd-db` | NLCD database override for model-parameters.json |
| `--base-project-runid` | Base project runid for model-parameters.json |

### Programmatic Usage (Module Integration)

The script can be imported and used programmatically in Culvert_web_app workflows:

```python
from pathlib import Path
from build_payload import build_payload, PayloadError

# Build payload after watershed delineation completes
try:
    build_payload(
        project_name="MyProject",
        base_dir=Path("/path/to/user_data"),
        output_path=Path("/path/to/payload.zip"),
        user_id=1,                          # Optional: specify user
        out_dir=Path("/path/to/inspect"),   # Optional: extract for inspection
        dry_run=False,                      # Set True to validate only
        nlcd_db=None,                       # Optional: NLCD override
        base_project_runid=None,            # Optional: base project
    )
    print("Payload created successfully")
except PayloadError as e:
    print(f"Payload build failed: {e}")
```

### Integration into Culvert_web_app Task Pipeline

To automatically build payloads after watershed delineation:

```python
# In your task completion handler (e.g., after hydrogeo_vuln completes)
from build_payload import build_payload, PayloadError

def on_analysis_complete(user_id: int, project_name: str, user_data_dir: Path):
    """Called when watershed + hydrogeo analysis completes."""

    payload_path = user_data_dir / f"{user_id}_outputs" / project_name / "payload.zip"

    try:
        build_payload(
            project_name=project_name,
            base_dir=user_data_dir,
            output_path=payload_path,
            user_id=user_id,
        )
        # Payload ready for submission to wepp.cloud
        return payload_path
    except PayloadError as e:
        # Log validation failure - missing files, CRS mismatch, etc.
        logger.error(f"Payload build failed for {project_name}: {e}")
        return None
```

### Validation Errors

The script raises `PayloadError` with descriptive messages for:

| Error | Cause |
|-------|-------|
| Missing required files | DEM, streams, culvert points, or watersheds not found |
| CRS mismatch | Files have different coordinate systems |
| Raster dimension mismatch | DEM and streams have different width/height |
| Missing Point_ID | Culvert points or watersheds lack Point_ID attribute |
| Unmapped watershed IDs | Watershed Point_ID not found in culvert points |

### Helper Functions

The module exposes these functions for custom workflows:

```python
from build_payload import (
    get_raster_metadata,      # Extract width, height, resolution, CRS, nodata
    get_vector_metadata,      # Extract feature count, geometry type, CRS, has_point_id
    convert_to_geojson,       # Convert shapefile to GeoJSON
    validate_crs_alignment,   # Check all files share same CRS
    validate_raster_alignment,# Check DEM/streams dimensions match
    sanitize_project_id,      # Normalize project name for metadata
    extract_flow_accum_threshold,  # Read from user_ws_deln_responses.txt
)
```

## SSL Payload Submission with `submit_payload.py`

The `scripts/submit_payload.py` script uploads `payload.zip` to the wepp.cloud culvert batch
endpoint, polls until job completion, and reports the final status.

### Requirements

- Python 3.9+
- `requests` library (`pip install requests`)

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WEPPCLOUD_HOST` | `wepp.cloud` | Target host (no protocol prefix) |
| `WEPPCLOUD_TOKEN` | unset | Bearer token for authenticated endpoints |

### CLI Usage

```bash
# Submit to production (wepp.cloud)
python scripts/submit_payload.py --payload payload.zip

# Submit with bearer token (required for culvert endpoints)
WEPPCLOUD_TOKEN=token-value python scripts/submit_payload.py --payload payload.zip

# Submit to test server (development)
WEPPCLOUD_HOST=wc.bearhive.duckdns.org python scripts/submit_payload.py --payload payload.zip

# Or use --host flag
python scripts/submit_payload.py --payload payload.zip --host wc.bearhive.duckdns.org

# With pre-computed hash/size (skips local computation)
python scripts/submit_payload.py --payload payload.zip \
    --zip-sha256 abc123def456... \
    --total-bytes 12345678

# Custom polling configuration
python scripts/submit_payload.py --payload payload.zip \
    --poll-seconds 1 \
    --timeout-seconds 7200

# Provide token via file
python scripts/submit_payload.py --payload payload.zip --token-file /path/to/token.txt
```

### CLI Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--payload` | Yes | - | Path to payload.zip |
| `--host` | No | `WEPPCLOUD_HOST` or `wepp.cloud` | Target host |
| `--zip-sha256` | No | (computed) | SHA256 hash of payload |
| `--total-bytes` | No | (computed) | Payload size in bytes |
| `--poll-seconds` | No | 5 | Polling interval in seconds |
| `--timeout-seconds` | No | 3600 | Maximum wait time in seconds |
| `--token` | No | `WEPPCLOUD_TOKEN` | Bearer token for authenticated endpoints |
| `--token-file` | No | - | Read bearer token from file |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Job completed successfully |
| 1 | Job failed or error occurred |
| 2 | Timeout exceeded |
| 3 | Invalid arguments or payload not found |

### Example: End-to-End Workflow

```bash
# 1. Build the payload
python scripts/build_payload.py "MyProject" --output payload.zip

# 2. Submit to test server and wait for completion
WEPPCLOUD_HOST=wc.bearhive.duckdns.org \
WEPPCLOUD_TOKEN=$MY_TOKEN \
python scripts/submit_payload.py --payload payload.zip

# 3. Results will be available at:
#    https://wc.bearhive.duckdns.org/weppcloud/culverts/<batch_uuid>/browse/
```

### Observability Output

The script logs each step with timestamps:

```
2026-01-05 10:30:00 [INFO] ============================================================
2026-01-05 10:30:00 [INFO] Culvert Batch Payload Submission
2026-01-05 10:30:00 [INFO] ============================================================
2026-01-05 10:30:00 [INFO] Host: wc.bearhive.duckdns.org
2026-01-05 10:30:00 [INFO] Payload file: payload.zip
2026-01-05 10:30:00 [INFO] Payload size: 45,678,901 bytes
2026-01-05 10:30:01 [INFO] Computing SHA256 hash...
2026-01-05 10:30:02 [INFO] Uploading payload...
2026-01-05 10:30:15 [INFO] Upload completed in 13.2s, status: 200
2026-01-05 10:30:15 [INFO] Response: job_id=abc-123-def
2026-01-05 10:30:15 [INFO] Response: culvert_batch_uuid=xyz-789-uvw
2026-01-05 10:30:15 [INFO] Polling status (1s interval)...
2026-01-05 10:40:25 [INFO] Job completed successfully after 610.2s
2026-01-05 10:40:25 [INFO] Browse results: https://wc.bearhive.duckdns.org/weppcloud/culverts/xyz-789-uvw/browse/
```

## Run Skeletons (`weppcloud_run_skeletons.zip`)

After batch completion, download `weppcloud_run_skeletons.zip` to retrieve model outputs:
```
https://{host}/weppcloud/culverts/{batch_uuid}/download/weppcloud_run_skeletons.zip
```
This archive contains all runs with essential outputs preserved and large intermediate
files removed.

### Why Skeletonization?

Each WEPP run generates significant intermediate data:
- Full-resolution DEM clips (can be 100+ MB for high-res LiDAR)
- Hillslope rasters and intermediate flow grids
- Temporary soil/landuse processing files
- Debug logs from profile recorders

For a batch of 50+ culverts, uncompressed outputs can exceed 50 GB. Skeletonization
reduces this to ~1-5 GB by keeping only the files needed for analysis while discarding
reproducible intermediates.

### Archive Contents

```
weppcloud_run_skeletons.zip
  runs_manifest.md              # Batch summary and per-run table
  culverts_runner.nodb          # Machine-readable batch state (JSON)
  runs/
    {point_id}/                 # One directory per culvert
      run_metadata.json         # Run status, timing, errors
      *.nodb                    # Controller state files
      *.log                     # Processing logs
      climate/                  # Climate inputs and summaries
      dem/wbt/                  # Watershed geometry (GeoJSON)
      watershed/                # Channel/hillslope attributes
      landuse/                  # Land use parquet
      soils/                    # Soil logs
      wepp/output/interchange/  # WEPP model outputs (parquet)
```

### Run Directory Structure

Each `runs/{point_id}/` directory contains:

```
{point_id}/
  run_metadata.json           # Status, timing, error details
  climate.nodb                # Climate controller state
  ron.nodb                    # DEM/topography controller state
  watershed.nodb              # Watershed controller state
  landuse.nodb                # Land use controller state
  soils.nodb                  # Soils controller state
  wepp.nodb                   # WEPP model controller state
  unitizer.nodb               # Unit conversion state
  disturbed.nodb              # Disturbance controller state
  nodb.version                # NoDb version marker
  redisprep.dump              # Redis state snapshot
  *.log                       # Processing logs for each stage

  climate/
    sc*.cli                   # CLIGEN climate file
    sc*.par                   # CLIGEN parameters
    sc*.inp                   # CLIGEN input
    wepp_cli.parquet          # Climate summary (parquet)
    wepp_cli_pds_mean_metric.csv
    atlas14_intensity_pds_mean_metric.csv

  dem/wbt/
    outlet.geojson            # Detected outlet point
    channels.geojson          # Channel network (UTM)
    channels.WGS.geojson      # Channel network (WGS84)
    subcatchments.geojson     # Subcatchment polygons (UTM)
    subcatchments.WGS.geojson # Subcatchment polygons (WGS84)
    netful.geojson            # Full stream network
    netful.WGS.geojson        # Full stream network (WGS84)
    subwta.geojson            # Subcatchment attributes
    *.vrt                     # Virtual raster references

  watershed/
    channels.parquet          # Channel attributes
    hillslopes.parquet        # Hillslope attributes
    network.txt               # Network topology summary
    structure.json            # Serialized watershed graph

  landuse/
    landuse.parquet           # Land use classification
    nlcd.vrt                  # NLCD virtual raster reference

  soils/
    *.log                     # Per-soil-unit processing logs

  wepp/output/interchange/
    interchange_version.json  # Output format version
    README.md                 # Output documentation
    # Annual summaries
    loss_pw0.out.parquet      # Watershed outlet losses
    loss_pw0.chn.parquet      # Channel losses
    loss_pw0.hill.parquet     # Hillslope losses
    loss_pw0.class_data.parquet
    # All-years time series
    loss_pw0.all_years.out.parquet
    loss_pw0.all_years.chn.parquet
    loss_pw0.all_years.hill.parquet
    loss_pw0.all_years.class_data.parquet
    # Hydrologic outputs
    totalwatsed3.parquet      # Total water/sediment
    chanwb.parquet            # Channel water balance
    chnwb.parquet             # Channel water balance (alt format)
    ebe_pw0.parquet           # Event-based erosion
    pass_pw0.events.parquet   # Pass event data
    pass_pw0.metadata.parquet # Pass metadata
    # Hillslope detail (H.* files)
    H.loss.parquet            # Hillslope losses
    H.ebe.parquet             # Hillslope event erosion
    H.element.parquet         # Hillslope elements
    H.soil.parquet            # Hillslope soils
    H.wat.parquet             # Hillslope water balance
    chan.out.parquet          # Channel outputs
    soil_pw0.parquet          # Soil outputs
```
### Key Output Files

| File | Description |
|------|-------------|
| `run_metadata.json` | Run status (`success`/`failed`), timing, error details |
| `dem/wbt/channels.geojson` | Channel network geometry for visualization |
| `dem/wbt/subcatchments.geojson` | Subcatchment boundaries for visualization |
| `watershed/channels.parquet` | Channel attributes (length, slope, contributing area) |
| `watershed/hillslopes.parquet` | Hillslope attributes (area, slope, aspect) |
| `wepp/output/interchange/loss_pw0.out.parquet` | Annual sediment/runoff at watershed outlet |
| `wepp/output/interchange/totalwatsed3.parquet` | Total water and sediment summary |

### What's NOT in the Skeleton

These files are deleted during skeletonization:
- `dem/*.tif` - Full-resolution DEM clips
- `dem/wbt/*.tif` - Intermediate raster products (flow direction, accumulation, etc.)
- `_logs/` directories - Profile recorder debug logs
- Temporary files from soil/landuse processing

If you need full rasters for a specific run, re-run that culvert individually or
request the full (non-skeletonized) output.

## API Reference

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/rq-engine/api/culverts-wepp-batch/` | Submit a payload and start batch processing |
| POST | `/rq-engine/api/culverts-wepp-batch/{batch_uuid}/retry/{point_id}` | Retry a single failed run |
| POST | `/rq-engine/api/culverts-wepp-batch/{batch_uuid}/finalize` | Rebuild batch summary artifacts after retries |
| GET | `/rq-engine/api/jobstatus/{job_id}` | Poll job status |
| GET | `/rq-engine/api/jobinfo/{job_id}` | Get detailed job info |
| GET | `/weppcloud/culverts/{batch_uuid}/browse/` | Browse batch artifacts |
| GET | `/weppcloud/culverts/{batch_uuid}/download/{subpath}` | Download artifacts (authenticated) |

### POST `/rq-engine/api/culverts-wepp-batch/`

Submit a culvert batch payload.

**Request:** `multipart/form-data`
- file field: `payload.zip` (required; `payload.zip` is the preferred form key, but `payload` / `file` are accepted aliases)
- `zip_sha256`: SHA256 hash of payload (optional, for verification)
- `total_bytes`: Payload size in bytes (optional)

**Response (200 OK):**
```json
{
  "job_id": "abc123-def456-...",
  "culvert_batch_uuid": "xyz789-uvw012-...",
  "status_url": "/rq-engine/api/jobstatus/abc123-def456-...",
  "browse_token": "eyJhbGciOi...",
  "browse_token_expires_at": 1760000000
}
```

**Response (400 Bad Request):**
```json
{
  "error": {
    "message": "Validation failed",
    "details": "Missing required file: topo/breached_filled_DEM_UTM.tif",
    "code": "validation_error"
  },
  "errors": [
    {
      "code": "missing_file",
      "message": "Missing required file: topo/breached_filled_DEM_UTM.tif",
      "path": "topo/breached_filled_DEM_UTM.tif"
    }
  ]
}
```

### POST `/rq-engine/api/culverts-wepp-batch/{batch_uuid}/retry/{point_id}`

Retry a single culvert run within an existing batch (for flake-checking or after transient failures).

**Response (200 OK):**
```json
{
  "job_id": "new-job-id-...",
  "culvert_batch_uuid": "xyz789-uvw012-...",
  "point_id": "42",
  "status_url": "/rq-engine/api/jobstatus/new-job-id-...",
  "browse_token": "eyJhbGciOi...",
  "browse_token_expires_at": 1760000000
}
```

### POST `/rq-engine/api/culverts-wepp-batch/{batch_uuid}/finalize`

Rebuild batch-level rollup artifacts (`runs_manifest.md`, `batch_summary.json`, and
`weppcloud_run_skeletons.zip`) after one or more point retries complete.

**Response (200 OK):**
```json
{
  "job_id": "finalizer-job-id-...",
  "culvert_batch_uuid": "xyz789-uvw012-...",
  "status_url": "/rq-engine/api/jobstatus/finalizer-job-id-...",
  "browse_token": "eyJhbGciOi...",
  "browse_token_expires_at": 1760000000
}
```

### GET `/rq-engine/api/jobstatus/{job_id}`

Poll job status until completion. **Recommended polling interval: 1 second.** The endpoint is
lightweight and designed for frequent polling.

**Response:**
```json
{
  "job_id": "abc123-def456-...",
  "status": "started",
  "runid": null,
  "started_at": "2026-01-05T10:30:05+00:00",
  "ended_at": null
}
```

**Status values:**
| Status | Description |
|--------|-------------|
| `queued` | Job is waiting in the queue |
| `started` | Job is currently running |
| `finished` | Job completed successfully |
| `failed` | Job failed (use `GET /rq-engine/api/jobinfo/{job_id}` plus batch artifacts for details) |
| `deferred` | Job is deferred |
| `scheduled` | Job is scheduled for later |
| `canceled` | Job was canceled |

Note: `jobstatus` is an aggregated status view and does not currently include execution error payloads.

### Artifact Access

After job completion, browse results at:
```
https://{host}/weppcloud/culverts/{batch_uuid}/browse/
```

**Progress tracking:** The browse endpoint is accessible while the batch is running. Developers can
monitor partial results as individual culvert runs complete. However, this is not recommended for
end-user interfaces—wait for job completion before presenting results.

**Webhook/callback notifications:** Push notifications for job completion are on the backlog. For
now, use polling.

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
