# Ash Transport NoDb Mod

> Post-fire ash transport modeling, post-processing, and catalog registration for WEPPcloud runs.

> **See also:** [AGENTS.md](../../../../AGENTS.md) for Working with NoDb Controllers and Module Organization best practices.

## Overview

The ash transport mod drives WEPPcloud wildfire response analytics by simulating how burned hillslopes lose ash to runoff, wind, and decomposition following a fire. It coordinates model calibration, gridded inputs, and hydrologic drivers to deliver reproducible time series for every TOPAZ hillslope in a watershed-scale project.

`Ash` is a NoDb controller that combines climate data, WEPP hydrology, burn severity maps, and optional raster overrides before executing calibrated transport models for each hillslope. Completed simulations feed directly into the `AshPost` pipeline, which produces versioned parquet datasets with embedded metadata so dashboards, query-engine clients, and incident teams can interrogate watershed-scale ash impacts with confidence.

Primary consumers include incident hydrologists, Burned Area Emergency Response (BAER) specialists, and developers integrating ash transport with contaminant routing or decision-support tooling. Outputs also drive automated reports, return-period summaries, and Redis-backed observability channels that surface run progress within the control UI.

## Workflow

### 1. Initialization and Input Harvesting
- `Ash.__init__` loads per-project configuration (the `[ash]` section), resolves raster paths for ash load, bulk density, and ash type, and loads contaminant defaults for low/moderate/high burn classes. Contaminant dictionaries fall back to `get_cc_default` when the config omits values.
- Existing artifacts in `ash_dir` are purged so reruns never mix schema versions or stale plots. The directory is recreated immediately after cleanup.
- Calibration parameters for both supported models (`multi` / Srivastava 2023 and `alex` / Watanabe 2025) are seeded so callers can switch calibrations without rebuilding NoDb state.

### 2. Hillslope Simulation
- `Ash.run_ash` iterates over watershed TOPAZ hillslopes, computes metadata (burn class, area, slope, ash type), and pulls inputs such as CLIGEN climate series (`ClimateFile.as_dataframe`) and WEPP hill water balance parquet (`load_hill_wat_dataframe`).
- Depending on `ash.model`, hillslope simulations use `ash_multi_year_model.White/BlackAshModel` (exponential decay controlled by bulk density and runoff) or `ash_multi_year_model_alex.White/BlackAshModel` (dynamic transport capacity sensitive to slope and organic matter).
- Simulations run in parallel through `createProcessPoolExecutor` when multiple CPUs are available. Each task writes `H{wepp_id}_ash.parquet` plus diagnostic PNGs into `ash_dir`.
- Runtime metadata (initial depths, loads, ash types) is cached on the NoDb instance for downstream inspection and post-processing.

### 3. Post-Processing and Documentation
- After hillslope simulations finish, `Ash` ensures an `AshPost` controller exists and invokes `AshPost.run_post`.
- `AshPost` removes incompatible outputs when the schema version changes (`ASHPOST_VERSION`), converts hillslope outputs into watershed-scale annual, daily, burn-class, and cumulative parquet tables, and stores semantic metadata (units, descriptions) in Arrow schemas via `pa_field`.
- Markdown documentation (`ash/post/README.md`) is regenerated from actual parquet schemas using `generate_ashpost_documentation`, keeping analysts aligned with the precise column definitions.

### 4. Catalog and Telemetry
- Successful runs call `update_catalog_entry(wd, "ash")`, registering artifacts with the Redis-backed query engine catalog so downstream consumers discover ash products automatically.
- `RedisPrep.timestamp(TaskEnum.run_watar)` marks ash completion in Redis DB 2, driving control-panel status indicators and historical telemetry.

## Installation / Setup

