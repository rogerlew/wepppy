# Rangeland Cover NoDb Mod

> Builds and persists per-hillslope rangeland cover fractions (percent) used by RHEM simulations and WEPPcloud map/report views.

> **See also:** [AGENTS.md](../../AGENTS.md) for NoDb locking/persistence conventions and validation entry points.

## Overview

`wepppy.nodb.mods.rangeland_cover` provides a NoDb controller (`RangelandCover`) that assembles a cover composition for each TOPAZ hillslope (subcatchment). The controller persists results to `rangeland_cover.nodb` in the run working directory, and exposes summaries used by:

- **RHEM** hillslope simulation prep (`wepppy.nodb.mods.rhem.Rhem.prep_hillslopes`) to populate parameter files.
- **WEPPcloud** UI layers (subcatchment map coloring) and report templates via `subs_summary`.
- **WEPPcloud** NoDb API routes for building, modifying, and querying cover values.

The controller can build cover fractions using one of these modes (`RangelandCoverMode`):

- `GriddedRAP`: Sample **RAP** rasters (the default in most RHEM/RAP configurations).
- `Gridded`: Sample **USGS shrubland** layers (via the `Shrubland` mod).
- `Single`: Apply a single default cover profile to every hillslope.

## API

### Data model

Cover values are stored as a mapping from TOPAZ hillslope ID to a per-hillslope cover dictionary:

- `RangelandCover.covers: dict[int | str, dict[str, float]] | None`

Each per-hillslope cover dictionary uses these keys (values are **percent** cover, typically `0.0`–`100.0`):

| Key | Meaning |
|---|---|
| `bunchgrass` | Perennial grass fraction (estimated in gridded builds) |
| `forbs` | Forb fraction (estimated in gridded builds) |
| `sodgrass` | Annual grass fraction (estimated in gridded builds) |
| `shrub` | Shrub fraction |
| `basal` | Basal cover proxy (vegetation total used by RHEM parameterization) |
| `rock` | Residual fraction after other components (and cryptogams) |
| `litter` | Litter fraction |
| `cryptogams` | Cryptogams fraction (defaulted and clipped to keep totals ≤ 100) |

### Main methods and properties

- `RangelandCover.mode: RangelandCoverMode`
  - Controls which build path runs (`GriddedRAP`, `Gridded`, `Single`).
- `RangelandCover.rap_year: int`
  - RAP year to request when building in `GriddedRAP` mode.
- `RangelandCover.build(rap_year: int | None = None, default_covers: Mapping[str, float] | None = None) -> None`
  - Builds `covers` for all watershed hillslopes using the current `mode`.
  - Optional `rap_year` overrides the persisted `rap_year`.
  - Optional `default_covers` overrides the controller’s default cover profile (used as a fallback when raster data is invalid, and as the universal profile in `Single` mode).
- `RangelandCover.modify_covers(topaz_ids: Iterable[int | str], new_cover: Mapping[str, float]) -> None`
  - Mutates cover values for the specified hillslopes (persisted via NoDb locking).
- `RangelandCover.current_cover_summary(topaz_ids: Iterable[int | str]) -> dict[str, str]`
  - Returns rounded per-field summaries for a selection; if values differ across the selection, the field value is `"-"`.
- `RangelandCover.subs_summary -> dict[int | str, dict[str, float | str]]`
  - Returns a copy of `covers` augmented with a `color` key (hex string) for UI rendering.

### Helper

- `gen_cover_color(cover: Mapping[str, float]) -> str`
  - Produces a hex color string (RGBA) derived from the cover proportions. Used by `subs_summary`.

## Inputs and outputs

### Inputs

- **Working directory (`wd`)**: must contain a built/abstracted watershed so `Watershed._subs_summary` is available (this supplies the TOPAZ hillslope IDs).
- **Config (`cfg_fn`)**: `RangelandCover.__init__` reads from the `rhem` section:
  - `rhem.mode` (default: `GriddedRAP`)
  - `rhem.rap_year`
