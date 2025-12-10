# Control View Inventory & Audit

_Date: 2025-10-22 (updated audit aligned with current Pure migration status)_

## Scope & Method
- Focuses on controller panels rendered on the `runs0` page (`routes/run_0/templates/0.htm`) and related controls that share the ControlBase contract.
- Reviews their template inheritance, paired JavaScript modules, and current Flask blueprints (`wepppy/weppcloud/routes/**`) to surface routing diversity ahead of the `/controls/<slug>/<action>` refactor.
- Highlights supporting fragments (advanced option includes, modals, map overlays) that will need macro coverage when `_pure_base.htm` lands.
- Flags controls whose wiring is incomplete or legacy so the team can triage before the Pure.css migration begins.
- Pair this inventory with the [NoDb API Blueprint Map](../../../wepppy/weppcloud/routes/nodb_api/README.md) when you need per-route singletons, helper stacks, or testing references.

## Interactive Controls (runs0 forms)
| Control / Panel | Template Extends | JS Controller | Primary Backend / Routes | Inputs & Uploads | Behaviour Notes & Dependencies |
| --- | --- | --- | --- | --- | --- |
| Map | Pure macros (`controls/map_pure.htm`) | `map.js` | `map_bp` (`routes/map.py`), geodata services, `elevationquery` microservice | Text input for center, tabbed map controls, Leaflet events | Pure implementation is live; UX polish & doc updates tracked in the 20251023 Frontend Integration package |
| BAER Upload | Pure macros (`disturbed_sbs_pure.htm`) · legacy `_base.htm` | `baer.js` | `disturbed_bp` (`tasks/upload_sbs`, `tasks/remove_sbs`, `tasks/set_firedate`) | SBS raster upload, radio-mode switches, uniform builders | Uses `FormData`, refreshes map overlays, conditional content by `ron.mods`; JS now delegates via `data-sbs-*` hooks so both layouts stay functional |
| Road Upload | `_base.htm` | Inline wiring via `run_page_bootstrap.js` (no dedicated module) | _TBD_ – legacy `disturbed` tasks (`/tasks/upload_road/`, `/tasks/remove_road/`) require confirmation | `.geojson` upload, upload/remove buttons | Needs explicit JS controller + active route check before standardisation |
| Channel Delineation | Pure macros (`controls/channel_delineation_pure.htm`) | `channel_delineation.js` | `watershed_bp` (`tasks/build_channels`, `tasks/update_extent`) | Map extent fields, numeric inputs, unitizer bindings | Pure implementation is live; refinements routed through the 20251023 Frontend Integration package |
| Set Outlet | Pure macros (`controls/set_outlet_pure.htm`) | `outlet.js` | `watershed_bp` (`tasks/set_outlet`, `tasks/clear_outlet`) | Mode radio group, coordinate text input, command buttons | Uses Pure shell with legacy IDs preserved for JS/preflight compatibility |
| Subcatchments | Pure macros (`controls/subcatchments_pure.htm`) | `subcatchment_delineation.js` | `watershed_bp` (`tasks/build_subcatchments`, `tasks/clear_subcatchments`) | Advanced options (TauDEM/Peridot), RQ-triggering buttons | Pure implementation is live; remaining color-map UX + docs tracked in the 20251023 Frontend Integration package |
| Rangeland Cover | Pure macros (`controls/rangeland_cover_pure.htm`) · legacy `_base.htm` | `rangeland_cover.js`, `rangeland_cover_modify.js` | `rangeland_cover_bp` (`tasks/set_rangeland_cover_mode`) & `rangeland_bp` (`tasks/build_rangeland_cover`, `tasks/modify_rangeland_cover`) | Mode radios (NLCD, RAP, single value), RAP year input, foliar/ground defaults, build button | Shares StatusStream pattern with other controls; modify panel remains in map tab (controls/modify_rangeland_cover.htm) |
| Landuse | Pure macros (`controls/landuse_pure.htm`) | `landuse.js`, `landuse_modify.js` | `landuse_bp` (`tasks/set_landuse_mode`, `tasks/modify_landuse`, `query/*`) | Multi-selects, locale-controlled lists, advanced modify forms | Pure main panel now live; modify panel remains under map tab. Dataset options supplied by `available_landuse_datasets`; JS bindings handle mode, upload, and coverage tweaks |
| Soil | Pure macros (`controls/soil_pure.htm`) | `soil.js` | `soils_bp` (`tasks/set_soil_mode`, `query/*`, `tasks/set_soils_ksflag`) | Mode radios (per hillslope, Mukey, database), optional ksflag/determined sol_ver selects | Pure control mirrors legacy behaviour; further UX polish pending |
| Climate | Pure macros (`controls/climate_pure.htm`) | `climate.js` | `climate_bp` (`tasks/update_climate`, `tasks/upload_cli`, `query/*`) | Radio groups, select inputs, `.cli` upload | Uses catalog-driven sections, delegated events, and StatusStream panels |
| RAP Timeseries | Pure macros (`controls/rap_ts_pure.htm`) | `rap_ts.js` | `rap_ts_bp` (`tasks/run_rap_ts`) & `rq/api/acquire_rap_ts` | Action button queues RAP TS acquisition job; status stream reports progress | Secondary reporting control; mirrors StatusStream panel contract |
| WEPP | Pure macros (`controls/wepp_pure.htm`) | `wepp.js` | `wepp_bp` (`tasks/run_wepp`, `tasks/download_results`), `/rq/api` job endpoints | Run/queue buttons, advanced options include stack | Core model execution; uses RQ polling and advanced option includes |
| Treatments (optional) | Pure macros (`controls/treatments_pure.htm`) | `treatments.js` | `treatments_bp` (`tasks/set_treatments_mode`) & `/rq/api/build_treatments` | Mode switch (per hillslope vs upload), raster upload, builder button | Pure control with StatusStream + upload helper. Renders as standalone section when treatments mod enabled |
| RHEM | Pure macros (`controls/rhem_pure.htm`) · legacy `_base.htm` | `rhem.js` | `rhem_bp` (`tasks/run_rhem`, `tasks/download_rhem`) | Single run button (`btn_run_rhem`) with hint text | Pure shell mirrors RAP TS; JS now auto-detects StatusStream panels while legacy template remains for classic runs |
| Observed Data | Pure macros (`observed_pure.htm`) · legacy `_base.htm` | `observed.js` | `observed_bp` (`tasks/run_model_fit`, `report/observed`) | CSV textarea submission (future: file upload) | `controlBase.attach_status_stream` wires StatusStream; fallback panels spawn when the legacy template omits Pure markup so no shim is required |
| Debris Flow | Pure macros (`controls/debris_flow_pure.htm`) · legacy `_base.htm` | `debris_flow.js` | `debris_flow_bp` (`tasks/run_debris_flow`) & `rq/api/run_debris_flow` | Single action button triggers debris-flow analysis (PowerUser only) | `controlBase.attach_status_stream` handles telemetry; fallback panels let legacy markup stream without additional shims |
| Ash (WATAR) | Pure macros (`controls/ash_pure.htm`) · legacy `_base.htm` | `ash.js` | `watar_bp` (`tasks/set_ash_*`, `report/ash`) | Mode radios, numeric params, optional map uploads | Pure template uses JSON payload + StatusStream; client-side + backend validations enforce upload limits. Legacy template retained for classic runs page |
| DSS Export | Pure macros (`controls/dss_export_pure.htm`) · legacy `_base.htm` | `dss_export.js` | `rq/api/post_dss_export_rq` (queues `post_dss_export_rq`) | Mode radios (select channels or by order), optional filters, export button | RQ-backed task with StatusStream logging; legacy template retained for classic runs |
| Omni Scenarios | Pure macros (`controls/omni_scenarios_pure.htm`) · legacy `_base.htm` | `omni.js` | `omni_bp` (`tasks/save_scenario`, `tasks/apply_contrast`) | Dynamic card builder, file uploads, multi-selects | Pure template uses macro helpers + delegated events; legacy view retained only for archival references |
| Omni Contrast Definition | Pure macros (`controls/omni_contrasts_pure.htm`) · legacy `_base.htm` | `omni.js` | `omni_bp` | Textareas, scenario selectors | Shares metadata with Omni scenarios; Pure view now active on runs₀ |
| Team / Collaborators | Pure macros (`controls/team_pure.htm`) · legacy `_base.htm` | `team.js` | `team_bp` (`tasks/adduser`, `tasks/removeuser`, `report/users`) | Email entry, remove buttons | Pure shell mirrors legacy IDs; StatusStream support added while legacy template remains on 0.htm | `team.js` | `project_bp` (`tasks/adduser`, `tasks/removeuser`, `report/users`) | Email entry, remove buttons | Uses ControlBase for status/logging; summary renders collaborator list |

