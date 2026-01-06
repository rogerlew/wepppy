# Scripts
Scripts in this directory are meant to be copyable into Culvert_web_app with minimal edits.

## Pre-Built Test Payload

A ready-to-use Santee payload is available for quick testing:
```
tests/culverts/test_payloads/santee_10m_no_hydroenforcement/payload.zip  (~1.5 MB)
```

Quick submit to test server:
```bash
WEPPCLOUD_HOST=wc.bearhive.duckdns.org python submit_payload.py \
  --payload /workdir/wepppy/tests/culverts/test_payloads/santee_10m_no_hydroenforcement/payload.zip
```

## build_payload.py - Payload Builder

Creates `payload.zip` from a Culvert_web_app project for submission to wepp.cloud.

### Requirements

- Python 3.9+
- GDAL/OGR command-line tools: `gdalinfo`, `ogrinfo`, `ogr2ogr`, `gdalsrsinfo`

### Usage

```bash
# From the user_data directory
cd /wc1/culvert_app_instance_dir/user_data

# Basic usage - auto-discovers project across user directories
python /path/to/build_payload.py "Santee_10m_no_hydroenforcement"

# Specify user ID (if project exists in multiple user directories)
python build_payload.py "Santee_10m_no_hydroenforcement" --user-id 1

# Custom output path
python build_payload.py "Santee_10m_no_hydroenforcement" -o /tmp/my_payload.zip

# Dry run - validate without creating files
python build_payload.py "Santee_10m_no_hydroenforcement" --dry-run

# Extract to directory for inspection
python build_payload.py "Santee_10m_no_hydroenforcement" --out-dir ./payload_contents

# With model parameter overrides
python build_payload.py "Santee_10m_no_hydroenforcement" \
    --nlcd-db custom_nlcd.db \
    --base-project-runid lt_wepp_template
```

### Required Source Files

The script expects these files in the Culvert_web_app project:

| Source Path | Payload Path | Description |
|-------------|--------------|-------------|
| `outputs/{project}/WS_deln/breached_filled_DEM_UTM.tif` | `topo/hydro-enforced-dem.tif` | Hydro-enforced DEM |
| `outputs/{project}/hydrogeo_vuln/main_stream_raster_UTM.tif` | `topo/streams.tif` | Stream network raster |
| `outputs/{project}/WS_deln/Pour_Point_UTM.shp` | `culverts/culvert_points.geojson` | Culvert locations |
| `outputs/{project}/WS_deln/all_ws_polygon_UTM.shp` | `culverts/watersheds.geojson` | Watershed polygons |

### Output Payload Structure

```
payload.zip
  topo/
    hydro-enforced-dem.tif    # Copy of breached_filled_DEM_UTM.tif
    streams.tif               # Copy of main_stream_raster_UTM.tif
  culverts/
    culvert_points.geojson    # Converted from Pour_Point_UTM.shp
    watersheds.geojson        # Converted from all_ws_polygon_UTM.shp
  metadata.json               # Project metadata (schema v1)
  model-parameters.json       # Model configuration (schema v1)
```

### Validation

The script validates:
- All required files exist
- `Point_ID` attribute exists in both shapefiles
- CRS matches across all rasters and vectors (proj4 comparison)

### Example: Testing with Santee_10m_no_hydroenforcement

```bash
# Navigate to user_data directory
cd /wc1/culvert_app_instance_dir/user_data

# Run dry-run first to validate
python /workdir/wepppy/docs/culvert-at-risk-integration/dev-package/scripts/build_payload.py \
    "Santee_10m_no_hydroenforcement" --dry-run

# Build actual payload
python /workdir/wepppy/docs/culvert-at-risk-integration/dev-package/scripts/build_payload.py \
    "Santee_10m_no_hydroenforcement" \
    --output santee_payload.zip \
    --out-dir santee_payload_contents

# Inspect contents
ls -la santee_payload_contents/
cat santee_payload_contents/metadata.json
```

### JSON Schemas

#### metadata.json (v1)

```json
{
  "schema_version": "1.0",
  "source": {
    "system": "Culvert_web_app",
    "project_name": "Santee_10m_no_hydroenforcement"
  },
  "created_at": "2026-01-05T15:30:00+00:00",
  "culvert_count": 63,
  "crs": {
    "proj4": "+proj=utm +zone=17 +datum=WGS84 +units=m +no_defs"
  },
  "dem": {
    "path": "topo/hydro-enforced-dem.tif",
    "width": 1234,
    "height": 5678,
    "resolution_m": 9.33,
    "nodata": -9999
  },
  "streams": {
    "path": "topo/streams.tif",
    "nodata": 0
  },
  "culvert_points": {
    "path": "culverts/culvert_points.geojson",
    "feature_count": 63,
    "point_id_field": "Point_ID"
  },
  "watersheds": {
    "path": "culverts/watersheds.geojson",
    "feature_count": 36,
    "point_id_field": "Point_ID"
  }
}
```

