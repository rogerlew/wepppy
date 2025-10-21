# Climate Control Deep-Dive (Runs₀ Migration Prep)

This plan inventories the legacy climate control so we can translate it to the Pure stack with a catalog-driven, locale-aware experience similar to the landuse rewrite.

---

## 1. Current UI Anatomy (`wepppy/weppcloud/templates/controls/climate.htm`)
- **Build mode toggle** – `climate_build_mode` radios decide between CLIGEN workflows (`mode=0`) and user-defined uploads (`mode=1`). JS flips visibility of `#climate_cligen` vs `#climate_userdefined` and forces station mode `4` (UserDefined) when the upload path is active.
- **Station filter radios** – `climatestation_mode` presents “Closest” (0) and “Multi-Factor Ranking” (1). Locale branches for `eu`/`au` exist but render the same pair; modes `2`–`3` (EU/AU heuristics) never surface in markup despite existing JS backends. (R: do not support modes 2 and 3)
- **Station selector + PAR link** – `<select id="climate_station_selection">` is empty until JS loads `/view/*_stations/`. The “View PAR” anchor opens raw `.par` metadata in a new tab.
- **Monthlies placeholder** – `#climate_monthlies` receives the station summary table via `/view/climate_monthlies/` and re-applies unitizer conversions.
- **Climate mode radios** – Hard-coded list of `ClimateMode` options with nested locale checks:
  - Default (US) branch shows modes 5, 0, 9, 11, 13, 3, 6, 7.
  - All locales get 4 and 14 (single storm variants).
  - EU adds a second block for 0 and 8.
  - No branch surfaces `Observed` (2) or AU’s `AGDC` (10); DB-backed modes (6/7) lack follow-on UI to choose a file. (R: do not need to surface, these were for scripted runs)
  - Several JS-controlled sections (`#climate_mode5_controls`, `#climate_mode6_controls`, `#climate_mode10_controls`, etc.) are missing entirely, leaving MODE_CONFIG entries orphaned.
- **Parameter sections**:
  - `#input_years_container` for stochastic year counts (Vanilla, PRISM, etc.).
  - `#observed_years_container` and `#future_years_container` capture year bounds for observed/future datasets.
  - `#climate_mode4_controls` and `#climate_mode14_controls` handle single-storm inputs, including unitizer pairs for inch/mm conversions.
  - `#climate_mode13_controls` exposes breakpoint temperature overrides (`climate_daily_temp_ds`).
  - `#climate_spatialmode_controls` reappears mid-template with radios for Single, Multiple (PRISM revision), and Multiple Interpolated. The same IDs are duplicated inside `#climate_userdefined`, leading to redundant controls.
- **Advanced Options accordion**:
  - Toggle for `use_gridmet_wind_when_applicable`.
  - `precip_scaling_mode` radios (0–4) with dedicated sections for scalar, monthly, reference, and spatial scaling. Month-by-month inputs are verbose manual fields.
- **Build action** – `#btn_build_climate` triggers `Climate.build()` via the RQ API. Status hints (`#hint_*`) display textual feedback from JS.
- **Accessibility gaps** – Several tooltips rely on image icons with empty `alt` text, and hidden sections toggle purely via display changes without `aria-controls`.

## 2. Front-End Behaviour (`wepppy/weppcloud/controllers_js/climate.js`)
- **Singleton controller** – `Climate.getInstance()` wraps `controlBase` and maintains WebSocket wiring, RQ job polling, and status messaging.
- **Mode orchestration**:
  - `MODE_CONFIG` shows/hides section IDs and disables spatial mode 2 where unsupported. Because the template omits many referenced IDs, several toggles are no-ops today.
  - `setBuildMode` toggles upload vs CLIGEN panes and forces station mode 4 for uploads.
  - `setMode`, `setSpatialMode`, and `setStationMode` POST to `/tasks/set_climate_*` endpoints then immediately call their corresponding show/hide helpers.
