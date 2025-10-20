# Climate Control Implementation Plan (Runs₀ → Pure Migration)

This document turns the deep-dive findings into a buildable roadmap. Every section references gaps and behaviours catalogued in `climate-ui-plan.md` and maps them to concrete tasks for the Pure rewrite.

---

## 1. Catalog & Locale Strategy

### 1.1 Proposed catalog schema
Create a structured dataset (JSON/YAML or DuckDB table) that mirrors the landuse catalog. Each entry represents a climate option.

| Field | Type | Purpose |
| --- | --- | --- |
| `id` | string | Stable key (`vanilla_cligen`, `observed_gridmet`, `agdc`, etc.). |
| `climate_mode` | int (matches `ClimateMode`) | Enables backend dispatch without hard-coded radio values. |
| `label` | string | Primary UI label. |
| `description` | string | Short helper text for tooltips/inline copy. |
| `locales` | struct {allow: [], deny: []} | Declarative locale gating instead of `ron.locales` checks. |
| `mods_required` | list[string] | Mods (e.g., `rap_ts`) that must be active. |
| `year_bounds` | struct {min_start, max_end, current_end, source_note} | Populate default ranges and validation messaging. |
| `spatial_modes` | list[int] | Supported spatial modes (`[0, 1, 2]`). Drives UI enablement. |
| `default_spatial_mode` | int | Preselect appropriate option (e.g., stochastic vs. interpolated). |
| `station_modes` | list[int] | Allowed `ClimateStationMode` values per locale (Expose EU/AU heuristics when present). |
| `inputs` | list[string] | Required UI sections (`stochastic_years`, `observed_years`, `future_years`, `single_storm`, `precip_scaling`, `upload`). |
| `dependencies` | list[string] | Signals backend prerequisites (`prism_rasters`, `gridmet_nc`, `observed_cli_catalog`). |
| `rap_compatible` | bool | Flags datasets that meet RAP timeseries requirements; used for warnings. |
| `upload_behaviour` | enum (`inline`, `catalog`, `external`) | Describes whether the mode relies on uploads or the curated libraries (`observed_db`, `future_db`). |
| `telemetry_profile` | struct {ws_channel, expected_duration, note} | Prepares StatusStream messaging. |
| `unitizer_config` | struct | Defines metric/imperial presentation for relevant inputs. |
| `metadata_links` | list[{label, url}] | Optional reference documentation per dataset. |

### 1.2 Data flow
1. **Server load**: A catalog service (Python module or DuckDB query) loads and filters entries using run-specific `ron.locales`, active mods, and available data directories (`observed_clis_wc`, etc.).
2. **Template context**: Pass the filtered list plus supporting lookups (station-mode map, section manifest, year defaults) into the Pure template.
3. **Frontend JSON**: Serialize the same data to the JS controller so show/hide logic, validation hints, and tooltips remain consistent.
4. **NoDb integration**: When `parse_inputs` runs, validate that the incoming mode/spatial mode combination exists in the catalog. Reject stale or disabled choices.

### 1.3 Locale alignment tasks
- Populate catalog entries for:
  - **US baseline**: `vanilla_cligen`, `prism_stochastic`, `observed_daymet`, `observed_gridmet`, `dep_nexrad`, `future_cmip5`, `single_storm`, `single_storm_batch`, `user_defined`. Keep `observed_db`/`future_db` definitions for parity, but mark `ui_exposed: false` (out of scope for this pass).
  - **EU**: `vanilla_cligen`, `eobs_modified`, `single_storm`, `single_storm_batch`.
  - **AU/Alaska/Hawaii/Nigeria**: single visible entry `vanilla_cligen` with metadata pointing at the GHCN station database. Retain `agdc` in the catalog for backend compatibility yet flag as `ui_exposed: false`.
- Encode EU/AU heuristics availability in `station_modes` so the Pure template can surface modes 2/3 when applicable.
- Mark RAP-compatible entries so the UI can warn when incompatible datasets are selected.
- Store the climate catalog alongside locale assets (`wepppy/nodb/locales/`) to reuse existing configuration loaders and keep region-specific metadata centralized.

### 1.4 Metadata & validation
- Derive `year_bounds` from controller constants (`daymet_last_available_year`, etc.) and keep them in sync via a single source of truth (utility method or config file).
- Store dependency checks (e.g., `observed_clis_wc` existence) in the catalog loader so UI never renders options that will fail later.
- Provide tooltip/help content centrally (per catalog entry). The Pure macros already accept a `help` attribute that renders accessible descriptive text; populate it directly and avoid bespoke icon-only tooltips.
- Observed/Future CLI browsing UIs remain out of scope. Catalog entries should include validation metadata but remain hidden until we design a dedicated picker.