- No extra installation is required beyond the standard WEPPcloud development stack. Ensure CLIGEN inputs, WEPP hillslope outputs, and burn severity rasters are present in the working directory.
- Populate the `[ash]` section of the run configuration (`*.cfg`) with raster paths and model options before instantiating `Ash`.
- Optional contaminant thresholds live under `[ash.contaminants.low|moderate|high]` and override baked-in defaults when provided.
- When running outside Docker, confirm `wepppyo3` shared libraries are available so `identify_median_single_raster_key` can summarize rasters.

## Quick Start / Examples

```python
from pathlib import Path
from wepppy.nodb.mods.ash_transport import Ash, AshPost

wd = Path("/path/to/workdir")

# Upstream controllers (Watershed, Wepp, Climate, Landuse) must already be populated.
ash = Ash.getInstance(wd, "project.cfg")
ash.model = "alex"  # choose between "multi" (Srivastava2023) and "alex" (Watanabe2025)
ash.run_ash(fire_date="8/4", ini_white_ash_depth_mm=3.0, ini_black_ash_depth_mm=5.0)

# Post-processing can be rerun independently to regenerate parquet outputs and documentation.
ash_post = AshPost.getInstance(wd)
ash_post.run_post()
```

After execution, inspect `wd/ash` for per-hillslope parquet files and `wd/ash/post` for aggregated datasets, version manifests, and the generated documentation.

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `ash.fire_date` | `8/4` | Default ignition date (`YearlessDate`) applied when `run_ash` is first invoked. |
| `ash.ini_white_ash_depth_mm` | `5.0` | Initial white ash depth (mm) set on controller initialization; per-run overrides accepted via `run_ash`. |
| `ash.ini_black_ash_depth_mm` | `5.0` | Initial black ash depth (mm) set on controller initialization; per-run overrides accepted via `run_ash`. |
| `ash.model` | `multi` | Selects the calibration: `multi` (Srivastava 2023) or `alex` (Watanabe 2025). |
| `ash.run_wind_transport` | `false` | Enables wind-driven removal using thresholds from `wind_transport_thresholds.py`. |
| `ash.ash_load_fn` | `None` | Raster (kg m⁻²) providing initial ash load per hillslope; cropped to the watershed DEM when loaded. |
| `ash.ash_bulk_density_fn` | `None` | Raster (g cm⁻³) that overrides bulk density per hillslope before calibration. |
| `ash.ash_type_map_fn` | `None` | Raster (0 = black, 1 = white) mapped to `AshType`; burn class mapping is used when absent. |
| `ash.black_ash_bulkdensity` | `0.22` | Modeled bulk density (g cm⁻³) used during simulation for black ash. |
| `ash.white_ash_bulkdensity` | `0.31` | Modeled bulk density (g cm⁻³) used during simulation for white ash. |
| `ash.field_black_ash_bulkdensity` | `0.22` | Field-measured bulk density (g cm⁻³) applied when converting depths to loads. |
| `ash.field_white_ash_bulkdensity` | `0.31` | Field-measured bulk density (g cm⁻³) applied when converting depths to loads. |
| `ash.reservoir_capacity_m3` | `1_000_000` | Capacity gate for routing ash to a reservoir; adjust when modeling retention structures. |
| `ash.reservoir_storage` | `80` | Initial reservoir storage percent; setter enforces numeric input. |
| `ash.contaminants.<severity>.<name>` | Built-in defaults | Optional contaminant concentration lookup (mg kg⁻¹ or μg kg⁻¹) per burn severity. |

Configuration values are cached inside the NoDb instance; wrap overrides within `with ash.locked():` and rely on property setters (for example, `ash.black_ash_bulkdensity = 0.28`) so changes persist to disk and Redis.

## Key Concepts / Domain Model