- **Station fetching** – `refreshStationSelection` routes requests to `/view/closest_stations/`, `/view/heuristic_stations/`, `/view/eu_heuristic_stations/`, or `/view/au_heuristic_stations/` based on the currently selected mode. Without radios for modes 2/3, the EU/AU endpoints never receive traffic.
- **Uploads** – `upload_cli` builds a `FormData` submission to `/tasks/upload_cli/`. On success the controller fakes a “build complete” event to refresh the climate report without queuing an RQ job.
- **Build workflow** – `build()` serialises the entire form to `/rq/api/build_climate`, starts the WebSocket stream (`WSClient`) to follow job progress, and surfaces the resulting report once the RQ event fires.
- **Precip scaling** – `updatePrecipScalingControls` is the only place sections 1–4 are toggled; scalar/monthly/reference/spatial inputs remain visible unless this handler runs, so the new build should pre-collapse them by default.

## 3. Backend Mapping (`wepppy/nodb/core/climate.py`, `…/routes/nodb_api/climate_bp.py`, `…/routes/rq/api/api.py`)
- **State parsing** – `Climate.parse_inputs()` reads `climate_mode`, `climate_spatialmode`, `input_years`, observed/future years, single-storm specs, precipitation scaling settings, and the breakpoint dataset radio. Validation enforces `CLIMATE_MAX_YEARS`, start/end-year bounds, and file existence for DB-backed selections.
- **NoDb setters** – The controller exposes `nodb_setter` properties for station mode, mode, spatial mode, scaling options, and CLI/PRN filenames. Most UI inputs map one-to-one (e.g., `input_years`, `observed_start_year`, `precip_scale_factor`).
- **Build routing** – `/rq/api/build_climate` calls `parse_inputs` and, unless in batch mode, enqueues the `build_climate_rq` worker. The worker ultimately invokes `Climate.build()`, which dispatches on `ClimateMode` and `ClimateSpatialMode`.
- **Mode implementations** (selected highlights):
  - `Vanilla (0)` – runs CLIGEN for stochastic years; spatial mode “Multiple” triggers `_prism_revision` to clone and spatially adjust hillslope CLIs.
  - `PRISM (5)` – uses Cligen seed synchronisation, downloads PRISM rasters via `wmesque_retrieve`, and applies the same `_prism_revision` for hillslopes.
  - `Observed Daymet (9)` – calls `_build_climate_observed_daymet` (single) or `_observed_daymet_multiple` (hillslope PRN/CLI generation with optional GridMET wind fallback controlled by `use_gridmet_wind_when_applicable`).
  - `Observed GridMET (11)` – `_build_climate_observed_gridmet` or `_…_multiple` orchestrate NetCDF downloads, interpolation, and per-hillslope PRN generation with heavy multiprocessing.
  - `DEP Nexrad (13)` – downloads breakpoint `.cli` files from Iowa State, clips to requested years, and optionally overwrites temperature/wind fields using PRISM/GridMET/Daymet timeseries.
  - `Future CMIP5 (3)` – fetches downscaled climate via `build_future` (RCP scenarios).
  - `Single Storm` variants (4, 14) – call `cligen_client.selected_single_storm`, either once or batch-parsed from textarea rows.
  - `E-OBS (8)` / `AGDC (10)` – delegate to `_build_climate_mod` with `eobs_mod` or `agdc_mod`. Presentation for AGDC is currently absent in the template.
  - `Observed/Future DB (6/7)` – expect `climate_*_selection` fields pointing at curated `.cli` directories (`observed_clis_wc`, `future_clis_wc`); the template only surfaces the radio, not the selector.
- **Uploads** – `/tasks/upload_cli/` saves the file into `cli_dir` and calls `set_user_defined_cli()`, which sets `_orig_cli_fn`, computes monthlies, and (if necessary) flags `ClimateMode.UserDefinedSingleStorm`.
- **Station endpoints** – `/tasks/set_climatestation_mode`, `/tasks/set_climatestation`, `/view/*_stations/`, `/view/par/`, and `/view/climate_monthlies/` provide all data powering the station picker and preview.
- **Advanced toggles** – `/tasks/set_use_gridmet_wind_when_applicable` mutates the corresponding flag in NoDb for reuse across sessions.

## 4. Locale & Mode Inventory

