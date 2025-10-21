# Control Components (Pure UI Draft)

This note captures the design contract for the Pure.css-based control shell and component macros.
Use it alongside:
- `docs/ui-docs/control-ui-styling/control-inventory.md` – catalog of every production control and the data each field exposes.
- `/ui/components/` showcase route – the living gallery for every macro. Update the showcase whenever arguments or markup change so reviewers can see the rendered diff.

Goal: define a consistent, minimal component set that we can apply to existing controls with zero ambiguity.

---

## 1. Component Contracts

### 1.1 `control_shell`
**Purpose**
- Provides the structural scaffolding for WEPP controls and console forms: header, optional description/toolbar row, primary input column, and side-panel column.
- Keeps spacing, typography, and accessibility consistent while allowing callers to focus on their fields.

**Arguments**
| Argument | Type | Notes |
| --- | --- | --- |
| `form_id` | str (required) | Used for `<form id="...">` and as the anchor JS controllers attach to. |
| `title` | str (required) | Rendered in the header/summary line. |
| `toolbar` | HTML | Placed beside the description; useful for action buttons or status chips. |
| `description` | HTML | Appears above the inputs column; accepts markup (for example `<p>`). |
| `meta` | HTML | Renders under the title (for metadata pills, status badges, etc.). |
| `collapsible` | bool (default `True`) | Wraps the control in `<details>` when enabled; set `False` for consoles. |
| `open` | bool (default `True`) | Initial open state when `collapsible` is enabled. |
| `form_class` | str | Extra classes appended to `wc-control__form` (for Pure grid helpers, etc.). |
| `form_attrs` | dict | Arbitrary attributes injected on the `<form>` (`{'novalidate': True}`, autocomplete hints). |
| `status_panel_override` | HTML or `''` | Custom status panel markup; pass `''` to suppress the panel entirely. |
| `summary_panel_override` | HTML or `''` | Custom or suppressed summary panel. |
| `stacktrace_panel_override` | HTML or `''` | Custom or suppressed stack trace panel. |

**Behaviour**
- Supply inputs with `{% call control_shell(...) %} ... {% endcall %}`. Content renders inside `.wc-control__inputs`.
- Override hooks let callers swap in `status_panel` / `stacktrace_panel` or opt out entirely with `''`.
- Legacy run controls still rely on the default panels; migrate them once ControlBase switches to `StatusStream`.

_Collapsible run control_
```jinja
{% import "controls/_pure_macros.html" as ui %}

{% call ui.control_shell(
     form_id="climate_form",
     title="Climate Data",
     description="<p>Select the climate dataset and optional filters.</p>",
     toolbar=render_toolbar(),
     collapsible=True
   ) %}
  {{ ui.select_field('dataset', 'Dataset', dataset_options, selected=current_dataset) }}
  {{ ui.checkbox_field('includeNormals', 'Include normals', checked=include_normals) }}
  {% call button_row() %}
    <button type="submit" class="pure-button pure-button-primary" id="submit_climate">Run climate</button>
  {% endcall %}
{% endcall %}
```

_Fixed console shell_
```jinja
{% import "controls/_pure_macros.html" as ui %}

{% call ui.control_shell(
     form_id="fork_form",
     title="Fork Project",
     collapsible=False,
     form_class="pure-form-aligned",
     form_attrs={'novalidate': True},
     status_panel_override=ui.status_panel(
       id="fork_status_panel",
       title="Console",
       variant="console",
       log_id="fork_status_log",
       meta='<div id="the_console" class="wc-status" data-state="attention">Waiting for submission...</div>',
       height="300px"
     ),
     summary_panel_override='',
     stacktrace_panel_override=ui.stacktrace_panel(
       id="fork_stacktrace_panel",
       summary="Stack trace",
       empty_state="No stack trace captured."
     )
   ) %}
  {{ ui.text_field('runid_input', 'Source run ID', value=runid, attrs={'readonly': 'readonly'}) }}
  {{ ui.checkbox_field('undisturbify_checkbox', 'Undisturbify output (optional)', checked=undisturbify == 'true') }}
  {% call button_row() %}
    <button type="submit" class="pure-button" id="submit_button">Fork project</button>
  {% endcall %}
{% endcall %}
```

