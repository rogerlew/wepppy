# Shrubland NoDb Mod

> Retrieves USGS NLCD Shrubland (2016) gridded fractional cover/height layers via WMESque, aggregates values to TOPAZ hillslopes, and exposes summaries consumed by WEPPcloud dashboards and downstream NoDb mods.

> **See also:** [AGENTS.md](../../AGENTS.md) for NoDb locking/persistence conventions and validation entry points.

## Overview

`wepppy.nodb.mods.shrubland` provides a NoDb controller (`Shrubland`) that:

- Downloads a fixed set of NLCD Shrubland 2016 layers (annual herb, bare ground, shrub height, etc.).
- Caches the clipped rasters under `<wd>/shrubland/*.asc` for reproducibility and inspection.
- Aggregates raster values to TOPAZ hillslope IDs using the watershed `subwta` raster.
- Persists per-hillslope layer summaries to `<wd>/shrubland.nodb` and exposes a lightweight report used by WEPPcloud UI panels.

This mod is primarily used as an input to rangeland cover building (the “USGS shrubland” gridded path).

## Workflow

1. **Prerequisites**
   - A `Ron` map exists for the run (provides `extent` and `cellsize` for WMESque downloads).
   - A `Watershed` exists for the run (provides `subwta` for hillslope aggregation and `bound` for watershed-wide stats).
2. **Acquire rasters** (`Shrubland.acquire_rasters()`)
   - Fetches each dataset in `nlcd_shrubland_layers` from WMESque (`nlcd_shrubland/2016/<dataset>`), clipped to the Ron map extent, saved as ASCII grids under `<wd>/shrubland/`.
3. **Analyze** (`Shrubland.analyze()`)
   - For each dataset, computes a **median** value per TOPAZ hillslope ID (from `subwta`) and stores the per-hillslope mapping in `Shrubland.data`.
4. **Consume**
   - Iterate `Shrubland` to get per-hillslope `ShrublandPointData`.
   - Use `Shrubland.report` to get watershed-wide spatial stats per dataset for UI/reporting.

## API

### Datasets

The controller works over this fixed set of layer names:

- `nlcd_shrubland_layers: tuple[str, ...]`
  - `annual_herb`
  - `bare_ground`
  - `big_sagebrush`
  - `sagebrush`
  - `herbaceous`
  - `sagebrush_height`
  - `litter`
  - `shrub`
  - `shrub_height`

Layers with `*_height` are treated as height layers (see “Outputs” and “Developer notes”).

### Main controller

- `class Shrubland(NoDbBase)`
  - `filename = "shrubland.nodb"`
  - `data: dict[int | str, dict[str, float]] | None`
  - `shrubland_dir -> str`
    - Returns `<wd>/shrubland`.
  - `acquire_rasters() -> None`
    - Downloads and caches all raster layers under `<wd>/shrubland/<dataset>.asc`.
  - `analyze() -> None`
    - Aggregates all cached rasters to per-hillslope summaries in `data`.
  - `report -> dict[str, dict[str, float]] | None`
    - Returns per-dataset spatial stats over the watershed boundary (`Watershed.bound`), or `None` if `data` has not been built.
  - `__iter__() -> Iterator[tuple[int | str, ShrublandPointData]]`
    - Iterates `(topaz_id, ShrublandPointData)` across `data`.

### Per-hillslope values

- `class ShrublandPointData`
  - Holds optional floats for each dataset (keys match the layer names).
  - Convenience properties:
    - `total_cover` and `*_normalized` properties compute percent-of-total across the non-height cover components.
    - `isvalid` indicates whether all expected fields are present (including height fields).

## Inputs and outputs

### Inputs

- **Run working directory** (`wd`)
- **Ron map** (`Ron.getInstance(wd).map`)
  - `extent` + `cellsize` constrain WMESque retrieval.
- **Watershed rasters** (`Watershed.getInstance(wd)`)
  - `subwta` maps raster cells to TOPAZ hillslope IDs (used by `analyze()`).
  - `bound` identifies the watershed footprint (used by `report`).

