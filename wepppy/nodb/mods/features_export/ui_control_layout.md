# Features Export Runs-Page UI Control Layout

Status: Spec-only  
Audience: template, controller, and test implementers for `wepppy/nodb/mods/features_export`

## Grounding

- Use the existing Runs-page control shell: `ui.control_shell(...)`, `button_row`, `data-status-panel`, `data-stacktrace-panel`, and `data-job-hint`.
- Follow the WEPPcloud controller contract: singleton bootstrap, idempotent re-hydration, `controlBase.attach_status_stream`, `set_rq_job_id`, `WCControllerBootstrap.resolveJobId`, delegated events only.
- Borrow GL dashboard discoverability ideas, not its layout implementation: grouped taxonomy, section counts, search/filter-first discovery, and small capability badges on each selectable item.
- Do not introduce a new widget framework, tokenized multiselect dependency, or modal wizard. This stays a normal Runs-page control.

## 1. Control Goals

- Make export layer discovery fast even when the catalog grows.
- Keep required selectors obvious without showing SWAT, Omni, scope, and temporal controls all at once.
- Preserve WEPPcloud async expectations: visible status log, visible stacktrace panel, visible job hint, poll fallback, and stable DOM hooks for tests.
- Make partial success legible. This control must surface warnings as a first-class success state, not only as a backend detail.

## 2. Layout Overview

### 2.1 Desktop ASCII Wireframe

```text
+------------------------------------------------------------------------------------------------------------------+
| Features Export                                                                                                 |
| Export run-scoped spatial and tabular artifacts across WEPP, Omni, Ash/WATAR, SWAT, and AgFields.             |
+---------------------------------------------------------------+--------------------------------------------------+
| A. Run Settings                                               | E. Selected Summary                             |
| [Load Defaults] (gpkg-adjacent profile)                       | Selected: 3 layers                              |
| [Format radios/select] [Units radios] [CRS radios]            | Families: WEPP Summary (1), Watershed (2)       |
| Packaging hint: "1 container" / "zip of 3 files"              | Scope-aware: 1   Temporal-capable: 1            |
|                                                               |                                                  |
+---------------------------------------------------------------+--------------------------------------------------+
| B. Layer Catalog                                              | F. Conditional Options                           |
| [Search layers.........................] [All][Selected]      | [Output scopes] baseline [x] roads [ ]          |
| [Temporal][Scope-aware][Needs selector] [Clear filters]       | Hint: scope-invariant layers export once shared |
| [Select visible] [Clear selected]                             |                                                  |
|                                                               | [Temporal] mode: ( ) annual avg ( ) yearly      |
| v Watershed (2 / 2)                                           |             ( ) event                           |
|   [x] Subcatchments    [polygon] [shared] [non-temporal]      |   if yearly: year selection...                  |
|   [x] Channels         [line]    [shared] [annual/yearly]     |   if event: selector=date|return period         |
| v WEPP Summary (1 / 2)                                        |                                                  |
|   [x] Hillslopes       [polygon] [scope-aware] [ann/yr/event] | [Omni] appears only for Omni families           |
|   [ ] Channels         [line]    [scope-aware] [ann/yr]       | [SWAT] appears only for SWAT tables             |
| > WEPP Interchange (0 / 3)                                    |                                                  |
| > Ash / WATAR (0 / 1)                                         +--------------------------------------------------+
| > Omni Scenarios (0 / 1)                                      | G. Actions                                       |
| > Omni Contrasts (0 / 1)                                      | [Export Features] [Clear selection]             |
| > SWAT Interchange (0 / n)                                    | Job hint: rq dashboard link only                |
| > AgFields Spatial (0 / 2)                                    +--------------------------------------------------+
| > AgFields Metrics (0 / 2)                                    | H. Results / Warnings                            |
|                                                               | State badge: idle | running | success | partial |
| Layer row details toggle shows columns (with units + include toggles), measures, selectors, and notes | Download artifact                               |
| such as "needs Omni scenario", "AgFields auto-prep", or       | Cache-hit/source job note                       |
| "geojson/kmz skips non-spatial SWAT tables".                  | Warning list                                    |
+---------------------------------------------------------------+--------------------------------------------------+
| I. Status Panel                                                                                                 |
| Status summary text (separate from job hint), spinner, live log                                                  |
+------------------------------------------------------------------------------------------------------------------+
| J. Stacktrace Panel (collapsed until failure; opens automatically on error)                                      |
+------------------------------------------------------------------------------------------------------------------+
```

### 2.2 Mobile ASCII Wireframe

