# DSS Export Guide

> Reference playbook for WEPP Cloud’s DSS integration: how we build files, how **pydsstools** represents them, and how the browse service introspects them.

## Overview

| Component | Purpose | Source |
| --- | --- | --- |
| `run_totalwatsed3()` | Aggregates hydrology + ash metrics into `totalwatsed3.parquet`. | `wepppy/wepp/interchange/totalwatsed3.py` |
| `totalwatsed_partitioned_dss_export()` | Writes one DSS file per channel (`totalwatsed3_chan_<id>.dss`) using `totalwatsed3.parquet`. | `wepppy/wepp/interchange/watershed_totalwatsed_export.py` |
| `chanout_dss_export()` | Converts `chan.out.parquet` peak flows into `peak_chan_<id>.dss` (irregular `IR-Year` series). | `wepppy/wepp/interchange/watershed_chan_peak_interchange.py` |
| Browse DSS view | Provides a “pandas `.info()`”-style summary for any `*.dss`. | `wepppy/microservices/browse.py`, template `browse/dss_file.htm` |

Exports run either from the UI (RQ job `post_dss_export_rq`) or from `Wepp._export_partitioned_totalwatsed2_dss()`. Date filtering uses the `dss_start_date` / `dss_end_date` fields stored in `wepp.nodb`.

## Export Contents (produced by `post_dss_export_rq`)

All artifacts land in `export/dss/` and are zipped to `export/dss.zip`:

- `totalwatsed3_chan_<topaz_id>.dss` — regular daily DSS series for every metric in `totalwatsed3` (runoff, sediment, ash, etc.) per exported channel.
- `peak_chan_<topaz_id>.dss` — irregular peak-flow DSS from `chan.out`.
- `sed_vol_conc_by_event_and_chn_id.csv` — per-channel daily CSV including `sed_vol_conc`, `ash_vol_conc`, `sed+ash_vol_conc`, and `ash_black_pct_by_vol` when ash data exists.
- `dss_channels.geojson` — filtered channel geometries plus boundary-condition features and metadata.
- `boundaries/bc_<topaz_id>.gml` (+ `.shp` sidecars) — HEC-RAS boundary condition polygons; accompanies the GeoJSON.
- `channel_buffer.gml` / `channel_buffer.shp` + `buffer_raster/*` (when buffer generation succeeds) — floodplain buffer derived from channel widths.
- `README.dss_export.md` — this guide, copied into the export directory for downstream consumers.

### How the volumetric/percent ash metrics are computed

- **Inputs**:  
  - `H.pass.parquet` (from `H*.pass.dat`): per-hillslope runoff volume (`runvol`) and sediment concentrations `sedcon_1`–`sedcon_5` (kg/m³).  
  - `H.wat.parquet` (from `H*.wat.dat`): per-hillslope areas.  
  - Ash parquet files (`ash/H{wepp_id}_ash.parquet`): per-day ash transport masses (tonne) plus `Ash.meta` (ash type black/white, bulk density). Defaults if meta is absent: black 0.22 g/cm³, white 0.31 g/cm³.

- **`sed_vol_conc` (sediment volumetric concentration)**  
  1) per hillslope/day: `seddep_i = sedcon_i * runvol` (kg).  
  2) class volumes: `V_i = seddep_i / ρ_i`, with densities [2600, 2650, 1800, 1600, 2650] kg/m³ for classes 1–5.  
  3) sum solids volume: `V_sed = Σ V_i`.  
  4) aggregate `V_sed`, `runvol` across hillslopes.  
  5) `sed_vol_conc = V_sed / runvol_total` (guarded against zero runoff).

- **`ash_vol_conc` (ash volumetric concentration)**  
  1) per hillslope/day ash mass = `ash_transport` (tonne).  
  2) pick bulk density (kg/m³): `ash_bulkdensity` or `field_ash_bulkdensity` from `Ash.meta`, else default by ash type; convert g/cm³ → kg/m³.  
  3) `V_ash = ash_transport_tonne * 1000 / density_kg_m3`.  
  4) aggregate `V_ash`, `runvol` across hillslopes.  
  5) `ash_vol_conc = V_ash / runvol_total` (guarded).

