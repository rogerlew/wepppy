# CDA (Coeur d'Alene) data assets

> Shapefile datasets for the Coeur d'Alene (CDA) basin boundary and HUC polygons used to define and inspect the CDA study area in WEPPpy.

> **See also:** [AGENTS.md](../../AGENTS.md) for NoDb operational notes and debugging conventions.

## Overview

This directory is **data-only**. It contains ESRI Shapefiles (plus sidecar files) for the Coeur d'Alene basin boundary and nested hydrologic unit polygons (HUC6/HUC10/HUC12) in **NAD83 / EPSG:4269**.

In WEPPpy, the `cda` configuration references a *GeoJSON* boundary (served as a static asset) for map/UI bounding and region definition. The Shapefiles stored here appear to be the source/reference datasets for that boundary and for HUC-level overlays, but they are **not directly imported by Python code at runtime**.

## Contents

All datasets live under `hucs/` and are standard Shapefile bundles:

- Required core files: `.shp` (geometry), `.shx` (index), `.dbf` (attributes)
- Required sidecars here: `.prj` (CRS WKT), `.cpg`/`.CPG` (DBF encoding)
- Optional spatial indexes included: `.sbn`, `.sbx`
- Optional metadata (present for `CdABsn`): `.shp.xml`

### Datasets

| Dataset (basename) | Description | Feature count | Key attributes (DBF fields) | CRS |
|---|---|---:|---|---|
| `CdABsn` | CDA basin boundary polygon | 1 | `Id` | NAD83 (EPSG:4269) |
| `CdABsnHUC6` | HUC6 polygons covering CDA region | 6 | `HUC8`, `Name`, `States`, `AreaAcres`, `AreaSqKm` | NAD83 (EPSG:4269) |
| `CdABsnHUC10` | HUC10 polygons covering CDA region | 32 | `HUC10`, `Name`, `HUType`, `HUMod`, `AreaAcres`, `AreaSqKm` | NAD83 (EPSG:4269) |
| `CdABsnHUC12` | HUC12 polygons covering CDA region | 128 | `HUC12`, `Name`, `HUType`, `HUMod`, `ToHUC`, `NonContrib` | NAD83 (EPSG:4269) |

## How WEPPpy uses this data

The active `cda` model configuration points its map boundary at:

- `wepppy/nodb/configs/cda.cfg` → `boundary = "/static/mods/cda/cda_basin.json"`
- `wepppy/weppcloud/static/mods/cda/cda_basin.json` → a GeoJSON `FeatureCollection` named `CdABsn` with `crs` set to EPSG:4269

That GeoJSON is what the application consumes for the CDA region boundary. This `wepppy/nodb/mods/cda/` directory is retained as a convenient place to keep the **source/reference** Shapefiles close to the NoDb configuration that selects the CDA region.

## Updating / regenerating derived assets

If you update the CDA basin boundary geometry, you will typically also need to update the derived GeoJSON consumed by WEPPcloud:

1. Edit/replace the Shapefile dataset(s) under `hucs/`.
2. Regenerate the GeoJSON boundary used by `cda.cfg`.
3. Verify the resulting JSON shape matches the existing contract (top-level `name`, `crs`, and expected properties such as `Id`).

An example GDAL-based conversion (exact output may vary by GDAL version):

```bash
ogr2ogr -f GeoJSON /tmp/cda_basin.json wepppy/nodb/mods/cda/hucs/CdABsn.shp
```

## Constraints and gotchas

- **Coordinate reference system:** All datasets are stored in **NAD83 / EPSG:4269** (lat/lon degrees). Keep this consistent with `cda_basin.json`.
- **Shapefile bundles must stay complete:** treat each dataset as a unit; do not commit only `.shp` without its `.shx`/`.dbf`/`.prj`/`.cpg`.
- **Attribute names are part of the interface:** downstream tooling often keys off DBF field names like `HUC10`/`HUC12` and `Id`.
- **Provenance/licensing:** the only explicit provenance in-tree is the ArcGIS metadata file (`CdABsn.shp.xml`), which references an internal network path. Confirm upstream licensing/provenance before redistributing these datasets outside of WEPPpy.

## Developer notes

- These files are primarily binary; avoid hand-editing and expect large diffs.
- If you add additional CDA spatial assets, keep them under `hucs/` and prefer stable basenames to minimize downstream churn.

## Further reading

- `wepppy/nodb/configs/cda.cfg`
- `wepppy/weppcloud/static/mods/cda/cda_basin.json`