```text
+---------------------------------------------------------------+
| Features Export                                               |
| Export run-scoped spatial and tabular artifacts               |
+---------------------------------------------------------------+
| A. Run Settings                                               |
| [Load Defaults]                                               |
| Format                                                        |
| Units                                                         |
| CRS                                                           |
| Packaging hint                                                |
+---------------------------------------------------------------+
| B. Selected Summary                                           |
| 3 layers selected                                             |
| Scope-aware: 1   Temporal-capable: 1                          |
| [Clear selection]                                             |
+---------------------------------------------------------------+
| C. Layer Catalog                                              |
| [Search............................]                          |
| [All][Selected][Temporal][Needs selector]                     |
| [Select visible] [Clear filters]                              |
| v Watershed                                                   |
| v WEPP Summary                                                |
| > WEPP Interchange                                            |
| > Ash / WATAR                                                 |
| > Omni Scenarios                                              |
| > Omni Contrasts                                              |
| > SWAT Interchange                                            |
| > AgFields                                                    |
+---------------------------------------------------------------+
| D. Conditional Options                                        |
| Output scopes (when needed)                                   |
| Temporal (when needed)                                        |
| Omni selector (when needed)                                   |
| SWAT run/table filters (when needed)                          |
+---------------------------------------------------------------+
| E. Actions                                                    |
| [Export Features] [Clear selection]                           |
| Job hint link                                                 |
+---------------------------------------------------------------+
| F. Results / Warnings                                         |
+---------------------------------------------------------------+
| G. Status Panel                                               |
+---------------------------------------------------------------+
| H. Stacktrace Panel                                           |
+---------------------------------------------------------------+
```

## 3. Control Groups And Progressive Disclosure

| Group | Purpose | Default State | Disclosure Rule |
| --- | --- | --- | --- |
| Run Settings | Choose `format`, `units`, and `crs`; show packaging hint. | Always visible. | Never hidden. |
| Defaults Action | Apply the gpkg-adjacent default profile in one click. | Always visible in Run Settings. | Never hidden. Updates controls and layer selections but never auto-submits. |
| Selected Summary | Show selected count, family counts, scope/temporal capability counts, and current validation status. | Always visible. | Never hidden. |
| Layer Catalog | Searchable grouped list of layer families from the catalog. | Always visible. | Family sections use `<details>`; keep the first two families open by default on desktop, first family only on mobile. |
| Output Scopes | Choose `baseline` and optional `roads` for scope-aware WEPP layers. | Hidden. | Show when at least one selected layer has `scope_class=scope_aware`. If all selected layers are scope-invariant, keep the card hidden and show a read-only note in Selected Summary. |
| Temporal | Choose export temporal mode and subordinate selectors. | Hidden. | Show when at least one selected layer supports one or more temporal modes. Keep expanded while invalid. |
| Temporal Year Options | Choose `all`, `exclude_first`, `exclude_first_two`, `exclude_first_five`, or `custom`. | Hidden inside Temporal. | Show only when Temporal mode is `annual_average` or `yearly` and at least one selected layer supports year selection. |
| Temporal Event Selector | Choose event-by-date or event-by-return-period. | Hidden inside Temporal. | Show only when Temporal mode is `event`. |
| Dataset Columns | Expand a selected dataset row and choose columns to include/exclude using unit-aware checkboxes. | Collapsed per row. | Show in row details when a dataset is selected; keep collapsed by default. |
| Omni Selector | Choose scenario or contrast instance. | Hidden. | Show when any selected layer belongs to `omni_scenarios` or `omni_contrasts`. The card title changes to `Omni Scenario` or `Omni Contrast`; both modes cannot be shown at once. |
| SWAT Options | Choose SWAT run and optional include/exclude table filter. | Hidden. | Show when `swat.interchange.table` is selected. |
| Results / Warnings | Show final artifact link, cache-hit note, warning list, and manifest-related details. | Visible but empty. | Populate after successful `jobinfo.result`; badge becomes `partial` when warnings are non-empty. |
| Status Panel | Live job progress and short human-readable status text. | Always visible. | Never hidden. |
| Stacktrace Panel | Synchronous validation failures and async job failures. | Hidden or collapsed. | Open automatically when stacktrace text exists. |

### Family Order

The catalog should render in this stable order unless the server explicitly overrides labels:

1. Watershed
2. Landuse
3. Soils
4. WEPP Summary
5. WEPP Temporal
6. WEPP Interchange
7. Ash / WATAR
8. Omni Scenarios
9. Omni Contrasts
10. SWAT Interchange
11. AgFields Spatial
12. AgFields Metrics

### Layer Row Content

Each layer row should expose the following scan-friendly elements without requiring expansion:

- Checkbox
- Human label
- `layer_id` in muted monospace
- Geometry badge: `polygon`, `line`, or `table`
- Scope badge: `shared` or `scope-aware`
- Temporal badge: `none`, `annual/yearly`, `event`, or `annual/yearly/event`
- Selector badge when required: `Omni scenario`, `Omni contrast`, `SWAT`, `AgFields auto-prep`

Row details disclosure requirements:

- Each dataset row must provide an expandable `Columns` block.
- The columns block must list columns with:
  - Include checkbox
  - Human label + canonical `column_id`
  - Source-backed description text when available
  - Unit chip/text (`mm`, `kg/m2`, etc.) or `non-unitized`
  - Required-lock indicator for mandatory identity/join columns
- If catalog metadata omits explicit column definitions for a dataset, the UI uses runtime source-schema discovery to populate columns and units.
- Metadata precedence for rendered column rows is: parquet field metadata (`label`, `description`, `units`) -> interchange `README.md` docs for the resolved source file -> deterministic fallback label/unit inference.
- Required identity/join locks should be canonicalized by token so alias-equivalent keys (for example `topaz_id` and `TopazID`) do not appear as duplicate mandatory rows.
- Include/exclude interactions should be selectable without opening a separate modal.
- The row details disclosure may also show measure notes, optional-measure warning behavior, and format caveats.

This preserves scan-first behavior while allowing precise per-dataset field control.

## 4. Control-State Matrix

| State | CTA State | Status Panel | Results Panel | Stacktrace | Notes |
| --- | --- | --- | --- | --- | --- |
| Idle | Disabled until minimum valid payload exists. | `Waiting for export selection.` | Empty placeholder. | Hidden. | No layers selected or required conditional inputs missing. |
| Ready | Enabled. | Shows packaging and selector hint text only. | Empty placeholder. | Hidden. | Valid payload assembled client-side. |
| Running | Disabled. | Live log connected; summary text updates; spinner visible. | Previous result content cleared. | Hidden unless sync error occurs before queue. | Job hint shows dashboard link once `job_id` exists. |
| Success | Enabled. | Final status summary, no error styling. | Download enabled; warnings section empty; cache-hit note optional. | Hidden. | `job:completed` fired. |
| Partial Success | Enabled. | Final status summary plus warning count. | Download enabled; warnings list populated; state badge `partial`. | Hidden. | Use this for dropped layers, skipped SWAT tables, selector defaults, or measure warnings. |
| Error | Enabled. | Final status summary in error styling. | Download disabled; keep last good artifact hidden or clearly stale. | Open with stacktrace text. | `job:error` fired; focus handling moves to first relevant error surface. |

## 5. Template Structure And DOM Contract

### 5.1 Shell Contract

Use `ui.control_shell(...)` with:

- `form_id="features_export_form"`
- `title="Features Export"`
- `collapsible=True`
- `status_panel_options={"id": "features_export_status_panel"}`
- `stacktrace_panel_options={"panel_id": "features_export_stacktrace_panel", "body_id": "features_export_stacktrace"}`
- `summary_panel_override` set to a custom results/selection panel rather than a generic summary placeholder

### 5.2 Required Template Skeleton

```html
<form id="features_export_form" data-features-export-root>
  <div
    data-features-export-config
    data-features-export-job-key="run_features_export"
    data-features-export-channel="features_export"
    data-features-export-submit-url="{{ url_for_run('export-features', prefix='/rq-engine/api') }}"
    data-features-export-download-url-template="{{ url_for_run('download-features-export', job_id='__JOB_ID__', prefix='/rq-engine/api') }}"
    data-features-export-utm-available="{{ 'true' if resolved_utm_epsg else 'false' }}"
    data-features-export-default-format="geopackage"
    data-features-export-default-units="project"
    data-features-export-default-crs="wgs"
    data-features-export-default-profile-key="gpkg_adjacent"
    hidden></div>

  <script type="application/json" id="features_export_catalog_data" data-features-export-catalog>...</script>
  <script type="application/json" id="features_export_bootstrap_data" data-features-export-bootstrap>...</script>

  <section data-features-export-group="settings">
    <button type="button"
      data-features-export-action="load-defaults"
      class="btn btn-secondary">
      Load Defaults
    </button>
    ...
  </section>
  <section data-features-export-group="summary">...</section>
  <section data-features-export-group="catalog">...</section>
  <section data-features-export-group="scopes" hidden>...</section>
  <section data-features-export-group="temporal" hidden>...</section>
  <section data-features-export-group="omni" hidden>...</section>
  <section data-features-export-group="swat" hidden>...</section>
  <section data-features-export-group="actions">
    <button type="submit" id="btn_run_features_export" data-features-export-action="submit">Export Features</button>
    <button type="button" data-features-export-action="clear-selection">Clear selection</button>
  </section>

  <aside id="features_export_results_panel" data-features-export-results>
    <p id="features_export_result_state" data-features-export-region="result-state"></p>
    <div data-features-export-region="download"></div>
    <div data-features-export-region="artifact-meta"></div>
    <ul data-features-export-region="warnings"></ul>
  </aside>

  <section id="features_export_status_panel" data-status-panel aria-live="polite">
    <p id="features_export_message" data-features-export-region="message"></p>
    <div id="features_export_status_log" data-status-log role="log"></div>
  </section>

  <details id="features_export_stacktrace_panel" data-stacktrace-panel hidden>
    <summary>Stack trace</summary>
    <pre id="features_export_stacktrace" data-stacktrace-body></pre>
  </details>

  <p id="hint_run_features_export" data-job-hint class="wc-job-hint wc-text-muted"></p>
</form>
```