## Read-Only & Report Panels
| Panel | Template Extends | Entry Point(s) | What It Surfaces | Notes |
| --- | --- | --- | --- | --- |
| Export | `_content_base.htm` | Included on runs0 (`controls/export.htm`) | Links to packaged downloads (ZIP, JSON) | Styling tied to legacy `.controller-section`; no JS |
| WEPP Reports | `_content_base.htm` | Conditional include (`controls/wepp_reports.htm`) | Links to WEPP summary/return period reports & fork actions | Locale-aware text, heavy reliance on `url_for_run` helpers |
| RHEM Reports | `_content_base.htm` | Conditional include (`controls/rhem_reports.htm`) | Report shortcuts for RHEM outputs | Only visible when RHEM runs; inherits Bootstrap list styling |
| Climate Monthlies | Partial table (`controls/climate_monthlies.htm`) | Rendered inside climate dialogs | Tabular summary of climate stats with unitizer helpers | Uses inline `<table>` markup; designed for modal display |

## Modal & Supporting Partials
- `_base.htm` / `_content_base.htm`: current layout shells providing `form`, status, summary, and stacktrace placeholders; target for replacement by `_pure_base.htm`.
- `controls/unitizer_modal.htm` + `unitizer.htm`: modal and preference controls for unit conversion (`project.js` orchestrates preference changes).
- `controls/wepp_pure_advanced_options/*.htm`: advanced WEPP includes (baseflow, frost, clip soils, etc.) pulled into the WEPP panel via `{% include %}`; legacy `controls/wepp_advanced_options` templates were removed.
- `controls/map/rhem_hillslope_visualizations.htm`, `wepp_hillslope_visualizations.htm`: Leaflet overlay templates consumed by MapController.
- `controls/edit_csv.htm`: generic CSV editor used by disturbed workflows.
- `controls/poweruser_panel.htm`: global modal enabling push notifications and advanced resources; embeds extensive inline JS and CSS.

## JavaScript Infrastructure Snapshot
- `control_base.js`: shared ControlBase mixin handling job polling, stacktrace rendering, button disables, and WebSocket wiring.
- `status_stream.js` + `control_base.js`: Redis/Status2 WebSocket bridge; ControlBase attaches per panel via `attach_status_stream`.
- `controllers.js` (generated via `build_controllers_js.py` and `controllers_js/templates/controllers.js.j2`): bundles singleton controllers and exposes them to templates.
- `run_page_bootstrap.js.j2`: builds a `runContext` object (run metadata, job ids, feature flags) and calls `WCControllerBootstrap.bootstrapMany` so each controller can hydrate itself via `instance.bootstrap(context)`. Cross-control hooks (BAER ↔ Disturbed, outlet map listeners, etc.) now live inside the respective controllers.
- `project.js`, `disturbed.js`, `utils.js`, `preflight.js`: shared helpers for unit preferences, disturbed module utilities, generic DOM helpers, and preflight checks.
- Third-party helpers (`tinyqueue`, `polylabel`, `leaflet-ajax`, `glify`) are injected at the end of `0.htm` and are tightly coupled to MapController.