### 1.2 `status_panel`
- Purpose: reusable log viewport for controls and console dashboards.
- DOM contract: `<section class="wc-status-panel" data-status-panel data-variant="...">` containing `<div class="wc-status-panel__log" data-status-log role="log">`.
- Key arguments: `id`, `variant` (defaults to `"compact"`; use `"console"` for tall dashboards), `meta`, `description`, `actions`, `footer`, `log_id`, `aria_live`, `initial`, `height`.
- Height: omit unless you intentionally want a fixed viewport. Defaults clamp to 12–20rem; set ~`3.25rem` for a single line or a larger value for streaming consoles.
- Auto-scrolls to the bottom when the viewer is already near the end (< 12 px).
- Accessibility: `role="log"` with `aria-live` (default `polite`) ensures screen readers announce new lines without stealing focus.

### 1.3 `stacktrace_panel`
- Renders `<details class="wc-stacktrace" data-stacktrace-panel>` with `<summary>` and `<pre data-stacktrace-body>`.
- Arguments: `id`, `summary`, `collapsed`, `description`, `actions`, `body_id`, `empty_state`.
- When stack trace text arrives, un-hide the panel and set `open=true` so disclosure is accessible.

### 1.4 StatusStream integration
- `StatusStream` ships in `/static/js/controllers.js`. Load that bundle (and the vendor jQuery include) before inline scripts that call `StatusStream.attach`.
- Example:
```html
<script src="{{ url_for('static', filename='vendor/jquery/jquery.js') }}"></script>
<script src="{{ url_for('static', filename='js/controllers.js') }}"></script>
<script>
  StatusStream.attach({
    element: document.getElementById('archive_status_panel'),
    channel: 'archive',
    runId: runid,
    logLimit: 3000,
    stacktrace: { element: document.getElementById('archive_stacktrace_panel') },
    onTrigger(detail) {
      if (detail.event === 'ARCHIVE_COMPLETE') archiveFinished();
    }
  });
</script>
```
- Events dispatched on the root element: `status:connected`, `status:disconnected`, `status:append`, `status:trigger`, `status:error`. Listen for these when you need bespoke automation beyond the `onTrigger` callback.
- The log body must expose `[data-status-log]`; stacktrace panels should use `[data-stacktrace-body]` so `StatusStream` can hydrate them.

### 1.5 Migration guidance
- Prefer the new macros whenever you refactor a console or build a fresh control. Use the override hooks (or `''`) to opt out of panels instead of cloning legacy markup.
- Conversion checklist:
  1. Import `controls/_pure_macros.html`.
  2. Wrap markup in `control_shell`; set `collapsible=False` for consoles.
  3. Supply `status_panel` / `stacktrace_panel` overrides (or `''` to omit panels).
  4. Ensure `/static/js/controllers.js` is included so `StatusStream` is available.
  5. Call `StatusStream.attach` with the new IDs (`status_panel`, custom `log_id`, etc.).
  6. Verify existing JS selectors still match the rendered IDs (`status`, `stacktrace`, etc.).
- Live examples: `rq-fork-console.htm`, `rq-archive-dashboard.htm`, `query_console.html`.
- Legacy run controls still rely on `_pure_base.htm`; migrate them once `controlBase` is StatusStream-aware.

---

## 2. Layout Notes
- Group related inputs into cards using `.wc-control__inputs` and spacing utilities instead of ad-hoc Bootstrap rows.
- Consult `docs/ui-docs/control-ui-styling/final-implementation-blueprint.md` for broader layout guidance during the Pure migration.

### 2.1 Runs Page Layout
- **Header**: fixed Pure header (run-specific variant includes name/scenario inputs, power user tools, readonly/public toggles).
- **Navigation**: left column Table of Contents (about 20% width) controlling tabs/anchors (`wc-run-layout__toc`, sticky on large screens).
- **Main content**: right column (about 80% width) containing controls stacked inside `wc-run-layout__content`.
- **Footer**: command bar anchored to the bottom (full width).
- The new control shell must coexist with this layout; when embedded elsewhere (e.g., batch runner) the same shell keeps styling consistent.

### 2.2 Run Header Components
- Name and Scenario inputs use the `wc-run-header__field` pattern (see CSS). The forthcoming `header_text_field` macro abstracts the label/input layout.
- Action buttons (Readme, Fork, Archive, etc.) stay in the header toolbar; macros should not recreate them.
- Dropdown entries (`PowerUser`, `Browse`, `Unitizer`, `Readonly`, `Public`, `Access log`) remain accessible via the header menu (`header/_run_header_fixed.htm`).