---

## 2. UI Component Plan (Pure Template)

### 2.1 Shell & layout
- Replace `_base.htm` usage with `control_shell` macro (`docs/ui-docs/control-ui-styling/control-components.md`).
- Break the form into logical cards within `.wc-control__inputs`:
  1. Build mode & upload card.
  2. Station selection card.
  3. Climate dataset chooser (catalog-driven radio grid).
  4. Parameter panels (years, storms, scaling).
  5. Advanced options accordion.
  6. Build/telemetry footer.

### 2.2 Macro inventory
- `mode_selector` macro: renders radio groups from catalog, using the entry’s `help` text via the macro attribute for WCAG-compliant assistance, and appending dataset metadata pills and disabled states.
- `station_panel` macro: outputs station mode radios via catalog-driven map, optional help text, and the `<select>` dropdown. Should attach IDs consumed by JS (`data-station-panel`).
- `upload_panel` macro: handles file input + call-to-action button, with slot for hint text.
- `spatial_mode_selector` macro: single source for radio buttons (no duplicate markup); accepts allowed values and disables unsupported options.
- `year_range_panel` macro: re-usable for observed/future/stochastic inputs; optionally bound to unitizer.
- `single_storm_panel` macro: wrap existing unitizer inputs, ensure metric/imperial toggles use consistent Pure components.
- `scaling_panel` macro: convert month-by-month inputs into a structured grid or editable table; ensure sections collapse when inactive.
- `advanced_toggle` macro: for `use_gridmet_wind_when_applicable`, convert to Pure-styled switch with accessible labels.
- `status_panel_override`: integrate StatusStream macro variant to display build progress instead of manual `<small>` hints.

### 2.3 Section mapping
- **Build mode** – Replace `hide-readonly` block with `catalog`-driven toggles. When `user_defined` selected, `station_panel` automatically shifts to mode 4 (UserDefined) and disables other options.
- **Station selection** – Use `station_panel` macro to expose EU/AU heuristics when catalog says they apply; include instructions and fallback messages when data sets are missing.
- **Monthlies / report** – Keep placeholder container but convert to Pure markup (likely a `<section data-climate-monthlies>`). Apply unitizer after content injection.
- **Climate method radios** – Replace entire manual block with `mode_selector`.
- **Parameter containers** – Each `div` (years, observed/future, storm, scaling) becomes a macro slot. Only render macros for inputs flagged in the catalog entry.
- **Advanced options** – Wrap them in `details/summary` macros defined in control style guide; convert tooltip icons to standard help components.
- **Build controls** – Use `button_row` macro and integrate lock/status state via `StatusStream.attach`.

---

## 3. JS Refactor Strategy

### 3.1 Controller structure
- Move `climate.js` into `controllers_js/` Pure-era module pattern (ES module if bundler supports). The call to `controlBase()` stays but we add catalog awareness.
- Replace hard-coded `MODE_CONFIG`, `SECTION_IDS`, and `PRECIP_SECTIONS` with data derived from the catalog JSON passed from the template (`window.__CLIMATE_CATALOG__`).
- Normalize section toggling by targeting `data-section` attributes rather than explicit IDs.

### 3.2 Status & events
- Integrate new StatusStream control pipeline (per `control-components.md`). Replace direct `WSClient` wiring with `StatusStream.attach`, ensuring run events (`CLIMATE_BUILD_TASK_COMPLETED`) still trigger report refresh.
- Leave user-defined uploads synchronous. After a successful upload, show an inline toast/message and refresh the report instead of emitting StatusStream telemetry (processing is near-instant).

### 3.3 Locale-driven logic
- Use catalog-provided `station_modes` to decide which `/view/...` endpoint to call. Map mode integers to endpoint paths in a dictionary instead of chained `if/else`.
- Include fallback messaging when an endpoint returns empty (e.g., no stations available).

### 3.4 Form serialization & validation
- Build a payload generator that reads only visible / required inputs (driven by catalog `inputs`). Remove unused fields from submissions.
- Add client-side validation hints (range checks, required fields) based on catalog metadata before submitting to `/rq/api/build_climate`.
- Drop unused handlers (e.g., `pass()` blocks for station modes 4/-1) and remove references to missing sections (`#climate_mode5_controls`, etc.).

### 3.5 Fetch helpers
- Convert jQuery AJAX calls to fetch wrappers or ensure they work with CSRF requirements of the new stack.
- Consolidate repeated POST helpers (mode/spatial mode/station) into a generic `postTask` utility.