## Backend Route Overview
- `nodb_api/watershed_bp.py`: channel delineation, outlet placement, subcatchment build/clear, plus metadata queries.
- `nodb_api/landuse_bp.py`, `rangeland_bp.py`, `rangeland_cover_bp.py`: landuse switching, coverage edits, RAP integration, rangeland summaries.
- `nodb_api/soils_bp.py`: soil modes, summaries, Ks flag updates.
- `nodb_api/climate_bp.py`: climate source selection, station fetch, `.cli` upload, RAP timeseries launch.
- `nodb_api/wepp_bp.py`, `rhem_bp.py`, `debris_flow_bp.py`, `watar_bp.py`: model execution routes and report endpoints for WEPP, RHEM, debris flow, and WATAR respectively.
- `nodb_api/disturbed_bp.py`: BAER/SBS handling, fire date, disturbed lookup maintenance.
- `nodb_api/observed_bp.py`: observed data ingestion, model fit, report & plot resources.
- `nodb_api/treatments_bp.py`: optional treatments control tasks and RQ build endpoints.
- `nodb_api/project_bp.py`: collaborator (`team`) management, project metadata.
- `routes/map.py`, `routes/geodata.py`, and microservices (`elevationquery`) back the map control’s live data.
- `routes/rq`: job status (`/rq/api/*`) polled by ControlBase across WEPP, treatments, Omni, etc.

## Additional Notes & Gaps
- **Road Upload wiring**: template exists but there is no dedicated JS controller and the expected `/tasks/upload_road/` endpoint is not surfaced in current blueprints—needs verification or removal from the migration scope.
- **Inline scripting debt**: panels such as `ash.htm`, `poweruser_panel.htm`, and portions of `map.htm` embed large `<script>` blocks that must be factored into the macro/component plan.
- **Locale branching**: Landuse, climate, and rangeland templates still branch on `ron.locales`/`ron.mods`; the future metadata contract should eliminate these ad-hoc checks.
- **Advanced option includes**: WEPP advanced option partials (Pure variants under `controls/wepp_pure_advanced_options/`) and Omni fragments share markup patterns that will need macro equivalents to avoid duplicate Pure.css conversions.
- **Read-only panels**: Export/Report views inherit `.controller-section` styling even though they render static content—confirm whether they migrate to `_pure_base.htm` or a leaner wrapper.

## Field Metadata Extracts
To prepare for macro-driven rendering, the tables below document the primary form fields for high-priority controls. Columns capture the DOM identifier, element type, human-facing label, how options are populated, the backend attribute or route that receives the value, and any conditional visibility rules that templates or JS enforce. Advanced option includes (WEPP, Omni) still require deeper enumeration; the entries here focus on the core panels that most frequently block migration work.

### Landuse Control
| Field ID | Input Type | Label / Purpose | Options & Data Source | Backend Binding | Visibility / Notes |
| --- | --- | --- | --- | --- | --- |
| `landuse_mode` | radio group | Choose how landuse is assigned (per hillslope, single value, uploaded map, RRED presets) | Hard-coded values mapped to `LanduseMode` enum; RRED options rendered only when `'rred' in ron.mods` | `POST /runs/<runid>/<config>/tasks/set_landuse_mode/` → `Landuse.mode` | Drives which `_controls` block is shown; selection echoed in `landuse_form` form data for build |
| `landuse_db` | select | Select raster catalog for gridded mode | Locale-specific catalog paths (NLCD, CORINE, local overrides) provided by `available_landuse_datasets` (landcover entries tagged `kind == "landcover"`) | `POST /runs/<runid>/<config>/tasks/set_landuse_db/` → `Landuse.nlcd_db` | Displayed only when `landuse_mode == 0`; disabling copy/paste styling critical when converted to macros |
| `landuse_single_selection` | select | Pick management class for single-landuse mode | Catalog built from `Landuse.available_datasets` (backed by `wepppy.nodb.locales.landuse_catalog`) | Submitted with `set_landuse_mode` request → `Landuse.single_selection` | Displayed when `landuse_mode == 1`; JS triggers `handleSingleSelectionChange` to persist immediately |
| `input_upload_landuse` | file (.img/.tif) | Upload thematic landuse raster | User chooses local file; expects SBS-aligned values | Consumed by `POST /runs/<runid>/<config>/rq/api/build_landuse` → `Landuse.parse_inputs` | Only visible when `landuse_mode == 4`; ensure macro annotates accept list & describes required schema |
| `landuse_management_mapping_selection` | select | Map uploaded raster classes to management sets | `landuse_management_mapping_options` from context | Captured during `build_landuse` RQ submission → `Landuse.mapping` | Tied to upload mode; link to docs currently hard-coded into template |
| `mofe_buffer_selection` | select | Choose management for buffer strips in multi-OFE workflows | Reuses `landuseoptions`; pre-select uses `landuse.mofe_buffer_selection` | Form payload ingested by `Landuse.parse_inputs`; sets `Landuse.mofe_buffer_selection` | Rendered only when `wepp.multi_ofe` is truthy; toggles live under advanced options collapse |

#### Landuse Report