### 5.3 `data-*` Hook Map

| Selector / Hook | Purpose | Notes |
| --- | --- | --- |
| `form#features_export_form` | Controller root and event target. | Required stable selector for bootstrap and smoke tests. |
| `[data-features-export-config]` | Hidden run-scoped config node. | Required per WEPPcloud front-end bundle guidance; do not rely on global variables alone. |
| `[data-features-export-catalog]` | JSON payload derived from `layer_catalog.yaml`. | Controller reads this instead of hardcoded layer maps. |
| `[data-features-export-bootstrap]` | JSON for dynamic runtime choices. | Includes available Omni scenarios/contrasts, SWAT runs/tables, pre-resolved labels, and optional persisted view state. |
| `[data-features-export-group="settings"]` | Format/units/CRS group. | Always mounted. |
| `[data-features-export-group="catalog"]` | Search, quick filters, and family list. | Main discoverability region. |
| `[data-features-export-group="scopes"]` | Output scope card. | Hide with `hidden` when not relevant. |
| `[data-features-export-group="temporal"]` | Temporal card. | Hide with `hidden` when not relevant. |
| `[data-features-export-group="omni"]` | Omni selector card. | Mutually exclusive scenario/contrast modes. |
| `[data-features-export-group="swat"]` | SWAT selector card. | Includes run select plus table filter mode and table list. |
| `[data-features-export-field="format"]` | Canonical export format input. | Emit `geodatabase`, never `f_esri`. |
| `[data-features-export-field="units"]` | Units input. | `project`, `si`, or `english`. |
| `[data-features-export-field="crs"]` | CRS input. | `wgs` or `utm`. |
| `[data-features-export-field="layer-search"]` | Layer search input. | Filters by label, `layer_id`, family, and measure aliases present in catalog metadata. |
| `[data-features-export-filter]` | Quick filter buttons. | `all`, `selected`, `temporal`, `scope-aware`, `needs-selector`. |
| `[data-features-export-family]` | Per-family `<details>` root. | Includes count badge and empty-state line. |
| `[data-features-export-layer]` | Repeated layer row root. | Carries `data-layer-id`, `data-family`, `data-scope-class`, and serialized capability tokens. |
| `[data-features-export-layer-columns]` | Expandable columns container for one dataset row. | Rendered from catalog column metadata + current selection state. |
| `[data-features-export-column]` | One selectable column row. | Carries `data-layer-id`, `data-column-id`, and optional required flag. |
| `[data-features-export-action="toggle-layer"]` | Layer checkbox target. | Delegated change handler only. |
| `[data-features-export-action="toggle-layer-columns"]` | Expand/collapse one dataset's columns section. | Delegated click handler only. |
| `[data-features-export-action="toggle-column"]` | Include/exclude one column for one dataset. | Delegated change handler only. |
| `[data-features-export-action="load-defaults"]` | Apply gpkg-adjacent defaults profile. | Resets key selectors/selections to profile values; never auto-submits. |
| `[data-features-export-action="select-visible"]` | Bulk-select filtered rows. | Secondary action. |
| `[data-features-export-action="clear-selection"]` | Clear all selected layers. | Secondary action and reset helper. |
| `[data-features-export-action="submit"]` | Primary export button. | Suggested id: `#btn_run_features_export`. |
| `[data-features-export-action="download"]` | Artifact download button/link. | Disabled or hidden until `jobinfo.result.download_url` exists. |
| `[data-features-export-action="download-manifest"]` | Optional manifest link/button. | Only render when the backend exposes a safe manifest URL or template. |
| `[data-status-panel]` | Status stream root. | Required. |
| `[data-status-log]` | Status stream log body. | Required. |
| `[data-stacktrace-panel]` | Stacktrace container. | Required. |
| `[data-stacktrace-body]` | Stacktrace text body. | Required. |
| `[data-job-hint]` | Job dashboard link region. | Reserved for the job link only; never use for human status text. |
| `[data-features-export-region="message"]` | Human-readable status summary. | Separate from job hint. |
| `[data-features-export-region="warnings"]` | Warning list. | Used for partial success. |
| `[data-features-export-region="download"]` | Download CTA slot. | Populated from `jobinfo.result.download_url`. |

