# SBS Map Utilities (`sbs_map.py`)

> Classifies Soil Burn Severity (SBS) rasters into canonical WEPP burn classes, whether the source raster uses numeric breaks or a color table.

> **See also:** [`../../AGENTS.md`](../../AGENTS.md) for NoDb controller conventions and test expectations.

## Overview

`wepppy/nodb/mods/baer/sbs_map.py` is the canonical SBS raster normalization module used by BAER and disturbed-land workflows. It accepts source rasters with or without color tables, validates map readiness, and produces stable class outputs used by WEPP pipelines and map clients.

The module supports two ingestion paths:
- Numeric-class rasters (4-class or BARC-like `0..255` ranges) using breakpoint classification.
- Palette rasters using GDAL color-table lookup mapped to SBS severities (`unburned`, `low`, `mod`, `high`).

The output contract is stable across both paths:
- Runtime classification can use `130..133` (`130=unburned`, `131=low`, `132=moderate`, `133=high`).
- `export_4class_map` writes canonical output classes `0..3` (plus `255` for NoData/unknown).
- Unknown color-table indices map to `255` in the color-table classification path.
- `export_4class_map(..., export_palette="shifted")` is the default.
- `export_4class_map(..., export_palette="legacy")` remains available for transition workflows.

## Preparing SBS Map for wepp.cloud

Use this section when preparing an SBS file for upload to wepp.cloud, especially if you are not a GIS specialist.

### Minimum checklist before upload

- Use a single-band raster (GeoTIFF is the safest choice).
- Store integer values only (no decimal pixel values).
- Keep total unique values at `<= 256`.
- Ensure the file has a valid spatial reference (projection metadata). If uncertain, reproject to a local UTM CRS.
- Use one of these data styles:
  - Integer classes without a color table (for example `0,1,2,3` or BARC-style `0..255`), or
  - A color-table raster whose colors match known SBS severity colors.

### Practical workflow (QGIS/ArcGIS style)

1. Open your SBS raster and confirm it is a thematic class map (not a continuous float surface).
2. Reproject to your local UTM zone if needed. Use nearest-neighbor resampling.
3. Convert/export as an integer raster (`Byte` or another integer type) and preserve NoData where possible.
4. Save as GeoTIFF and keep the layer as one band.
5. If you use a color table, make sure at least one burn class color (`low`, `mod`, or `high`) is a recognized SBS color.
6. Upload to wepp.cloud; if validation fails, use the message table below.

### Common validation messages and fixes

| Message from upload validation | What it means | Quick fix |
| --- | --- | --- |
| `Map contains an invalid projection. Try reprojecting to UTM.` | CRS metadata is missing or invalid. | Reproject to a valid projected CRS (typically UTM), then export again. |
| `Map has non-integer classes` | Pixel values contain decimals/floats. | Reclassify or round to integer class values and export as integer raster. |
| `Map has more than 256 classes` | Too many unique pixel values were detected. | Reclassify to a smaller set of thematic classes (for example 4-class or BARC-style). |
| `Map has no valid color table` | A color table exists, but recognized SBS colors were not found. | Fix/remap the palette to known SBS colors, or remove the color table and use numeric classes. |

## API

| Symbol | Purpose |
| --- | --- |
| `sbs_map_sanity_check(fname)` | Fast validity gate for uploads and batch ingestion. |
| `get_sbs_color_table(fn, color_to_severity_map=None)` | Reads GDAL color table and resolves severity index buckets. |
| `classify(v, breaks, nodata_vals=None, offset=0)` | Numeric breakpoint classification path. |
| `ct_classify(v, ct, offset=0, nodata_vals=None)` | Color-table index classification path. |
| `SoilBurnSeverityMap` | Main wrapper with class maps, counts, and export helpers. |

## Installation / Setup

`sbs_map.py` relies on GDAL in two ways:
- Python bindings (`from osgeo import gdal`)
- CLI tools used by export helpers (`gdalwarp`, `gdaldem`, `gdal_translate`)

Optional acceleration:
- Rust helpers from `wepppyo3.sbs_map` are used when available.
- Python logic is the fallback and remains the behavior baseline.

## Color Table And Palette Contracts

**Source of truth:** if code and docs diverge, update both in the same change.

Lookup map locations:
- `wepppy/nodb/mods/baer/data/sbs_color_map.json` (primary)
- `_DEFAULT_COLOR_TO_SEVERITY` in `wepppy/nodb/mods/baer/sbs_map.py` (fallback)

### Ingest Color Recognition (color-table path)

The lookup accepts multiple aliases per class. Representative examples:

| Severity | Recognized RGB examples |
| --- | --- |
| `unburned` | `0,100,0`, `0,115,74`, `0,158,115`, `0,0,0` |
| `low` | `127,255,212`, `77,230,0`, `86,180,233`, `0,255,255` |
| `mod` | `255,255,0`, `255,232,32`, `240,228,66` |
| `high` | `255,0,0`, `204,121,167` |

Validation rule used by `sbs_map_sanity_check`:
- A color table is considered valid when at least one of `low`, `mod`, or `high` is recognized.

### 4-Class Export Palettes

`export_4class_map` writes classes `0..3` and applies one of these palettes:

| Severity | Export class | `shifted` (default) | `legacy` |
| --- | --- | --- | --- |
| Unburned | `0` | `0,158,115` (`#009E73`) | `0,100,0` (`#006400`) |
| Low | `1` | `86,180,233` (`#56B4E9`) | `127,255,212` (`#7FFFD4`) |
| Moderate | `2` | `240,228,66` (`#F0E442`) | `255,255,0` (`#FFFF00`) |
| High | `3` | `204,121,167` (`#CC79A7`) | `255,0,0` (`#FF0000`) |
| NoData | `255` | `255,255,255,0` | `255,255,255,0` |

## Quick Start / Examples

```python
from wepppy.nodb.mods.baer.sbs_map import SoilBurnSeverityMap, sbs_map_sanity_check

status, message = sbs_map_sanity_check("/path/to/sbs.tif")
if status != 0:
    raise RuntimeError(message)

sbs = SoilBurnSeverityMap("/path/to/sbs.tif")

# Raw value -> canonical class code strings ("130".."133", or "255")
pixel_map = sbs.class_pixel_map

# Human-facing grouped counts
counts = sbs.burn_class_counts

# Export normalized 4-class GeoTIFF (0..3 + 255 nodata)
sbs.export_4class_map("/tmp/sbs_4class.tif")
```

Override lookup map (for controlled ingest experiments):

```python
custom_map = {
    (0, 158, 115): "unburned",
    (86, 180, 233): "low",
    (240, 228, 66): "mod",
    (204, 121, 167): "high",
}
sbs = SoilBurnSeverityMap("/path/to/sbs.tif", color_map=custom_map)
```

## Key Concepts / Domain Model

| Concept | Description |
| --- | --- |
| Runtime class codes | `130..133` when classification uses an SBS offset (`130=unburned`, `133=high`). |
| Export class codes | `0..3` in `export_4class_map`; this is the canonical 4-class raster output. |
| Unknown class handling | Unknown color-table entries map to `255` (NoData sentinel). |
| `ignore_ct=True` | Forces breakpoint classification even when a color table exists. |
| `is256` | Indicates inferred BARC-like style (`0..255`) in non-color-table workflows. |

## Accessibility Guidance: Color-Shifted SBS Maps

Use this checklist when implementing or reviewing Color Shift behavior for universal design:

- Keep severity semantics stable. Color Shift changes display color only, not class meaning.
- Keep text labels explicit (`Unburned`, `Low`, `Moderate`, `High`) in legends and tooltips.
- Keep one-to-one class mapping across raster colors, legend chips, and tooltips.
- Keep unknown colors explicit (`255`) rather than silently coercing values.
- Ensure color is not the only cue; pair color with labels, order, or numeric codes.

## Developer Notes

- Rust acceleration is used when available (`wepppyo3.sbs_map`); Python fallback remains authoritative.
- `_SBS_COLOR_MAP_PATH` is passed into Rust helpers so Python and Rust share the same lookup contract.
- `export_4class_map` fails fast with `ValueError` for unsupported `export_palette` values.
- When updating color lookup behavior:
  - Update `sbs_map.py` fallback defaults.
  - Update `data/sbs_color_map.json`.
  - Update SBS tests that mirror lookup dictionaries.

Targeted tests:

```bash
wctl run-pytest tests/nodb/mods/baer/test_sbs_map_extended.py tests/nodb/mods/baer/test_sbs_map_classify_validation.py tests/sbs_map/test_sbs_map.py
```

## Operational Notes

- `sbs_map_sanity_check` validates projection, integer classes, class count, and color-table recognizability; it does not clip/crop rasters to a run extent.
- BAER/Disturbed run workflows perform grid alignment later (for example, `gdalwarp` to project/run extent in BAER).

## Further Reading

- `wepppy/nodb/mods/baer/README.md`
- `wepppy/nodb/mods/baer/sbs_map.py`
- `wepppy/nodb/mods/baer/sbs_map.pyi`
- `wepppy/nodb/mods/baer/data/sbs_color_map.json`
- `docs/ui-docs/control-ui-styling/sbs_controls_behavior.md`