| View | Template | Notes |
| --- | --- | --- |
| Landuse coverage summary | `reports/landuse.htm` | Pure table + collapsible overrides fed by `Landuse.available_datasets`; JS hooks use data attributes instead of inline handlers; coverage selects source options from controller-provided percentages. |
| Soil coverage summary | `reports/soils.htm` | Pure table (`wc-table`) with numeric alignment helper; read-only links to soil files and coverage percentages. |
| `burn_shrubs`, `burn_grass` | checkbox | Opt-in SBS-driven vegetation adjustments | Boolean toggles (`on/off`) | Parsed in `rq/api/build_landuse` and written to `Disturbed.burn_shrubs` / `Disturbed.burn_grass` | Only present when `'disturbed' in ron.mods`; tie into SBS map availability |
| `btn_build_landuse` | button | Submit landuse build job | N/A | Triggers `POST /runs/<runid>/<config>/rq/api/build_landuse` (enqueues RQ job) | ControlBase disables/enables button; ensure macros tag `data-command` for HTMX replacement |

### Climate Control
| Field ID | Input Type | Label / Purpose | Options & Data Source | Backend Binding | Visibility / Notes |
| --- | --- | --- | --- | --- | --- |
| `climate_build_mode` | radio group | Toggle between CLIGEN-generated vs user-defined climates | Values `0` (CLIGEN) / `1` (user-defined) | JS calls `setBuildMode`; indirectly drives `Climate.climatestation_mode` (4 for user-defined) | Determines whether `#climate_cligen` or `#climate_userdefined` sections render |
| `input_upload_cli` | file (.cli) | Upload custom climate file | Local `.cli` file, validated by `Climate.set_user_defined_cli` | `POST /runs/<runid>/<config>/tasks/upload_cli/` | Only enabled when build mode = user-defined; macro needs to surface allowed extension |
| `climatestation_mode` | radio group | Station ranking filter | Values `0` (Closest), `1` (Heuristic/Multi-factor); locale-specific wording | `POST /runs/<runid>/<config>/tasks/set_climatestation_mode/` → `Climate.climatestation_mode` | Hidden when build mode = user-defined (JS forces mode 4) |
| `climate_station_selection` | select | Choose CLIGEN station | Options populated via `/view/closest_stations/` or `/view/heuristic_stations/` | `POST /runs/<runid>/<config>/tasks/set_climatestation/` → `Climate.climatestation` | Only visible for CLIGEN mode; change also triggers monthlies preview |
| `climate_mode` | radio group | Select dataset / generation mode (e.g., Vanilla CLIGEN, PRISM, GRIDMET, Single Storm, Future CMIP5) | Hard-coded list mapped to `ClimateMode` enum; availability depends on locale and observed/future dataset presence | Captured in `Climate.parse_inputs` during `build_climate` RQ submission | Controls which secondary sections (years, single storm inputs, precip scaling) display; macro set must centralize tooltip content |
| `climate_spatialmode` | radio group | Configure spatial distribution (single vs multiple climates) | Values `0` (single), `1` (multiple PRISM revision), `2` (multiple interpolated) | `POST /runs/<runid>/<config>/tasks/set_climate_spatialmode/` → `Climate.climate_spatialmode` | Option `2` disabled for modes that forbid per-hillslope interpolation; gating handled in JS (`MODE_CONFIG`) |
| `input_years` | numeric text | Number of stochastic years | Manual entry; default from `Climate.input_years` | Stored via `Climate.parse_inputs` for modes that rely on CLIGEN or stochastic datasets | Section shown for modes that generate synthetic climates (Vanilla, PRISM, etc.); enforce ≤ `CLIMATE_MAX_YEARS` |
| `observed_start_year`, `observed_end_year` | numeric text | Year bounds for observed datasets | Defaults pulled from `Climate.observed_*` | `Climate.parse_inputs` → `Climate.set_observed_pars` | Section displayed when mode expects observed data (DAYMET/GRIDMET) |
| `future_start_year`, `future_end_year` | numeric text | Year bounds for CMIP5 futures | Defaults from `Climate.future_*` | `Climate.parse_inputs` → `Climate.set_future_pars` | Visible only when `climate_mode` == Future |
| `ss_*` fields (`ss_storm_date`, `ss_design_storm_amount_mm`, `ss_duration_of_storm_in_hours`, `ss_time_to_peak_intensity_pct`, `ss_max_intensity_inches_per_hour`) | text / unit-paired inputs | Configure designed single storm events | Inputs allow metric/imperial pairing via unitizer attributes | `Climate.parse_inputs` → `Climate.set_single_storm_pars` | Group visible for `climate_mode` 4 (single storm) or 14 (batch storms); macros must preserve unitizer bindings |
| `climate_daily_temp_ds` | radio group | Override temperature source for breakpoint climates | Values: `null`, `prism`, `gridmet`, `daymet` | Stored via `Climate.parse_inputs` → `Climate.climate_daily_temp_ds` | Shown when `climate_mode` == 13 (NEXRAD breakpoint) |
| `precip_scaling_mode` and companions (`precip_scale_factor`, `precip_scale_factor_map`, `precip_monthly_scale_factors_*`, `precip_scale_reference`) | radio + numeric inputs | Configure precipitation scaling strategy | Options map to `ClimatePrecipScalingMode` (0–4); inputs captured from text fields | Parsed in `Climate.parse_inputs`, updating `Climate.precip_*` attributes | Sections conditionally rendered based on selected scaling mode; includes file selectors for spatial maps |
| `use_gridmet_wind_when_applicable` | checkbox | Use GRIDMET winds when available | Boolean toggle | `POST /runs/<runid>/<config>/tasks/set_use_gridmet_wind_when_applicable/` → `Climate.use_gridmet_wind_when_applicable` | Lives in precipitation scaling block; only meaningful for datasets that support wind substitution |
| `btn_build_climate` | button | Submit climate build job | N/A | Triggers `POST /runs/<runid>/<config>/rq/api/build_climate` (enqueues job, writes NoDb via `parse_inputs`) | JS manages state (`MODE_CONFIG`) and WebSocket lifecycle |