| Concept | Description |
|---------|-------------|
| `Ash` | NoDb controller (`ash.py`) that aggregates inputs, schedules hillslope simulations, and coordinates with Redis telemetry. |
| `AshPost` | Post-processing controller (`ashpost.py`) that validates artifacts, writes parquet summaries, and documents schema versions. |
| `AshType` | IntEnum (`ash_type.py`) distinguishing black vs. white ash; drives parameter selection and raster decoding. |
| `AshSpatialMode` | Mode flag controlling whether ash depth inputs are single values or gridded rasters; stored on the controller for UI toggles. |
| `ash_multi_year_model` | Srivastava 2023 calibration focused on exponential decay of transport capacity governed by bulk density and runoff. |
| `ash_multi_year_model_alex` | Watanabe 2025 calibration with dynamic transport capacity, slope sensitivity, and organic matter feedbacks. |
| `AshPost` artifacts | `ash/post/*.parquet`, `ash/post/ashpost_version.json`, and `ash/post/README.md` are versioned deliverables consumed by dashboards and analytics. |
| `contaminants_iter` | Generator yielding per-severity contaminant concentrations and units for ash chemistry reporting. |

## Developer Notes

- **Code layout:** Core controllers live in `ash.py` and `ashpost.py`. Calibrations reside in `ash_multi_year_model.py` (Srivastava 2023) and `ash_multi_year_model_alex.py` (Watanabe 2025); auxiliary utilities include `wind_transport_thresholds.py`, `ashpost_versioning.py`, and `ashpost_documentation.py`.
- **Concurrency:** Hillslope simulations parallelize through `createProcessPoolExecutor`. Set `ash.MULTIPROCESSING = False` when debugging to run serially.
- **Calibration data:** Default parameter tables ship in `data/`, while provenance artifacts (spreadsheets, notebooks) live under `dev/`.
- **Versioning:** Bump `ASHPOST_VERSION` alongside schema changes. `remove_incompatible_outputs` clears stale parquet files before regeneration, and `write_version_manifest` records the active version.
- **Serialization:** Add new public attributes or helpers to `__all__` in `__init__.py` so legacy NoDb payloads hydrate cleanly. Use `nodb_setter` on mutating properties to persist changes.
- **Testing:** Integration-heavy tests live in `wepppy/nodb/mods/ash_transport/tests/` (for example `multi_year_test.py`, `annuals_test.py`). Run `pytest wepppy/nodb/mods/ash_transport/tests` from the repository root; tests expect WEPP outputs and sample rasters stored in `tests/data/`.

## Operational Notes

- Invoke `Ash.run_ash` only after upstream controllers (`Watershed`, `Wepp`, `Climate`, `Landuse`) have populated their outputs. Missing CLIGEN or hill water balance data triggers runtime assertions.
- Raster overrides rely on `wepppyo3.raster_characteristics.identify_median_single_raster_key`; ensure the shared library is available in the execution environment.
- `AshPost` regenerates watershed aggregates and documentation idempotently, allowing post-processing reruns without re-simulating hillslopes.
- All mutations must occur inside `with ash.locked():` or `with ash_post.locked():` blocks to respect Redis-backed locking. Avoid mutating state while multiprocessing tasks execute.
- Telemetry signals (catalog updates and Redis timestamps) fire only after successful runs; failed hillslope tasks are cancelled and raised back to the caller for troubleshooting.

## Further Reading

- `docs/ui-docs/ash-control-plan.md` — Control UI workflow for configuring ash transport runs.
- `docs/ui-docs/control-ui-styling/control-inventory.md` — Catalog of UI controls, including ash transport toggles.
- `wepppy/nodb/mods/ash_transport/ashpost_documentation.py` — Markdown documentation generator implementation details.
- `wepppy/nodb/mods/ash_transport/dev/README.md` — Research notes and calibration references for the ash models.
- `wepppy/readme.md` — Repository-wide architecture overview with NoDb and Redis integration notes.

## Credits / License

Ash transport calibrations originate from Srivastava et al. (2023) and Watanabe et al. (2025) wildfire ash transport studies. The module ships under the University of Idaho BSD‑3 Clause license, and authorship follows the policy outlined in `AGENTS.md`; retain research citations within calibration notebooks under `dev/`.
