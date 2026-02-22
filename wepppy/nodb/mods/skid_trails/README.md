# Skid Trails NoDb Mod (`wepppy.nodb.mods.skid_trails`)

> Ingests a skid-trail vector layer for a WEPPcloud run, rasterizes it onto the run DEM grid, and (optionally) derives approximate trail polylines by walking the raster mask downhill.

> **See also:** [AGENTS.md](../../AGENTS.md) for NoDb conventions and validation entry points.

> **Status:** Deprecated and abandoned experimental module as of February 22, 2026. Do not use for new development or new run configurations.

## Overview

This NoDb “mod” was created as an experimental salvage-logging / forest-operations workflow and is now officially deprecated. Keep it only for legacy reproducibility and historical debugging.

For active work, do not add new dependencies on `skid_trails` in configs, routes, or background jobs.

Historically, `SkidTrails` brought skid-trail inputs into a run working directory (`wd`) in a way that was spatially consistent with watershed rasters.

At a glance, `SkidTrails`:

- Copies a configured skid-trails vector file into `wd/skid_trails/`.
- Rasterizes the vector geometry onto the run DEM grid (creating a binary GeoTIFF mask).
- Provides a “walk” routine that traces connected skid pixels into per-trail point sequences and exports a WGS84 GeoJSON LineString layer for visualization/analysis.

Important: this module **does not directly modify** the `Soils` or `Landuse` controllers. Instead, it produces artifacts (a raster mask and a derived GeoJSON) that downstream workflows can use to apply soil compaction adjustments, create disturbance/management areas, or add overlays in reports/UX.

## Legacy Workflow (Deprecated)

### 1) Configure and enable the mod

Enable the mod in the run config and provide a skid-trails vector file path:

```toml
[nodb]
mods = ["skid_trails"]

[skid_trails]
skid_trails_map = "static/mods/north_star_fire/skid_segments.geojson"
```

`skid_trails_map` is loaded via `NoDbBase.config_get_path()`, so configs may also contain the string tokens `MODS_DIR` and `EXTENDED_MODS_DATA` (they are substituted at read time).

If the configured path starts with `static/`, `SkidTrails.__init__()` resolves it relative to the WEPPcloud app directory and then copies the file into the run working directory under `wd/skid_trails/`.

### 2) Rasterize the vector trails onto the run DEM grid

Call `SkidTrails.rasterize_skid_trails()` to create `wd/skid_trails/skid.tif` aligned with the run DEM:

- Reads the run DEM metadata from `Watershed.ron_instance.dem_fn`.
- Loads the vector file with GeoPandas (`gpd.read_file(...)`).
- Reprojects the vector layer to the DEM CRS (if needed).
- Rasterizes geometry with `rasterio.features.rasterize(..., all_touched=True)`.

### 3) (Optional) Walk the raster mask to derive polylines

Call `SkidTrails.walk_skid_trails()` to:

- Load watershed rasters (`bound`, `netful`, `subwta`) and the rasterized skid mask.
- Clip skid pixels to the watershed bounds (`bound == 1`).
- Mask the DEM to skid pixels and repeatedly:
  - Find endpoints (skid pixels with exactly one unmasked neighbor).
  - Choose the highest-elevation endpoint as the origin.
  - Step to the highest-elevation unmasked neighbor until the trace ends or branches.
- Export a GeoJSON FeatureCollection of LineStrings in WGS84 (EPSG:4326).
- Persist the computed `skidtrails` structure to `skid_trails.nodb`.

## Inputs / Contracts

### Required run state (integration with `Watershed`)

`SkidTrails` is built around the watershed raster stack and expects a working directory where the `Watershed` controller has already produced:

- `Watershed.ron_instance.dem_fn` (the run DEM; used as the rasterization template)
- `Watershed.bound` (watershed/subbasin bounds raster; used to clip skid pixels)
- `Watershed.netful` (channel network raster; used to annotate whether a point is on a channel)
- `Watershed.subwta` (subcatchment/TOPAZ ID raster; used to annotate each point with `topaz_id`)

### Skid-trails vector file (`[skid_trails].skid_trails_map`)

- **Type**: any vector format readable by GeoPandas / OGR (commonly GeoJSON or a shapefile).
- **Geometry**: intended for linear features (trail centerlines); polygons may rasterize but are not the primary use case.
- **CRS**: may be different from the run DEM CRS; the layer is reprojected to match the DEM before rasterization.
- **Path resolution**:
  - If the path starts with `static/`, it is resolved relative to the WEPPcloud app directory before copying into `wd/skid_trails/`.
  - Config string tokens `MODS_DIR` and `EXTENDED_MODS_DATA` are substituted by `NoDbBase.config_get_path()`.

## Outputs

Artifacts are written under the run working directory (`wd`):