### WEPP Control (base panel)
| Field ID | Input Type | Label / Purpose | Options & Data Source | Backend Binding | Visibility / Notes |
| --- | --- | --- | --- | --- | --- |
| `btn_run_wepp` | button | Launch WEPP run | N/A | `POST /runs/<runid>/<config>/tasks/run_wepp/` → enqueues RQ job & logs via NoDb | Always visible unless `ron.mods` switches panel to RHEM; ControlBase handles status updates |
| Advanced include stack (`controls/wepp_pure_advanced_options/*.htm`) | multiple (text, number, checkbox, file) | Configure channel parameters, flowpaths, PMET, frost, snow, baseflow, phosphorus, clipping, executable paths | Values seeded from `Wepp` attributes and per-module config defaults | Parsed in `rq/api/build_wepp` (`Wepp.parse_inputs`) updating attributes such as `Wepp.dtchr_override`, `Wepp.channel_erodibility`, `Wepp.baseflow_opts`, etc. | Each include renders inside the collapse; future metadata work should enumerate all field IDs so macros can map labels/units without duplicating HTML |

#### WEPP Advanced Options (partial summary)
| Section / Partial | Key Fields | Backend Binding | Visibility & Notes |
| --- | --- | --- | --- |
| Flowpaths (`flowpaths.htm`) | `run_flowpaths` checkbox toggles flowpath loss grid generation | `POST /runs/<runid>/<config>/tasks/set_run_wepp_routine` → `Wepp.set_run_flowpaths` | Experimental output; ControlBase manages WebSocket lifecycle |
| Channel Input (`chan_inp.htm`) | `dtchr_override` (seconds), `chn_topaz_ids_of_interest` (ID list) | `Wepp.parse_inputs` normalizes values (ints) and validates `dtchr_override ≥ 60` | Macro should retain guidance text and input constraints |
| Channel Parameters (`channels.htm`) | `checkbox_wepp_tcr` toggle; `channel_critical_shear` select; `channel_erodibility`; `channel_manning_*`; optional `tcr_opts_*` numeric fields | Toggle hits `set_run_wepp_routine('tcr')`; value fields stored via `Wepp.parse_inputs` / `TCROpts.parse_inputs` | TCR inputs render only when `wepp.tcr_opts` exists; options for critical shear supplied by `critical_shear_options` context |
| Baseflow (`baseflow.htm`) | `gwstorage`, `bfcoeff`, `dscoeff`, `bfthreshold` | `BaseflowOpts.parse_inputs` (invoked by `Wepp.parse_inputs`) | Not applicable to single-storm climates; keep units (mm, per day, ha) explicit |
| PMET (`pmet.htm`) | `pmet_kcb`, `pmet_rawp`, `checkbox_wepp_pmet` | Toggle via `set_run_wepp_routine('pmet')`; numeric values stored on `Wepp` (`_pmet_kcb`, `_pmet_rawp`) | Coefficient inputs hidden when `'disturbed' in ron.mods`; macros should encode tooltip & placeholder text |
| Frost (`frost.htm`) | `checkbox_wepp_frost` | `set_run_wepp_routine('frost')` → `Wepp.set_run_frost` | Simple toggle; retain guidance about hydraulic/thermal adjustments |
| Snow (`snow.htm`) | `checkbox_wepp_snow`; `snow_opts_rst`; `snow_opts_newsnw`; `snow_opts_ssd` | Toggle posts to `set_run_wepp_routine('snow')`; numeric values parsed via `SnowOpts.parse_inputs` | Includes unitizer-style metric inputs; defaults drawn from `SnowOpts` |
| Bedrock (`bedrock.htm`) | `kslast` (restrictive layer ksat) | `Wepp.parse_inputs` sets `_kslast` (float or `None`) | Accepts blanks; macro should show hint that empty disables override |
| Clip Hillslopes (`clip_hillslopes.htm`) | `clip_hillslopes` checkbox; `hillslope_clip_length` (m) | `api_run_wepp` updates `Watershed.clip_hillslopes` / `.clip_hillslope_length` | Ineffective for multi-OFE runs; ensure macros annotate units and default source |
| Clip Soils & Initial Saturation (`clip_soils_depth.htm`) | `clip_soils`; `clip_soils_depth` (mm); `initial_sat` (fraction) | `api_run_wepp` writes to `Soils.clip_soils`, `.clip_soils_depth`, `.initial_sat` | Shared with subcatchment builder; highlight validation (numeric) |
| Phosphorus (`phosphorus.htm`) | `surf_runoff`; `lateral_flow`; `baseflow`; `sediment` | `PhosphorusOpts.parse_inputs` updates concentrations | Header text varies when `'lt' in ron.mods`; macros must keep mg/L vs mg/kg cues |
| WEPP Binary (`wepp_bin.htm`) | `wepp_bin` select listing installed binaries | `Wepp.parse_inputs` sets `_wepp_bin` | Options provided via `wepp_bin_opts` context |
| Hourly Seepage (`wepp_ui.htm`) | `checkbox_hourly_seepage` | `set_run_wepp_routine('wepp_ui')` → `Wepp.set_run_wepp_ui` | Only affects projects with 7778 soils; include warning in macro tooltip |
| Export on Completion (`prep_details.htm`) | `prep_details_on_run_completion`; `arc_export_on_run_completion`; `legacy_arc_export_on_run_completion` checkboxes | `api_run_wepp` updates corresponding `_prep_*` flags | Combined with main-panel `dss_export_on_run_completion` to orchestrate packaging |
| Revegetation (`revegetation.htm`) | `reveg_scenario` select; `input_upload_cover_transform` file | `api_run_wepp` invokes `Revegetation.load_cover_transform` (when module active) | Section rendered only when `reveg` mod is enabled; macro should allow file upload gating |

