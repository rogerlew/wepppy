# Climate Controller Migration Plan
> Status: Completed (helper-first controller migration). See [controllers_js Modernization Retrospective](../../../../dev-notes/controllers_js_jquery_retro.md).

> Tracking helper-driven modernization work for `wepppy/weppcloud/controllers_js/climate.js`.

## 1. Current Status
- **Controller**: `climate.js` now depends exclusively on `WCDom`, `WCForms`, `WCHttp`, and `WCEvents`. Singleton wiring auto-initialises on `DOMContentLoaded`, and all DOM listeners run through delegated `data-climate-action` hooks.
- **Templates**: `wepppy/weppcloud/templates/controls/climate_pure.htm` and `climate.htm` expose `data-climate-action`, `data-climate-section`, and `data-precip-section` attributes. Inline `on*` handlers have been removed; hidden inputs (`data-climate-field`) keep catalog/mode state in sync with the backend.
- **Backend**: `wepppy/weppcloud/routes/nodb_api/climate_bp.py` and `routes/rq/api/api.py::api_build_climate` use `parse_request_payload` so JSON bodies and legacy form submissions share the same parsing logic. `Climate.parse_inputs` operates on native ints/floats/bools.
- **Status/Telemetry**: The controller attaches `StatusStream` to `#climate_status_panel` and forwards legacy `CLIMATE_*` status messages into a scoped emitter so downstream modules can subscribe without scraping DOM.

## 2. Event Map (`Climate.events`)
`WCEvents.useEventMap` guards the following names:

| Event name | Description |
|------------|-------------|
| `climate:dataset:changed` | Dataset radio toggled; payload includes `catalogId` + dataset descriptor |
| `climate:dataset:mode` | Climate mode derived from the selected catalog |
| `climate:station:mode` | Station strategy changed (Closest/Heuristic/etc.) |
| `climate:station:selected` | User chose a station from the select element |
| `climate:station:list:loading` / `climate:station:list:loaded` | Async refresh for station `<option>` markup |
| `climate:build:started` / `climate:build:completed` / `climate:build:failed` | Lifecycle for `/rq/api/build_climate` submissions |
| `climate:precip:mode` | Post-CLIGEN scaling mode changed (No scaling, Monthly, etc.) |
| `climate:upload:completed` / `climate:upload:failed` | `/tasks/upload_cli/` outcomes |
| `climate:gridmet:updated` | Advanced checkbox toggled `use_gridmet_wind_when_applicable` |

Subscribe via `Climate.getInstance().events.on(...)` instead of reading private controller state.

## 3. Payload & Route Contracts
- **`tasks/set_climate_mode/`**: JSON `{mode: int, catalog_id?: str}`. Route persists mode and resolved catalog id; missing catalog id leaves existing value unchanged.
- **`tasks/set_climatestation_mode/`**: JSON `{mode: int}` (0–4). Acknowledges silently if the controller is already in the requested state.
- **`tasks/set_climatestation/`**: JSON `{station: str}`; returns `Success` when the selection is persisted.
- **`tasks/set_climate_spatialmode/`**: JSON `{spatialmode: int}`.
- **`tasks/set_use_gridmet_wind_when_applicable/`**: JSON `{state: bool}`; toggles the advanced option.
- **`rq/api/build_climate`**: JSON mirror of the form produced by `WCForms.serializeForm(form, { format: "json" })`. Includes catalog metadata, spatial mode, precipitation scaling parameters, and single-storm settings. Parsed by `Climate.parse_inputs`.
- **`tasks/upload_cli/`**: `FormData` with `input_upload_cli`. Controller emits `climate:upload:*` events; backend continues to save payloads via `save_run_file`.
- **Station lookups** (`view/closest_stations/`, `view/heuristic_stations/`, `view/eu_heuristic_stations/`, `view/au_heuristic_stations/`): controller expects raw `<option>` HTML and triggers `climate:station:list:*` events after updates.
- **Reports**: `report/climate/` and `view/climate_monthlies/` return HTML fragments consumed via `WCHttp.request`.

## 4. Template & Helper Contract
- Required DOM elements: `#climate_form`, `#info`, `#status`, `#stacktrace`, `#rq_job`, `#climate_status_panel`, `#climate_stacktrace_panel`, `#climate_dataset_message`, `#climate_station_selection`, `#climate_monthlies`, `#btn_build_climate`, `#btn_upload_cli`, and the dataset JSON script tag.
- Section toggles rely on `[data-climate-section]` and `[data-precip-section]`. Ensure new inputs are wrapped accordingly so the controller can hide/show panels by dataset.
- Buttons/radios/selects must carry `data-climate-action` values: `dataset`, `station-mode`, `station-select`, `spatial-mode`, `mode`, `precip-mode`, `gridmet-wind`, `build-mode`, `upload-cli`, `build`.
- Status handling requires the standard `controlBase` IDs plus `[data-status-panel]`/`[data-status-log]` markup for `StatusStream`.

## 5. Testing & Tooling
- **Jest**: `wctl run-npm test -- controllers_js/__tests__/climate.test.js` (jsdom). Suite exercises dataset changes, station-mode refresh, precipitation toggles, RQ job submission, upload handling, gridmet toggles, and station selection.
- **Pytest**: `wctl run-pytest tests/weppcloud/routes/test_climate_bp.py` covers JSON payload parsing for the Flask routes and file-upload behavior.
- **Bundle**: `python wepppy/weppcloud/controllers_js/build_controllers_js.py` must be run (or the dev container restarted) so the UI serves the updated controller.
- **Lint**: `wctl run-npm lint` keeps helper usage consistent across controllers.

## 6. Follow-ups / Watch list
- Legacy console template (`controls/climate.htm`) remains in maintenance mode; schedule deletion once all deployments use the Pure UI.
- Monitor references to `climate:station:list:*` events—downstream consumers may need documentation updates as they migrate away from DOM scraping.
- Future migrations (e.g., adding RAP-specific datasets) should extend this document with new payload fields or event names before landing in `main`.