| Path (relative to `wd`) | Produced by | Purpose |
|---|---|---|
| `skid_trails/<input_basename>` | `SkidTrails.__init__()` | Copy of the configured input vector file (for run-local provenance). |
| `skid_trails/skid.tif` | `SkidTrails.rasterize_skid_trails()` | Binary skid-trails mask raster aligned with the run DEM (`1` where trails touch cells, else `0`). |
| `skid_trails/skid_trails0.geojson` | `SkidTrails.walk_skid_trails()` | Derived WGS84 LineStrings representing walked trail traces (best-effort). |
| `skid_trails.nodb` | `NoDbBase` persistence | Serialized controller state (including the computed `skidtrails` structure). |

If `wepppy.query_engine` is available, `walk_skid_trails()` attempts to refresh the run catalog entry for `skid_trails` (best effort).

## Legacy Usage / Examples (Deprecated)

### Example: run-local skid trail artifacts from Python

```python
from wepppy.nodb.core import Watershed
from wepppy.nodb.mods.skid_trails import SkidTrails

wd = "/wc1/runs/<runid>"

# Ensure watershed artifacts exist (dem, bound, netful, subwta).
Watershed.getInstance(wd)

skid = SkidTrails.getInstance(wd)

# 1) Vector -> DEM-aligned mask
skid.rasterize_skid_trails()

# 2) (Optional) Mask -> walked polylines + persisted state
skid.walk_skid_trails()

print(skid.skid_trails_raster)  # wd/skid_trails/skid.tif
print(skid.skid_trails_dir)     # wd/skid_trails/
```

### Example: load the derived GeoJSON for inspection

```python
import os
import geopandas as gpd

wd = "/wc1/runs/<runid>"
geojson_fn = os.path.join(wd, "skid_trails", "skid_trails0.geojson")

gdf = gpd.read_file(geojson_fn)
print(gdf[["ID", "n", "start_z", "end_z"]].head())
```

### Example: legacy config snippet (salvage logging scenario)

This mod is enabled only in legacy salvage configs (example: `wepppy/nodb/configs/legacy/salvage-north_star.toml`):

```toml
[nodb]
mods = ["disturbed", "debris_flow", "ash", "skid_trails"]

[skid_trails]
skid_trails_map = "static/mods/north_star_fire/skid_segments.geojson"
```

## Integration Points

### `Watershed` (current, required)

`SkidTrails` consumes watershed rasters and the run DEM to ensure all outputs are co-registered to the run grid and can be overlaid with:

- flowpaths / subcatchments (`subwta`)
- channels (`netful`)
- watershed bounds (`bound`)

### `Landuse` (downstream, not automatic)

Common downstream uses of `skid_trails/skid.tif` include:

- Creating a “skid trails” disturbance class mask to drive landuse/management mapping.
- Summarizing disturbed area by subcatchment/TOPAZ ID.

This controller does **not** currently write into landuse rasters or landuse option mappings; treat its outputs as inputs to those steps.

### `Soils` (downstream, not automatic)

Skid trails are often associated with compaction and altered hydraulic properties. A typical integration pattern is to use `skid_trails/skid.tif` to:

- Select affected cells in the run soil raster(s).
- Apply a soils adjustment workflow (for example via a dedicated disturbance/compaction routine).

This controller does **not** apply soil parameter changes directly.

## Developer Notes

- **Module layout**:
  - `wepppy/nodb/mods/skid_trails/skid_trails.py`: controller implementation plus raster-walk helpers.
  - `wepppy/nodb/mods/skid_trails/__init__.py`: exports `SkidTrails`.
- **Locking**: `SkidTrails.__init__()` performs setup under `with self.locked():`. `walk_skid_trails()` persists `self.skidtrails` under a lock at the end.
- **Coordinate handling**: walked points store a WGS84 coordinate (`wgs`) computed from the watershed rasters’ projection via `GeoTransformer(..., dst_epsg=4326)`.

## Deprecation Policy

- This module is abandoned and receives no feature development.
- Avoid adding new call sites, configuration references, or integration points.
- Limit changes to narrowly scoped fixes needed to reproduce historical runs.
- Prefer external preprocessing or maintained NoDb workflows for new disturbance modeling work.

## Caveats / Known Limitations

- `walk_skid_trails()` is a best-effort trace of connected skid pixels; branching behavior is handled by stopping the trace when multiple downhill neighbors exist.
- The implementation currently includes debug `print(...)` calls (not structured logging).
- `walk_skid_trails()` writes the GeoJSON using `convert_to_geojson(self.skidtrails)`, but `self.skidtrails` may not exist until the end of the method (the in-scope list is `skidtrails`). If you hit an `AttributeError` here, it is likely this mismatch.
- `clean()` references `self.skid_trails_dirinterpolate_slp`, which does not appear to be defined in this controller.

## Further Reading

- `wepppy/nodb/mods/salvage_logging/README.md` (related exploratory skid-trail tooling and examples)
- `wepppy/nodb/core/watershed.py` (producer of `bound`, `netful`, `subwta`, and the run DEM)