### Treatments Control
| Field ID | Input Type | Label / Purpose | Options & Data Source | Backend Binding | Visibility / Notes |
| --- | --- | --- | --- | --- | --- |
| `treatments_mode` | radio group | Pick workflow (per-hillslope selection vs uploaded raster) | Values map to `TreatmentsMode` (`1` selection, `4` map upload) | `POST /runs/<runid>/<config>/tasks/set_treatments_mode/` → `Treatments.mode` | Mode `4` reveals upload controls and lookup table; mode `1` surfaces the selection dropdown |
| `input_upload_landuse` | file (.img/.tif) | Upload treatment map | User-provided raster; validated & reprojected during build | `POST /runs/<runid>/<config>/rq/api/build_treatments` (reuses `build_landuse_rq` pipeline) | Pure control uses `save_run_file` (100&nbsp;MB limit, `.tif/.img` allow-list); field hidden unless mode `4` selected |
| `treatments_single_selection` | select | Choose treatment when specifying hillslopes | Options drawn from `treatmentoptions` context | Submitted alongside `set_treatments_mode` to sync selected treatment | Visible only when mode `1` is active |
| `btn_build_treatments` | button | Apply treatments | N/A | Calls `/rq/api/build_treatments`, which triggers `build_landuse_rq` with treatment context | RQ job shares WS channel `treatments`; button wired via delegated handler |

### Rangeland Cover Control
| Field ID | Input Type | Label / Purpose | Options & Data Source | Backend Binding | Visibility / Notes |
| --- | --- | --- | --- | --- | --- |
| `rangeland_cover_mode` | radio group | Choose data source (NLCD shrubland, RAP hillslope, single watershed value) | Locale-aware labels; RAP option rendered when `'rap' in rangeland_cover.mods` | `POST /runs/<runid>/<config>/tasks/set_rangeland_cover_mode/` → `RangelandCover.mode` & `.rap_year` | Mode `2` reveals RAP year input; macros need to toggle sections |
| `rap_year` | numeric text | Specify RAP year when RAP mode selected | Default from `RangelandCover.rap_year` | Persisted in `set_rangeland_cover_mode` payload; used during build | Only visible for RAP mode; JS hides otherwise |
| `btn_build_rap_ts` | button | Trigger RAP time-series acquisition | `POST /runs/<runid>/<config>/rq/api/acquire_rap_ts` → enqueues worker job | ControlBase disables during readonly/lock; JS listens for completion to refresh status | `hint_build_rap_ts` announces success or errors via `aria-live` |
| Default cover inputs (`bunchgrass_cover`, `forbs_cover`, `sodgrass_cover`, `shrub_cover`, `basal_cover`, `rock_cover`, `litter_cover`, `cryptogams_cover`) | numeric text | Seed foliar/ground cover defaults (%) | Values sourced from NoDb defaults | Submitted to `/runs/<runid>/<config>/tasks/build_rangeland_cover/` → `RangelandCover.build` | All inputs share CSS classes; macros should enforce % validation hints |
| `btn_build_rangeland_cover` | button | Generate rangeland cover map | N/A | `POST /runs/<runid>/<config>/tasks/build_rangeland_cover/` updates NoDb & triggers map export | ControlBase/WS channel `rangeland_cover`; ensure summary updates via `report()` |

### Rangeland Cover Modify Panel
| Field ID | Input Type | Label / Purpose | Backend Binding | Visibility / Notes |
| --- | --- | --- | --- | --- |
| `checkbox_modify_rangeland_cover` | checkbox | Enable interactive map selection | JS toggles Leaflet selection & collects Topaz IDs | Works alongside `textarea_modify_rangeland_cover`; macros should provide instructions |
| `textarea_modify_rangeland_cover` | textarea | Manual Topaz ID list | Posted via `RangelandCoverModify.modify()` to `/runs/<runid>/<config>/tasks/modify_rangeland_cover/` | IDs feed NoDb adjustments; ensure placeholder text preserved |
| Cover inputs (`bunchgrass_cover`, `forbs_cover`, `sodgrass_cover`, `shrub_cover`, `basal_cover`, `rock_cover`, `litter_cover`, `cryptogams_cover`) | numeric text | Override selected hillslopes | Sent with modify payload | `loadCovers` helper can prefill values; macros should enable compact layout |
| `btn_modify_rangeland_cover` | button | Apply manual overrides | `RangelandCoverModify.modify()` posts JSON to `/tasks/modify_rangeland_cover/` | Refreshes map color map on completion |

### BAER / Disturbed Upload Control
| Field ID | Input Type | Label / Purpose | Backend Binding | Visibility / Notes |
| --- | --- | --- | --- | --- |
| `sbs_mode` | radio group | Toggle between map upload and uniform severity presets | `Baer.showHideControls` toggles sections | Mode `0` enables file upload; mode `1` enables uniform buttons |
| `input_upload_sbs` | file (.tif/.img) | Upload Soil Burn Severity raster | `POST /runs/<runid>/<config>/tasks/upload_sbs/` → map saved/validated via `Baer.validate` | Accepts uint8/short thematic rasters; macros must note projection expectations |
| Upload/Remove buttons (`upload_sbs`, `remove_sbs`) | button | Manage SBS map | `Baer.upload_sbs()` / `remove_sbs()` call `tasks/upload_sbs` and `tasks/remove_sbs` | Buttons hidden in readonly mode; expose `data-sbs-action="upload/remove"` so delegated handlers work in both legacy and Pure layouts |
| Uniform build buttons (`build_uniform_sbs`) | button | Generate uniform SBS by severity | `Baer.build_uniform_sbs()` hits `tasks/build_uniform_sbs` (via disturbed NoDb) | Buttons carry `data-sbs-uniform` severities; populate hints and update map |
| `firedate` input + set button | text + button | Store fire date for vegetation logic | `Baer.set_firedate()` posts to `/tasks/set_firedate/` updating `Disturbed.fire_date` | Visible when `rap_ts` in climate mods; set button uses `data-sbs-action="set-firedate"`; macros should show required format mm dd yy |

