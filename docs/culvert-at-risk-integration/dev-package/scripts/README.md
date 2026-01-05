# Scripts
Scripts in this directory are meant to be copyable into Culvert_web_app with minimal edits.

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
