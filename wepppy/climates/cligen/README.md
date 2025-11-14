# CLIGEN Climate Builders
> CLIGEN wrappers, station catalogs, and service clients that turn PRISM/Daymet (and global analogs) into runnable WEPP climate inputs.
> **See also:** `docs/prompt_templates/module_documentation_workflow.prompt.md` for the documentation + typing workflow that governs this module.

## Overview
- `wepppy/climates/cligen` bundles everything WEPPcloud needs to select an appropriate CLIGEN station, rewrite its `.par` file with localized statistics, and run the legacy CLIGEN executables to emit `.cli`, `.prn`, and storm files.
- The package ships the 2015 CONUS catalog plus optional Australian (`au_*`), Chilean, and GHCN-backed station sets. Heavy assets (SQLite DBs, `.par` bundles, CLIGEN binaries) live next to the Python entry points so Git LFS keeps them versioned.
- Higher-level controllers call into this package to (a) pick the “best” station for a lat/lon, (b) align precipitation/temperature distributions with PRISM, EOBS, AGDC, or Daymet, (c) generate multi-year or observed runs, and (d) provide APIs for downstream services (gridMET/MACA, wildfire support, outreach tooling).

## Layout At A Glance
| Path | Role |
| --- | --- |
| `wepppy/climates/cligen/__init__.py` | Re-exports the public API from `cligen.py`, plus helpers (`_stations_dir`, `_bin_dir`, `par_row_formatter`, `make_clinp`). |
| `wepppy/climates/cligen/cligen.py` | Core implementation: station metadata readers, localization math, CLIGEN runner, `.cli/.par/.prn` helpers, heuristics for station search, and `par_mod`. |
| `wepppy/climates/cligen/_scripts/stations_sqlitedb_builder.py` | Offline utility that scans `.par` files and rebuilds the SQLite catalogs (`stations.db`, `2015_stations.db`, `au_stations.db`, etc.). |
| `wepppy/climates/cligen/stations/__init__.py` | Empty marker so packaged `stations/` data can be imported and located with `pkg_resources`. |
| `wepppy/climates/cligen/tests/conftest.py` | Forces the special `collection_error` helper in `geojson_export_test.py` to be collected even though it is not prefixed with `test_`. |
| `wepppy/climates/cligen/tests/geojson_export_test.py` | Exercises `CligenStationsManager.export_to_geojson`, guarding against missing LFS assets. |
| `wepppy/climates/cligen/tests/future_climate_builder.py` | Script-like regression for building future climates from downscaled NMME RCP8.5 time series. |
| `wepppy/climates/cligen/tests/gridmet_maca_climate_builder.py` | MACA/gridMET ingestion workflow (netCDF retrieval, DataFrame → `.prn`, CLIGEN invocation) with optional runtime dependency on the standalone `cligen` package. |
| `wepppy/climates/cligen/tests/prism_point_builder.py` | Convenience utility that localizes a station to a 3×3 PRISM grid around an input point. |
| `wepppy/climates/cligen/single_storm.py` | Direct CLI builder for the single-storm workflow (used by `Climate` NoDb controller). |

## Core APIs (cligen.py)
- **Station / StationMeta**
  - `Station` parses a `.par` file into numpy arrays (`ppts`, `pwws`, `pwds`, `tmaxs`, `tmins`) and exposes `localize()` to rewrite monthly means using PRISM/Daymet/EOBS/AGDC surfaces.
  - `StationMeta` holds catalog metadata (state, description, `tp5/tp6` thunderstorm params, annual precip) and can emit dictionaries (optionally embedding monthlies) or build ad‑hoc GHCN-based observed climates via `build_ghcn_daily_climate`.
- **CligenStationsManager**
  - Loads the requested SQLite catalog (`2015`, `legacy`, `au`, `ghcn`, `chile`) and exposes distance-first searches (`get_closest_station(s)`), heuristic searches that combine distance, elevation, and climatology, plus specialized heuristics for Europe (`get_stations_eu_heuristic_search`) and Australia (`get_stations_au_heuristic_search`).
  - `export_to_geojson`/`to_geojson` serialize the currently loaded stations, falling back to a temp dir when the requested destination is unwritable; the geojson test covers this path.
  - When an LFS asset is unavailable the manager falls back to `tests/neverland_.par` so developers still have something to interact with.