| Locale flag(s) | Default mode on init | Modes exposed in template | Modes implemented but hidden | Notes / Dependencies |
| --- | --- | --- | --- | --- |
| none (US baseline) | `Undefined` (forces user to pick; defaults to Vanilla on first build) | 5 (PRISM), 0 (Vanilla), 9 (Observed Daymet), 11 (Observed GridMET), 13 (DEP Nexrad), 3 (Future), 6 (Observed DB), 7 (Future DB), 4/14 (Storms) | 2 (Observed legacy), 10 (AGDC), 12/15 (UserDefined) | Observed/Future DB radios appear but there is no UI to browse `.cli` libraries. |
| `eu` | `EOBS` (set in `__init__`) | 0 (Vanilla), 4/14 (Storms), 8 (E-OBS Modified) | 5, 9, 11, 13, 3, 6, 7 (explicitly suppressed), 10 | Station filter still shows “Multi-Factor Ranking” but EU heuristics mode (2) is unreachable. |
| `au` | `AGDC` (set in `__init__`) | 4/14 only (due to template guard) | 10 (AGDC), 0/5/9/11/13/3/6/7 | Current UI effectively blocks Australian datasets; the AGDC builder exists in backend but lacks UI exposure. |
| `alaska`, `hawaii`, `nigeria` | `Undefined` | 4/14 only (same branch as AU) | 0/5/9/11/13/3/6/7 | Need confirmation whether these locales should surface bespoke options; data is implemented but unreachable. |
| Any locale + `climate.mods` containing `rap_ts` | various | Adds advisory text reminding users to select historical datasets compatible with RAP (1986–2023) | – | No direct UI; mod-specific integration happens elsewhere. |

**Other discrepancies**
- `ClimateStationMode` values 2 (EU heuristics) and 3 (AU heuristics) have routes but no radio buttons.
- `MultipleInterpolated` spatial mode (value 2) is only valid for modes 9 and 11; JS disables it correctly, but the double rendering of `climate_spatialmode` makes intent unclear.
- DB-backed CLI selectors and AGDC/E-OBS metadata should be catalog entries with provenance, required products, and availability windows.

## 5. Routing & API Touchpoints

| Endpoint | Purpose | Invoked by |
| --- | --- | --- |
| `POST /runs/<runid>/<config>/tasks/set_climatestation_mode/` | Persist station filter (Closest, Heuristic, etc.) | JS `setStationMode` |
| `POST /runs/<runid>/<config>/tasks/set_climatestation/` | Store the selected station ID | JS `setStation` |
| `GET /runs/<runid>/<config>/view/closest_stations/` | Render `<option>` list via `CligenStationsManager.get_closest_stations` | JS `refreshStationSelection` (mode 0) |
| `GET /runs/<runid>/<config>/view/heuristic_stations/` | Multi-factor station ranking | JS `refreshStationSelection` (mode 1) |
| `GET /runs/<runid>/<config>/view/eu_heuristic_stations/` | EU-specific heuristic ranking | JS `refreshStationSelection` (mode 2; currently unreachable) |
| `GET /runs/<runid>/<config>/view/au_heuristic_stations/` | AU-specific heuristic ranking | JS `refreshStationSelection` (mode 3; unreachable) |
| `GET /runs/<runid>/<config>/view/par/` | Inline `.par` content for quick inspection | “View PAR” link |
| `GET /runs/<runid>/<config>/view/climate_monthlies/` | Render summary table for selected station | JS `viewStationMonthlies` |
| `POST /runs/<runid>/<config>/tasks/upload_cli/` | Upload and validate user-defined `.cli` | JS `upload_cli` |
| `POST /runs/<runid>/<config>/tasks/set_climate_mode/` | Persist radio selection → `Climate.climate_mode` | JS `setMode` |
| `POST /runs/<runid>/<config>/tasks/set_climate_spatialmode/` | Persist spatial mode | JS `setSpatialMode` |
| `POST /runs/<runid>/<config>/tasks/set_use_gridmet_wind_when_applicable/` | Toggle GridMET wind fallback | Advanced options checkbox |
| `POST /runs/<runid>/<config>/rq/api/build_climate` | Queue RQ job after parsing inputs | Build button |
| `GET /runs/<runid>/<config>/report/climate/` | Render HTML report after build/upload | JS `report` |


