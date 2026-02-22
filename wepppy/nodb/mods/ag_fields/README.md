# AgFields NoDb Mod (`wepppy.nodb.mods.ag_fields`)

> Manages agricultural field boundary ingestion, sub-field abstraction (Peridot), and per-sub-field WEPP runs for WEPPcloud projects.

> **See also:** [AGENTS.md](../../AGENTS.md) for NoDb locking/caching conventions and test guidance.

## Overview

This module provides the `AgFields` NoDb controller, which coordinates an “ag fields” workflow inside a WEPPcloud run working directory (`wd`). At a high level it:

- Normalizes and validates a user-supplied field boundary GeoJSON into a canonical location.
- Extracts tabular attributes (crop rotation schedule columns, IDs, etc.) into a Parquet “rotation schedule” for fast access.
- Rasterizes the field boundary polygons onto the project DEM grid for downstream tools.
- Runs Peridot “sub-field” abstraction (intersecting fields with hydrologic subwatersheds and generating representative slope files).
- Builds multi-year WEPP management files from crop rotation schedules and runs a WEPP hillslope simulation per sub-field.

The controller is stateful and persisted as `ag_fields.nodb` at the root of the working directory.

## Workflow

Typical sequence (some steps are optional depending on the UI/route calling into this module):

1. **Ingest boundaries**: `AgFields.validate_field_boundary_geojson(...)`
2. **Pick the ID column**: `AgFields.set_field_id_key(...)`
3. **Define crop column accessor**: `AgFields.set_rotation_accessor("Crop{}")`
4. **Rasterize boundaries**: `AgFields.rasterize_field_boundaries_geojson()`
5. **Abstract sub-fields (Peridot)**: `AgFields.periodot_abstract_sub_fields(...)`
6. **Polygonize sub-fields**: `AgFields.polygonize_sub_fields()`
7. **Provide crop→management mapping**: create `ag_fields/rotation_lookup.tsv` (and optionally populate `ag_fields/plant_files/` via `handle_plant_file_db_upload`)
8. **Run WEPP per sub-field**: `AgFields.run_wepp_ag_fields(max_workers=...)`

## Inputs and outputs

### Required inputs (in or relative to `wd`)

- Field boundary GeoJSON (user-supplied) containing:
  - a `field_id` attribute column (required by validation)
  - crop rotation columns covering the observed climate year range (column names addressed via `rotation_accessor`)
- `ag_fields/rotation_lookup.tsv`: crop name → management source mapping (see format below)
- Existing watershed/climate context produced by the normal WEPPcloud workflow (e.g., `dem`, `wepp/runs`, and the `Watershed`, `Climate`, `Landuse` NoDb controllers)

### Key generated artifacts

| Path (relative to `wd`) | Produced by | Purpose |
|---|---|---|
| `ag_fields/fields.WGS.geojson` | `validate_field_boundary_geojson` | Canonical boundary GeoJSON for downstream tooling and UI overlays |
| `ag_fields/rotation_schedule.parquet` | `validate_field_boundary_geojson` | Field attribute table extracted from the GeoJSON (used to read crop columns per year) |
| `ag_fields/field_boundaries.tif` | `rasterize_field_boundaries_geojson` | Field ID raster aligned to the project DEM grid |
| `ag_fields/sub_fields/fields.parquet` | `periodot_abstract_sub_fields` | Sub-field metadata (field/topaz/wepp/sub_field IDs, geometry stats, etc.) |
| `ag_fields/sub_fields/sub_field_id_map.tif` | Peridot | Sub-field ID raster (intersection of hydrology + fields) |
| `ag_fields/sub_fields/sub_fields.geojson` | `polygonize_sub_fields` | Polygonized sub-fields with `field_id`, `topaz_id`, `wepp_id`, `sub_field_id` |
| `wepp/ag_fields/runs/p<sub_field_id>.*` | `run_wepp_ag_fields` | Per-sub-field WEPP inputs (`.run`, `.man`, `.slp`) |
| `wepp/ag_fields/output/H<sub_field_id>.*.dat` | WEPP | Per-sub-field WEPP outputs (loss, plot, soil, water balance, etc.) |