### 2.3 Map Layout Helpers
- Use `.wc-map-layout` for the map control split view. It collapses to a single column on narrow screens and expands to a map/inspector grid beyond ~960px.
- `.wc-map` wraps the Leaflet canvas with shared borders, radius, and `clamp()` height; the inner element should carry `.wc-map__canvas` (typically `<div id="mapid">`) so it stretches to fill the frame.
- `.wc-map-layout__inspector` stacks tab navigation, legends, and configuration cards with consistent spacing.
- `.wc-map-status` replaces ad-hoc rows for center/zoom/elevation copy. Keep existing IDs (`mapstatus`, `mouseelev`) inside the flex row so `MapController` continues to patch text.
- These helpers live in `ui-foundation.css`; avoid inline sizes so Leaflet can run `invalidateSize()` against predictable containers.

### 2.4 Modal Scaffolding and Resource Panels
- Build modals with `.wc-modal` wrappers (see `controls/unitizer_modal.htm`). The PowerUser panel conversion illustrates dialog sizing at 90% viewport width/height while keeping the shared overlay, header, and close button contracts intact.
- When rendering repeated resource rows inside a modal, create a local macro (e.g. `resource_block`) that emits a `.wc-run-header__field` heading, lock icon placeholder, and paired `.pure-button.pure-button-secondary` links. This keeps lock toggles (`preflight.js`) compatible across layouts.
- Use semantic lists with `.wc-link wc-link--file` for browse shortcuts. Buttons remain `.pure-button` variants so modal actions blend with the foundation palette; adjust spacing via shared tokens (`var(--wc-space-*)`) instead of inline pixel values.
- Fix modal footers when they host command bars: `poweruser_panel.htm` applies a scoped rule that sets `.wc-modal__footer { height: 3rem; }` so the close button stays aligned even when the body scrolls.

---

## 3. Component Catalogue (macro inventory)
Every macro below now lives in `controls/_pure_macros.html` and is showcased inside `/ui/components/` (`component_gallery.htm`). Update both the macro and the gallery in tandem whenever arguments or markup change so reviewers can trace behaviour end-to-end.

- All field-style macros now accept an optional `error` argument. When provided, the macro flags the control as invalid (`aria-invalid="true"` on inputs or radiogroups), appends the error id to `aria-describedby`, and emits a `.wc-field__message.wc-field__message--error` block announced via `role="alert"`.

### 3.1 `header_text_field`
- **Purpose**: Run header inputs (Name, Scenario).
- **Layout**: `wc-run-header__field` – label and input stacked vertically on narrow screens, two-column on wide.
- **Args**: `field_id`, `label`, `value`, `placeholder`, optional `help`, `attrs`, optional `extra_class` for additional input classes.
- **Notes**: Debounced updates still handled by `Project` JS; macro simply renders markup/class names.
- **Status**: Implemented; see “Run Header Fields” section of the showcase.
- Secondary actions (Unitizer, PowerUser, Readonly/Public toggles, Access Log) live inside the `wc-run-header__menu` dropdown so the primary row stays compact.

### 3.2 `text_field`
- **Purpose**: Generic text input inside a card.
- **Layout**: Label above input; responsive width 100%. (Older 1/5 + 1/5 ratio replaced with Pure container widths.)
- **Args**: `field_id`, `label`, `value`, optional `help`, `placeholder`, `type` (default `text`), `attrs` (dict of extra HTML attributes), optional `extra_control_class` to append additional classes (for example `disable-readonly`).
- **Status**: Implemented; helper text now wires through `aria-describedby`.

### 3.3 `numeric_field`
- **Purpose**: Number input with optional unit display.
- **Layout**: Label, number input, optional unit suffix (e.g. `mm`, `mg/L`).
- **Args**: `field_id`, `label`, `value`, `unit_label`, optional `precision`, `min`, `max`, `required`, `nullable`, optional `unit_category`, optional `unit_name` (canonical unit string, e.g. `kg/ha`).
- **Notes**: When `unit_category` is provided the macro emits `data-unitizer-*` attributes (`data-unitizer-category`, `data-unitizer-unit`, `data-unitizer-label`) so `UnitizerClient` can keep labels in sync with user preferences.
- **Status**: Implemented with `data-precision` + `data-nullable`; unit label renders inside `.wc-field__unit` and now auto-updates via the static unitizer map.