### 5.4 Status, Stacktrace, And Job-Hint Regions

- Status summary text lives in `#features_export_message`.
- Status log lives in `#features_export_status_log`.
- Job hint lives in `#hint_run_features_export` and should only show the RQ dashboard link emitted by `set_rq_job_id`.
- Stacktrace text lives in `#features_export_stacktrace` inside `#features_export_stacktrace_panel`.
- Results and warnings live outside the status panel so logs do not overwrite final artifact information.

## 6. Controller Lifecycle And Event Contract

### 6.1 Lifecycle

1. `FeaturesExport.getInstance()` returns a singleton and never requires `new`.
2. `bootstrap(context)` re-queries `#features_export_form`, status/stacktrace/job-hint nodes, config node, and JSON script nodes.
3. `bootstrap(context)` attaches delegated listeners once, or re-attaches if the control was injected later by the Mods menu.
4. `bootstrap(context)` parses catalog/bootstrap JSON, renders the family list, restores family open state, and computes progressive-disclosure visibility.
   - During render, each selected layer gets an expandable columns list sourced from catalog `columns` metadata.
5. `bootstrap(context)` resolves the last job id in this order:
   - `WCControllerBootstrap.resolveJobId(ctx, "run_features_export")`
   - `controllerContext.job_id`
   - `ctx.jobIds.run_features_export`
6. If a prior job id exists, the controller sets `poll_completion_event = "FEATURES_EXPORT_TASK_COMPLETED"` and calls `set_rq_job_id(controller, jobId)` immediately.
7. The controller calls `attach_status_stream` with the `features_export` channel and keeps polling fallback enabled. Completion logic must be idempotent because both paths may fire.
8. On submit, the controller clears old result/warning/stacktrace content, preserves any existing hint until the new `job_id` arrives, posts JSON only, then stores the returned `job_id` via `set_rq_job_id`.
9. On terminal success, the controller fetches `jobinfo`, renders artifact/warning results, and re-enables the primary action.
10. On failure, `controlBase` surfaces jobinfo stacktrace enrichment automatically; the controller adds domain error state and leaves the stacktrace panel open.

Column selection payload contract:

- Controller serializes per-layer column decisions into request `column_selection`.
- Default state honors catalog `default_selected` values.
- Required columns are always sent as selected and cannot be deselected client-side.

### 6.2 Event Surface

The controller should expose:

```javascript
FeaturesExport.getInstance().events = WCEvents.useEventMap([
  "features_export:catalog:loaded",
  "features_export:selection:changed",
  "features_export:validation:changed",
  "features_export:defaults:loaded",
  "features_export:scope:changed",
  "features_export:temporal:changed",
  "features_export:omni:changed",
  "features_export:swat:changed",
  "features_export:submit:started",
  "features_export:submit:queued",
  "features_export:jobinfo:loaded",
  "features_export:completed",
  "features_export:error",
  "job:started",
  "job:completed",
  "job:error"
]);
```

### 6.3 Event Contract