## Quick start / examples

### Python (controller-driven workflow)

```python
from wepppy.nodb.mods.ag_fields import AgFields

wd = "/wc1/runs/co/copacetic-note"
ag = AgFields.getInstance(wd)

# 1) Normalize + validate boundaries (copies into wd/ag_fields/fields.WGS.geojson)
ag.validate_field_boundary_geojson("inputs/field_boundaries.geojson")

# 2) Column to burn into rasters and to join rotation rows to peridot outputs
ag.set_field_id_key("field_id")

# 3) Crop columns are typically named like Crop2008, Crop2009, ...
ag.set_rotation_accessor("Crop{}")

# 4) Create wd/ag_fields/field_boundaries.tif aligned to the project DEM
ag.rasterize_field_boundaries_geojson()

# 5) Abstract sub-fields with Peridot (requires the normal WEPPcloud watershed inputs)
ag.periodot_abstract_sub_fields(sub_field_min_area_threshold_m2=0.0, verbose=True)
ag.polygonize_sub_fields()

# 6) Provide crop->management mapping and run WEPP per sub-field
# - Ensure wd/ag_fields/rotation_lookup.tsv exists (see below).
# - Optionally populate wd/ag_fields/plant_files/ with:
#   ag.handle_plant_file_db_upload("plant_db.zip")
ag.run_wepp_ag_fields(max_workers=8)
```

### `rotation_lookup.tsv` format

`CropRotationManager` reads `wd/ag_fields/rotation_lookup.tsv`. It must have three tab-delimited columns:

1. `crop_name`: string matching values found in the rotation schedule columns
2. `database`: `weppcloud` or `plant_file_db`
3. `rotation_id`:
   - for `weppcloud`: a management ID (must parse as an integer)
   - for `plant_file_db`: a `.man` filename present under `wd/ag_fields/plant_files/` (spaces are normalized to underscores)

Example:

```tsv
crop_name	database	rotation_id
Corn	plant_file_db	corn_spring_NT.man
Forest	weppcloud	42
```

## Integration points

- **NoDb controllers**: uses `Climate`, `Landuse`, and `Watershed` (`wepppy.nodb.core`) for observed year range, landuse mapping, and Topaz/WEPP translator behavior.
- **Topography / Peridot**: calls `wepppy.topo.peridot.peridot_runner.run_peridot_wbt_sub_fields_abstraction` and `post_abstract_sub_fields`.
- **WEPP execution**: writes per-sub-field `.run` files using `run_templates/sub_field.template` and runs hillslopes via `wepp_runner.wepp_runner.run_hillslope`.
- **Optional catalog refresh**: best-effort calls into `wepppy.query_engine.update_catalog_entry` when available.
- **UI/analysis tooling**: the canonical `ag_fields/fields.WGS.geojson` and generated Parquet outputs are used by run explorers (for example, the embedded D-Tale service can register AgFields overlays when the module is importable).

## Developer notes

- **Locking**: `AgFields` is a `NoDbBase` controller; mutations are expected to occur under the NoDb lock. Many public methods acquire the lock internally (via `with self.locked():`) and persist on success.
- **GeoJSON requirements**:
  - must include a `field_id` column (validation fails otherwise)
  - must declare a CRS; rasterization requires it and will reproject to the DEM CRS when needed
  - features must overlap the project DEM extent, or rasterization fails fast
- **Peridot prerequisites**: Peridot’s sub-field abstraction asserts `wd/dem/wbt/flovec.tif` and `wd/ag_fields/field_boundaries.tif` exist.
- **Concurrency**: `run_wepp_ag_fields()` runs sub-fields in a `ThreadPoolExecutor`; use `max_workers` to control parallelism.

## Further reading

- `wepppy/weppcloud/routes/usersum/weppcloud/ag_field-mod.md` (WEPPcloud-focused notes and example run layouts)
- `wepppy/topo/peridot/peridot_runner.py` (Peridot sub-field abstraction details)
