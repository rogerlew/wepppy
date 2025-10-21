# Ash Transport Coding Guide

> Maintained by GitHub Copilot / Codex. Follow this guide when working on `wepppy.nodb.mods.ash_transport`.

## Module Purpose
- Model post-fire ash depletion and export hillslope daily time series (`Ash` controller).
- Convert hillslope parquet outputs into watershed summaries with versioned schemas (`AshPost`).
- Register results in the query-engine catalog and surface telemetry to Redis observers.

## Key Files & Exports
- `ash.py` → `Ash`, `AshSpatialMode`, `run_ash_model`. Holds NoDb state, orchestrates hillslope simulations, manages contaminants metadata.
- `ashpost.py` → `AshPost`. Performs artifact cleanup, aggregation, Arrow schema metadata injection, documentation generation.
- `ash_multi_year_model.py` / `_alex.py` → Srivastava 2023 (“multi”) and Watanabe 2025 (“alex”) calibrations. Return parquet per hillslope with shared column conventions.
- `ashpost_versioning.py` → `ASHPOST_VERSION`, manifest helpers, cache invalidation.
- `ash_type.py` → `AshType` enum (black vs white ash).
- `__init__.py` reexports `Ash`, `AshSpatialMode`, `AshPost`, `AshType`. Update `__all__` whenever you add public helpers.

## Run Workflow (Ash)
1. **Initialization**: `Ash.__init__` locks NoDb, seeds defaults, resolves config paths (`ash.*`), removes stale `ash_dir`, instantiates `AshPost` so both controllers share a manifest root.
2. **Input Prep**: Crops optional rasters (ash load, bulk density, ash type) to the watershed DEM via `raster_stacker`. Uses `identify_median_single_raster_key` to map rasters to TOPAZ IDs.
3. **Simulation**: `run_ash` iterates all hillslopes, composes kwargs (climate dataframe, WEPP hill-wat dataframe, metadata), selects calibration, and dispatches `run_ash_model`.
4. **Parallel Execution**: `MULTIPROCESSING` toggles a process pool managed by `createProcessPoolExecutor`. Respect logging/exception handling; cancel remaining futures on failure.
5. **Post Trigger**: After hillslopes finish, `Ash` fetches/creates `AshPost` and calls `run_post`. It also pings `RedisPrep` to timestamp `TaskEnum.run_watar` for telemetry.

### Core Invariants
- Always mutate controller state inside `with self.locked():`. Reuse `nodb_setter` for property setters.
- Keep `meta`, `fire_years`, `ash_load_d`, and `ash_type_d` consistent; downstream helpers expect them populated before post-processing.
- When using new rasters, ensure the file lives under the working directory or provide a deterministic staging step (crop + copy).
- If you adjust CLI/WEPP file naming conventions, update both the model and post-processing loaders (`read_hillslope_out_fn`).

## Post-Processing (AshPost)
1. **Version Gate**: `_join(ash_dir, 'post')` is cleared when the stored manifest major version mismatches `ASHPOST_VERSION`. Bump the constant for schema-breaking changes only.
2. **Aggregation**: Processes every `H{wepp_id}_ash.parquet`, joins metadata, casts numeric types (uint8/uint16), converts per-area metrics to totals, and computes cumulative transport.
3. **Statistics**: Builds daily, annual, burn-class, and cumulative tables; calculates Weibull-based return periods via `probability_of_occurrence` helpers.
4. **Output**: Writes parquet files with Arrow metadata (`units`, `description`, dataset version info) and renders `post/README.md` documenting schema previews.
5. **Catalog**: Calls `update_catalog_entry` so dashboards and DuckDB agents discover the newly generated datasets.

### AshPost Expectations
- Schema metadata must remain in sync with the parquet columns. Update `COLUMN_DESCRIPTIONS`, `UINT16_COLUMNS`, `UINT8_COLUMNS`, and helper transformations when adding/removing columns.
- Ensure new columns receive both per-area (`(tonne/ha)`) and total (`(tonne)`) variants when appropriate. `_add_per_area_columns` handles automatic conversion, but only for correctly named source columns.
- Regenerate `ash/post/README.md` through `generate_ashpost_documentation`; never edit the generated file manually.

