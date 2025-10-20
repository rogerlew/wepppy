# Climate Control Architecture (Pure UI Stack)

This note captures the steady-state design of the climate control after the Pure migration. It focuses on runtime structure, data sources, and extension points so follow-up work can reference a single document without revisiting the migration plan.

## 1. Runtime Overview
- **Surface**: `wepppy/weppcloud/templates/controls/climate_pure.htm` rendered inside the runs₀ Pure layout. The legacy template remains isolated for classic pages until those are retired.
- **Controller**: `wepppy/weppcloud/controllers_js/climate.js` (catalog-driven, StatusStream-enabled). Instantiated automatically via DOM ready hook.
- **Backend**: `wepppy/nodb/core/climate.Climate` plus the climate catalog defined in `wepppy/nodb/locales/climate_catalog.py`. Routes live under `wepppy/weppcloud/routes/nodb_api/climate_bp.py`; run context wiring is in `routes/run_0/run_0_bp.py`.
- **State persistence**: As before, `Climate.parse_inputs` hydrates `.nodb` fields. The new field `catalog_id` keeps the selected dataset in sync with the catalog metadata.

## 2. Catalog Architecture
- Catalog entries (`ClimateDataset`) provide:
  - `catalog_id`, `climate_mode`, `allowed_locales`, `station_modes`, `spatial_modes`, `inputs`, `help_text`, `metadata` (e.g., year bounds).
  - `ui_exposed` flag toggles legacy/hidden datasets (e.g., Observed/Future DB, AGDC).
- Filtering logic (`available_climate_datasets`) considers locales and active mods. It always returns at least Vanilla CLIGEN as a fail-safe.
- Tests: `tests/nodb/test_climate_catalog.py` validates filtering plus catalog-aware `parse_inputs`.

## 3. Backend Integration
- `Climate.parse_inputs` now:
  - Resolves catalog IDs before applying other form data.
  - Validates spatial mode compatibility against the dataset descriptor.
  - Leaves old `climate_mode` fallbacks in place when no catalog ID is supplied (legacy template / API parity).
- New route `query/climate_catalog/` exposes catalog JSON for JS clients.
- Run context includes `climate_catalog=climate.catalog_datasets_payload(include_hidden=True)` so templates can render dataset choices even for hidden entries.

## 4. Pure Template Anatomy
- Renders dataset selector (`ui.radio_group`) backed by JSON from `<script id="climate_catalog_data">`.
- Sections are tagged with `data-climate-section` (e.g., `stochastic_years`, `observed_years`, `upload`). The controller toggles them based on `dataset.inputs`.
- Advanced options use standard Pure macros (`ui.collapsible_card`, `ui.checkbox_field`, etc.) so the control matches new design language.
- Hidden inputs `climate_catalog_id` and `climate_mode` keep form submissions compatible with existing endpoints.
- Status panel is a macro instance that pairs with StatusStream (log limit 400 by default).

## 5. JavaScript Controller Highlights
- Catalog bootstrap:
  - Parses JSON seed, builds `datasetMap`, default-selects the current catalog ID (or first exposed dataset).
  - `applyDataset` updates dataset message, toggles sections, enforces allowed station/spatial modes, and refreshes station list unless dataset is upload-only.
- Status telemetry:
  - `attachStatusStream()` binds to the climate status panel, listening on the `climate` channel.
  - Builds append messages using `appendStatus` helper.
  - Lightweight uploads skip RQ queues but still log success in the panel.
- Compatibility shims: legacy inline handlers (`handleBuildModeChange`, `showHideControls`, etc.) are intentionally removed; once the legacy template goes away we will delete the shims. Until then only the Pure page should use the new controller.
- Unitizer integration: no bespoke logic; the template uses standard macros and existing Unitizer hooks.

## 6. Legacy Interface Notes
- Classic template (`controls/climate.htm`) is still rendered on historic pages. It includes inline `onchange` handlers that no longer exist. Those pages remain in maintenance mode and are not expected to run after the Pure rollout. When removing the legacy page, drop the template and handler references, then clean up any unused JS.
- Until the legacy page is removed, avoid wiring the new controller there to prevent runtime errors.

## 7. Testing & QA
- **Automated**: `tests/nodb/test_climate_catalog.py` (runs with `wctl run-pytest`). Additional UI-level tests can be added via Cypress or Selenium if desired.
- **Manual**:
  1. Toggle between datasets and confirm sections show/hide accordingly.
  2. Switch station modes (Closest ↔ Heuristic) and ensure the select updates without errors.
  3. Submit builds for Vanilla, PRISM, and a gridded observed dataset; verify StatusStream logs progress and reports success.
  4. Upload a `.cli` file and ensure the success message appears without queue interaction.
  5. Check RAP warnings under datasets flagged as `rap_compatible=False`.
  6. Confirm run bootstrap (`run_page_bootstrap.js.j2`) no longer calls removed handlers and the climate control initialises cleanly.

## 8. Extension Points
- Adding a new dataset:
  - Add a `ClimateDataset` entry (populate `inputs`, `help_text`, locale constraints).
  - Update `Climate.parse_inputs` only if the dataset requires new form elements.
  - Extend the template with a corresponding `data-climate-section` block if needed.
- Telemetry tweaks: adjust the StatusStream log limit or formatter via `StatusStream.attach` options in the controller.
- Future conversion: once the legacy page is retired, remove compatibility scaffolding (`hidden` fallback code, `handlePrecipScalingModeChange()` bootstrap wiring, dormant routes).
