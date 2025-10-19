# nodb_api Blueprint Reference

Authored: 10-18-2025

This note summarises every Flask blueprint under `wepppy/weppcloud/routes/nodb_api/`. The goal is to orient contributors to the NoDb-backed API surface that powers the Control UI and report views. Use it as an index before drilling into module source or NoDb controllers.

## Common Patterns
- Every module imports shared helpers from `wepppy/weppcloud/routes/_common.py` for `Blueprint`, request helpers, and `load_run_context`.
- Route prefixes follow `/runs/<runid>/<config>/…` and expect callers to include the current working directory identifier and configuration name.
- Most handlers fetch the run’s working directory with `get_wd()` or `load_run_context()` and then operate on a singleton NoDb controller (for example `Climate.getInstance(wd)`).
- `tasks/` routes mutate state and usually return `success_factory()`; `query/` routes return JSON snapshots; `report/` and `view/` render HTML templates; `resources/` streams files in `static`/`_reports` directories.
- Authorization helpers (`authorize`, `authorize_and_handle_with_exception_factory`, `login_required`) wrap endpoints that require authenticated users or ownership checks.

## Blueprint Catalogue

### `climate_bp.py`
- **Purpose**: Drive climate-source selection, heuristics, and reporting for a run’s `Climate` controller.
- **Dependencies**: `Climate`, `ClimateStationMode`, `Ron`, `StationMeta`; uses `secure_filename` to persist uploaded `.cli` files.
- **Key routes**:
  - `tasks/`: set climate station mode, choose a station, upload user `.cli`, switch climate mode/spatial mode, and toggle GridMET wind fallback.
  - `query/`: return the active climate station string and a `has_observed` indicator.
  - `view/`: render HTML dropdowns for closest/heuristic stations (domestic and EU/AU variants), preview `.par` contents, and climate monthly summaries.
  - `report/`: render `reports/climate.htm` with station metadata.
- **Notes**: Many `view/` endpoints honour `Climate.getInstance(wd, ignore_lock=True)` so read-only runs can browse cached results without mutating state.

### `debris_flow_bp.py`
- **Purpose**: Present debris-flow analysis for runs with the `DebrisFlow` mod enabled.
- **Dependencies**: `DebrisFlow`, `Ron`, `Unitizer`, `wepppy.nodb.unitizer.precisions`.
- **Key routes**:
  - `report/debris_flow`: renders `reports/debris_flow.htm` populated with the NoDb controllers and user context.
- **Notes**: Read-only blueprint; all work happens inside the template using supplied NoDb instances.

### `disturbed_bp.py`
- **Purpose**: Manage SBS/BAER disturbed-land inputs, fire dates, and cover transforms.
- **Dependencies**: `Disturbed`, `Baer`, `Ron`, `write_disturbed_land_soil_lookup`, revegetation helpers, SBS sanity checks.
- **Key routes**:
  - `tasks/`: reset or extend the land/soil lookup, apply edits, adjust burn classes, upload SBS rasters and cover transforms, toggle fire date, and build uniform SBS placeholders.
  - `api/`: lightweight JSON endpoints for SBS presence flags.
  - `query/` and `view/`: surface BAER map bounds and render classification UI.
  - `resources/baer.png`: streams the RGB overlay for the map widget.
- **Notes**: Most routes enforce `authorize_and_handle_with_exception_factory` to guard sensitive raster updates.

### `interchange_bp.py`
- **Purpose**: Kick off Redis Queue jobs that migrate legacy WEPP interchange archives into the modern schema.
- **Dependencies**: `run_interchange_migration` RQ task, `RedisDB.RQ`.
- **Key routes**:
  - `tasks/interchange/migrate`: validates optional subpath input, enqueues RQ job, and returns the job id.
- **Notes**: `_sanitize_subpath` protects against traversal by rejecting `..` or absolute prefixes.

### `landuse_bp.py`
- **Purpose**: Control landuse modes, NLCD database selection, and coverage edits.
- **Dependencies**: `Landuse`, `LanduseMode`, `Ron`.
- **Key routes**:
  - `tasks/`: set landuse mode/database, mutate landuse coverage and mapping, bulk modify landuse assignments.
  - `query/`: expose domain dictionaries plus subcatchment/channel summaries and cover tables.
  - `report/`: render `reports/landuse.htm` with computed options and summaries.