### Outputs

- Cached rasters: `<wd>/shrubland/<dataset>.asc`
  - Cover layers are interpreted as **percent** values (masked when > 100).
  - Height layers are interpreted as **meters** in reporting (see “Developer notes”).
- Persisted NoDb state: `<wd>/shrubland.nodb`
  - `Shrubland.data` (per-hillslope dataset summaries)
- UI/reporting summary: `Shrubland.report`
  - Per dataset: `num_pixels`, `valid_pixels`, `mean`, `std`, `units`.

## Quick start / examples

### Acquire and analyze shrubland layers

```python
from wepppy.nodb.mods.shrubland import Shrubland

wd = "/wc1/runs/my-run"
shrubland = Shrubland.getInstance(wd)

shrubland.acquire_rasters()
shrubland.analyze()

print(shrubland.report)
```

### Iterate per-hillslope values

```python
from wepppy.nodb.mods.shrubland import Shrubland

wd = "/wc1/runs/my-run"
shrubland = Shrubland.getInstance(wd)

for topaz_id, point in shrubland:
    if point.isvalid:
        print(topaz_id, point.shrub_normalized, point.sagebrush_height)
        break
```

### Load a single cached raster as a `ShrublandMap`

```python
from wepppy.nodb.mods.shrubland import Shrubland, nlcd_shrubland_layers

wd = "/wc1/runs/my-run"
shrubland = Shrubland.getInstance(wd)

ds = nlcd_shrubland_layers[0]
shrub_map = shrubland.load_shrub_map(ds)
from wepppy.nodb.core import Watershed

print(shrub_map.spatial_stats(bounds_fn=Watershed.getInstance(wd).bound))
```

## Configuration

WMESque settings come from the run config via `NoDbBase`:

| Parameter | Default | Description |
|---|---:|---|
| `wmesque.version` | `1` | WMESque protocol/version passed to `wmesque_retrieve(..., v=...)`. |
| `wmesque.endpoint` | `None` | Optional override for the WMESque base URL passed to `wmesque_retrieve(..., wmesque_endpoint=...)`. |

## Integration points

- **Rangeland cover (USGS shrubland mode)**: `wepppy.nodb.mods.rangeland_cover.RangelandCover` calls `Shrubland.acquire_rasters()` and `Shrubland.analyze()` when building gridded covers from NLCD Shrubland layers.
- **WEPPcloud reporting**: templates use `RangelandCover.usgs_shrubland_report`, which is a thin proxy to `Shrubland.report`.
- **NoDb trigger wiring**: `NoDbBase.trigger()` constructs `Shrubland` when `"shrubland"` is enabled in the run’s mod list and calls `Shrubland.on(evt)` (currently a no-op in this mod).
- **Query engine catalog**: `acquire_rasters()` calls `update_catalog_entry(wd, shrubland_dir)` so cached rasters show up as run artifacts.

## Developer notes

- **Masking/units**
  - In `ShrublandMap`, cover layers are masked when values exceed `100`, and height layers are masked when values exceed `997`.
  - In `ShrublandMap.spatial_stats()`, height layers are scaled by `0.01` and reported in meters (`units="m"`); cover layers report `units="%"`.
- **Aggregation statistic**: per-hillslope aggregation uses the **median** of raster cells within each TOPAZ ID (not the mean).
- **TOPAZ IDs**: `ShrublandMap.spatial_aggregation()` returns keys as strings (e.g., `"12"`), so `Shrubland.data` will typically be keyed by string IDs.
- **Directory creation**: `Shrubland.__init__` creates `<wd>/shrubland` under a NoDb lock; the directory is expected not to exist for a fresh run.

## Further reading

- `wepppy/nodb/mods/shrubland/shrubland.py` (controller implementation)
- `wepppy/nodb/mods/shrubland/shrubland_map.py` (raster masking, aggregation, and stats)
- `wepppy/nodb/mods/rangeland_cover/README.md` (primary consumer)
- `wepppy/nodb/AGENTS.md` (NoDb debugging and locking conventions)