- **`sed+ash_vol_conc` (combined solids volumetric concentration)**  
  `(V_sed + V_ash) / runvol_total` using the same solids volumes as above.

- **`ash_black_pct_by_vol` (black-ash share of ash solids)**  
  1) per hillslope/day: if `Ash.meta` says “black”, `V_black = V_ash`, else 0.  
  2) aggregate `V_black`, `V_ash` across hillslopes.  
  3) `ash_black_pct_by_vol = (V_black / V_ash) * 100`, guarded so zero ash volume → 0.

## Working With `pydsstools`

### Dependencies

The compose build installs **pydsstools==2.4.0** into `/opt/venv`. That wheel bundles the native HECDSS C library, so we do *not* need to compile from source.

Key APIs:

```python
from pydsstools.heclib.dss import HecDss
from pydsstools.core import TimeSeriesContainer, dss_info, DssPathName
```

Common patterns:

```python
with HecDss.Open(dss_path) as fid:
    tsc = TimeSeriesContainer()
    tsc.pathname = "/A/B/C/D/E/F/"
    tsc.startDateTime = "01Feb2011 00:00:00"
    tsc.interval = 1440                  # minutes for regular daily
    tsc.numberValues = len(values)
    tsc.units = "M3"
    tsc.type = "INST"
    tsc.values = values.astype(float)
    fid.deletePathname("/A/B/C//E/F/")   # wipe prior versions
    fid.put_ts(tsc)

with HecDss.Open(dss_path, mode="r") as fid:
    ts = fid.read_ts("/A/B/C/D/E/F/")
    info = dss_info(fid, "/A/B/C/D/E/F/")
```

### DSS Date Semantics

Regular time-series (code 100) always use **block storage**:

- The pathname `D` part is normalized to `01Jan<YEAR>` when you write the record. `pydsstools` does this even if you pass `D="01Feb2011"`.
- `ts.startDateTime` stores the *actual* first timestamp (e.g., `01Feb2011 00:00:00`).
- `logicalNumberValues` is the block size (365 / 366 for daily).
- `numberValues` counts how many values you actually filled. Everything else is the DSS missing sentinel (`-3.4028235e38`).

Irregular series (code 115) behave similarly: they sit in the yearly block, but the real timestamps live with each value. Our peak-flow exports use `E="IR-Year"` and set `ts.times` to a Python list of datetimes.

### Inspecting Records

```python
with HecDss.Open(path, mode="r") as fid:
    info = dss_info(fid, pathname)
    print(info.numberValues, info.logicalNumberValues, info.startDateTime)
```

Use this to confirm how many slots we stored and what DSS considers the true start time. The browse service relies on `dss_preview.build_preview()` to collect this metadata.

## Export Functions

### `totalwatsed_partitioned_dss_export(wd, start_date=None, end_date=None, …)`

1. Loads `Watershed` + translator to map TopAZ channel IDs → WEPP hillslope IDs.
2. Runs `run_totalwatsed3()` with a `WHERE wepp_id IN (...)` clause and sorts by `(year, julian, sim_day_index)`.
3. Applies `apply_date_filters()` using the inclusive bounds from `dss_start_date` / `dss_end_date`.
4. Converts each metric column to a `TimeSeriesContainer`:
   - `label` is sanitized to DSS-friendly text (replace spaces, parentheses, underscores).
   - D-part is derived from the filtered `series_start` (`df.iloc[0]`).
   - Values are `float64`. `np.nan` columns are skipped entirely.
   - DSS pathname pattern: `/WEPP/TOTALWATSED3/<LABEL>/<DDMonYYYY>/1DAY/<TopazID>/`.
5. Deletes any prior `//1DAY/<TopazID>/` record to avoid stale blocks.

