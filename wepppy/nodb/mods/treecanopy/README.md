# Tree Canopy (NLCD) NoDb Mod

> Retrieves an NLCD tree canopy raster for a WEPPcloud run and summarizes canopy fractional cover to TOPAZ hillslopes for dashboards and watershed analytics.

> **See also:** [AGENTS.md](../../AGENTS.md) for NoDb locking/persistence conventions and validation entry points.

## Overview

`wepppy.nodb.mods.treecanopy` provides a NoDb controller (`Treecanopy`) that:

- Downloads the **NLCD Tree Canopy (2016)** raster for the run’s map extent (`Ron.map`) via WMESque.
- Caches the raster under the run working directory for reproducibility.
- Aggregates canopy values to each TOPAZ hillslope using the watershed `subwta` raster (median per hillslope).
- Exposes watershed-wide summary statistics for UI/report panels via `Treecanopy.report`.

This mod is designed to be run after the watershed has been built/abstracted so the required watershed rasters exist.

## Workflow

1. **Acquire the canopy raster**
   - `Treecanopy.acquire_raster()` calls `wmesque_retrieve("nlcd_treecanopy/2016", ...)` using `Ron.getInstance(wd).map.extent` and `Ron.getInstance(wd).map.cellsize`.
   - The raster is cached as an ESRI ASCII grid under `wd/treecanopy/treecanopy.asc` and registered with the query-engine catalog via `update_catalog_entry(wd, "treecanopy")`.
2. **Aggregate to hillslopes**
   - `Treecanopy.analyze()` loads `Watershed.getInstance(wd).subwta` and summarizes canopy values for each nonzero TOPAZ ID.
   - Results are stored on the NoDb instance as `Treecanopy.data`.
3. **Summarize and consume**
   - `Treecanopy.report` computes watershed-wide stats using `Watershed.getInstance(wd).bound` (a 0/1 raster mask).
   - Iteration (`for topaz_id, point in treecanopy:`) yields per-hillslope values as `TreecanopyPointData`.

## API

### `Treecanopy` (NoDb controller)

Primary attributes and methods:

- `Treecanopy.treecanopy_fn -> str`
  - Cached raster path: `wd/treecanopy/treecanopy.asc`.
- `Treecanopy.acquire_raster() -> None`
  - Downloads and caches the NLCD tree canopy raster for the run extent.
- `Treecanopy.analyze() -> None`
  - Aggregates canopy values to hillslopes (median by TOPAZ ID) and stores results in `Treecanopy.data`.
- `Treecanopy.data: dict[int | str, float] | None`
  - Per-hillslope canopy fraction (typically percent). Keys are TOPAZ hillslope IDs (stringified in current implementation).
  - Values may be missing/invalid where the raster is masked (handled as `None` internally by the map helper).
- `Treecanopy.report -> dict[str, float] | None`
  - Watershed-wide statistics for UI/reporting (keys include `num_pixels`, `valid_pixels`, `mean`, `std`, `units`).

### `TreecanopyMap` (raster helper)

`TreecanopyMap` encapsulates raster loading and provides the spatial aggregation primitives used by the controller:

- `TreecanopyMap.spatial_aggregation(subwta_fn: str) -> dict[str, float | None]`
  - Computes the median canopy value for each TOPAZ ID in `subwta_fn`.
- `TreecanopyMap.spatial_stats(bounds_fn: str) -> dict[str, float | str]`
  - Computes `mean`/`std` and pixel counts within the watershed bounds mask.

## Inputs and outputs

### Required inputs (working directory artifacts)

| Input | Produced by | Used by |
|---|---|---|
| `Ron.map` (extent, cell size) | `wepppy.nodb.core.Ron` | `Treecanopy.acquire_raster()` |
| `watershed/subwta.*` | `wepppy.nodb.core.Watershed` | `Treecanopy.analyze()` |
| `watershed/bound.*` | `wepppy.nodb.core.Watershed` | `Treecanopy.report` |

### Outputs

| Path | Contents |
|---|---|
| `treecanopy/treecanopy.asc` | Cached NLCD tree canopy raster for the run extent. |
| `treecanopy.nodb` | Persisted NoDb state (includes `data` after `analyze()`). |

In-memory outputs:

- `Treecanopy.data` for per-hillslope canopy values.
- `Treecanopy.report` for watershed-wide summary stats.

## Quick start / examples

### Typical controller usage (download + analyze)

```python
from wepppy.nodb.core import Ron, Watershed
from wepppy.nodb.mods.treecanopy import Treecanopy

wd = "/wc1/runs/<runid>/<config>"

# Ensure upstream controllers have produced required artifacts.
Ron.getInstance(wd)
Watershed.getInstance(wd)

treecanopy = Treecanopy.getInstance(wd)
treecanopy.acquire_raster()
treecanopy.analyze()

print(treecanopy.report)
for topaz_id, point in treecanopy:
    if point.isvalid:
        print(topaz_id, point.treecanopy)
```

### Use `TreecanopyMap` directly (existing raster)

```python
from wepppy.nodb.mods.treecanopy import TreecanopyMap

treecanopy_map = TreecanopyMap("/path/to/treecanopy.asc")
per_hillslope = treecanopy_map.spatial_aggregation("/path/to/watershed/subwta.asc")
stats = treecanopy_map.spatial_stats("/path/to/watershed/bound.asc")
```

## Integration points

- **Depends on**:
  - `wepppy.nodb.core.Ron` for map extent/cell size.
  - `wepppy.nodb.core.Watershed` for `subwta` (hillslope IDs) and `bound` (watershed mask).
- **Catalog/query-engine**:
  - `Treecanopy.acquire_raster()` calls `update_catalog_entry(wd, "treecanopy")` so downstream tooling can discover cached artifacts.
- **Downstream consumers**:
  - WEPPcloud dashboards and report templates can consume `Treecanopy.data` (per hillslope) and `Treecanopy.report` (watershed summary) to display canopy coverage alongside other vegetation layers.

## Developer notes

- Raster decoding is handled by `TreecanopyMap`:
  - Reads canopy values as numeric data and masks values greater than `255`.
  - Uses the **median** canopy value per hillslope (not mean).
- All state mutation should occur inside `with treecanopy.locked():` blocks to respect NoDb locking and persistence conventions.