### 3.4 `file_upload`
- **Purpose**: Upload control with help text and existing filename.
- **Layout**: Label above `<input type="file">`, help below, optional “current file” display.
- **Args**: `field_id`, `label`, `accept`, optional `help`, `current_filename`, `attrs`, optional `extra_control_class` for additional CSS tokens (e.g., `disable-readonly`).
- **Notes**: Macro should include accessible description linking input to help text.
- **Status**: Implemented with `.wc-field__meta` for current filename display; extra control class landed during landuse conversion to support read-only toggling.

### 3.5 `radio_group`
- **Purpose**: Mode selectors (e.g. landuse mode, climate mode). Supports horizontal/vertical layouts.
- **Layout**: Option list plus optional static or mode-specific help block.
- **Args**: `name`, `layout` (`horizontal`/`vertical`), `options` (list of dicts: label, value, description, selected, disabled), optional `mode_help` (mapping value → help HTML).
- **Notes**: Should expose data attributes for HTMX or JS toggles.
- **Status**: Implemented with `.wc-choice-group`, per-option `attrs`, and `data-choice-help-*` hooks for JS toggles.

### 3.6 `select_field`
- **Purpose**: Standard `<select>` element with label/help.
- **Args**: `field_id`, `label`, `options` (list of `(value, text)`), `selected`, optional `help`, `attrs`, optional `extra_control_class` for additional CSS tokens (e.g., `disable-readonly`).
- **Status**: Implemented and wired into the gallery as a legacy select comparison; landuse report uses the new `extra_control_class` hook.

### 3.7 `checkbox_field`
- **Purpose**: Single checkbox with help text (e.g. `readonly`/`public`, `clip hillslopes`).
- **Layout**: Checkbox aligned with label; help text below.
- **Args**: `field_id`, `label`, `checked`, optional `help`, `attrs`.
- **Status**: Implemented with `.wc-choice--checkbox` styling.

### 3.8 `textarea_field`
- **Purpose**: Multi-line text (notes, CSV paste).
- **Args**: `field_id`, `label`, `value`, `rows`, optional `help`, `placeholder`, optional `extra_control_class` to append additional textarea classes.
- **Status**: Implemented.

### 3.9 `wepp_pure` composite
- **Purpose**: Pure implementation of the WEPP control embedded on the runs₀ page.
- **Layout**: `control_shell` (non-collapsible) with `status_panel` + `stacktrace_panel`, primary run button, and an `advanced_options` card containing reusable partials (`wepp_pure_advanced_options/*`).
- **Key components**:
  - Checkboxes (`ui.checkbox_field`) tied to `Wepp.set_run_wepp_routine` for hourly seepage, PMET, snow, frost, baseflow, flowpaths, etc.
  - Numeric inputs (`ui.text_field`) for channel hydraulics, snow parameters, phosphorus concentrations, and soil clipping depths.
  - Select controls for channel critical shear / WEPP binary version / revegetation scenarios.
  - Inline script toggles the cover transform upload block when “User-Defined Transform” is chosen.
- **Status**: Implemented (`controls/wepp_pure.htm`) with legacy markup preserved under `controls/wepp.htm` until the classic runs page is retired.

### 3.9 `text_display`
- **Purpose**: Read-only block within a card (summaries, inline reports).
- **Layout**: Label in bold, content stacked below; may include HTML.
- **Args**: `label`, `content`, optional `variant` (info/success/warning), `actions` (links/buttons).
- **Status**: Implemented with `.wc-text-display--*` variants and optional action row.

### 3.10 `table_block`
- **Purpose**: Render tabular data (landuse, soils summaries).
- **Plan**: Macro will accept column definitions + rows, emit a Pure table with optional caption.
- **Next steps**: Prototype in showcase before migrating real tables.
- **Status**: First pass implemented using `wc-table`; landuse report now consumes the macro. Follow-up: refine sortable/hybrid tables after soils panels migrate.