- **ClimateFile & Prn helpers**
  - `ClimateFile` opens a CLIGEN `.cli`, standardizes headers, reports metadata (`lat`, `lng`, `elevation`), and offers utilities such as `clip`, `transform_precip`, `replace_var`, `make_storm_file`, `as_dataframe`, and `calc_monthlies`.
  - `Prn` wraps the fixed-width `.prn` format, replaces IQR outliers, and re-emits sanitized precipitation/temperature series. `df_to_prn()` converts a pandas DataFrame into a `.prn`, padding to the end of the year when needed.
  - `cli2pat()` back-calculates 10/30/60‑minute intensities for design storms; `_make_clinp()` emits the CLIGEN input files consumed by the binaries.
- **Cligen runner**
  - `Cligen` ties everything together. Given a `StationMeta` and working directory it copies or localizes the `.par`, feeds CLIGEN 4.3/5.2/5.3/5.3.2 binaries (bundled under `bin/`), enforces timeouts (`_run_cligen_posix`), and produces `.cli` files for multi-year or observed runs.
  - `par_mod()` is the high-level localization workflow: pull monthly means from PRISM/EOBS/AGDC, recompute wet-day probabilities (optionally Daymet-driven), rewrite the `.par`, and run CLIGEN in-place. It returns the simulated monthlies for quick QA.
- **NullStation utility**
  - Provides a sentinel `StationMeta` when no catalog entry exists so calling code can still render UI elements without null checks.

## Single-Storm Builder (`single_storm.py`)
- Replaces the legacy REST hop by invoking the bundled CLIGEN binaries directly.
- `build_single_storm_cli()` writes `.par/.cli` files into a caller-provided directory, returning a `SingleStormResult` (paths + computed monthlies).
- Input validation mirrors the legacy REST helper: storm dates accept `MM-DD-YYYY`, `MM/DD/YYYY`, or space-delimited tokens; peak intensity must be between 0–100%.

```python
from pathlib import Path
from wepppy.climates.cligen.single_storm import build_single_storm_cli

result = build_single_storm_cli(
    par=106152,
    storm_date="6-10-2014",
    design_storm_amount_inches=6.3,
    duration_of_storm_in_hours=4.0,
    time_to_peak_intensity_pct=40.0,
    max_intensity_inches_per_hour=3.0,
    output_dir=str(Path("/tmp/wepp_runs") / "cli"),
    filename_prefix="design_storm",
    version="2015",
)
print(result.cli_path)  # /tmp/wepp_runs/cli/design_storm.cli
print(result.monthlies)  # Calculated from the generated CLI (may be None on failure)
```

## Persistent Assets & Builder Script
- `2015_stations.db` + `2015_par_files/` (default), `au_*`, `ghcn_*`, `chile*`, and `stations/` (legacy) ship with the repo. Pull them via Git LFS before running tests (`git lfs pull wepppy/climates/cligen/*`).
- CLIGEN binaries (`bin/cligen43`, `bin/cligen52`, `bin/cligen53`, `bin/cligen532`) are Linux ELF executables; ensure they remain executable (`chmod +x`) after cloning.
- `_scripts/stations_sqlitedb_builder.py` rebuilds the SQLite metadata when `.par` inventories change:
  1. Place all `.par` files in a directory (nested folders acceptable).
  2. Prepare the wildcard → state name mapping (examples: `chile_state_code_wildcards`, `ghcn_state_code_wildcards` in the script).
  3. Run `python wepppy/climates/cligen/_scripts/stations_sqlitedb_builder.py` from the repo root after editing `build_db(...)` at the bottom with your config. The script parses each `.par` using `Station`, computes annual precipitation, and writes both `stations` and `states` tables before chmodding the DB to `0755`.
- `stations/__init__.py` is intentionally empty; its presence lets packaging tools treat `stations/` as a module so callers can locate the bundled assets via `importlib.resources`.

## Example Workflows
1. **Generate a localized multi-year CLI**
   ```python
   from pathlib import Path
   from wepppy.climates.cligen import CligenStationsManager, Cligen

   wd = Path("/tmp/wepp_run")
   wd.mkdir(exist_ok=True)

   manager = CligenStationsManager(version=2015)
   station = manager.get_closest_station((-117.0, 46.4))

   runner = Cligen(station=station, wd=str(wd), cliver="5.3.2")
   runner.run_multiple_year(years=30, cli_fname="wepp.cli", localization=(-117.0, 46.4))
   ```

