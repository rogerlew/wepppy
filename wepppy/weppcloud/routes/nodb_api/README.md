# NoDb API Routes

> Flask blueprints providing REST API access to NoDb controller state and operations within WEPPcloud runs.

> **See also:** [AGENTS.md](../../../../AGENTS.md) for NoDb patterns, Flask blueprint structure, and testing conventions.

## Overview

The NoDb API blueprints expose server-side endpoints for interacting with NoDb singleton controllers defined in `wepppy.nodb`. These routes power the dynamic features of the WEPPcloud web interface, enabling users to configure runs, query state, trigger background jobs, and retrieve model outputs.

**Key characteristics:**
- **Run-scoped**: Every endpoint operates within the context of a specific run (`/runs/<runid>/<config>/...`)
- **NoDb-centric**: All persistence flows through NoDb objects cached on disk and mirrored in Redis—no direct SQL/ORM access
- **Consistent helpers**: Shared utilities (`success_factory`, `exception_factory`, `authorize`, `parse_request_payload`) ensure uniform response patterns
- **Frontend integration**: Paired with JavaScript controllers in `wepppy/weppcloud/controllers_js/` (see [controllers_js/README.md](../../controllers_js/README.md))

**Typical request flow:**
1. Client makes request to `/runs/<runid>/<config>/<feature>/<endpoint>`
2. Blueprint handler resolves working directory via `get_wd(request)`
3. NoDb controller retrieved via `Controller.getInstance(wd)`
4. Handler reads/mutates controller state within distributed lock
5. Response returned as JSON or rendered template

5. Response returned as JSON or rendered template

## Route Organization

### URL Patterns

Routes follow consistent naming conventions:

| Pattern | Purpose | Example |
|---------|---------|---------|
| `/tasks/*` | Mutate NoDb state | `/tasks/set_outlet`, `/tasks/modify_landuse` |
| `/query/*` | Read-only state queries | `/query/subcatchments.json`, `/query/delineation_pass` |
| `/report/*` | Rendered HTML reports | `/report/wepp/summary`, `/report/climate` |
| `/view/*` | Template-rendered pages | `/view/closest_stations`, `/view/management/<key>` |
| `/resources/*` | Static file downloads | `/resources/subcatchments.json`, `/resources/baer.png` |
| `/api/*` | Specialized JSON APIs | `/api/omni/get_scenarios`, `/api/path_ce/status` |

### Helper Utilities

Shared helper functions used across blueprints:

| Helper | Purpose |
|--------|---------|
| `get_wd(request)` | Extract working directory from request context |
| `authorize()` | Check user permissions for run access |
| `authorize_and_handle_with_exception_factory()` | Authorization with automatic error handling |
| `load_run_context()` | Load run metadata and user permissions |
| `parse_request_payload()` | Parse and normalize JSON/form payloads with type coercion |
| `success_factory()` | Generate standardized success responses |
| `exception_factory()` | Generate standardized error responses |
| `error_factory()` | Generate error responses without exception objects |
| `save_run_file()` | Persist uploaded files to run directory |
| `upload_success()` / `upload_failure()` | File upload response helpers |

## How to Use This Reference

Each blueprint section below documents:
- **NoDb singletons**: Which controllers the blueprint interacts with (linked to source files)
- **Controller docs**: Links to frontend JavaScript controller documentation
- **Helper stack**: Shared utilities used by routes in this blueprint
- **Testing**: Location of test coverage and stubbing patterns
- **Route table**: Comprehensive endpoint listing with HTTP methods, NoDb interactions, and implementation notes

**Table conventions:**
- Trailing `[/]` means both the literal path and a version with trailing slash are registered
- `NoDb interactions` lists properties/methods accessed on the singleton
- `Notes` column highlights deviations (RQ enqueues, file streaming, special helpers)
- Routine helpers (`get_wd`, `jsonify`, `success_factory`) referenced in bullets, omitted from rows for readability

## Blueprint Catalog

