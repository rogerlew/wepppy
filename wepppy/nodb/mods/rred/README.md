# RRED NoDb Mod

> Integrates WEPPpy/WEPPcloud NoDb runs with an external “RRED” packaging service: upload a burn-severity raster, download a Disturbed WEPP package (DEM + land cover + soils), then build run landuse and soils from the returned grids.

> **See also:** [AGENTS.md](../../AGENTS.md) for NoDb controller conventions (locking, persistence, and tests).

## Overview

`wepppy/nodb/mods/rred/` provides a small NoDb controller (`Rred`) plus a thin HTTP client (`rred_api.py`) for pulling an “RRED” package from an external GeoDjango service. In practice, this module is typically invoked as part of post-fire workflows (for example, by the legacy `BAER` controller) to replace a run’s DEM/landuse/soils using a burn-severity-driven package.

At a high level:

- The caller provides a burn-severity raster (commonly a normalized “4-class” product).
- `rred_api.send_request(...)` uploads that raster and receives a `key`.
- `rred_api.retrieve_rred(key, ...)` downloads a ZIP archive containing ASCII grids and WEPP soil files.
- `Rred.import_project(key)` imports artifacts into the run working directory and captures run metadata (extent/center).
- `Rred.build_landuse(...)` and `Rred.build_soils(...)` write `Landuse` and `Soils` NoDb state derived from the package grids.

## Components

| Path | Purpose |
| --- | --- |
| `wepppy/nodb/mods/rred/rred.py` | `Rred` NoDb controller: imports the downloaded package into the run and builds landuse/soils state. |
| `wepppy/nodb/mods/rred/rred_api.py` | External API client: multipart upload (`send_request`) and ZIP download/extract (`retrieve_rred`). |
| `wepppy/nodb/mods/rred/__init__.py` | Re-exports `Rred`, `send_request`, and `retrieve_rred`. |

## Workflow

### 1) Request and download an RRED package

`Rred.request_project(sbs_4class_fn, srid)` orchestrates:

1. Upload `sbs_4class_fn` via `rred_api.send_request(...)`.
2. Extract the returned `key`.
3. Call `Rred.import_project(key)` to download + import the package into `wd/rred/`.

### 2) Import into the run (DEM + extent metadata)

`Rred.import_project(rred_key)`:

- Downloads and extracts a ZIP archive into `wd/rred/`.
- Converts `wd/rred/dem.asc` → `wd/dem/dem.tif` (via `translate_asc_to_tif`) and wires it into `Ron` via `ron.symlink_dem(...)`.
- Reads the new DEM to capture projection and extent metadata:
  - `Rred.utm_proj` (projection string; asserted to contain `"utm"`)
  - `Rred.wgs_extent` (WGS84 bounding box)
  - `Rred.wgs_center` (WGS84 center point)

### 3) Build landuse from RRED grids

`Rred.build_landuse(landuse_mode=LanduseMode.RRED_Burned)`:

- Selects `wd/rred/landcov_burned.asc` or `wd/rred/landcov_unburned.asc`.
- Uses `LandcoverMap.build_lcgrid(watershed.subwta, ...)` to build a hillslope→landcover map.
- Mutates `Landuse` NoDb state:
  - `Landuse._mode = landuse_mode`
  - `Landuse.domlc_d = ...`

### 4) Build soils from RRED grids + `.sol` files

`Rred.build_soils(soils_mode=SoilsMode.RRED_Burned)`:

- Copies all `*.sol` files from the extracted package tree under `wd/rred/` into `wd/soils/`.
- Loads `wd/rred/soilsmap.txt` to map grid codes → soil IDs.
- Selects `wd/rred/soil_burned.asc` or `wd/rred/soil_unburned.asc` and builds a hillslope→soil-ID map.
- Builds `SoilSummary` entries and computes percent coverages using `Watershed.wsarea` and `Watershed.hillslope_area(...)`.
- Mutates `Soils` NoDb state:
  - `Soils._mode = soils_mode`
  - `Soils.domsoil_d = ...`
  - `Soils.soils = {soil_id: SoilSummary(...), ...}`

## External API integration

`rred_api.py` currently targets an external service hosted at `geodjango.mtri.org`:

- Upload endpoint (multipart POST): `https://geodjango.mtri.org/baer/geowepp/supplied/maps/`
  - Multipart fields:
    - `fileUpload`: the supplied raster file (sent as `image/tiff`)
    - `class_low`, `class_mod`, `class_high`: string-encoded class codes
    - `srid`: string-encoded EPSG code (the run’s projected CRS)
  - Response: JSON that includes a project `key` (used for retrieval).
- Retrieval endpoint (GET): `https://geodjango.mtri.org/baer/geowepp/package.asc?...&key=<key>`
  - The query is hardcoded in `retrieve_rred(...)`:
    - `burned=true`
    - `simplify=false`
    - `scale=30`

## Quick Start / Examples

### Typical path (via BAER post-fire workflow)

`Baer.on(TriggerEvents.LANDUSE_DOMLC_COMPLETE)` exports a 4-class SBS raster and then calls into RRED:

```python
from wepppy.nodb.mods.baer.sbs_map import SoilBurnSeverityMap
from wepppy.nodb.core.ron import Ron
from wepppy.nodb.mods.rred import Rred

wd = "/wc1/runs/<runid>"

# Export a normalized 4-class raster (0..3) for the external service.
sbs = SoilBurnSeverityMap(f"{wd}/baer/baer.cropped.tif", breaks=[...], nodata_vals=[...], ignore_ct=True)
sbs_4class = f"{wd}/baer/baer.cropped.4class.tif"
sbs.export_4class_map(sbs_4class)

srid = Ron.getInstance(wd).map.srid
rred = Rred.getInstance(wd)
rred.request_project(sbs_4class, srid=srid)
rred.build_landuse()  # defaults to burned landcover
```

### Direct API usage (download/extract only)

```python
from wepppy.nodb.mods.rred import send_request, retrieve_rred

proj = send_request("/path/to/sbs_4class.tif", srid=26912, class_low=1, class_mod=2, class_high=3)
retrieve_rred(proj["key"], out_dir="/tmp/rred-package", extract=True)
```

### Build soils from the imported package

```python
from wepppy.nodb.core.soils import SoilsMode
from wepppy.nodb.mods.rred import Rred

wd = "/wc1/runs/<runid>"
rred = Rred.getInstance(wd)

# After request/import:
rred.build_soils(soils_mode=SoilsMode.RRED_Burned)
```

## Configuration

This module does not currently read run configuration keys directly, but the external upload call is parameterized:

| Parameter | Where | Default | Description |
| --- | --- | --- | --- |
| `srid` | `send_request(...)` / `Rred.request_project(...)` | required | EPSG code matching the run’s projected CRS (typically from `Ron.getInstance(wd).map.srid`). |
| `class_low` | `send_request(...)` | `2` | Burn severity class code in the supplied raster for “low”. |
| `class_mod` | `send_request(...)` | `3` | Burn severity class code in the supplied raster for “moderate”. |
| `class_high` | `send_request(...)` | `4` | Burn severity class code in the supplied raster for “high”. |
| `out_dir` | `retrieve_rred(...)` | `./` | Directory to write `DisturbedWepp_KEY-<key>.zip` and extract contents. Must exist. |
| `extract` | `retrieve_rred(...)` | `True` | Whether to extract the ZIP archive after download. |

## Outputs and side effects

When used as part of a run (working directory `wd`), RRED commonly produces/updates:

- `wd/rred.nodb`: persisted `Rred` controller state (`rred_key`, extents, etc.).
- `wd/rred/`: extracted package contents, including at least:
  - `dem.asc`, `dem.prj`
  - `landcov_burned.asc`, `landcov_unburned.asc`
  - `soil_burned.asc`, `soil_unburned.asc`
  - `soilsmap.txt`
  - one or more subdirectories containing `*.sol` files
  - `DisturbedWepp_KEY-<key>.zip` (downloaded archive)
- `wd/dem/dem.tif`: translated DEM (and any `Ron` symlink artifacts).
- `wd/landuse/` + `wd/landuse.nodb`: landuse DOMLC state updated when `build_landuse(...)` runs.
- `wd/soils/` + `wd/soils.nodb`: soil files copied and dominant-soil mapping updated when `build_soils(...)` runs.

## Developer Notes

- **Persistence + locking:** `Rred` is a `NoDbBase` subclass. All mutations are expected to occur under `with rred.locked():` (the controller methods handle their own locking where needed).
- **Prerequisites:** `build_landuse(...)` and `build_soils(...)` require a watershed abstraction, because they consume `Watershed.subwta` and hillslope areas.
- **Class-code contract:** `rred_api.send_request(...)` defaults assume the supplied raster encodes burn severities as low/mod/high = `2/3/4`. If you upload a raster encoded as `0..3` (as produced by `SoilBurnSeverityMap.export_4class_map`), pass explicit `class_low=1, class_mod=2, class_high=3` (or whatever mapping your upstream service expects) instead of relying on defaults.

## Operational Notes

- **Dependencies:** This mod relies on GDAL (Python bindings) and NumPy. DEM translation and raster reads use GDAL-backed utilities.
- **External service availability:** `send_request(...)` and `retrieve_rred(...)` make live network calls. There is no retry/backoff and no explicit timeout configuration in the current client.
- **Error handling:** Several failure modes currently surface as `AssertionError` (missing files, non-200 upload response, unexpected projection). Network failures can raise `requests` exceptions or `urllib` errors directly; callers should treat the overall workflow as non-atomic and be prepared to clean `wd/rred/` on partial failures.
- **Logging/IO quirks:** `send_request(...)` prints the raw response text to stdout and opens the uploaded file without an explicit close; avoid calling it in tight loops or performance-critical paths.

## Further Reading

- `wepppy/nodb/mods/baer/README.md` (how BAER triggers RRED and how SBS “4-class” exports are produced)
- `wepppy/nodb/core/landuse.py` (how `LanduseMode.RRED_*` delegates to `Rred.build_landuse`)
- `wepppy/nodb/core/soils.py` (how `SoilsMode.RRED_*` delegates to `Rred.build_soils`)