| Event | Emitter | When | Minimum Payload |
| --- | --- | --- | --- |
| `features_export:catalog:loaded` | `controller.events.emit` | Catalog JSON parsed and initial family UI rendered. | `{ families, layerCount }` |
| `features_export:selection:changed` | `controller.events.emit` | Selected layers or search-filtered visibility changes. | `{ selectedLayerIds, counts, visibleLayerIds }` |
| `features_export:validation:changed` | `controller.events.emit` | Client validity changes after any relevant input change. | `{ valid, errors, warnings }` |
| `features_export:defaults:loaded` | `controller.events.emit` | User clicks `Load Defaults` and the defaults profile is applied. | `{ profileKey, selectedLayerIds, changedFields, skippedLayerIds }` |
| `features_export:scope:changed` | `controller.events.emit` | Scope choices change. | `{ output_scopes }` |
| `features_export:temporal:changed` | `controller.events.emit` | Temporal mode or subordinate fields change. | `{ temporal, compatibleLayerIds, excludedLayerIds }` |
| `features_export:omni:changed` | `controller.events.emit` | Scenario or contrast selector changes. | `{ mode, scenario, contrast_id }` |
| `features_export:swat:changed` | `controller.events.emit` | SWAT run or table filters change. | `{ swat_run_id, swat_tables }` |
| `features_export:submit:started` | `controller.events.emit` and `triggerEvent("job:started", ...)` | User submits a valid export request. | `{ payload, task: "features_export:submit" }` |
| `features_export:submit:queued` | `controller.events.emit` | Submit returns `job_id`. | `{ payload, job_id, status: "queued" }` |
| `FEATURES_EXPORT_TASK_COMPLETED` | DOM `CustomEvent` via `poll_completion_event` and/or StatusStream trigger | The RQ job reaches success. | `{ job_id, status, source }` |
| `job:completed` | `controlBase.triggerEvent` | Polling path reaches `finished`. | `{ job_id, status, source }` |
| `features_export:jobinfo:loaded` | `controller.events.emit` | `jobinfo` result fetched and parsed. | `{ job_id, result }` |
| `features_export:completed` | `controller.events.emit` | Results panel fully rendered. | `{ job_id, result, warnings }` |
| `job:error` | `controlBase.triggerEvent` | Polling path reaches `failed`, `stopped`, `canceled`, or `not_found`. | `{ job_id, status, source }` |
| `features_export:error` | `controller.events.emit` | Submit, polling, or result fetch fails. | `{ job_id, error }` |

### 6.4 Completion Handling Rules

- `poll_completion_event` must be `FEATURES_EXPORT_TASK_COMPLETED`.
- The controller must guard completion with `_completion_seen` or equivalent.
- StatusStream trigger handlers must not re-dispatch `job:completed`; `controlBase` already does that on the poll path.
- After success, the controller should fetch `/rq-engine/api/jobinfo/<job_id>` exactly once per completion cycle and render:
  - `download_url`
  - `artifact_id`
  - `cache_hit`
  - `source_job_id`
  - `manifest_relpath`
  - `warnings`

## 7. Payload Assembly And Validation UX Rules

### 7.1 Transport Rules

- Submit with JSON only.
- Use `WCHttp.postJsonWithSessionToken(...)` or equivalent JSON helper with `{ form: controller.form }`.
- Never submit `FormData` for this control.
- Never emit the legacy alias `f_esri`; normalize any hydrated legacy value to `geodatabase` before rendering or submitting.

### 7.2 Assembly And Validation Matrix

| Concern | Payload Keys | Assembly Rules | Blocking UX Rule | Non-Blocking Warning Rule |
| --- | --- | --- | --- | --- |
| Format | `format` | Emit one canonical token from `geojson`, `geoparquet`, `parquet`, `csv`, `kmz`, `geopackage`, `geodatabase`. | Required. Disable submit until selected. | Show packaging hint only; `parquet` and `csv` are geometryless and export attributes only. |
| Layers | `layers` | Emit selected `layer_id` array in UI selection order. Server may canonicalize later. | At least one layer required. On failure, open the Layer Catalog family containing the first invalid state and focus the first checkbox. | None. |
| Units | `units` | Emit `project`, `si`, or `english`. Default UI selection should be `project`. | Required. | None. |
| CRS | `crs` | Emit `wgs` or `utm`. Default UI selection should be `wgs`. | If config says UTM is unresolved, disable the `utm` choice and explain why. | None. |
| Output scopes | `output_scopes` | Emit only when the scope card is active. Default to `["baseline"]`. When `roads` is checked, emit `["baseline", "roads"]` in that order. | None when the scope card is hidden. If visible, at least one scope must remain checked. | If only scope-invariant layers are selected, hide the card and show `shared export only` note instead of warning. |
| Temporal mode | `temporal.mode` | Require an explicit mode whenever any selected layer supports temporal export. | If Temporal card is visible and no mode is chosen, block submit. | If chosen mode excludes some selected layers but leaves at least one compatible layer, show `partial export` warning before submit. |
| Year selection | `temporal.year_selection`, `temporal.exclude_yr_indxs` | Emit only for `annual_average` or `yearly`. Emit `exclude_yr_indxs` only for `custom`. | If `custom` is chosen and no exclusions are entered, block submit. | If some selected layers do not support year selection, keep submit enabled and show `selector_defaulted` preview warning. |
| Event selector | `temporal.event.selector`, `temporal.event.dates`, `temporal.event.return_periods` | Emit only for `event` mode. Dates and return periods are mutually exclusive. | Require at least one value for the active selector. Never allow both selector sets to remain populated in payload state. | None. |
| Omni selector | `scenario` or `contrast_id` | Show one selector only. Selecting an Omni scenario layer family clears any contrast selection, and vice versa. | If Omni scenario layers are selected and `scenario` is empty, block submit. If Omni contrast layers are selected and `contrast_id` is empty, block submit. | Do not allow mixed scenario and contrast families in the selected layer list; resolve client-side instead of warning later. |
| SWAT run | `swat_run_id` | Show only when SWAT layers are selected. Default to `latest` unless the bootstrap payload provides a concrete preferred run. | If SWAT is selected and there are no discoverable runs, block submit and show empty-state message. | None. |
| SWAT table filters | `swat_tables.include` or `swat_tables.exclude` | Use a mode toggle: `all`, `include`, or `exclude`. Emit only one of `include` or `exclude`; emit neither for `all`. | If `include` or `exclude` is selected and no table is checked, block submit. | If the current format is `geojson` or `kmz` and one or more selected tables are known non-spatial, keep submit enabled and show `these tables will be skipped` warning. |
| AgFields metrics | no special request key | Selection alone triggers backend auto-prep behavior when needed. | None client-side unless bootstrap data explicitly says AgFields is unavailable. | Show an informational note: `AgFields interchange may be prepared on demand before export starts.` |