**Date filtering note:** we keep `start_date/end_date` in local variables (`start_bound`, `end_bound`) so every channel sees the same filter window even as we mutate `series_start`.

### `chanout_dss_export(wd, start_date=None, end_date=None, …)`

1. Reads `chan.out.parquet`, builds datetime stamps per channel, filters by the same bounds.
2. Writes irregular DSS records (`E="IR-Year"`, `ts.times = [...]`, `ts.interval = -1`).
3. Pathname `/WEPP/CHAN-OUT/PEAK-FLOW//IR-YEAR/<channel_id>/`.
4. Because irregular records rely on explicit timestamps, `numberValues` equals the number of peak events in the filtered window even though the pathname D-part is still normalized to `01Jan<year>`.

### `archive_dss_export_zip(wd)`

Simple helper that zips everything under `export/dss/` into `dss.zip`. Called after both DSS writers finish.

## Browse DSS Preview

`wepppy/microservices/dss_preview.py` is the source of truth for the browse view. It:

- Opens each file with `HecDss`.
- Uses `getPathnameList()` and `dss_info()` to collect:
  - Pathname parts (A-F).
  - Record type name (TS, PD, GRID, etc.) via `fid._record_type()`.
  - `numberValues` (stored) vs. `logicalNumberValues`.
  - `startDateTime` + derived end date (`start + interval * (stored-1)`).
- Summarizes unique A/B/C/D/E/F parts and record-type counts.
- Returns a `DssPreview` dataclass that the template renders in `browse/dss_file.htm`.

Because DSS normalizes the D-part, the preview relies on `startDateTime` rather than the literal `/01Jan2011/` string. When only three values are stored, the table shows `Values = 365 (stored: 3)`—the parentheses remind readers that most of the block is DSS missing data. Irregular (`IR-Year`) peak-flow files are summarized from the explicit event timestamps, so the Start/End columns reflect the actual peaks stored.

## Field Guide / Troubleshooting

### Understanding "Blocky" or Stepped Peak-Flow Hydrographs

The DSS peak-flow files (`peak_chan_<id>.dss`) are direct exports of WEPP's channel routing output (`chan.out`). If you see flat-topped or stair-stepped hydrographs, this is **expected model behavior**—not an export bug.

#### Why hydrographs can look stepped

WEPP doesn't have access to continuous flow measurements. Instead, it reconstructs channel inflow hydrographs from three summary values computed on each hillslope:

| Input | Description | Source |
|-------|-------------|--------|
| **Volume** (`vol`) | Total runoff volume (m³) | Hillslope water balance |
| **Peak** (`qp`) | Peak runoff rate (m³/s) | Computed from effective length and hydraulics |
| **Duration** (`td`) | Runoff duration (seconds) | From storm duration or upstream max |

From these three numbers, WEPP synthesizes a time-varying inflow hydrograph. The shape depends on a simple ratio:

```
A = Volume / (Peak × Duration)
```

**When A < 1** — The runoff volume "fits" under a peaked hydrograph. WEPP generates a double-exponential curve: flow rises to the peak, then falls. This looks like a natural storm response.

**When A ≥ 1** — The volume is too large to fit under a peaked curve. Mathematically, no solution exists for the exponential shape. WEPP falls back to a **rectangular (flat-top) hydrograph**: flow instantly jumps to the peak rate and holds there for the entire duration.

This rectangular fallback is the primary cause of "blocky" hydrographs.

#### The routing timestep also matters

Channel routing runs at a fixed timestep (`dtchr`), typically 60 seconds. Even smooth hydrographs become stair-stepped when discretized at this resolution. Longer timesteps make the steps more visible.

#### Where to look in the code

| File | Function |
|------|----------|
| `chrqin.for` | Builds inflow hydrograph from vol/qp/td; contains the rectangular fallback |
| `wshchr.for` | Routes flow through channels; finds peak as max of timestep series |
| `eqroot.for` | Solves `1 - exp(-u) = A×u` for the exponential shape (only valid when 0 < A ≤ 1) |