### Climate (`wepppy.weppcloud.routes.nodb_api.climate_bp`)
- **NoDb singletons**: [Climate](../../../nodb/core/climate.py), [Ron](../../../nodb/core/ron.py)
- **Controller docs**: [Climate Controller Reference (2024 helper migration)](../../controllers_js/README.md#climate-controller-reference-2024-helper-migration)
- **Helper stack**: `parse_request_payload`, `get_wd`, `success_factory`, `exception_factory`, `render_template`, `jsonify`, `save_run_file`, `upload_success`, `upload_failure`
- **Testing**: [tests/weppcloud/routes/test_climate_bp.py](../../../../tests/weppcloud/routes/test_climate_bp.py) — monkeypatches dummy Climate/Ron instances; update fixtures when payloads change.

| Route | Methods | NoDb interactions | Notes |
| --- | --- | --- | --- |
| `/runs/<string:runid>/<config>/tasks/set_climatestation_mode[/]` | `POST` | Climate.climatestation_mode (set) | — |
| `/runs/<string:runid>/<config>/tasks/set_climatestation[/]` | `POST` | Climate.climatestation (set) | — |
| `/runs/<string:runid>/<config>/tasks/upload_cli[/]` | `POST` | Climate.cli_dir, Climate.set_user_defined_cli | Uses `save_run_file()` plus `upload_success` / `upload_failure` for feedback |
| `/runs/<string:runid>/<config>/query/climatestation[/]` | `GET` | Climate.climatestation | — |
| `/runs/<string:runid>/<config>/query/climate_has_observed[/]` | `GET` | Climate.has_observed | — |
| `/runs/<string:runid>/<config>/query/climate_catalog[/]` | `GET` | Climate.catalog_datasets_payload | — |
| `/runs/<string:runid>/<config>/report/climate[/]` | `GET` | Climate.climatestation_meta | — |
| `/runs/<string:runid>/<config>/tasks/set_climate_mode[/]` | `POST` | Climate._resolve_catalog_dataset, Climate.catalog_id (set), Climate.climate_mode (set) | — |
| `/runs/<string:runid>/<config>/tasks/set_climate_spatialmode[/]` | `POST` | Climate.climate_spatialmode (set) | — |
| `/runs/<string:runid>/<config>/view/closest_stations[/]` | `GET` | Climate.climatestation, Climate.closest_stations, Climate.find_closest_stations, Climate.readonly | Calls `Climate.getInstance(..., ignore_lock=True)` so read-only runs can preview options |
| `/runs/<string:runid>/<config>/view/heuristic_stations[/]` | `GET` | Climate.climatestation, Climate.find_heuristic_stations, Climate.heuristic_stations, Climate.readonly | Uses `ignore_lock=True` and falls back to cached heuristics when readonly |
| `/runs/<string:runid>/<config>/view/par[/]` | `GET` | Climate.climatestation_par_contents | — |
| `/runs/<string:runid>/<config>/view/eu_heuristic_stations[/]` | `GET` | Climate.climatestation, Climate.find_eu_heuristic_stations | `ignore_lock=True` EU heuristic lookup |
| `/runs/<string:runid>/<config>/view/au_heuristic_stations[/]` | `GET` | Climate.climatestation, Climate.find_au_heuristic_stations | `ignore_lock=True` AU heuristic lookup |
| `/runs/<string:runid>/<config>/view/climate_monthlies[/]` | `GET` | Climate.climatestation_meta | — |
| `/runs/<string:runid>/<config>/tasks/set_use_gridmet_wind_when_applicable[/]` | `POST` | Climate.use_gridmet_wind_when_applicable (set) | Boolean payload normalized via `parse_request_payload` |

### Debris Flow (`wepppy.weppcloud.routes.nodb_api.debris_flow_bp`)
- **NoDb singletons**: [Ron](../../../nodb/core/ron.py), [DebrisFlow](../../../nodb/mods/debris_flow.py), [Unitizer](../../../nodb/unitizer.py)
- **Controller docs**: [Debris Flow Controller Reference (2025 helper migration)](../../controllers_js/README.md#debris-flow-controller-reference-2025-helper-migration)
- **Helper stack**: `get_wd`, `render_template`, `success_factory`, `exception_factory`
- **Testing**: [tests/weppcloud/routes/test_debris_flow_bp.py](../../../../tests/weppcloud/routes/test_debris_flow_bp.py) — validates rendered context with stubbed precision tables.

| Route | Methods | NoDb interactions | Notes |
| --- | --- | --- | --- |
| `/runs/<string:runid>/<config>/report/debris_flow[/]` | `GET` | DebrisFlow (template context), Ron (template context), Unitizer (template context) | Renders `reports/debris_flow.htm` with singleton instances in context |

### Disturbed / BAER (`wepppy.weppcloud.routes.nodb_api.disturbed_bp`)
- **NoDb singletons**: [Disturbed](../../../nodb/mods/disturbed.py), [Baer](../../../nodb/mods/baer/__init__.py), [Revegetation](../../../nodb/mods/revegetation.py), [Ron](../../../nodb/core/ron.py)
- **Controller docs**: [Disturbed Controller Reference (2025 helper migration)](../../controllers_js/README.md#disturbed-controller-reference-2025-helper-migration), [BAER Controller Reference (2025 helper migration)](../../controllers_js/README.md#baer-controller-reference-2025-helper-migration)
- **Helper stack**: `authorize`, `authorize_and_handle_with_exception_factory`, `load_run_context`, `parse_request_payload`, `secure_filename`, `send_file`, `save_run_file`, `upload_success`, `upload_failure`, `success_factory`, `exception_factory`, `error_factory`
- **Testing**: [tests/weppcloud/routes/test_disturbed_bp.py](../../../../tests/weppcloud/routes/test_disturbed_bp.py) — uses `tests.factories.singleton_factory` to stub Disturbed/Baer/Revegetation; keep stub signatures aligned.

| Route | Methods | NoDb interactions | Notes |
| --- | --- | --- | --- |
| `/runs/<string:runid>/<config>/modify_disturbed` | `GET` | Disturbed (template context) | Serves legacy CSV editor; no NoDb mutation until save. |
| `/runs/<string:runid>/<config>/tasks/reset_disturbed` | `GET, POST` | Disturbed.reset_land_soil_lookup | — |
| `/runs/<string:runid>/<config>/tasks/load_extended_land_soil_lookup` | `GET, POST` | Disturbed.build_extended_land_soil_lookup | — |
| `/runs/<string:runid>/<config>/api/disturbed/has_sbs[/]` | `GET` | Disturbed.has_sbs | — |
| `/runs/<string:runid>/<config>/tasks/modify_disturbed` | `POST` | Disturbed.lookup_fn | — |
| `/runs/<string:runid>/<config>/query/baer_wgs_map[/]` | `GET` | Disturbed.bounds, Disturbed.classes, Disturbed.has_map, Ron.mods | — |
| `/runs/<string:runid>/<config>/view/modify_burn_class` | `GET` | Disturbed.has_map, Ron.mods | — |
| `/runs/<string:runid>/<config>/tasks/modify_burn_class` | `POST` | Disturbed.has_map, Disturbed.modify_burn_class, Ron.mods | — |
| `/runs/<string:runid>/<config>/tasks/modify_color_map` | `POST` | Disturbed.has_map, Disturbed.modify_color_map, Ron.mods | — |
| `/runs/<string:runid>/<config>/resources/baer.png` | `GET` | Disturbed.baer_rgb_png, Disturbed.has_map, Ron.mods | Streams RGB overlay from either BAER or Disturbed controller |
| `/runs/<string:runid>/<config>/tasks/set_firedate[/]` | `POST` | Disturbed.fire_date (set) | — |
| `/runs/<string:runid>/<config>/tasks/upload_sbs[/]` | `POST` | Disturbed.baer_dir, Disturbed.validate, Ron.mods | Persists SBS raster, runs `sbs_map_sanity_check`, then validates via controller |
| `/runs/<string:runid>/<config>/tasks/upload_cover_transform` | `POST` | Revegetation.validate_user_defined_cover_transform | Delegates to `Revegetation.validate_user_defined_cover_transform()` |
| `/runs/<string:runid>/<config>/tasks/remove_sbs` | `POST` | Baer.remove_sbs, Disturbed.remove_sbs, Ron.mods | Removes SBS raster from whichever controller owns it |
| `/runs/<string:runid>/<config>/tasks/build_uniform_sbs<br>/runs/<string:runid>/<config>/tasks/build_uniform_sbs/<value>` | `POST` | Disturbed.build_uniform_sbs, Disturbed.validate | Builds uniform raster then validates; accepts optional severity parameter |

### Interchange Migration (`wepppy.weppcloud.routes.nodb_api.interchange_bp`)
- **NoDb singletons**: _None_
- **Controller docs**: [Batch Runner Controller Reference (2025 helper migration)](../../controllers_js/README.md#batch-runner-controller-reference-2025-helper-migration)
- **Helper stack**: `authorize_and_handle_with_exception_factory`, `load_run_context`, `jsonify`, `error_factory`
- **Testing**: [tests/weppcloud/routes/test_interchange_bp.py](../../../../tests/weppcloud/routes/test_interchange_bp.py) — asserts payload validation and RQ enqueue wiring.

| Route | Methods | NoDb interactions | Notes |
| --- | --- | --- | --- |
| `/runs/<string:runid>/<config>/tasks/interchange/migrate` | `POST` | — | Validates optional subpath then enqueues `run_interchange_migration` on Redis Queue |

### Landuse (`wepppy.weppcloud.routes.nodb_api.landuse_bp`)
- **NoDb singletons**: [Landuse](../../../nodb/core/landuse.py), [Ron](../../../nodb/core/ron.py)
- **Controller docs**: [Landuse Modify Controller Reference (2025 helper migration)](../../controllers_js/README.md#landuse-modify-controller-reference-2025-helper-migration)
- **Helper stack**: `parse_request_payload`, `get_wd`, `jsonify`, `render_template`, `success_factory`, `exception_factory`
- **Testing**: [tests/weppcloud/routes/test_landuse_bp.py](../../../../tests/weppcloud/routes/test_landuse_bp.py) — covers coercion helpers and JSON payload handling.

| Route | Methods | NoDb interactions | Notes |
| --- | --- | --- | --- |
| `/runs/<string:runid>/<config>/tasks/set_landuse_mode[/]` | `POST` | Landuse.mode (set), Landuse.single_selection (set) | — |
| `/runs/<string:runid>/<config>/tasks/set_landuse_db[/]` | `POST` | Landuse.nlcd_db (set) | — |
| `/runs/<string:runid>/<config>/tasks/modify_landuse_coverage[/]` | `POST` | Landuse.modify_coverage, Landuse.modify_coverage() | Normalizes domain/cover IDs then writes via `Landuse.modify_coverage()` |
| `/runs/<string:runid>/<config>/tasks/modify_landuse_mapping[/]` | `POST` | Landuse.modify_mapping | Uses `_coerce_topaz_ids` to keep legacy form inputs compatible |
| `/runs/<string:runid>/<config>/query/landuse[/]` | `GET` | Landuse.domlc_d | — |
| `/runs/<string:runid>/<config>/query/landuse/subcatchments[/]` | `GET` | Landuse.subs_summary | — |
| `/runs/<string:runid>/<config>/query/landuse/channels[/]` | `GET` | Landuse.chns_summary | — |
| `/runs/<string:runid>/<config>/report/landuse[/]` | `GET` | Landuse.landuseoptions | Builds template context via `build_landuse_report_context()` |
| `/runs/<string:runid>/<config>/tasks/modify_landuse[/]` | `POST` | Landuse.modify | Accepts comma-separated Topaz IDs, coerces landuse code, then calls `Landuse.modify()` |
| `/runs/<string:runid>/<config>/query/landuse/cover/subcatchments[/]` | `GET` | Landuse.hillslope_cancovs | — |

### Observed (`wepppy.weppcloud.routes.nodb_api.observed_bp`)
- **NoDb singletons**: [Observed](../../../nodb/mods/observed.py), [Wepp](../../../nodb/core/wepp.py), [Ron](../../../nodb/core/ron.py), [Unitizer](../../../nodb/unitizer.py)
- **Controller docs**: [Observed Controller Reference (2025 helper migration)](../../controllers_js/README.md#observed-controller-reference-2025-helper-migration)
- **Helper stack**: `parse_request_payload`, `success_factory`, `exception_factory`, `error_factory`, `render_template`, `send_file`
- **Testing**: [tests/weppcloud/routes/test_observed_bp.py](../../../../tests/weppcloud/routes/test_observed_bp.py) — stubs Observed singleton to exercise parsing and plotting routes.

| Route | Methods | NoDb interactions | Notes |
| --- | --- | --- | --- |
| `/runs/<string:runid>/<config>/tasks/run_model_fit[/]` | `POST` | Observed.calc_model_fit, Observed.parse_textdata | Parses inline CSV, runs `Observed.calc_model_fit()` synchronously (TODO RQ) |
| `/runs/<string:runid>/<config>/report/observed[/]` | `GET` | Observed.results, Observed.stat_names | — |
| `/runs/<string:runid>/<config>/plot/observed/<selected>[/]` | `GET` | Wepp.observed_dir | — |
| `/runs/<string:runid>/<config>/resources/observed/<file>` | `GET` | Ron.observed_dir | Streams CSV artifacts from `Ron.observed_dir` |

### Omni Scenarios (`wepppy.weppcloud.routes.nodb_api.omni_bp`)
- **NoDb singletons**: [Omni](../../../nodb/mods/omni.py), [Treatments](../../../nodb/mods/treatments.py), [Ron](../../../nodb/core/ron.py), [Watershed](../../../nodb/core/watershed.py)
- **Controller docs**: [Omni Controller Reference (2024 helper migration)](../../controllers_js/README.md#omni-controller-reference-2024-helper-migration)
- **Helper stack**: `authorize`, `parse_request_payload`, `success_factory`, `exception_factory`, `error_factory`, `jsonify`, `render_template`
- **Testing**: [tests/weppcloud/routes/test_rq_api_omni.py](../../../../tests/weppcloud/routes/test_rq_api_omni.py) — covers downstream job orchestration; add blueprint-specific tests when behavior expands.

| Route | Methods | NoDb interactions | Notes |
| --- | --- | --- | --- |
| `/runs/<string:runid>/<config>/api/omni/get_scenarios` | `GET` | Omni.scenarios | — |
| `/runs/<string:runid>/<config>/api/omni/get_scenario_run_state` | `GET` | Omni.scenario_dependency_tree, Omni.scenario_run_state | — |
| `/runs/<string:runid>/<config>/tasks/omni_migration` | `GET` | Ron._mods, Ron.locked | Adds `omni`/`treatments` mods inside `Ron.locked()` then instantiates controllers |
| `/runs/<string:runid>/<config>/report/omni_scenarios[/]` | `GET` | Omni.scenarios_report | Builds scenario summary table using `Omni.scenarios_report()` and `Watershed.getInstance` |

### Path Cost-Effective (`wepppy.weppcloud.routes.nodb_api.path_ce_bp`)
- **NoDb singletons**: [PathCostEffective](../../../nodb/mods/path_ce.py), [Ron](../../../nodb/core/ron.py)
- **Controller docs**: [Path CE Controller Reference (2025 helper migration)](../../controllers_js/README.md#path-ce-controller-reference-2025-helper-migration)
- **Helper stack**: `authorize`, `authorize_and_handle_with_exception_factory`, `load_run_context`, `parse_request_payload`, `jsonify`, `success_factory`
- **Testing**: [tests/weppcloud/routes/test_path_ce_bp.py](../../../../tests/weppcloud/routes/test_path_ce_bp.py) — exercises payload normalization and status/result endpoints.

| Route | Methods | NoDb interactions | Notes |
| --- | --- | --- | --- |
| `/runs/<string:runid>/<config>/tasks/path_cost_effective_enable` | `GET` | Ron._mods, Ron._mods (set), Ron.locked, Ron.mods | Appends `path_ce` mod inside `Ron.locked()` and bootstraps controller |
| `/runs/<string:runid>/<config>/api/path_ce/config` | `GET` | PathCostEffective.config | `GET` lazily instantiates controller if missing; `POST` normalizes numeric ranges before persisting |
| `/runs/<string:runid>/<config>/api/path_ce/config` | `POST` | PathCostEffective.config | `GET` lazily instantiates controller if missing; `POST` normalizes numeric ranges before persisting |
| `/runs/<string:runid>/<config>/api/path_ce/status` | `GET` | PathCostEffective.progress, PathCostEffective.status, PathCostEffective.status_message | — |
| `/runs/<string:runid>/<config>/api/path_ce/results` | `GET` | PathCostEffective.results | — |
| `/runs/<string:runid>/<config>/tasks/path_cost_effective_run` | `POST` | Ron.mods | Enqueues `run_path_cost_effective_rq` on Redis Queue |

### Project (`wepppy.weppcloud.routes.nodb_api.project_bp`)
- **NoDb singletons**: [Ron](../../../nodb/core/ron.py), [Watershed](../../../nodb/core/watershed.py)
- **Controller docs**: [Project Controller Contract (2024 refresh)](../../controllers_js/README.md#project-controller-contract-2024-refresh), [Map Controller Reference (2025 helper migration)](../../controllers_js/README.md#map-controller-reference-2025-helper-migration)
- **Helper stack**: `authorize`, `authorize_and_handle_with_exception_factory`, `login_required`, `load_run_context`, `parse_request_payload`, `jsonify`, `render_template`, `send_file`, `success_factory`, `exception_factory`, `error_factory`
- **Testing**: [tests/weppcloud/routes/test_project_bp.py](../../../../tests/weppcloud/routes/test_project_bp.py) — covers lock clearing, collaborator management, and GeoJSON streaming.

| Route | Methods | NoDb interactions | Notes |
| --- | --- | --- | --- |
| `/runs/<string:runid>/<config>/tasks/clear_locks` | `GET` | NoDbBase.clear_locks | Calls `wepppy.nodb.base.clear_locks()` after loading run context |
| `/runs/<string:runid>/<config>/tasks/clear_nodb_cache` | `GET` | NoDbBase.clear_nodb_file_cache | Clears cached `.nodb` payloads via `clear_nodb_file_cache()` |
| `/runs/<string:runid>/<config>/tasks/delete[/]` | `POST` | Ron.readonly | Deletes working directory then removes run from user datastore |
| `/runs/<string:runid>/<config>/meta/subcatchments.WGS.json[/]` | `GET` | Ron.export_dir | Runs `wepppy.export.arc_export` before streaming GeoJSON |
| `/runs/<string:runid>/<config>/tasks/adduser[/]` | `POST` | — | — |
| `/runs/<string:runid>/<config>/tasks/removeuser[/]` | `POST` | — | — |
| `/runs/<string:runid>/<config>/report/users[/]` | `GET` | Ron (ownership lookup) | — |
| `/runs/<string:runid>/<config>/resources/netful.json` | `GET` | Watershed.netful_shp | Streams GeoJSON from `Watershed.channels_shp` |
| `/runs/<string:runid>/<config>/resources/subcatchments.json` | `GET` | Ron.name, Watershed.subwta_shp | Injects run name into subcatchment GeoJSON before return |
| `/runs/<string:runid>/<config>/resources/bound.json` | `GET` | Ron.name, Watershed.bound_shp | Optional ogr2ogr simplify branch retained but disabled |
| `/runs/<string:runid>/<config>/tasks/setname[/]` | `POST` | Ron.name (set) | — |
| `/runs/<string:runid>/<config>/tasks/setscenario[/]` | `POST` | Ron.scenario (set) | — |
| `/runs/<string:runid>/<config>/tasks/set_public` | `POST` | Ron.public (set) | — |
| `/runs/<string:runid>/<config>/tasks/set_readonly` | `POST` | — | Enqueues `set_run_readonly_rq`; payload coerced via `parse_request_payload(boolean_fields={...})` |
| `/runs/<string:runid>/<config>/tasks/set_mod[/]` | `POST` | Ron.mods (set/remove), Ron.remove_mod | Toggles optional modules, enforces dependencies, and instantiates controllers when available |

### Rangeland Cover (`wepppy.weppcloud.routes.nodb_api.rangeland_bp`)
- **NoDb singletons**: [RangelandCover](../../../nodb/mods/rangeland_cover.py), [Ron](../../../nodb/core/ron.py)
- **Controller docs**: [Rangeland Cover Controller Reference (2025 helper migration)](../../controllers_js/README.md#rangeland-cover-controller-reference-2025-helper-migration)
- **Helper stack**: `load_run_context`, `parse_request_payload`, `success_factory`, `exception_factory`, `jsonify`
- **Testing**: [tests/weppcloud/routes/test_rangeland_cover_bp.py](../../../../tests/weppcloud/routes/test_rangeland_cover_bp.py) — verifies cover normalization and job payload construction.

| Route | Methods | NoDb interactions | Notes |
| --- | --- | --- | --- |
| `/runs/<string:runid>/<config>/tasks/modify_rangeland_cover[/]` | `POST` | RangelandCover.modify_covers | Normalizes Topaz IDs and cover percentages before calling `modify_covers()` |
| `/runs/<string:runid>/<config>/query/rangeland_cover/subcatchments[/]` | `GET` | RangelandCover.subs_summary | — |
| `/runs/<string:runid>/<config>/report/rangeland_cover[/]` | `GET` | RangelandCover (template context) | — |
| `/runs/<string:runid>/<config>/tasks/build_rangeland_cover[/]` | `POST` | RangelandCover.build | Accepts RAP year + defaults payload; values cast to float before `build()` |

### Rangeland Cover Modify (`wepppy.weppcloud.routes.nodb_api.rangeland_cover_bp`)
- **NoDb singletons**: [RangelandCover](../../../nodb/mods/rangeland_cover.py)
- **Controller docs**: [Rangeland Cover Modify Controller Reference (2025 helper migration)](../../controllers_js/README.md#rangeland-cover-modify-controller-reference-2025-helper-migration)
- **Helper stack**: `load_run_context`, `parse_request_payload`, `jsonify`, `success_factory`, `exception_factory`
- **Testing**: [tests/weppcloud/routes/test_rangeland_cover_bp.py](../../../../tests/weppcloud/routes/test_rangeland_cover_bp.py) — covers current-cover summaries and mode toggles alongside the main blueprint.

| Route | Methods | NoDb interactions | Notes |
| --- | --- | --- | --- |
| `/runs/<string:runid>/<config>/query/rangeland_cover/current_cover_summary[/]` | `POST` | RangelandCover.current_cover_summary | — |
| `/runs/<string:runid>/<config>/tasks/set_rangeland_cover_mode[/]` | `POST` | RangelandCover.mode (set), RangelandCover.rap_year (set) | Requires both mode and RAP year; coerces to ints before persisting |

### RHEM (`wepppy.weppcloud.routes.nodb_api.rhem_bp`)
- **NoDb singletons**: [RhemPost](../../../nodb/mods/rhem.py), [Ron](../../../nodb/core/ron.py), [Unitizer](../../../nodb/unitizer.py)
- **Controller docs**: [RHEM Controller Reference (2025 helper migration)](../../controllers_js/README.md#rhem-controller-reference-2025-helper-migration)
- **Helper stack**: `authorize`, `get_wd`, `render_template`, `jsonify`, `exception_factory`
- **Testing**: [tests/weppcloud/routes/test_rhem_bp.py](../../../../tests/weppcloud/routes/test_rhem_bp.py) — covers report rendering and JSON query helpers with stubbed output files.

| Route | Methods | NoDb interactions | Notes |
| --- | --- | --- | --- |
| `/runs/<string:runid>/<config>/report/rhem/results[/]` | `GET` | RhemPost (template context) | Serves template shell; individual reports fetched via AJAX |
| `/runs/<string:runid>/<config>/report/rhem/run_summary[/]` | `GET` | RhemPost (template context), Ron (template context) | Counts `.sum` files under `rhem/output` to populate summary |
| `/runs/<string:runid>/<config>/report/rhem/summary[/]` | `GET` | RhemPost (template context), Ron (template context), Unitizer (template context) | Injects `Unitizer` precisions for display |
| `/runs/<string:runid>/<config>/report/rhem/return_periods[/]` | `GET` | RhemPost (template context), Ron (template context), Unitizer (template context) | Supports `extraneous=true` query flag for additional rows |
| `/runs/<string:runid>/<config>/query/rhem/runoff/subcatchments[/]` | `GET` | RhemPost.query_sub_val | — |
| `/runs/<string:runid>/<config>/query/rhem/sed_yield/subcatchments[/]` | `GET` | RhemPost.query_sub_val | — |
| `/runs/<string:runid>/<config>/query/rhem/soil_loss/subcatchments[/]` | `GET` | RhemPost.query_sub_val | — |

### Soils (`wepppy.weppcloud.routes.nodb_api.soils_bp`)
- **NoDb singletons**: [Soils](../../../nodb/core/soils.py), [Disturbed](../../../nodb/mods/disturbed.py)
- **Controller docs**: No dedicated controllers_js entry yet; UI reuses project + map helpers.
- **Helper stack**: `load_run_context`, `parse_request_payload`, `jsonify`, `render_template`, `success_factory`, `exception_factory`, `error_factory`
- **Testing**: [tests/weppcloud/routes/test_soils_bp.py](../../../../tests/weppcloud/routes/test_soils_bp.py) — covers mode toggles, ksflag boolean coercion, and disturbed sol_ver passthrough.

| Route | Methods | NoDb interactions | Notes |
| --- | --- | --- | --- |
| `/runs/<string:runid>/<config>/tasks/set_soil_mode[/]` | `POST` | Soils.mode (set), Soils.single_dbselection (set), Soils.single_selection (set) | Normalizes optional single-selection/dbselection values before applying |
| `/runs/<string:runid>/<config>/query/soils[/]` | `GET` | Soils.domsoil_d | — |
| `/runs/<string:runid>/<config>/query/soils/subcatchments[/]` | `GET` | Soils.subs_summary | — |
| `/runs/<string:runid>/<config>/query/soils/channels[/]` | `GET` | Soils.chns_summary | — |
| `/runs/<string:runid>/<config>/report/soils[/]` | `GET` | Soils.report | — |
| `/runs/<string:runid>/<config>/tasks/set_soils_ksflag[/]` | `POST` | Soils.ksflag (set) | Boolean payload handled via `parse_request_payload(boolean_fields={...})` |
| `/runs/<string:runid>/<config>/tasks/set_disturbed_sol_ver[/]` | `POST` | Disturbed.sol_ver (set) | Updates `Disturbed.sol_ver` for compatibility with BAER workflows |

### Treatments (`wepppy.weppcloud.routes.nodb_api.treatments_bp`)
- **NoDb singletons**: [Treatments](../../../nodb/mods/treatments.py)
- **Controller docs**: [Treatments Controller Reference (2025 helper migration)](../../controllers_js/README.md#treatments-controller-reference-2025-helper-migration)
- **Helper stack**: `parse_request_payload`, `success_factory`, `error_factory`, `exception_factory`
- **Testing**: [tests/weppcloud/routes/test_treatments_bp.py](../../../../tests/weppcloud/routes/test_treatments_bp.py) — covers mode coercion and error handling.

| Route | Methods | NoDb interactions | Notes |
| --- | --- | --- | --- |
| `/runs/<string:runid>/<config>/tasks/set_treatments_mode[/]` | `POST` | Treatments.mode (set) | Supports legacy `treatments_mode` field before coercing to enum |

### Unitizer (`wepppy.weppcloud.routes.nodb_api.unitizer_bp`)
- **NoDb singletons**: [Unitizer](../../../nodb/unitizer.py)
- **Controller docs**: [Project Controller Contract (2024 refresh)](../../controllers_js/README.md#project-controller-contract-2024-refresh)
- **Helper stack**: `load_run_context`, `parse_request_payload`, `success_factory`, `exception_factory`
- **Testing**: [tests/weppcloud/routes/test_unitizer_bp.py](../../../../tests/weppcloud/routes/test_unitizer_bp.py) — covers preference persistence and context-processor wrappers.

| Route | Methods | NoDb interactions | Notes |
| --- | --- | --- | --- |
| `/runs/<string:runid>/<config>/report/tasks/set_unit_preferences[/]<br>/runs/<string:runid>/<config>/tasks/set_unit_preferences[/]` | `POST` | Unitizer.set_preferences | Report variant proxies to the main task for legacy templates |
| `/runs/<string:runid>/<config>/unitizer[/]` | `GET` | Unitizer.context_processor_package | Invokes context processor to convert supplied value |
| `/runs/<string:runid>/<config>/unitizer_units[/]` | `GET` | Unitizer.context_processor_package | Returns preferred units metadata via context processor |

### WATAR (`wepppy.weppcloud.routes.nodb_api.watar_bp`)
- **NoDb singletons**: [Ash](../../../nodb/mods/ash_transport/__init__.py), [AshPost](../../../nodb/mods/ash_transport/__init__.py), [Disturbed](../../../nodb/mods/disturbed.py), [Climate](../../../nodb/core/climate.py), [Wepp](../../../nodb/core/wepp.py), [Watershed](../../../nodb/core/watershed.py), [Unitizer](../../../nodb/unitizer.py), [Ron](../../../nodb/core/ron.py)
- **Controller docs**: No dedicated controllers_js entry; ash panels reuse disturbed + project helpers.
- **Helper stack**: `get_wd`, `authorize`, `parse_rec_intervals`, `render_template`, `jsonify`, `success_factory`, `exception_factory`
- **Testing**: [tests/weppcloud/routes/test_rq_api_ash.py](../../../../tests/weppcloud/routes/test_rq_api_ash.py) — covers RQ interfaces; add blueprint tests when hillslope/run dashboards evolve.

| Route | Methods | NoDb interactions | Notes |
| --- | --- | --- | --- |
| `/runs/<string:runid>/<config>/hillslope/<topaz_id>/ash[/]` | `GET` | Climate.cli_path, Ron.public, Watershed.sub_summary, Watershed.translator_factory, Wepp.output_dir | Runs multi-year ash model (Black/White) and writes hill summaries under `_ash/` |
| `/runs/<string:runid>/<config>/tasks/set_ash_wind_transport[/]` | `POST` | Ash.run_wind_transport (set) | Accepts JSON body, toggles `Ash.run_wind_transport` |
| `/runs/<string:runid>/<config>/report/run_ash[/]` | `GET` | Ash (template context) | — |
| `/runs/<string:runid>/<config>/report/ash[/]` | `GET` | Ash.burn_class_summary, Ash.fire_date, Ash.ini_black_ash_depth_mm, Ash.ini_white_ash_depth_mm, AshPost.cum_return_periods, AshPost.recurrence_intervals, AshPost.return_periods, Climate.years | Builds watershed summary with burn class + recurrence tables |
| `/runs/<string:runid>/<config>/query/ash_out[/]` | `GET` | AshPost.ash_out | — |
| `/runs/<string:runid>/<config>/report/ash_contaminant[/]` | `GET, POST` | Ash.high_contaminant_concentrations, Ash.parse_cc_inputs, AshPost.burn_class_return_periods, AshPost.pw0_stats, AshPost.recurrence_intervals, AshPost.return_periods, Climate.years | Supports POST form updates via `Ash.parse_cc_inputs` before rendering |

### Watershed (`wepppy.weppcloud.routes.nodb_api.watershed_bp`)
- **NoDb singletons**: [Watershed](../../../nodb/core/watershed.py), [Ron](../../../nodb/core/ron.py)
- **Controller docs**: [Map Controller Reference (2025 helper migration)](../../controllers_js/README.md#map-controller-reference-2025-helper-migration), [Subcatchment Delineation Controller (2025 helper migration)](../../controllers_js/README.md#subcatchment-delineation-controller-2025-helper-migration)
- **Helper stack**: `authorize_and_handle_with_exception_factory`, `load_run_context`, `jsonify`, `render_template`, `success_factory`, `request`
- **Testing**: [tests/weppcloud/routes/test_rq_api_subcatchments.py](../../../../tests/weppcloud/routes/test_rq_api_subcatchments.py) — covers related subcatchment jobs; add direct blueprint coverage when endpoints expand.

| Route | Methods | NoDb interactions | Notes |
| --- | --- | --- | --- |
| `/runs/<string:runid>/<config>/query/delineation_pass[/]` | `GET` | Watershed.has_channels, Watershed.has_subcatchments | — |
| `/runs/<string:runid>/<config>/resources/channels.json` | `GET` | Ron.name, Watershed.channels_shp | Loads shapefile, injects project name before returning JSON |
| `/runs/<string:runid>/<config>/query/extent[/]` | `GET` | Ron.extent | — |
| `/runs/<string:runid>/<config>/report/channel` | `GET` | Ron.map | Renders `reports/channel.htm` with `Ron.map` |
| `/runs/<string:runid>/<config>/query/outlet[/]` | `GET` | Watershed.outlet | — |
| `/runs/<string:runid>/<config>/report/outlet[/]` | `GET` | Watershed.outlet | — |
| `/runs/<string:runid>/<config>/query/has_dem[/]` | `GET` | Ron.has_dem | — |
| `/runs/<string:runid>/<config>/query/watershed/subcatchments[/]` | `GET` | Watershed.subs_summary | — |
| `/runs/<string:runid>/<config>/query/watershed/channels[/]` | `GET` | Watershed.chns_summary | — |
| `/runs/<string:runid>/<config>/report/watershed[/]` | `GET` | Watershed (template context) | — |
| `/runs/<string:runid>/<config>/tasks/abstract_watershed[/]` | `GET, POST` | Watershed.abstract_watershed | — |
| `/runs/<string:runid>/<config>/tasks/sub_intersection[/]` | `POST` | Ron.map, Watershed.subwta | Uses `Ron.map.raster_intersection` to find Topaz IDs within extent |

### WEPP (`wepppy.weppcloud.routes.nodb_api.wepp_bp`)
- **NoDb singletons**: [Wepp](../../../nodb/core/wepp.py), [Ron](../../../nodb/core/ron.py), [Climate](../../../nodb/core/climate.py), [Landuse](../../../nodb/core/landuse.py), [Watershed](../../../nodb/core/watershed.py), [Unitizer](../../../nodb/unitizer.py), [RedisPrep](../../../nodb/redis_prep.py)
- **Controller docs**: [Outlet Controller Reference (2025 helper migration)](../../controllers_js/README.md#outlet-controller-reference-2025-helper-migration), [Map Controller Reference (2025 helper migration)](../../controllers_js/README.md#map-controller-reference-2025-helper-migration), [Landuse Modify Controller Reference (2025 helper migration)](../../controllers_js/README.md#landuse-modify-controller-reference-2025-helper-migration)
- **Helper stack**: `authorize_and_handle_with_exception_factory`, `get_wd`, `parse_request_payload`, `jsonify`, `render_template`, `send_file`, `success_factory`, `exception_factory`, `activate_query_engine`, `run_query`
- **Testing**: [tests/weppcloud/routes/test_wepp_bp.py](../../../../tests/weppcloud/routes/test_wepp_bp.py) — covers query engine activation, report CSV rendering, and resource streaming.

| Route | Methods | NoDb interactions | Notes |
| --- | --- | --- | --- |
| `/runs/<string:runid>/<config>/view/channel_def/<chn_key>[/]` | `GET` | — | Uses `wepppy.wepp.management` helpers (no NoDb singleton) |
| `/runs/<string:runid>/<config>/view/management/<key>[/]` | `GET` | Landuse.managements | — |
| `/runs/<string:runid>/<config>/tasks/set_run_wepp_routine[/]` | `POST` | Wepp.set_run_flowpaths, Wepp.set_run_frost, Wepp.set_run_pmet, Wepp.set_run_snow, Wepp.set_run_tcr, Wepp.set_run_wepp_ui | Toggles multiple execution flags via setter helpers |
| `/runs/<string:runid>/<config>/report/wepp/results[/]` | `GET` | Climate (template context), RedisPrep (template context), Watershed (template context), Wepp (template context) | Loads `RedisPrep` cache plus `Wepp` summaries before rendering |
| `/runs/<string:runid>/<config>/query/subcatchments_summary[/]` | `GET` | Ron.subs_summary | — |
| `/runs/<string:runid>/<config>/query/channels_summary[/]` | `GET` | Ron.chns_summary | — |
| `/runs/<string:runid>/<config>/report/wepp/prep_details[/]` | `GET` | Ron.chns_summary, Ron.subs_summary | — |
| `/runs/<string:runid>/<config>/query/wepp/phosphorus_opts[/]` | `GET` | Wepp.phosphorus_opts | — |
| `/runs/<string:runid>/<config>/report/wepp/run_summary[/]` | `GET` | Ron (template context), Unitizer (template context), Wepp (template context) | Renders aggregated run summaries with Unitizer preferences |
| `/runs/<string:runid>/<config>/report/wepp/summary[/]` | `GET` | Climate.is_single_storm | — |
| `/runs/<string:runid>/<config>/report/wepp/yearly_watbal[/]` | `GET` | — | Streams `TotalWatbalReport` data via `_render_report_csv` helper |
| `/runs/<string:runid>/<config>/report/wepp/avg_annual_by_landuse[/]` | `GET` | — | Aggregates by landuse before rendering |
| `/runs/<string:runid>/<config>/report/wepp/avg_annual_watbal[/]` | `GET` | Wepp.report_chn_watbal, Wepp.report_hill_watbal | — |
| `/runs/<string:runid>/<config>/plot/wepp/streamflow[/]` | `GET` | — | Streams PNG from cached plot directory |
| `/runs/<string:runid>/<config>/report/wepp/return_periods[/]` | `GET` | Climate.years, Watershed.translator_factory, Watershed.translator_factory(), Wepp.chn_topaz_ids_of_interest, Wepp.report_return_periods | Requires translator + recur intervals; optional extraneous flag |
| `/runs/<string:runid>/<config>/report/wepp/frq_flood[/]` | `GET` | Watershed.translator_factory, Watershed.translator_factory(), Wepp.report_frq_flood, Wepp.report_frq_flood() | Delegates to `Wepp.report_frq_flood()` and translator |
| `/runs/<string:runid>/<config>/report/wepp/sediment_characteristics[/]` | `GET` | Watershed.translator_factory, Watershed.translator_factory(), Wepp.report_sediment_delivery, Wepp.report_sediment_delivery() | Delegates to `Wepp.report_sediment_delivery()` with translator |
| `/runs/<string:runid>/<config>/query/wepp/phosphorus/subcatchments[/]` | `GET` | Wepp.query_sub_val | — |
| `/runs/<string:runid>/<config>/query/chn_summary/<topaz_id>[/]` | `GET` | Ron.chn_summary | — |
| `/runs/<string:runid>/<config>/query/sub_summary/<topaz_id>[/]` | `GET` | Ron.sub_summary | — |
| `/runs/<string:runid>/<config>/report/chn_summary/<topaz_id>[/]` | `GET` | Ron.chn_summary | — |
| `/runs/<string:runid>/<config>/query/topaz_wepp_map[/]` | `GET` | Watershed.translator_factory, Watershed.translator_factory() | — |
| `/runs/<string:runid>/<config>/report/sub_summary/<topaz_id>[/]` | `GET` | Ron.sub_summary | — |
| `/runs/<string:runid>/<config>/resources/wepp_loss.tif` | `GET` | Ron.plot_dir | Streams raster from `Ron.plot_dir` |
| `/runs/<string:runid>/<config>/resources/flowpaths_loss.tif` | `GET` | Ron.plot_dir | Streams raster from `Ron.plot_dir` |
| `/runs/<string:runid>/<config>/query/bound_coords[/]` | `GET` | Ron.topaz_wd | — |

## Developer Notes

### Adding New Endpoints

When creating new NoDb API routes:

1. **Choose the appropriate blueprint** - Group related functionality (climate, soils, watershed, etc.)

2. **Follow URL patterns** - Use consistent prefixes:
   ```python
   @blueprint.route('/tasks/my_action', methods=['POST'])  # Mutations
   @blueprint.route('/query/my_data', methods=['GET'])     # Read-only
   @blueprint.route('/report/my_report', methods=['GET'])  # HTML reports
   ```

3. **Use run-scoped prefixes** - Blueprint URL prefix should include run context:
   ```python
   blueprint = Blueprint('feature', __name__, 
                        url_prefix='/runs/<string:runid>/<string:config>/feature')
   ```

4. **Access NoDb controllers** - Always use `getInstance()` pattern:
   ```python
   from wepppy.weppcloud.utils.helpers import get_wd
   from wepppy.nodb.core import MyController
   
   @blueprint.route('/tasks/my_action', methods=['POST'])
   def my_action():
       wd = get_wd(request)
       controller = MyController.getInstance(wd)
       
       with controller.locked():
           controller.property = new_value
           controller.dump_and_unlock()
       
       return success_factory()
   ```

5. **Use helper utilities** - Leverage shared helpers for consistency:
   ```python
   from wepppy.weppcloud.utils.helpers import (
       parse_request_payload, 
       success_factory, 
       exception_factory
   )
   
   try:
       payload = parse_request_payload(request, 
                                      boolean_fields={'enabled'},
                                      int_fields={'year'})
       # Process payload
       return success_factory(data=result)
   except Exception as e:
       return exception_factory(e)
   ```

6. **Document the route** - Add entry to this README with NoDb interactions

7. **Add tests** - Create or extend test coverage in `tests/weppcloud/routes/`

### Testing Patterns

**NoDb stubbing:**
```python
from tests.factories.singleton_factory import create_stub

def test_my_endpoint(client, tmp_path):
    # Stub NoDb controller
    controller_stub = create_stub(MyController, wd=str(tmp_path))
    controller_stub.property = 'value'
    
    # Make request
    response = client.post('/runs/test/config/tasks/my_action')
    
    assert response.status_code == 200
```

**Helper mocking:**
```python
from unittest.mock import patch

def test_with_mocked_helper(client):
    with patch('wepppy.weppcloud.routes.nodb_api.my_bp.get_wd') as mock_wd:
        mock_wd.return_value = '/fake/wd'
        response = client.get('/runs/test/config/query/my_data')
        assert response.status_code == 200
```

### Common Pitfalls

- **Missing locks**: Always use `with controller.locked():` before mutations
- **Forgetting `dump_and_unlock()`**: State changes won't persist without it
- **Incorrect helper imports**: Import from `wepppy.weppcloud.utils.helpers`, not individual modules
- **Missing type coercion**: Use `parse_request_payload()` to normalize form data types
- **Not handling exceptions**: Wrap route logic in try/except with `exception_factory()`

### Performance Considerations

- **Keep routes fast**: Offload work >2 seconds to Redis Queue (RQ) background jobs
- **Minimize lock time**: Acquire locks, mutate quickly, dump, and release
- **Cache expensive queries**: Use `@cached_property` or Redis caching for hot paths
- **Stream large files**: Use `send_file()` instead of loading into memory

## Maintaining This Reference

**When adding new routes:**
1. Add entry to appropriate blueprint section table
2. List NoDb singleton interactions (properties/methods accessed)
3. Note any helper deviations (RQ jobs, file streams, custom error handling)
4. Update blueprint's **Helper stack** bullet if new utilities are used
5. Add or extend test coverage under `tests/weppcloud/routes/`
6. Document new stubs in test files so imports stay in sync

**When updating existing routes:**
1. Keep table entries current with actual route decorators
2. Update NoDb interaction column if controller usage changes
3. Document breaking changes in Notes column
4. Update related frontend controller documentation links

**When refactoring helpers:**
1. Search for usages: `rg 'helper_name' wepppy/weppcloud/routes/nodb_api`
2. Update all blueprint **Helper stack** bullets
3. Update this section's helper table
4. Ensure test stubs remain compatible

**Quality checks:**
- Run `rg 'README.md' wepppy/weppcloud/routes/nodb_api` to confirm this is the only README
- Verify Markdown linting passes
- Ensure all links to source files and docs are valid
- Check that controller_js cross-references use exact heading names for doc-extract tooling

## Further Reading

- [AGENTS.md](../../../../AGENTS.md) - NoDb patterns, Flask blueprint conventions, and testing strategies
- [controllers_js/README.md](../../controllers_js/README.md) - Frontend controller documentation and API contracts
- [controller_foundations.md](../../../../docs/dev-notes/controller_foundations.md) - UI wiring and architecture
- [controllers_js_jquery_retro.md](../../../../docs/dev-notes/controllers_js_jquery_retro.md) - Helper migration history
- [tests/weppcloud/routes/](../../../../tests/weppcloud/routes/) - Test suite with stubbing patterns
- [wepppy/nodb/](../../../nodb/) - NoDb controller source code

## Credits

NoDb API design and implementation by the wepppy development team.

License: BSD-3 Clause (see [../../../../license.txt](../../../../license.txt))