### 3.11 `dynamic_slot`
- **Purpose**: Placeholder `<div>` for controller-managed DOM (e.g. map overlays, JS builders).
- **Layout**: Macro wraps a `<div>` with consistent padding/spacing so dynamic content blends with cards.
- **Args**: `slot_id`, optional `help`.
- **Notes**: Document which controls rely on custom JS so designers know what to expect.
- **Status**: Implemented; renders `.wc-dynamic-slot` with optional helper copy.

### 3.12 `collapsible_card`
- **Purpose**: Hide advanced/optional sections (filters, expert settings) behind an accessible toggle.
- **Layout**: `<details>` + styled `<summary>` header with rotating chevron and optional description; content area stacks children with standard spacing.
- **Args**: `title`, optional `description`, optional `expanded` (default false), optional `card_id` for external toggles, optional `attrs` dict for extra attributes.
- **Status**: Implemented; `/ui/components/` demo wraps advanced options in the new card. Landuse report uses `card_id` so table buttons can toggle coverage overrides.

### 3.13 `status_panel`
- **Purpose**: Standard log surface for controls and console dashboards.
- **Layout**: `<section class="wc-status-panel" data-status-panel>` with optional header actions, descriptive text, and a monospace log body (`[data-status-log]`). CSS custom property `--wc-status-height` defaults to `20rem` (console variant) while `--wc-status-min-height` clamps to `12rem`; both can be overridden per panel.
- **Args**: `id`, optional `title`, `variant`, `meta` (HTML block above the log for job metadata or state chips), `description`, `actions`, `footer`, `log_id`, `aria_live`, `initial`. `height` accepts any CSS length (px, rem, etc.) and sets both custom properties (`--wc-status-height` and `--wc-status-min-height`) to keep the viewport fixed (for compact run controls, use ~`3.25rem`). Invoking the macro with `call` renders the caller block inside `wc-status-panel__slot` (useful for legacy IDs during migration).
- **Status**: Implemented; showcased with both variants. `StatusStream.attach({ element, channel, runId })` streams updates into `[data-status-log]`. Legacy helpers remain available as `legacy_status_panel()` until ControlBase is updated.

### 3.14 `stacktrace_panel`
- **Purpose**: Shared disclosure for exception payloads emitted by RQ jobs.
- **Layout**: `<details class="wc-stacktrace" data-stacktrace-panel>` with summary copy, optional actions, description, and a `<pre data-stacktrace-body>` target.
- **Args**: `id`, `summary`, optional `collapsed` (default true), `description`, `actions`, `body_id`, `empty_state`.
- **Status**: Implemented; paired with `StatusStream` stacktrace enrichment on the fork console and archive dashboard. Legacy `#stacktrace` panels remain until run controls migrate.

### 3.15 `tabset`
- **Purpose**: Accessible tab navigation for inspector panes (map overlays, drilldowns, results dashboards).
- **Layout**: `<div class="wc-tabs" data-tabset>` containing a `.wc-tabs__nav` button row and aligned `.wc-tabs__panels`. Buttons carry `role="tab"`, `aria-controls`, and `data-tab-target`; panels use `role="tabpanel"` and toggle `hidden`.
- **Args**: `tabs` list where each item sets `id`, optional `icon`, `label`, optional `active`, and `content` (HTML string). Active state defaults to the first tab when not supplied.
- **Behaviour**: Helper JS toggles the `is-active` class, updates `aria-selected`/`tabindex`, and fires a custom `wc-tabset:change` event. Controls can listen for that event to refresh Leaflet overlays or invalidate tile layers.
- **Status**: Implemented and showcased; use the macro instead of Bootstrap nav-tabs.

### 3.16 `color_scale`
- **Purpose**: Bundles slider, legend canvas, and value labels for map visualization controls.
- **Layout**: `.wc-color-scale` grid with labelled range input, optional units element, framed canvas (`wc-color-scale__bar` + `wc-color-scale__canvas`), and flexed min/max spans.
- **Args**: Required `range_id`, `canvas_id`, `min_id`, `max_id`; optional `label`, `range_attrs`, `canvas_attrs`, `units_id`, and `help`.
- **Notes**: IDs must match the JS contract used by `SubcatchmentDelineation`. Range attrs support `min`, `max`, `step`, `value` without inline styles. Canvas width/height handled via CSS.
- **Status**: Implemented; map/rangeland partials now use the macro instead of bespoke Bootstrap grids.