#### model-parameters.json (v1)

```json
{
  "schema_version": "1.0",
  "base_project_runid": "lt_wepp_template",
  "nlcd_db": "custom_nlcd.db"
}
```

All fields except `schema_version` are optional.

## submit_payload.py - SSL Payload Submission

Uploads `payload.zip` to the wepp.cloud culvert batch endpoint and polls until job completion.

### Requirements

- Python 3.9+
- `requests` library (`pip install requests`)

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WEPPCLOUD_HOST` | `wepp.cloud` | Target host (no protocol prefix) |

### Usage

```bash
# Submit to production (wepp.cloud)
python submit_payload.py --payload /path/to/payload.zip

# Submit to test server
WEPPCLOUD_HOST=wc.bearhive.duckdns.org python submit_payload.py --payload payload.zip

# Or use --host flag
python submit_payload.py --payload payload.zip --host wc.bearhive.duckdns.org

# With pre-computed hash/size (skips local computation)
python submit_payload.py --payload payload.zip \
    --zip-sha256 abc123def456... \
    --total-bytes 12345678

# Custom polling configuration
python submit_payload.py --payload payload.zip \
    --poll-seconds 10 \
    --timeout-seconds 7200
```

### CLI Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--payload` | Yes | - | Path to payload.zip |
| `--host` | No | `WEPPCLOUD_HOST` or `wepp.cloud` | Target host |
| `--zip-sha256` | No | (computed) | SHA256 hash of payload |
| `--total-bytes` | No | (computed) | Payload size in bytes |
| `--poll-seconds` | No | 5 | Polling interval |
| `--timeout-seconds` | No | 3600 | Maximum wait time |

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
cd /wc1/culvert_app_instance_dir/user_data
python /workdir/wepppy/docs/culvert-at-risk-integration/dev-package/scripts/build_payload.py \
    "Santee_10m_no_hydroenforcement" \
    --output santee_payload.zip

# 2. Submit to test server and wait for completion
WEPPCLOUD_HOST=wc.bearhive.duckdns.org \
python /workdir/wepppy/docs/culvert-at-risk-integration/dev-package/scripts/submit_payload.py \
    --payload santee_payload.zip

# 3. Results will be available at:
#    https://wc.bearhive.duckdns.org/culverts/<batch_uuid>/browse/
```

### Observability

The script logs each step with timestamps:

```
2026-01-05 10:30:00 [INFO] ============================================================
2026-01-05 10:30:00 [INFO] Culvert Batch Payload Submission
2026-01-05 10:30:00 [INFO] ============================================================
2026-01-05 10:30:00 [INFO] Host: wc.bearhive.duckdns.org
2026-01-05 10:30:00 [INFO] Base URL: https://wc.bearhive.duckdns.org
2026-01-05 10:30:00 [INFO] Upload target: https://wc.bearhive.duckdns.org/rq-engine/api/culverts-wepp-batch/
2026-01-05 10:30:00 [INFO] Payload file: santee_payload.zip
2026-01-05 10:30:00 [INFO] Payload size: 45,678,901 bytes
2026-01-05 10:30:01 [INFO] Computing SHA256 hash...
2026-01-05 10:30:02 [INFO] Payload SHA256: abc123def456...
2026-01-05 10:30:02 [INFO] Uploading payload...
2026-01-05 10:30:15 [INFO] Upload completed in 13.2s, status: 200
2026-01-05 10:30:15 [INFO] Response: job_id=abc-123-def
2026-01-05 10:30:15 [INFO] Response: culvert_batch_uuid=xyz-789-uvw
2026-01-05 10:30:15 [INFO] Response: status_url=/rq-engine/api/jobstatus/abc-123-def
2026-01-05 10:30:15 [INFO] ------------------------------------------------------------
2026-01-05 10:30:15 [INFO] Polling status: https://wc.bearhive.duckdns.org/rq-engine/api/jobstatus/abc-123-def
2026-01-05 10:30:15 [INFO] Poll interval: 5s, timeout: 3600s
2026-01-05 10:30:15 [INFO] Poll 1 (0s): status=started
2026-01-05 10:35:20 [INFO] Poll 61 (305s): status=started
2026-01-05 10:40:25 [INFO] Job completed successfully after 610.2s
2026-01-05 10:40:25 [INFO] ============================================================
2026-01-05 10:40:25 [INFO] Final Summary
2026-01-05 10:40:25 [INFO] ============================================================
2026-01-05 10:40:25 [INFO] Job ID: abc-123-def
2026-01-05 10:40:25 [INFO] Batch UUID: xyz-789-uvw
2026-01-05 10:40:25 [INFO] Final Status: finished
2026-01-05 10:40:25 [INFO] Browse results: https://wc.bearhive.duckdns.org/culverts/xyz-789-uvw/browse/
```
