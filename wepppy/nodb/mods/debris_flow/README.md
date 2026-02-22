# Debris Flow NoDb Controller

> Computes debris-flow volume and probability grids for a watershed using USGS empirical equations plus precipitation frequency curves from NOAA PDS and/or the Holden WRF Atlas.

> **See also:** [AGENTS.md](../../AGENTS.md) for NoDb controller conventions (locking, persistence, and debugging).

## Overview

`wepppy.nodb.mods.debris_flow` provides the `DebrisFlow` NoDb controller, which orchestrates debris-flow risk calculations for a WEPPcloud run. It combines:

- Basin characteristics from the `Watershed` controller (area/slope metrics, ruggedness, centroid).
- Burn severity coverage from either the `Baer` mod or the `Disturbed` mod (depending on which is enabled for the run).
- Soil properties from the `Soils` controller (clay content and liquid limit), with optional manual overrides.
- Precipitation frequency curves fetched at the watershed centroid from NOAA and/or the Holden WRF Atlas.

The controller produces gridded precipitation totals and intensities by duration/recurrence interval, then computes debris-flow **volume** and **probability of occurrence** matrices for each available precipitation datasource. WEPPcloud UI components and summaries use these outputs to display debris-flow risk products.

## Workflow

Typical run sequence:

1. Load the current run’s `Watershed`, `Soils`, and `Ron` controllers.
2. Determine burn severity coverage source:
   - If `'baer' in Ron.mods`, use `Baer.sbs_coverage`
   - Otherwise, use `Disturbed.sbs_coverage`
3. Derive basin and soil inputs used by the USGS equations:
   - `%A` / `A`: percent and area (km²) with slopes ≥ 30%
   - `%B` / `B`: percent and area (km²) burned at moderate + high severity
   - `R`: basin ruggedness
   - `C`: clay content (%), defaulting to `7.0` if missing/unparseable
   - `LL`: liquid limit, defaulting to `13.25` if missing/unparseable
4. Fetch precipitation frequency data (if available) from:
   - NOAA (quantiles are converted from inches to millimeters, then to intensity in mm/hr)
   - Holden WRF Atlas (precipitation totals are reshaped to duration × recurrence, then converted to intensity in mm/hr)
5. For each datasource, compute:
   - `volume[datasource]`: predicted debris-flow volume matrix
   - `prob_occurrence[datasource]`: probability of occurrence matrix
6. Emit a Redis “task timestamp” (`TaskEnum.run_debris`) to signal completion to downstream consumers (best-effort).

## Key Attributes

| Attribute | Type | Description |
|---|---:|---|
| `T` | `dict[str, list[list[float]]] \| None` | Precipitation totals (mm), shaped `[duration][recurrence]`, keyed by datasource. |
| `I` | `dict[str, list[list[float]]] \| None` | Precipitation intensity (mm/hr), shaped `[duration][recurrence]`, keyed by datasource. |
| `durations` | `dict[str, list[str]] \| None` | Duration labels (e.g., `"15-min"`, `"1-hour"`), keyed by datasource. |
| `rec_intervals` | `dict[str, list[float]] \| None` | Recurrence intervals (years), keyed by datasource. |
| `volume` | `dict[str, list[list[float]]] \| None` | Predicted debris-flow volume matrix per datasource. |
| `prob_occurrence` | `dict[str, list[list[float]]] \| None` | Debris-flow probability-of-occurrence matrix per datasource. |
| `datasource` | `str` | Active datasource name (defaults to `"NOAA"` if unset). |
| `A`, `A_pct` | `float \| None` | Area (km²) / percent area with slopes ≥ 30%. |
| `B`, `B_pct` | `float \| None` | Burned area (km²) / percent burned (moderate + high severity). |
| `C` | `float \| None` | Clay content (%), optionally overridden via `run_debris_flow(cc=...)`. |
| `LL` | `float \| None` | Liquid limit, optionally overridden via `run_debris_flow(ll=...)`. |
| `R` | `float \| None` | Basin ruggedness from `Watershed`. |
| `wsarea` | `float \| None` | Total watershed area as reported by `Watershed`. |

## Usage

### Run debris-flow analysis (default inputs)