- **Notes**: Many mutations rely on JSON payloads with domain identifiers (`dom`, `cover`, `value`).

### `observed_bp.py`
- **Purpose**: Handle observed timeseries ingestion, calibration, and reporting.
- **Dependencies**: `Observed`, `Wepp`, `Ron`, `Unitizer`.
- **Key routes**:
  - `tasks/run_model_fit`: queue or run the observed-model fitting routine.
  - `report/observed`: serve the observed summary template.
  - `plot/observed/<selected>`: stream Matplotlib plots for selected observed datasets.
  - `resources/observed/<file>`: download CSV/JSON artifacts created during fitting.
- **Notes**: Most endpoints wrap responses with `exception_factory` to surface fit errors to the UI.

### `omni_bp.py`
- **Purpose**: Manage Omni scenario bundles and migration for multi-scenario projects.
- **Dependencies**: `Omni`, `Treatments`, `Ron`, `Watershed`.
- **Key routes**:
  - `api/omni/get_scenarios` and `get_scenario_run_state`: return scenario metadata and dependency trees.
  - `tasks/omni_migration`: initializes Omni (and Treatments if missing) inside the project’s `_mods`.
  - `report/omni_scenarios`: builds the Omni scenario summary report using run statistics.
- **Notes**: Migration enforces exclusive access via `ron.locked()` before mutating `_mods`.

### `project_bp.py`
- **Purpose**: Project-level orchestration: cache management, ownership, metadata, and geometry exports.
- **Dependencies**: `Ron`, `Watershed`, `arc_export`, `clear_nodb_file_cache`, RQ helpers for set-readonly, Redis connections.
- **Key routes**:
  - `tasks/`: clear locks/cache, delete runs, add/remove users, update project name/scenario, toggle `public`/`readonly` flags (with RQ job), and manage metadata.
  - `meta/` and `resources/`: stream shapefiles/GeoJSON (subcatchments, netful, bounding polygons) after ensuring state.
  - `report/users`: renders collaborator list for the run.
- **Notes**: Deletion removes filesystem run directory and associated database rows; most routes call `authorize_and_handle_with_exception_factory`.

### `rangeland_bp.py`
- **Purpose**: Configure rangeland cover fractions and build RAP-driven coverage.
- **Dependencies**: `RangelandCover`, `Ron`.
- **Key routes**:
  - `tasks/modify_rangeland_cover` and `build_rangeland_cover`: accept JSON or form payloads to update cover percentages and bootstrap defaults.
  - `query/rangeland_cover/subcatchments`: JSON summary for UI tables.
  - `report/rangeland_cover`: render rangeland cover report for the run.
- **Notes**: Validates cover percentages (0–100) before applying updates.

### `rangeland_cover_bp.py`
- **Purpose**: Surface RAP-driven rangeland cover summaries and manage RAP year/mode toggles.
- **Dependencies**: `RangelandCover`, `RangelandCoverMode`.
- **Key routes**:
  - `query/rangeland_cover/current_cover_summary`: POST JSON list of Topaz ids and returns cover snapshot.
  - `tasks/set_rangeland_cover_mode`: update mode and RAP year on the NoDb controller.
- **Notes**: Uses `load_run_context` to resolve the working directory, mirroring `rangeland_bp`.

### `rhem_bp.py`
- **Purpose**: Provide RHEM (rangeland hydrology and erosion model) reports and derived queries.
- **Dependencies**: `RhemPost`, `Ron`, `Unitizer`, RAP precisions.
- **Key routes**:
  - `report/`: family of templates for results, run summary, average annuals, and return periods.
  - `query/rhem/...`: JSON helpers for runoff, sediment yield, and soil loss per subcatchment.
- **Notes**: Templates expect precomputed files in `rhem/output/`; route guards use `authorize`.

