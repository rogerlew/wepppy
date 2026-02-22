# BAER NoDb Mod

> Legacy Burned Area Emergency Response (BAER) workflows: validate and normalize Soil Burn Severity (SBS) rasters, remap landuse, and apply post-fire soil replacements for WEPPcloud runs.

> **See also:** [AGENTS.md](../../AGENTS.md) for NoDb controller conventions (locking, persistence, and tests).

## Overview

`wepppy/nodb/mods/baer/` contains two closely related pieces of functionality:

- `Baer` (`baer.py`): a **legacy NoDb controller** (deprecated in favor of `Disturbed`) that still supports projects expecting the historical 4-class BAER/SBS pipeline. It manages SBS raster state under a run working directory and coordinates downstream landuse and soils changes.
- SBS map utilities (`sbs_map.py`): the **canonical SBS raster normalization** implementation used by BAER and other post-fire workflows. It handles both numeric-class rasters and palette/color-table rasters, and can export stable 4-class outputs for GIS clients.

If you are integrating new SBS work, prefer the modern `Disturbed` controller for run orchestration and treat `Baer` as compatibility glue for older workflows and UI surfaces.

## Components

| Path | Purpose |
| --- | --- |
| `wepppy/nodb/mods/baer/baer.py` | `Baer` NoDb controller: SBS raster validation + WGS overlay + landuse/soil remapping orchestration. |
| `wepppy/nodb/mods/baer/sbs_map.py` | `SoilBurnSeverityMap` + helpers to classify SBS rasters (breakpoints or color tables) and export normalized 4-class GeoTIFFs. |
| `wepppy/nodb/mods/baer/README.sbs_map.md` | Detailed contract and examples for `sbs_map.py` (palettes, sanity checks, export behavior). |
| `wepppy/nodb/mods/baer/data/sbs_color_map.json` | RGB→severity mapping source of truth for color-table ingest. |
| `wepppy/nodb/mods/baer/data/soils/` | BAER replacement soil templates used by `Baer.modify_soils`. |

## Workflow

### 1) SBS raster validation and web overlay artifacts (BAER)

`Baer.validate(...)` (after the raster is placed in `wd/baer/`) performs:

1. Reproject to WGS84 for Leaflet display (`gdalwarp` → `*.wgs.tif`).
2. Infer burn classes and default breaks (4-class vs. BARC-like 0–255) and capture counts/bounds.
3. Write a GDAL color table (`wd/baer/color_table.txt`) and render overlay outputs:
   - `wd/baer/<name>.wgs.rgb.vrt` (via `gdaldem color-relief`)
   - `wd/baer/baer.wgs.rgba.png` (via `gdal_translate`)

`Baer.modify_burn_class(...)` lets users override breaks and NoData handling, then regenerates these overlay artifacts.

### 2) Landuse remapping (BAER)

When landuse DOMLC building completes (`TriggerEvents.LANDUSE_DOMLC_COMPLETE`), `Baer`:

1. Warps/crops the SBS raster to the run’s UTM grid extent and cellsize (`wd/baer/baer.cropped.tif`).
2. Uses `SoilBurnSeverityMap(..., ignore_ct=True)` to build a burn-severity landcover grid.
3. Updates `Landuse.domlc_d` (with some special-case remaps for certain mod sets like `lt/portland/seattle/general`), then rebuilds managements.

### 3) Soils replacement (BAER)

When soils building completes (`TriggerEvents.SOILS_BUILD_COMPLETE`), `Baer` either:

- Triggers RRED follow-on work (when the `rred` mod is present), or
- Applies BAER soil replacements for gridded soils (`SoilsMode.Gridded`) by mapping each hillslope’s dominant soil to a burn-severity-specific soil template (optionally preserving texture via `simple_texture` when `baer.legacy_mode` is off).

Some configurations also activate special soil-key suffixing (`*_lowmod_sev`, `*_high_sev`) for EU/AU fire configs.

### 4) Optional RRED integration

When the `rred` mod is enabled, BAER exports a normalized 4-class raster (via `SoilBurnSeverityMap.export_4class_map`) and requests an RRED project build, then triggers landuse/soil builds through the RRED controller.

## Installation / Setup

This module assumes GDAL is available in both Python and the system PATH:

- Python bindings: `from osgeo import gdal`
- CLI tools invoked by BAER/SBS helpers: `gdalwarp`, `gdaldem`, `gdal_translate`

Missing tools typically surface as assertion failures (missing outputs) or `RuntimeError` (non-zero `gdalwarp` return codes).

## Quick Start / Examples