### Snowmelt and Baseflow: Why They Produce Long Plateaus

Snowmelt and baseflow present a special challenge because WEPP tracks them as **daily totals**, not as sub-daily time series.

#### How melt enters the channel

1. **Duration defaults to 24 hours.** When melt produces runoff but no storm duration is available, WEPP assigns a 24-hour duration. This causes the runoff to be "spread" across the entire day.

2. **Subsurface and baseflow are uniform.** Lateral inflow from groundwater and subsurface flow is distributed evenly over 24 hours:
   ```
   lateral inflow rate = daily volume / 86400 seconds
   ```
   This produces perfectly flat contributions to channel flow.

3. **Large volumes trigger the rectangular fallback.** Melt events often produce large volumes relative to peak rates. This pushes the ratio A above 1, forcing the flat-top hydrograph.

The combination of these factors means snowmelt-dominated periods often show plateau-like flow patterns lasting many hours—this reflects how WEPP internally represents melt, not measurement error.

#### Interpreting melt-period hydrographs

When you see a flat peak lasting 6–24 hours during spring or after snow events:
- It likely represents melt-driven runoff
- The peak *magnitude* is still meaningful (it's the max routed flow)
- The *shape* reflects WEPP's daily melt accounting, not instantaneous conditions

#### Options for smoother output

| Approach | Tradeoff |
|----------|----------|
| Reduce routing timestep (`dtchr`) | More computation; doesn't fix rectangular fallback |
| Use breakpoint climate data | May yield shorter, higher-peaked storms that avoid A ≥ 1 |
| Adjust `MX .5 P` in CLIGEN | Changes storm intensity/duration relationships |
| Accept the plateau | Appropriate if volume and peak magnitude matter more than shape |

### Common Questions

1. **"Browse says 2011-01-01 but I filtered Feb 2021."**  
   Check the `stored` count and expand the record via `read_ts`. If `startDateTime` is correct and `numberValues` matches your filter window, the export is fine—the D-part is just a DSS block key.

2. **Peak flow rows show `IR-Year` with stored=3.**  
   That’s expected: irregular series sit in yearly blocks. Use `fid.read_ts()` to see the actual event datetimes.

3. **Need to verify filtered date range for a specific channel.**  
   ```python
   from wepppy.wepp.interchange.dss_dates import parse_dss_date
   from wepppy.wepp.interchange.date_filters import apply_date_filters
   from wepppy.wepp.interchange.totalwatsed3 import run_totalwatsed3
   # run_totalwatsed3(... wepp_ids=[<channel hillslopes>]) then apply_date_filters
   ```

4. **Adding new DSS metrics.**  
   - Update `totalwatsed3` schema.
   - Extend `totalwatsed_partitioned_dss_export()` to include the column (update `identifier_columns`, label sanitization, units metadata).
   - Confirm the browse preview auto-lists it (no template change needed).

5. **`dss_info` errors (“Seems invalid Data Size Query”).**  
   This happens when a pathname doesn’t exist for the requested TopAZ ID. Ensure `translator.iter_chn_ids()` returns valid IDs and that `_channel_wepp_ids()` finds at least one hillslope.

6. **PyPI version vs. source build?**  
   Stick with the packaged wheel unless you need a bugfix upstream. Our Dockerfile resolves all numeric / GDAL deps (`gdal-bin`, `libgdal-dev`, etc.) so `pydsstools` works out of the box.

## References

- [pydsstools documentation](https://github.com/gyanz/pydsstools)
- `docker/Dockerfile` – runtime stack ensuring GDAL/PROJ/HDF5 libs exist for `pydsstools`.
- `wepppy/microservices/browse.py` – browse service handler (`_maybe_render_dss_preview`).
- `wepppy/nodb/scripts/dss_export/plot_peak_chan_compare.py` - overlay plot comparing `peak_chan_<id>.dss` vs `chan.out.parquet`.
- `tests/wepp/interchange/test_watershed_totalwatsed_export.py` – regression test for date filtering and per-channel exports.