### `soils_bp.py`
- **Purpose**: Configure soil selections, toggles, and summaries.
- **Dependencies**: `Soils`, `SoilsMode`, `Disturbed`.
- **Key routes**:
  - `tasks/`: set soil mode (including DB selections), toggle KS flags, and push disturbed soil versions down to the Disturbed mod.
  - `query/`: domain dictionary plus subcatchment/channel summaries.
  - `report/soils`: render soils report.
- **Notes**: Validates JSON payloads for flag updates; all state is persisted through the NoDb singleton.

### `treatments_bp.py`
- **Purpose**: Switch treatment planning modes.
- **Dependencies**: `Treatments`, `TreatmentsMode`.
- **Key routes**:
  - `tasks/set_treatments_mode`: update treatments mode from form data.
- **Notes**: Narrow blueprint introduced to replace logic embedded in landuse routes.

### `unitizer_bp.py`
- **Purpose**: Provide unit conversion helpers for UI widgets.
- **Dependencies**: `Unitizer`.
- **Key routes**:
  - `tasks/set_unit_preferences`: persist per-run unit preferences (length, area, discharge, etc.).
  - `/unitizer` and `/unitizer_units`: expose context-processor functions (`unitizer` and `unitizer_units`) returning conversion tables.
  - `report/tasks/set_unit_preferences`: alias for report contexts.
- **Notes**: Routes return `success_factory` JSON for direct UI use; errors fall back to `exception_factory`.

### `watar_bp.py`
- **Purpose**: Serve WATAR ash transport analytics, including hillslope simulations and contaminant reports.
- **Dependencies**: `Ash`, `AshPost`, `AshType`, `Disturbed`, `Climate`, `Wepp`, `Watershed`, `Unitizer`, `load_hill_wat_dataframe`, report builders (`HillSummaryReport`, `ChannelSummaryReport`, `OutletSummaryReport`).
- **Key routes**:
  - `hillslope/<topaz_id>/ash`: run per-hillslope ash transport evaluation using selected ash type and fire date.
  - `tasks/set_ash_wind_transport`: toggle wind transport processing.
  - `report/`: suite covering run dashboard, ash summaries, contaminant reports, recurrence tables.
  - `query/ash_out`: return JSON emission summaries for UI widgets.
- **Notes**: Hillslope route performs runtime simulations and writes to `_ash/`; access requires ownership unless the project is public or the user is an admin.

### `watershed_bp.py`
- **Purpose**: Manage watershed delineation outputs, subcatchment/channel metadata, and abstraction triggers.
- **Dependencies**: `Watershed`, `Ron`, `ChannelRoutingError`, authorization helpers.
- **Key routes**:
  - `query/`: presence checks (`has_dem`, `delineation_pass`), bounding extents, outlet metadata, subcatchment/channel summaries, map layers.
  - `report/`: render watershed summaries and detailed channel/outlet reports.
  - `resources/channels.json`: stream cached channel GeoJSON.
  - `tasks/`: trigger watershed abstraction and subcatchment intersection rebuilds.
- **Notes**: Many query routes simply `jsonify` cached NoDb properties, keeping expensive processing in the controllers.

### `wepp_bp.py`
- **Purpose**: Central blueprint for WEPP model execution, reporting, and map resources.
- **Dependencies**: `Wepp`, `Landuse`, `Climate`, `Watershed`, `Ron`, `RedisPrep`, `Unitizer` (converters and precisions), query engine (`activate_query_engine`, `run_query`), WEPP report classes.
- **Key routes**:
  - `tasks/set_run_wepp_routine`: toggle long-running WEPP routines.
  - `view/`: return HTML fragments for channel definitions and management editors.
  - `report/wepp/*`: extensive library of summary, annual, watbal, return-period, flood, and sediment reports alongside subcatchment/channel detail views.
  - `query/`: JSON results covering summary tables, phosphorus options/subcatchments, time-series pulls, map boundaries, recurrence interval parsing.
  - `plot/`: stream hydrograph plots such as streamflow.
  - `resources/`: expose raster outputs (loss grids, flowpath rasters) for download or map overlays.
- **Notes**: Several routes call `activate_query_engine()` before running DuckDB-backed queries; others reach into NoDb controllers for cached results. Error paths prefer `exception_factory` for telemetry.