```python
from wepppy.nodb.mods.debris_flow import DebrisFlow

wd = "/path/to/run/working_dir"
debris = DebrisFlow.getInstance(wd)

debris.run_debris_flow()

source = debris.datasource
volume_grid = debris.volume[source]
prob_grid = debris.prob_occurrence[source]
```

### Override soil inputs and/or pick a precipitation datasource

```python
from wepppy.nodb.mods.debris_flow import DebrisFlow

debris = DebrisFlow.getInstance(wd)

# `cc` and `ll` accept floats or numeric strings; `req_datasource` matches
# case-insensitively against available datasources.
debris.run_debris_flow(cc=12.5, ll="25.0", req_datasource="Holden WRF Atlas")
```

### Inspect precipitation tables

```python
from wepppy.nodb.mods.debris_flow import DebrisFlow

debris = DebrisFlow.getInstance(wd)
debris.fetch_precip_data()

for source in (debris.datasources or []):
    print(source, debris.durations[source], debris.rec_intervals[source])
    print("Totals (mm):", debris.T[source])
    print("Intensity (mm/hr):", debris.I[source])
```

## Outputs

Primary outputs after `run_debris_flow()`:

- `volume`: debris-flow volume matrix for each datasource.
- `prob_occurrence`: probability-of-occurrence matrix for each datasource.
- `T` and `I`: precipitation totals (mm) and intensities (mm/hr), aligned to `durations` × `rec_intervals`.

The controller also stores the intermediate basin/soil inputs (`A`, `B`, `A_pct`, `B_pct`, `C`, `LL`, `R`, `wsarea`) that were used for the most recent run, which can be useful for debugging or displaying “inputs to the equation” in UI.

## Integration Points

- **Depends on (NoDb controllers/mods)**:
  - `wepppy.nodb.core.Watershed` (centroid, area/slope metrics, ruggedness)
  - `wepppy.nodb.core.Soils` (clay percent, liquid limit)
  - `wepppy.nodb.core.Ron` (mod enablement)
  - `wepppy.nodb.mods.baer.Baer` (burn severity coverage when enabled)
  - `wepppy.nodb.mods.disturbed.Disturbed` (burn severity coverage when BAER is not enabled)
- **Depends on (climate clients)**:
  - `wepppy.climates.noaa_precip_freqs_client.fetch_pf`
  - `wepppy.climates.holden_wrf_atlas.fetch_pf`
- **Signals completion via**:
  - `wepppy.nodb.redis_prep.RedisPrep.timestamp(TaskEnum.run_debris)`
- **Consumed by**:
  - WEPPcloud dashboards / run summaries that visualize debris-flow risk products (volume + probability grids).

## Persistence

- **Filename**: `debris_flow.nodb`
- **Locking**: All mutations occur under `DebrisFlow.locked()` (via `NoDbBase`) to avoid concurrent writers.
- **Caching**: Uses the standard NoDb in-memory + Redis cache behavior described in `wepppy/nodb/AGENTS.md`.

## Developer Notes

- **Datasource selection**:
  - If NOAA data is available, it is preferred as the default active datasource (`debris.datasource`).
  - If only Holden WRF Atlas data is available, it becomes the default.
  - `run_debris_flow(req_datasource=...)` can override the active datasource (validated against what was fetched).
- **Error behavior**:
  - If no precipitation frequency data is available from either source, `run_debris_flow()` raises `DebrisFlowNoDbLockedException` with a descriptive message.
  - If `req_datasource` is not available, `run_debris_flow()` raises `ValueError` listing available datasources.
- **Units**:
  - Precipitation totals are stored in millimeters; intensities are millimeters per hour.
  - Basin areas `A` and `B` are converted to km² for the volume equation; `%A` and `%B` are stored as percentages.

## Further Reading

- `wepppy/nodb/AGENTS.md` (locking, TTLs, NoDb persistence/cache behavior)
- `wepppy/nodb/mods/baer/` and `wepppy/nodb/mods/disturbed/` (burn severity coverage inputs)
- `wepppy/climates/noaa_precip_freqs_client.py` and `wepppy/climates/holden_wrf_atlas.py` (precipitation frequency lookups)