### 7.2A Load Defaults Behavior

`Load Defaults` applies profile key `gpkg_adjacent` from the config node and resets the control to a legacy-adjacent starting point:

- `format=geopackage`
- `units=project`
- `crs=wgs`
- `output_scopes=["baseline"]`
- `swat_run_id=latest`
- Clear all temporal selectors.
- Clear Omni selectors (`scenario`, `contrast_id`) and SWAT include/exclude table filters.
- Replace selected layers with this ordered set when present in catalog:
  - `watershed.subcatchments`
  - `watershed.channels`
  - `landuse.dominant`
  - `soils.dominant`
  - `wepp.summary.hillslopes`
  - `wepp.summary.channels`

Rules:

- The action updates controls and selections only; it never auto-submits.
- If some profile layers are absent in the active catalog, apply available layers and emit one non-blocking warning in Selected Summary.
- If the catalog fails to load, disable the button and show an inline reason near the action.
- Future follow-on profile work (post-WP-7) may add a geometryless tabular preset intended to replace `prep_details`; this does not change the `gpkg_adjacent` behavior above.

### 7.3 Practical Validation Rules

- Client validation should use catalog metadata where determinable, but should not duplicate deep backend dependency checks.
- Validation errors should be field-local whenever possible.
- Validation that spans multiple groups should surface in Selected Summary and also mark the owning group.
- `Load Defaults` must remain enabled unless the catalog/bootstrap payload is missing or invalid.
- The primary button label stays `Export Features`; do not rename it per format.
- The button remains disabled only for true blocking errors, not for partial-export warnings.

### 7.4 Result Rendering Rules

- After `jobinfo.result` loads, render the artifact CTA first.
- Render warnings as a flat list beneath the artifact CTA.
- If `cache_hit=true`, show a muted badge and the `source_job_id`.
- Do not treat warnings as stacktrace content.
- Do not write warnings into the job hint region.

## 8. Accessibility And Keyboard Behavior

### 8.1 Accessibility Notes

- `#features_export_status_panel` must use `aria-live="polite"`.
- `#features_export_status_log` must keep `role="log"`.
- Inline field errors should use the existing field-message pattern with `role="alert"`, `aria-invalid="true"`, and `aria-describedby`.
- Family groups should be real `<details>` elements with `<summary>` labels so screen readers announce expanded/collapsed state.
- The selected-summary count should be readable text, not badge-only color.
- Warning, partial, and error states must not rely on color alone; include text badges.
- When a client-side validation failure occurs in a hidden card, open the card before moving focus.
- When an async job failure occurs, move focus to the stacktrace panel summary or the status heading, not directly into the log stream.

### 8.2 Keyboard Behavior

| Area | Keyboard Rule |
| --- | --- |
| Layer search | Standard text input behavior. `Escape` clears the search when non-empty. |
| Quick filters | Buttons are reachable by `Tab`; activate with `Enter` or `Space`. |
| Family groups | `<summary>` toggles with `Enter` or `Space`. |
| Layer checkboxes | Toggle with `Space`; no custom roving tabindex needed. |
| Radio groups | Native browser arrow-key behavior only. |
| Load Defaults | Reachable by `Tab`; activate with `Enter` or `Space`; no implicit submit. |
| Bulk actions | `Select visible`, `Clear filters`, and `Clear selection` are normal buttons. |
| Submit | `Enter` on the primary button submits only when the form is valid. No hidden implicit submit-on-field-enter behavior is required. |
| Error focus order | Focus the first invalid control in DOM order after opening its parent group. If there is no specific field, focus Selected Summary, then Status Panel, then Stacktrace summary. |