## Configuration & Parameters
- Required config lives under `[ash]` in the run `*.cfg`. Use `config_get_*` helpers to honor defaults and type assertions.
- Supported keys:
  - `model`: `"multi"` (Srivastava 2023) or `"alex"` (Watanabe 2025).
  - `run_wind_transport`: Enables wind thresholds (`wind_transport_thresholds.py`).
  - `ash_load_fn`, `ash_bulk_density_fn`, `ash_type_map_fn`: Rasters in kg m⁻² / g cm⁻³ / categorical. When absent, fall back to defaults derived from burn class and configuration.
  - `black_ash_bulkdensity`, `white_ash_bulkdensity`: Overrides for simulated ash bulk density (distinct from field bulk densities used to back-calculate depth).
  - `ash.contaminants.<severity>.<name>`: Optional per-severity concentration values. `Ash` seeds defaults via `get_cc_default`.
- Fire timing: `fire_date` defaults to 8/4 (YearlessDate). `run_ash` accepts overrides as MM/DD strings.

## Interactions & Dependencies
- Relies on upstream NoDb controllers: `Watershed`, `Wepp`, `Climate`, `Landuse`, `Ron`. Ensure they are hydrated before invoking `Ash`.
- Uses `wepppy.climates.cligen.ClimateFile` and `wepppy.wepp.interchange.hill_wat_interchange.load_hill_wat_dataframe`. Keep interfaces compatible when refactoring those packages.
- Catalog integration depends on `wepppy.query_engine.activate.update_catalog_entry`; verify query-engine metadata when introducing new parquet schemas.
- Telemetry hooks leverage `RedisPrep`. Handle `FileNotFoundError` when redis prep is optional.

## Adding or Updating Models
1. Create a new calibration module (e.g., `ash_multi_year_model_new.py`) mirroring the existing API (`run_model`, `_run_ash_model_until_gone`, shared column names).
2. Register the model in `Ash.__init__` and expose via `available_models`.
3. Ensure per-hillslope outputs adhere to the same column contract; update `AshPost` if additional metrics are introduced.
4. Document the calibration in `README.md` and research notebooks under `dev/`.

## Adjusting AshPost Schemas
1. Update aggregation logic in `ashpost.py`, column metadata dictionaries, and Arrow schema generation.
2. Bump `ASHPOST_VERSION.major` for breaking schema changes; bump `.minor` for additive updates that maintain compatibility.
3. Run the relevant pytest targets and regenerate documentation (`AshPost.run_post()`).
4. Validate the catalog entry payload if the dataset list changes.

## Testing Guidance
- Primary tests live in `wepppy/nodb/mods/ash_transport/tests/`. They expect a fully built working directory with hillslope outputs; prefer integration environments or curated fixtures.
- Recommended commands:
  - `pytest wepppy/nodb/mods/ash_transport/tests --maxfail=1`
  - For exploratory runs, use the scripts under `tests/` (`multi_year_test.py`) with a local working directory.
- When editing calibration logic, manually inspect generated plots (`H*_ash.png` & `_ash_scatter.png`) to confirm transport curves remain physically plausible.

## Debugging & Troubleshooting
- Enable verbose logging by raising Redis DB 15 log level or swapping `MULTIPROCESSING = False` to run serially.
- Verify raster alignment issues by checking cropped files in `ash/`.
- When outputs disappear, check `ashpost_version.json`; a major version bump triggers deletion and regeneration.
- If `AshPost` skips hillslopes, inspect `ash.meta` for missing `ash_type` or `ini_ash_load`. These fields are populated during simulation setup.

## Coding Standards & Housekeeping
- Respect singleton semantics: `Ash.getInstance(wd)` / `AshPost.getInstance(wd)` should be the only entry points. Never instantiate via the class constructor outside initialization logic.
- Always run `diff -u path <(uk2us path)` before committing doc updates to maintain American English.
- Do not manually edit generated parquet or markdown under `ash/post`; rely on the controller pipeline.
- Keep new helpers private unless they are part of the external API. Prefix with `_` and avoid adding to `__all__` unless used elsewhere.
- When touching documentation or configuration handling, update `README.md` in the same change so external teams stay aligned.

## Reference Material
- `docs/ui-docs/ash-control-plan.md` for UI & workflow context.
- `docs/prompt_templates/readme_authoring_template.md` for documentation standards.
- `dev/` notebooks and spreadsheets for calibration provenance.
- `AGENTS.md` (repository root) for global NoDb patterns, locking rules, and authorship policy reminders.