### Road Upload Panel (Salvage Mod)
| Field ID | Input Type | Label / Purpose | Backend Binding | Notes |
| --- | --- | --- | --- | --- |
| `input_upload_road` | file (.geojson) | Upload road network | _Unverified_ legacy routes `/tasks/upload_road/` / `/tasks/remove_road/` (not present in current blueprints) | Template includes buttons but JS/back-end wiring appears missing—confirm before migration |
| `btn_upload_road`, `btn_remove_road` | buttons | Trigger upload/remove actions | Expected to post multipart/FormData / JSON to disturbed blueprint | Documented as TODO; macro should only surface once backend confirmed |

### Treatments / Rangeland Reports & Utilities
| Panel | Template | Purpose | Notes |
| --- | --- | --- | --- |
| Modify Rangeland Cover | `controls/modify_rangeland_cover.htm` | Manual override form embedded under map tabs | Shares input IDs with main rangeland panel—macros must avoid duplicate ID collisions when rendering |
| Treatments table | `treatments.treatments_lookup` | Displayed in `treatments_pure.htm` map upload section to explain raster coding | Values derived from NoDb lookup; keep table accessible |

### BAER/Road-Related Routes (for reference)
- `disturbed_bp`: `/tasks/upload_sbs/`, `/tasks/remove_sbs/`, `/tasks/set_firedate/`, `/tasks/modify_burn_class`, etc.
- _Missing_: `/tasks/upload_road/` & `/tasks/remove_road/` endpoints are referenced historically but absent—flag for follow-up before Pure.css conversion.

### Omni Scenario & Contrast Fields
| Section | Key Inputs | Backend Binding | Notes for Macro Implementation |
| --- | --- | --- | --- |
| Scenario builder (`omni_scenarios_pure.htm`) | Dynamically repeats: `scenario` select (values map to `OmniScenario.parse`); scenario params (`canopy_cover`, `ground_cover`, `ground_cover_increase`, `base_scenario`, `sbs_file`) depending on chosen type | `Omni.serializeScenarios()` builds `FormData` → `POST /rq/api/run_omni`; server saves uploads in `omni/_limbo` and calls `Omni.parse_scenarios` | Macro now drives the card layout; metadata still pulled from JS until descriptor work lands |
| Omni run trigger | `btn_run_omni` command button | Enqueues `run_omni_scenarios_rq`; ControlBase listens on `omni` channel | Delegated handlers operate on `data-omni-*` hooks in the Pure template |
| Contrast definition (`omni_contrasts_pure.htm`) | `omni_contrast_objective_parameter`, `omni_control_scenario`, `omni_contrast_scenario` selects; `contrast_cumulative_obj_param_threshold_fraction` numeric; (additional optional fields consumed by `Omni.parse_inputs`: `omni_contrast_hillslope_limit`, `omni_contrast_hill_min_slope`, `omni_contrast_hill_max_slope`, `omni_contrast_select_burn_severities`, `omni_contrast_select_topaz_ids`) | Posted to `/rq/api/run_omni_contrasts`; `Omni.parse_inputs` maps values to enum fields/properties | Pure view renders collapsible advanced inputs; legacy template retained for reference |
| Scenario reporting | Summary slot populated via `Omni.report_scenarios()` fetching `report/omni_scenarios/` | Triggered after `OMNI_SCENARIO_RUN_TASK_COMPLETED` event | `_pure_base.htm` summary region now hosts the rendered HTML; macros reserve placeholder IDs |

### Observed Data Control
| Field ID | Input Type | Label / Purpose | Backend Binding | Visibility / Notes |
| --- | --- | --- | --- | --- |
| `observed_text` | textarea | Paste CSV-formatted observed series (Date + measures) | `POST /runs/<runid>/<config>/tasks/run_model_fit/` → `Observed.parse_textdata`/`calc_model_fit` | Control shown when climate enables observed datasets; macro provides instructions list and disables via `disable-readonly` |
| `btn_run_observed` | button | Run model fit against observed data | Same endpoint; re-renders report link | RQ not used—calc runs synchronously; ensure button styles align with other commands |
| Summary link | Rendered in JS (`report()`) | Link to `report/observed/` | Ensure `_pure_base.htm` summary slot can host anchor |

### Debris Flow Control
| Field ID | Input Type | Label / Purpose | Backend Binding | Visibility / Notes |
| --- | --- | --- | --- | --- |
| `btn_run_debris_flow` | button | Submit debris flow model | `POST /runs/<runid>/<config>/rq/api/run_debris_flow` → enqueues `run_debris_flow_rq` | Panel gated to PowerUser (see template include); macros should warn results use Cannon 2010 model |
| Summary link | Injected by `DebrisFlow.report()` | Link to `report/debris_flow/` | `_pure_base.htm` summary block should support anchor |

### Ash Transport Control
| Field ID | Input Type | Label / Purpose | Backend Binding | Visibility / Notes |
| --- | --- | --- | --- | --- |
| `ash_depth_mode` radios | Select depth entry mode (depth/load/upload) | `Ash.setAshDepthMode()` toggles mode containers and caches selection | Determines which fieldset (depth, load, map upload) renders; radios now use `data-ash-depth-mode` for both legacy and Pure views |
| `fire_date`, `ini_black_depth`, `ini_white_depth`, etc. | Numeric/text inputs for ash parameters | Stored on `Ash` NoDb via AJAX posts | `ash.js` hydrates defaults from JSON payload, caches per-model edits, and preserves values when switching calibrations |
| `input_upload_*` (map uploads) | File inputs for ash maps | Posted to `rq/api/run_ash` (handled by `_task_upload_ash_map` + `save_run_file`) | Client-side + backend validation enforce <100 MB and `.tif/.tiff/.img` extensions; Pure template passes data attributes for future enhancements |