## 9. Test Checklist

### 9.1 Jest

- Add `wepppy/weppcloud/controllers_js/__tests__/features_export.test.js`.
- Verify singleton bootstrap with missing DOM, then successful re-hydration after dynamic mod insertion.
- Verify catalog parsing from `[data-features-export-catalog]` and runtime data parsing from `[data-features-export-bootstrap]`.
- Verify quick filters and search update visible counts without mutating selected layers unexpectedly.
- Verify `Load Defaults` applies the `gpkg_adjacent` profile, emits `features_export:defaults:loaded`, and does not auto-submit.
- Verify progressive disclosure for:
  - scope card
  - temporal card
  - Omni card
  - SWAT card
- Verify payload assembly for:
  - basic non-temporal export
  - scope-aware baseline plus roads export
  - yearly export with custom excluded year indices
  - event export by explicit dates
  - event export by return periods
  - Omni scenario export
  - Omni contrast export
  - SWAT include mode
  - SWAT exclude mode
  - legacy hydrated `f_esri` normalized to `geodatabase`
- Verify blocking validation disables submit and opens the correct group.
- Verify `job:started`, `features_export:submit:queued`, `FEATURES_EXPORT_TASK_COMPLETED`, `job:completed`, and `features_export:completed` sequencing is idempotent across poll and status-stream triggers.
- Verify `jobinfo.result` rendering populates download CTA, warning list, cache-hit note, and does not overwrite the job hint.
- Verify `pushResponseStacktrace` and `pushErrorStacktrace` behavior for 4xx validation errors and async job failures.

### 9.2 Playwright

- Add a controller smoke case in `wepppy/weppcloud/static-src/tests/smoke/controller-cases.js`.
- Suggested smoke selectors:
  - `form#features_export_form`
  - defaults selector: `[data-features-export-action="load-defaults"]`
  - action selector: `#btn_run_features_export`
  - request pattern: `**/rq-engine/api/**/export/features`
  - stacktrace locator: `#features_export_stacktrace_panel [data-stacktrace-body]`
  - stacktrace panel locator: `#features_export_stacktrace_panel`
  - hint locator: `#hint_run_features_export`
- Verify the control expands correctly from the Runs page `<details>` shell.
- Verify a successful mocked submit populates the job hint and preserves it after a follow-up failure.
- Verify a mocked failure opens the stacktrace panel and keeps the results panel from showing stale download links.
- Verify the control still boots after enabling the mod through the Mods menu.
- Verify a narrow viewport keeps the group order from the mobile wireframe and keeps the primary button reachable without horizontal scrolling.
- Verify `Load Defaults` is visible near the top of the control and keeps `Export Features` disabled until payload is valid.

### 9.3 pytest

- Add route contract coverage in `tests/weppcloud/routes/test_rq_api_features_export.py`.
- If a dedicated WEPPcloud page/bootstrap route or template helper is added, also add `tests/weppcloud/routes/test_features_export_bp.py`.
- Cover JSON-only transport behavior:
  - non-JSON submission returns `415`
  - empty JSON returns `400`
- Cover selector validation:
  - missing layers
  - invalid format
  - invalid CRS
  - mixed Omni scenario and contrast request
  - missing Omni selector
  - SWAT include/exclude mutual exclusion
  - unresolved UTM returns `409`
- Cover partial-success warnings:
  - scope-aware layer missing one scope
  - temporal incompatibility drops some layers
  - non-spatial SWAT table skipped for `geojson` or `kmz`
  - AgFields auto-prep warning path when other layers still export
- Cover success result shape:
  - `job_id`
  - `status_url`
  - `jobinfo.result.download_url`
  - `artifact_id`
  - `cache_hit`
  - `source_job_id`
  - `manifest_relpath`
  - `warnings`
- Cover download gating:
  - non-finished job returns `409`
  - finished job returns the artifact

## 10. Implementation Notes For This Repo

- Prefer `ui.radio_group`, `ui.checkbox_field`, `ui.text_field`, and a custom catalog list block inside the control shell; do not pull in a JS multiselect library.
- Keep the layer catalog DOM stable enough for smoke tests. The catalog may be data-driven, but the outer selectors and action ids should not drift.
- Keep status text, job hint, warnings, and stacktrace as separate surfaces. This matches the repo’s strongest existing controller pattern and prevents the common “job link overwritten by progress text” regression.