---

## 4. Backend Adjustments

### 4.1 Catalog integration
- Implement a loader (`wepppy/weppcloud/catalogs/climate.py` or similar) that:
  - Reads catalog entries.
  - Filters by run context (locales, mods, file availability).
  - Supplies both template context and controller JSON.
- Add `catalog_id` to `Climate` NoDb state so selections persist as stable identifiers even if ordering changes.
- Catalog metadata lives under `wepppy/nodb/locales/` with the other locale-driven configuration files.

### 4.2 Route updates (`nodb_api/climate_bp.py`)
- Simplify station endpoints to reference catalog state (e.g., infer default station mode per dataset rather than storing duplicates).
- Extend `/tasks/set_climate_mode/` to accept a catalog ID. Server resolves to `ClimateMode` and ensures the mode is enabled; legacy modes remain callable for existing `.nodb` payloads but will never be presented by the Pure UI catalog.
- Add endpoints for catalog-driven resources if required (e.g., fetch observed/future CLI manifests).
- Standardize success payloads to align with StatusStream conventions (include `event` keys for triggers).

### 4.3 `Climate` controller changes
- Introduce parsing helpers that validate incoming data against catalog definitions (spatial mode compatibility, required year fields, etc.).
- Keep legacy modes (`ClimateMode.Observed`, etc.) for backward compatibility, but mark them as non-exposed in the catalog so the Pure UI never links to them.
- Normalize user-defined uploads: ensure `set_user_defined_cli` sets `climate_mode` consistently and triggers Redis telemetry.
- Expose data needed by the catalog (e.g., derived year bounds) via properties instead of copying constants.

### 4.4 Telemetry alignment
- Update `RedisPrep` and trigger calls to ensure all pathways (including uploads) emit `TaskEnum.build_climate` timestamps.
- Verify report generation (`report/climate/`) works when new catalog IDs are in place.

---

## 5. Testing & Rollout

### 5.1 Automated tests
- **Unit tests**:
  - Catalog loader filtering (locale/mod combinations, dependency availability).
  - `Climate.parse_inputs` validation using catalog-driven fixtures.
  - Route handlers returning correct stations for each `station_mode`.
- **Integration tests**:
  - End-to-end build via `/rq/api/build_climate` for representative modes (Vanilla, Observed Daymet, DEP Nexrad). Backend coverage for `agdc` can remain in unit tests until the UI exposes it.
  - Upload workflow ensuring telemetry + report.
  - Regression comparison against the legacy layout (snapshot fixtures or golden HTML) to ensure endpoint parity after migrating the template.
- Update stubs `.pyi` files alongside code changes.

### 5.2 Manual QA
- Verify UI across locales (US, EU, AU, Alaska/Hawaii/Nigeria) in sandbox runs, confirming Vanilla-only behaviour with GHCN defaults for the non-US locales and broader catalog exposure elsewhere.
- Validate station selection heuristics return expected results (especially EU/AU).
- Test RAP scenarios to ensure warnings display when incompatible datasets are chosen.
- Confirm unitizer conversions in single-storm and scaling panels operate correctly.

### 5.3 Deployment strategy
- Replace the placeholder section with the Pure climate control in all runs₀ pages—no runtime toggle. Once merged, new deployments should always include the Pure climate UI.
- Stage catalog rollout in non-production environments first; back up existing `.nodb` files in case serialization needs migration.
- Coordinate with landuse Pure migration to reuse components/macros (avoid diverging design systems).

### 5.4 Dependencies & coordination
- **Unitizer** – ensure macros use the new unitizer hooks and JS re-applies conversions after AJAX pulls.
- **RAP Timeseries** – confirm dataset compatibility flags integrate with RAP mod warnings.
- **Station heuristics** – EU/AU algorithms rely on raster interpolators; confirm they are available in target environments.
- **Query Engine** – `update_catalog_entry(wd, 'climate')` should consume the new catalog metadata (potential schema update).

---

## 6. Open Questions & Assumptions

---

## Sequencing Summary
1. **Catalog foundation** – finalize schema, populate entries per locale, build loader.
2. **Backend validation** – wire catalog into `Climate` + `climate_bp` and add tests.
3. **Pure template + macros** – implement new layout using catalog data.
4. **JS rebuild** – refactor controller to consume catalog JSON, integrate StatusStream.
5. **Upload/telemetry normalization** – ensure all flows report through shared pipeline.
6. **Testing & rollout** – add automated coverage, QA across locales, and promote the Pure runs₀ template (climate included) through environments.