### Team / Collaborator Control
| Field ID | Input Type | Label / Purpose | Backend Binding | Visibility / Notes |
| --- | --- | --- | --- | --- |
| `adduser-email` | text | Invite new collaborator | `POST /runs/<runid>/<config>/tasks/adduser/` → associates user via SQLAlchemy datastore | Only visible to authenticated owners; macros should keep placeholder & validation |
| Add user button | button | Trigger invite | JS `Team.adduser_click()` posts form | On success, triggers report refresh |
| Remove user actions | Buttons rendered in report partial (`reports/users.htm`) | `POST /runs/<runid>/<config>/tasks/removeuser/` | Report HTML embeds remove buttons (JS binds to `Team.removeuser`) |
| Summary (`team.info`) | HTML from `report/users/` | Lists collaborators with remove buttons | `_pure_base.htm` summary block should support list markup |

### Modal Utilities & Editors
| Component | Template / Asset | Purpose | Notes for Migration |
| --- | --- | --- | --- |
| Unitizer Preferences | `controls/unitizer_modal.htm` (includes `unitizer.htm`) | Modal to adjust unit system & per-measure preferences | Pure modal (`wc-modal`) managed by `ModalManager`; `UnitizerClient` reads the static `unitizer_map.js` export to keep labels/values in sync. Global + per-category radios emit `data-unitizer-*` attributes and reuse `Project` handlers. |
| Edit CSV Utility | `controls/edit_csv.htm` | CSV editor (jspreadsheet) used for disturbed land/soil lookup | Standalone HTML page (not `_base.htm`); reference in `disturbed_bp.modify_disturbed` routes—document structure for redesign |
| Power User Modal | `controls/poweruser_panel.htm` | Push notification & resource hub | Inline service-worker logic; treat as modal-managed component when migrating |

### Read-Only / Content Panels
| Panel | Template | Key Links / Content | Notes |
| --- | --- | --- | --- |
| Export | `controls/export.htm` | Download links for GeoPackage, geodatabase, return-period TSVs, prep details, archive dashboard, ERMiT CSV | No JS; relies on `ron.mods` to toggle ERMiT & daily water balance sections. Macro should focus on semantics & spacing |
| WEPP Reports | `controls/wepp_reports.htm` | Links to watershed summaries, return periods, sediment characteristics, Deval report, fork project actions | Conditional content based on `climate.is_single_storm`, `prep.has_sbs`, user roles | Requires external anchor styling but no inputs |
| RHEM Reports | `controls/rhem_reports.htm` | Average annuals, return periods, run log links | Visible only when RHEM mod active; minimal markup |
| Climate Monthlies | `controls/climate_monthlies.htm` | Tabular summary with `unitizer` helpers for monthly stats | Embedded via modals/summary blocks; ensure macros preserve table classes |
| Power User Panel | `controls/poweruser_panel.htm` | Modal for push notifications/resources | Inline JS manages service worker; already captured in summary but treat as modal-only content when porting |

> **Next metadata pass**: verify legacy road upload pipeline, extend coverage to batch runner/command bar utilities, and inventory any remaining modals (e.g., edit CSV) that require redesign before `_pure_base.htm` rollout.

### Header & Command Bar Summary
| Component | Template / JS | Purpose | Notes for Migration |
| --- | --- | --- | --- |
| Run Header | `header/_run_header_fixed.htm` | Fixed navbar with project name/scenario editors, action icons, readonly/public toggles | Uses `Project` JS for debounced updates; treat as layout component outside `_pure_base.htm` scope |
| Non-run / Global Headers | `header/_non_run_user_header_fixed.htm`, `_global_header_fixed.htm` | Navigation for authenticated users and anonymous visitors | Minimal inputs; ensure styling aligns with Pure design tokens later |
| Command Bar | `routes/command_bar/templates/command-bar.htm`, `command_bar.js` | Keyboard-driven palette for triggering actions | Current template mixes CSS + JS; consider extracting styles and wiring to design tokens |

### Batch Runner Console (catalogued, out of main scope)
| Section | Template | Key Inputs / Actions | Backend Binding | Notes |
| --- | --- | --- | --- | --- |
| Resource Intake | `routes/batch_runner/templates/batch_runner_pure.htm` | `geojson_file` upload, validation status nodes | `BatchRunner.uploadGeojson()` (custom API) | Pure UI variant; legacy Bootstrap template removed |
| Run ID Template | same | `template-input` textarea, validate button, preview tables | `BatchRunner.validateTemplate()` -> batch API | Heavy client logic; treat as standalone console |
| Batch Tasks | same | Task toggles, run button (`btn_run_batch`) | `BatchRunner.runBatch()` -> `/rq/api/run-batch` | Layout currently uses Bootstrap cards; document for future redesign |

## Next Actions
1. Validate active routes for controls flagged `_TBD_` (Road Upload) and document required changes to align with the `/controls/<slug>/<action>` blueprint strategy.
2. Prioritise Pure migrations/cleanup for the remaining panels: map + delineation bundle and RHEM (legacy console). Update this inventory as each control flips to Pure.
3. Extend the audit to cover:
   - Controls gated behind other run modes or blueprints (e.g., Batch Runner, RHEM reports, additional console modals).
   - JavaScript modules without direct template counterparts (`project.js`, `disturbed.js`) to plan macro data contracts.
4. Annotate field-level metadata requirements (label, locale availability, unit hints) for each control so NoDb descriptors can be authored in parallel with the Pure.css migration.