2. **Convert daily observations into a `.prn` and run an observed simulation**
   ```python
   import pandas as pd
   from wepppy.climates.cligen import df_to_prn, Cligen

   df = pd.read_csv("daymet_extract.csv")  # must contain precipitation, Tmax, Tmin columns
   df_to_prn(df, prn_fn="observed.prn", p_key="PRCP (mm)", tmax_key="TMAX (C)", tmin_key="TMIN (C)")

   runner = Cligen(station=station, wd=str(wd))
   runner.run_observed(prn_fn="observed.prn", cli_fn="observed.cli")
   ```

3. **Export the station catalog to GeoJSON (used by tests/geojson_export_test.py)**
   ```python
   from wepppy.climates.cligen import CligenStationsManager

   manager = CligenStationsManager(bbox=[-124, 49, -110, 40])
   manager.export_to_geojson("stations.geojson")
   ```

4. **Build a PRISM-surrounding parameter set (tests/prism_point_builder.py)**
   ```python
   from wepppy.climates.cligen.tests.prism_point_builder import prism_surrounding
   prism_surrounding("1_Steuben-Co-NY", lng=-77.33, lat=42.33)
   ```

## Tests & Developer Utilities
- `tests/geojson_export_test.py` is the only pytest-native test today. Run it via `wctl run-pytest tests/climates/cligen/test_geojson_export.py` (Git LFS assets must be present).
- `tests/conftest.py` hooks `_pytest` so the helper named `collection_error` executes even though it is not `test_*`. Do not rename unless you update the hook.
- `tests/future_climate_builder.py`, `tests/gridmet_maca_climate_builder.py`, and `tests/prism_point_builder.py` behave like integration notebooks. They demonstrate end-to-end flows (MACA downloads, RCP 8.5 projections, PRISM perturbations) but are too expensive for CI. Run them manually when adjusting the workflows they describe.
- `gridmet_maca_climate_builder` guards its imports: if the optional `cligen` PyPI package or `pandas` is not installed it raises a `ModuleNotFoundError` with a user-friendly message. Respect this pattern when adding new dependencies.
- For stub validation, target `wepppy.climates.cligen` when running `wctl run-stubtest` because `__init__.py` re-exports `cligen.py`.

## Troubleshooting & Tips
- **Git LFS assets missing?** `_db` reads fail fast, but the geojson test and station manager will fall back to `tests/neverland_.par`. Fetch the real data (`git lfs pull wepppy/climates/cligen`) when you need accurate station metadata.
- **Binaries on macOS/Windows?** The shipped CLIGEN executables are Linux-only. Use Docker (`wctl run ...`) or copy the appropriate binaries into `bin/` before running `Cligen`.
- **Timeout diagnostics.** `_run_cligen_posix` records stdout/stderr tails when CLIGEN hangs; check `cligen_*.log` in the working directory plus the captured `_tail()` output in raised exceptions.
- **Localization safeguards.** `par_mod` clamps wet days between 0.1 and `days_in_month - 0.25` and bounds adjustments to [50%, 200%] of the source values to keep CLIGEN stable. When extending localization logic, honor the same constraints.
- **Station heuristics.** `get_stations_heuristic_search`, `get_stations_eu_heuristic_search`, and `get_stations_au_heuristic_search` weight latitude distance, elevation, precipitation, and temperature with `[1, 1, 3, 1.5, 1.5]`. If you tweak these weights, update both the U.S. and EU/AU variants so downstream expectations stay aligned.

## Next Steps When Extending The Module
1. Mirror every public change in a `.pyi` (see `docs/prompt_templates/module_documentation_workflow.prompt.md`).
2. Rebuild or validate the station catalog with `_scripts/stations_sqlitedb_builder.py` whenever `.par` sources or metadata change.
3. Run `wctl run-pytest tests/climates/cligen -k geojson_export` and `wctl run-stubtest wepppy.climates.cligen` before sending a PR.
4. Document new workflows here—README coverage is required for new services, controllers, or heavy assets.