## 6. Pain Points & Modernisation Targets
- **Locale gating is brittle** – Hard-coded `ron.locales` checks hide entire feature sets (AGDC, Alaska/Hawaii/Nigeria data) while backend implementations exist. Stations modes 2/3 remain dead code.
- **Missing controls for DB-backed modes** – Radios for `Observed Climate Database` and `Future Climate Database` appear without any UI to browse or select `.cli` assets, making these modes unusable.
- **Template/JS drift** – MODE_CONFIG references non-existent sections (`#climate_mode5_controls`, etc.), spatial mode radios appear twice with shared IDs, and unchecked sections remain visible until JS runs.
- **Manual tooltips and duplicated markup** – Each radio embeds identical tooltip icons. Consolidating under macros (as done for landuse) will simplify localisation and theming.
- **Unit handling** – Single-storm inputs rely on `data-convert-*` attributes without visible labels or help text clarifying conversions. The Pure rewrite should surface unit toggles explicitly.
- **Uploads bypass job telemetry** – `upload_cli` short-circuits the build pipeline, meaning “User Defined” never emits progress events or timestamps in Redis. Consider normalising this flow so reports and telemetry behave consistently.
- **Advanced scaling UX** – Month-by-month scaling asks for 12 separate inputs; there is no validation feedback until the backend rejects values. A structured component (table or CSV) would improve usability and hook cleanly into a catalog.

## 7. Toward a Catalog-Driven, Locale-Aware Rewrite
To mirror the landuse catalog, climate datasets should be defined declaratively and rendered through Pure macros:
- **Catalog schema** (YAML/JSON/DB):
  - `id` → e.g., `vanilla_cligen`, `observed_daymet`.
  - `label`, `short_description`, `tooltip`.
  - `climate_mode` (enum value) and `default_spatial_mode`.
  - `supported_locales` (allow/deny lists, with fallbacks).
  - `year_range` metadata (`min_start`, `max_end`, `data_refresh_note`).
  - `requires` (e.g., `deps: ['prism_rasters']`, `requires_observed_clis: true`).
  - `form_sections` to render: `stochastic_years`, `observed_years`, `future_years`, `single_storm`, `precip_scaling`.
  - `station_modes` allowed (`closest`, `heuristic`, `eu`, `au`).
  - `telemetry` options (whether to stream `StatusMessenger` events, expected runtime).
  - `upload_support` (for user-defined flows).
  - `localization` blocks for copy/units.
- **Rendering strategy**:
  1. Load catalog, filter by locale/mod availability, and generate radio groups dynamically.
  2. Use component macros for shared sections (years, storms, scaling), ensuring they respect locale-specific defaults and unit preferences.
  3. Drive JS configuration from the same catalog (export JSON for controllers) so show/hide logic stays in sync with markup.
  4. Merge station mode radios into a capability-aware component that exposes EU/AU heuristics only when relevant.
  5. Integrate dataset metadata with run reports and Query Engine catalog entries (`update_catalog_entry(wd, 'climate')`) for observability.


## 8. Open Questions & Clarifications Needed
- **Australian stack** – Should AGDC be exposed via the main control or a dedicated flow? Confirm expected locale flags and whether additional datasets (e.g., AWAP) are planned.
- **Observed/Future DB libraries** – Determine how curated `.cli` collections are presented today (external wizard? config flag?) so we can design the missing selector UI.
- **Legacy modes** – Is `ClimateMode.Observed` (value 2) still required, or can it be retired once catalog work lands?
- **Station heuristics** – Confirm whether EU/AU station heuristics should remain separate modes or if unified metadata (elevation caps, bounding boxes) can replace them.
- **Telemetry expectations** – Should uploads (user-defined climates) emit the same Redis timestamps and WebSocket events as generated datasets? Aligning behaviour will simplify the Pure migration.

---

**Next Steps**
1. Finalise climate dataset catalog schema (mirroring landuse) and backfill metadata for each existing mode.
2. Prototype Pure macros for climate sections, ensuring they accept catalog-driven arguments and unitizer hooks.
3. Reconcile locale handling: replace direct `ron.locales` checks with catalog filters and provide per-locale fallback instructions.
4. Design file-selection UI for observed/future climate libraries and integrate with NoDb parsing (`climate_observed_selection`, `climate_future_selection`).