- **Raster-backed modes**:
  - `GriddedRAP` uses the `RAP` mod (`RAP.acquire_rasters(year=...)`, then `RAP.analyze()`).
  - `Gridded` uses the `Shrubland` mod (`Shrubland.acquire_rasters()`, then `Shrubland.analyze()`).

### Outputs

- Persisted NoDb file: `<wd>/rangeland_cover.nodb`
- In-memory API:
  - `covers` for downstream consumers (notably `Rhem`)
  - `subs_summary` for UI map layers (includes derived `color`)

## Quick start / examples

### Build covers (RAP)

```python
from wepppy.nodb.mods.rangeland_cover import RangelandCover, RangelandCoverMode

wd = "/wc1/runs/my-run"
rangeland_cover = RangelandCover.getInstance(wd)

rangeland_cover.mode = RangelandCoverMode.GriddedRAP
rangeland_cover.rap_year = 2022
rangeland_cover.build()

print(rangeland_cover.has_covers)
print(list(rangeland_cover.covers.items())[:1])
```

### Build covers with a custom default profile

`default_covers` must provide all expected keys.

```python
from wepppy.nodb.mods.rangeland_cover import RangelandCover

wd = "/wc1/runs/my-run"
rangeland_cover = RangelandCover.getInstance(wd)

rangeland_cover.build(
    rap_year=2021,
    default_covers={
        "bunchgrass": 15.0,
        "forbs": 5.0,
        "sodgrass": 20.0,
        "shrub": 30.0,
        "basal": 20.0,
        "rock": 10.0,
        "litter": 25.0,
        "cryptogams": 5.0,
    },
)
```

### Modify cover values for specific hillslopes

```python
from wepppy.nodb.mods.rangeland_cover import RangelandCover

wd = "/wc1/runs/my-run"
rangeland_cover = RangelandCover.getInstance(wd)

rangeland_cover.modify_covers(
    topaz_ids=["1", "2"],
    new_cover={"shrub": 35.0, "litter": 20.0},
)
```

## Integration points

- **NoDb controller conventions**: `RangelandCover` inherits from `NoDbBase` and persists changes via the `locked()` context manager (used internally by setters and build paths).
- **Watershed**: `Single` mode iterates `Watershed._subs_summary` to discover hillslopes.
- **RAP / Shrubland**: gridded modes depend on sibling mods to fetch/analyze rasters and yield per-hillslope summaries.
- **RHEM**: `wepppy.nodb.mods.rhem.Rhem.prep_hillslopes` requires `RangelandCover.covers` (it raises if cover data has not been built).
- **WEPPcloud routes**:
  - `POST /runs/<runid>/<config>/tasks/build_rangeland_cover/` enqueues an RQ job that ultimately calls `RangelandCover.build(...)`.
  - `POST /runs/<runid>/<config>/tasks/modify_rangeland_cover/` validates inputs then calls `RangelandCover.modify_covers(...)`.
  - `GET /runs/<runid>/<config>/query/rangeland_cover/subcatchments[/]` returns `RangelandCover.subs_summary`.
  - `POST /runs/<runid>/<config>/query/rangeland_cover/current_cover_summary/` returns `RangelandCover.current_cover_summary(...)`.

## Developer notes

- TOPAZ IDs may be `int` or `str`; upstream routes normalize inputs to string digits, while internal controllers often reuse the key type emitted by the watershed abstraction.
- `subs_summary` deep-copies `covers` before adding `color` so consumers can treat the return value as read-only.
- The controller exposes `rap_report` and `usgs_shrubland_report` as convenience proxies to the underlying mods’ reports.

## Further reading

- `wepppy/nodb/AGENTS.md` (NoDb locking, persistence, and validation workflow)
- `wepppy/nodb/mods/rhem/rhem.py` (consumes `covers` when building RHEM parameter files)
- `wepppy/weppcloud/routes/nodb_api/rangeland_bp.py` (WEPPcloud build/modify/query endpoints)