### Landuse Control (`controls/landuse.htm`)
- **Structure**: `ui.control_shell` with `collapsible=False` so status/stacktrace panels sit beside the inputs. Mode selection uses `ui.radio_group`, while dataset/time-series selects stay as raw `<select class="disable-readonly">` to keep the table layout predictable inside the control.
- **Catalog integration**: Dataset options come from `landuse.available_datasets` (management + landcover entries). The template builds three option lists:
  * `landcover_ns.options` (per-hillslope dataset select),
  * `single_ns.options` (single-landuse mode), and
  * `mapping_ns.options` (upload mode mapping select).
  Filtering/ordering is performed in Python so the template is a simple loop.
- **Advanced options**: Wrapped with `ui.collapsible_card` (animated `<details>`). Buffer select and disturbed toggles reuse `select_field`/`checkbox_field` with `extra_control_class="disable-readonly"` so project read-only mode can disable the inputs.
- **Status wiring**: Uses `ui.status_panel` (`height="4rem"`) plus `ui.stacktrace_panel`. `landuse.js` delegates form events (mode radio change, dataset select, build button) instead of inline `onchange` attributes.
- **Upload block**: `ui.file_upload(..., extra_control_class="disable-readonly")` provides the file input; the mapping select and helper text live beneath it.

### Landuse Report (`reports/landuse.htm`)
- **Layout**: Plain `<table class="wc-table wc-landuse-report__table">` wrapped in `.wc-landuse-report`. Summary rows carry inline selects; detail rows use `<details>` for collapsible overrides so the extra controls stay associated with their summary.
- **Selectors**: `.wc-landuse-report__summary`, `.wc-landuse-report__toggle`, `.wc-landuse-report__select`, `.wc-landuse-report__details-row`, `.wc-landuse-report__collapse`, and `.wc-landuse-report__controls` live in `ui-foundation.css`. These helpers enforce spacing, background inheritance, and the responsive flex layout for the three coverage selects.
- **Interactions**: `landuse.js` toggles the `<details>` element and adds/removes `.is-open` on the detail `<tr>` so CSS can collapse/expand the row. Buttons set `aria-expanded`, and coverage/mapping selects retain `data-landuse-role` hooks for the existing AJAX handlers.
- **Design notes**: Summary cells receive extra padding via `.wc-landuse-report__summary > td { padding-bottom: var(--wc-space-lg); }` for visual separation. Detail rows inherit table colors (no Bootstrap collapse) and gain a subtle divider when open.

### Soil Burn Severity Control (`controls/disturbed_sbs_pure.htm`)
- **Structure**: `ui.control_shell` keeps the SBS workflow inside a non-collapsible console. Mode selection uses `ui.radio_group`; upload view relies on `ui.file_upload` and `ui.text_display` for the current raster; uniform builders are rendered as `button_row()` actions with Pure buttons.
- **JS contract**: Buttons expose `data-sbs-action` (`upload`, `remove`, `set-firedate`) and `data-sbs-uniform` for low/moderate/high presets. `baer.js` delegates events off the form and initialises visibility via `showHideControls` so both legacy and Pure markup stay in sync.
- **Compatibility**: Legacy IDs (`#sbs_upload_form`, `#sbs_mode{0,1}_controls`, `hint_*`) are preserved to keep ControlBase logging and StatusStream wiring unchanged. The classic Bootstrap template remains at `controls/baer_upload.htm` for the legacy runs page until the toggle flips.
- **Status**: Implemented; TOC entry appears when `baer` or `disturbed` mods are active and `lt` is not present.

### Observed Data Control (`controls/observed_pure.htm`)
- **Structure**: `ui.control_shell(collapsible=False)` with inline description of CSV requirements. Text entry uses `ui.textarea_field` (`id="observed_text"`) plus a `button_row()` housing `btn_run_observed`. Legacy summary/status IDs (`info`, `status`, `stacktrace`) remain via override hooks so `controlBase` and `WSClient` continue to work.
- **Status wiring**: Uses `ui.status_panel` (`observed_status_panel`) + `ui.stacktrace_panel`. `observed.js` now binds button clicks via delegated handler while still supporting the legacy `_base.htm` inline `onclick`.
- **Hints & locks**: `run_observed_lock` image stays hidden by default and exposed through `preflight.js`. Hint label `hint_run_wepp` remains for compatibility.
- **Status**: Implemented; legacy template retained for classic runs page. Future enhancement: optional CSV upload hook to share logic with the uploads helper.