### Validate an SBS raster before accepting an upload (SBS utilities)

```python
from wepppy.nodb.mods.baer.sbs_map import sbs_map_sanity_check, SoilBurnSeverityMap

status, message = sbs_map_sanity_check("/path/to/sbs.tif")
if status != 0:
    raise RuntimeError(message)

sbs = SoilBurnSeverityMap("/path/to/sbs.tif")
print(sbs.burn_class_counts)  # {"No Burn": ..., "Low Severity Burn": ..., ...}
sbs.export_4class_map("/tmp/sbs_4class.tif")  # output classes 0..3 with palette
```

For color-table handling details and palette contracts, see `wepppy/nodb/mods/baer/README.sbs_map.md`.

### Use the `Baer` controller to validate and render overlay artifacts

```python
import os
import shutil

from wepppy.nodb.mods.baer import Baer

wd = "/wc1/runs/<runid>"
baer = Baer.getInstance(wd)

# `Baer.validate` expects the filename inside `wd/baer/`.
src_path = "/path/to/uploaded_sbs.tif"
dst_name = os.path.basename(src_path)
shutil.copyfile(src_path, os.path.join(baer.baer_dir, dst_name))

baer.validate(dst_name, mode=0)  # mode=0 is “upload”; mode=1 is “uniform”

print(baer.bounds)        # [[sw_lat, sw_lon], [ne_lat, ne_lon]]
print(baer.class_map)     # [(pixel_value, label, count), ...]
print(baer.baer_rgb_png)  # wd/baer/baer.wgs.rgba.png
```

Override breaks/NoData (regenerates the color relief outputs):

```python
baer.modify_burn_class(breaks=[75, 109, 187, 255], nodata_vals="255")
```

## Configuration

`Baer` reads a small amount of configuration at initialization:

| Parameter | Where | Description |
| --- | --- | --- |
| `baer.legacy_mode` | run config (`[baer]`) | When enabled, `modify_soils` uses a fixed `"sand loam"` texture instead of deriving texture from the dominant soil. |

## Key Concepts / Domain Model

| Concept | Description |
| --- | --- |
| SBS (Soil Burn Severity) | Post-fire burn severity raster used to drive landuse/soil changes. |
| Burn class codes | BAER/SBS workflows commonly encode severities as `130..133` (`130=unburned/no burn`, `131=low`, `132=moderate`, `133=high`). |
| 4-class export | `SoilBurnSeverityMap.export_4class_map` writes `0..3` output values (plus `255` for NoData) and applies either the shifted (default) or legacy palette. |
| `sbs_mode` / `uniform_severity` | Persisted BAER/Disturbed UI state for “upload vs. uniform” SBS workflows (see UI docs in Further Reading). |

## Developer Notes

- **Persistence:** `Baer` is a NoDb controller stored as `wd/baer.nodb`, with raster artifacts under `wd/baer/`. Mutations must occur inside `with baer.locked():` or via `@nodb_setter` properties to preserve locking and serialization contracts.
- **Input contract:** `Baer.validate(fn, ...)` expects `fn` to be a *filename* inside `baer.baer_dir`, not an arbitrary absolute path.
- **SBS classification paths:** `sbs_map.py` supports breakpoint and color-table ingest. BAER’s landuse/soil remapping currently forces numeric classification (`ignore_ct=True`) using the breakpoints captured during `Baer.validate` / `modify_burn_class`.
- **Palettes:** `sbs_map.py` defaults to an accessibility-oriented shifted palette for 4-class exports; BAER’s `legend` and overlay rendering use the legacy palette expected by older UI surfaces.
- **Tests:** Most coverage here is for SBS classification. Run:

  ```bash
  wctl run-pytest tests/nodb/mods/baer/test_sbs_map_extended.py tests/sbs_map/test_sbs_map.py
  ```

## Operational Notes

- SBS rasters must have a valid projection; `sbs_map_sanity_check` returns a user-facing error when it cannot validate SRS.
- BAER/SBS workflows rely on GDAL CLI tools; failures can manifest as missing output files (assertions) after `gdalwarp`/`gdaldem`/`gdal_translate`.
- `Baer._calc_sbs_coverage` expects the cropped SBS grid to align with `Watershed.bound`; misalignment raises an exception so the run does not silently mix grids.

## Further Reading

- `wepppy/nodb/mods/baer/README.sbs_map.md`
- `docs/ui-docs/control-ui-styling/sbs_controls_behavior.md` (UI mode semantics: upload vs. uniform)
- `tests/nodb/mods/baer/README.md` (test suite map)

