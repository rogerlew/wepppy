# Salvage Logging Utilities (`wepppy.nodb.mods.salvage_logging`)

> Utilities for preparing and analyzing salvage-logging road/skid-trail inputs (rasterization and optional DEM conditioning) used in WEPPpy/WEPPcloud runs.

> **See also:** [AGENTS.md](../../AGENTS.md) for NoDb conventions and validation entry points.

> **Status:** Deprecated and abandoned experimental module as of February 22, 2026. Do not use for new development or new run configurations.

## Overview

This package was a small set of GIS-focused utilities and scripts used to prototype salvage-logging workflows (especially skid-trail handling), and it is now officially deprecated.

Treat this directory as archival. Do not add new production dependencies on it.

The code here is **not** a fully integrated NoDb mod; it remains a set of helpers and one-off analysis scripts that operate on a WEPPcloud run working directory (`wd`) and its rasters.

At a glance, the modules cover:

- **Rasterization** of skid trails / roads into rasters aligned to a template DEM (`burn_roads.py`).
- **DEM conditioning** by lowering elevations along a rasterized road/skid mask (`roads.py`).

## Legacy Workflow (Deprecated)

### 1) Rasterize skid trails / roads onto the DEM grid

Use `burn_roads.rasterize()` to burn a vector attribute (by default, `CFF_ID`) into a raster that matches a template raster’s extent and resolution (typically the run DEM).

Inputs:
- A vector file (`.geojson`, shapefile, etc.) with an integer attribute to burn.
- A template raster (e.g., `dem/dem.tif`) that defines extent + resolution.

Output:
- A GeoTIFF such as `salvage/skid.tif` where pixel values are the burned attribute (0 where no feature was burned).

### 2) (Optional) Condition the DEM along roads/skid trails

`roads.RoadDEM` loads a DEM and validates key assumptions:

- DEM is in **UTM** coordinates (so offsets are in meters).
- DEM cells are **square**.
- DEM band datatype is **float**.

Then `RoadDEM._rasterize()` uses `gdal_rasterize` to create a binary mask, optionally dilates it (OpenCV), and returns a modified elevation array with a constant `z_offset` applied where the mask is nonzero.

Outputs:
- A rasterized mask GeoTIFF at the path you pass as `dst_fn` (often named something like `road_mask.tif`).
- An in-memory elevation array (`new_z`) that you can write out as a new DEM.

### 3) Retired flowpath attribution helper

The old `flowpaths.py` analysis script has been removed. It depended on the retired WEPP flowpath runtime and on watershed flowpath artifacts that are no longer produced by default. Historical notes that mention `salvage/up.tif` or `Watershed.fps_summary()` should be treated as archival only.

## Generated artifacts

Common files produced/consumed by the scripts in this directory:

| Path (relative to run `wd`) | Produced by | Purpose |
|---|---|---|
| `salvage/skid.tif` | `burn_roads.rasterize()` (or other rasterizers) | Skid trails / roads burned into a raster aligned to the run DEM. |
| `watershed/subwta*.tif` | `wepppy.nodb.core.Watershed` pipeline | Subcatchment map used to partition analysis by TOPAZ ID. |

## Legacy Usage / Examples (Deprecated)

### Rasterize a skid-trail vector into a DEM-aligned raster

```python
from wepppy.nodb.mods.salvage_logging.burn_roads import rasterize

vec_fn = "/path/to/Skid_segments.utm.geojson"
template_dem_fn = "/path/to/run/dem/dem.tif"
dst_fn = "/path/to/run/salvage/skid.tif"

rasterize(vec_fn, dst_fn, template_dem_fn, attr="CFF_ID")
```

Notes:
- `burn_roads.rasterize()` shells out to `gdal_rasterize`.
- The output pixel values come from the chosen attribute; set `attr` to a field that exists in your vector file.

### Lower a DEM along rasterized roads/skid trails

`RoadDEM._rasterize()` is a low-level helper that returns a modified elevation array but does not write the output DEM for you.

```python
from osgeo import gdal, osr

from wepppy.nodb.mods.salvage_logging.roads import RoadDEM

dem_fn = "/path/to/run/dem/dem.tif"
roads_vec_fn = "/path/to/roads_or_skidtrails.utm.geojson"
mask_fn = "/path/to/run/salvage/road_mask.tif"
out_dem_fn = "/path/to/run/salvage/dem_conditioned.tif"

rd = RoadDEM(dem_fn)
new_z = rd._rasterize(roads_vec_fn, dilation=1, dst_fn=mask_fn, z_offset=-0.1)

driver = gdal.GetDriverByName("GTiff")
dst = driver.Create(out_dem_fn, rd.num_cols, rd.num_rows, 1, gdal.GDT_Float32)
dst.SetGeoTransform(rd.transform)
dst.SetProjection(rd.srs_wkt)
dst.GetRasterBand(1).WriteArray(new_z.T)  # `read_raster()`/`RoadDEM` store arrays transposed
dst = None
```

## Integration points

- `wepppy.all_your_base.geo.RasterDatasetInterpolator`: used by `burn_roads.py` to match the output raster extent/resolution to a template raster.
- `wepppy.all_your_base.geo.read_raster`: used by `roads.py`; it returns arrays transposed (`.T`) relative to GDAL/rasterio read order.
- WEPPcloud scenario configs for salvage logging often use the dedicated skid-trail mod (`wepppy/nodb/mods/skid_trails/`) via `[nodb].mods = ["...","skid_trails"]` and `[skid_trails].skid_trails_map = ...` (see `wepppy/nodb/configs/legacy/salvage-north_star.toml`).

## Installation / Setup

These utilities assume a WEPPpy environment with GIS tooling available:

- `gdal_rasterize` on `PATH` (GDAL command-line tools).
- Python packages providing `osgeo` (GDAL bindings), `numpy`, and `cv2` (OpenCV) for `roads.py`.
- A run working directory with a DEM and aligned rasters when using the archival scripts here.

## Developer notes

- `roads.RoadDEM._rasterize()` is intentionally underscored; treat it as an internal helper for exploratory preprocessing.
- Example paths in `burn_roads.py` use `/geodata/...` conventions; update them for your environment.
- `dev/` contains notebooks and scratch assets used during development; `test/north_star/` contains sample GeoJSON inputs.

## Deprecation Policy

- This module is abandoned and receives no feature development.
- Do not add new references from configs, controllers, routes, or jobs.
- Limit changes to narrowly scoped fixes needed for historical reproducibility.
- Prefer maintained preprocessing pipelines or maintained NoDb modules for new work.

## Further reading

- `wepppy/nodb/mods/skid_trails/` (integrated skid-trail NoDb mod used by configs)
- `wepppy/all_your_base/geo/geo.py` (raster IO helpers, including `read_raster`)