### RAP Time Series Control (`controls/rap_ts_pure.htm`)
- **Structure**: Minimal `ui.control_shell` with a short description paragraph and a single action button rendered via `button_row()`. The button retains `btn_build_rap_ts` so `rap_ts.js` can delegate clicks; the legacy template keeps its inline handler until the classic page is retired.
- **Status wiring**: `ui.status_panel` + `ui.stacktrace_panel` mirror other converted controls, allowing ControlBase + WSClient to surface queue updates. The hint (`hint_build_rap_ts`) remains below the button for log messaging.
- **Status**: Implemented; bootstrap placeholder removed from `runs0_pure.htm`. Legacy `_base.htm` template persists for `0.htm` until Pure becomes default.

### Debris Flow Control (`controls/debris_flow_pure.htm`)
- **Structure**: `ui.control_shell(collapsible=False)` with a brief model disclaimer followed by a `button_row()` that retains `btn_run_debris_flow`. The PowerUser gate lives at the template include to mirror legacy behaviour.
- **Status wiring**: Uses `ui.status_panel` (`debris_flow_status_panel`) and `ui.stacktrace_panel` so ControlBase continues to stream RQ updates via `debris_flow.js`. The lock image `run_debris_flow_lock` remains for preflight integration.
- **Status**: Implemented; legacy template remains on `0.htm` until the Pure layout becomes default.

### DSS Export Control (`controls/dss_export_pure.htm`)
- **Structure**: `ui.control_shell(collapsible=False)` with a radio group (`dss_export_mode`) for export strategy and two conditional stacks mirroring the original mode-specific inputs. `dss_export_channel_ids` stays as a text field; channel-order exclusions reuse checkbox macros in a flex wrapper.
- **Status wiring**: `ui.status_panel` + `ui.stacktrace_panel` allow ControlBase + WSClient to surface queue updates (`post_dss_export_rq`). The export button retains `btn_export_dss` and lock image `btn_export_dss_lock` for preflight gating.
- **Compatibility**: `dss_export.js` now binds mode toggles and export clicks via delegated handlers while still supporting the legacy inline `onchange`. The anchor toggle recognizes both legacy and Pure TOC IDs.
- **Status**: Implemented; legacy template persists for `0.htm` until Pure is default.

### Rangeland Cover Control (`controls/rangeland_cover_pure.htm`)
- **Structure**: `ui.control_shell(collapsible=False)` wraps the mode selector (NLCD, RAP, watershed) and grouped foliar/ground default inputs. RAP-specific settings live in `#rangeland_cover_rap_year_div` so legacy JS can keep toggling visibility.
- **Status wiring**: Reuses legacy IDs for the status, stacktrace, hint, and build button, enabling ControlBase/WSClient to stream updates without JS changes beyond delegated handlers.
- **Integration**: The modify panel (`controls/modify_rangeland_cover.htm`) stays in the map tabset; the main control no longer duplicates that markup. `rangeland_cover.js` now delegates events so both legacy `_base.htm` and Pure layouts are supported.
- **Status**: Implemented; the legacy template remains on `0.htm` until the Pure layout becomes default.

---

## 4. Showcase Expectations
- The `/ui/components/` gallery must demonstrate every macro and layout pattern. Treat it as the canonical example for contributors and reviewers.
- Before migrating production controls:
  1. Implement new/updated macros.
  2. Document usage here.
  3. Add an example to the showcase.
- Only after those steps should we refactor real controls (starting with a low-risk panel).
- Gallery callouts now cover header fields, numeric/unit patterns, radio groups, file uploads, text displays, tables, dynamic slots, and the collapsible advanced options container. Update the gallery snippet when adding new args (e.g., validation state, error messaging) so accessibility/layout regressions surface quickly.
- Dark-mode styling is intentionally deferred; stay focused on light theme polish and accessible contrast in `ui-foundation.css`.

---

## 5. Next Steps
1. Pilot the new macros on a low-risk production control (e.g. channel delineation) and document migration lessons in the inventory.
2. Finalise metadata contracts (what each macro expects from NoDb controllers: labels, units, validation rules).
3. Define validation/error state patterns (visual + ARIA) and extend macros once the contract is agreed.
4. Keep this document and the showcase in sync as each production control migrates.
