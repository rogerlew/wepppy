# Control Components (Pure UI Draft)

This note captures the design contract for the new Pure.css-based control shell and component macros.  
Use it alongside:
- `docs/ui-docs/control-ui-styling/control-inventory.md` – catalog of every production control and the data each field exposes.
- `/ui/components/` showcase route – living gallery that demonstrates each macro in isolation. The showcase must be updated whenever we change or add components.

Goal: define a consistent, minimal component set that we can apply to existing controls with zero ambiguity.

---

## 1. Control Architecture

### 1.1 Shell (`controls/_pure_base.htm`)
- Wraps an entire control (title, optional toolbar, inputs, status panels) inside a `<details>` element so the whole block can collapse/expand.
- Summary row (`<summary>`) shows the title and optional meta; the chevron auto-rotates when open.
- When expanded, the form body renders inputs first and stacks default panels beneath:
  - **Status panel** (legacy controls expose `#rq_job`, `#status`, `#braille`; new builds should prefer `status_panel`, which provides `[data-status-panel]` and `[data-status-log]` hooks for shared JS).
  - **Summary panel** (`#info`).
  - **Details panel** (`#stacktrace` today; `stacktrace_panel` supplies `<details data-stacktrace-panel>` + `[data-stacktrace-body]`).
- Controls can override the panel stack via the `control_panels` block.
- Optional toolbars render inside the expanded header so interactive buttons never live inside the `<summary>` element.
- Macros in `_pure_macros.html` emit the same structure when a block-based approach is more convenient.
- `control_shell` accepts additional hooks:
  - `form_class` appends extra classes to the generated `<form>` (for example `pure-form-aligned`).
  - `form_attrs` injects arbitrary attributes (`{'novalidate': True}`).
  - `status_panel_override`, `summary_panel_override`, `stacktrace_panel_override` let callers supply custom panel markup (or an empty string to suppress a panel) while the default legacy panels remain the fallback. These hooks are how console pages swap in the new `status_panel`/`stacktrace_panel` components today.

### 1.2 Card Layout
- Each control should group related inputs into “cards”. A card is a simple section containing a heading (optional) and a stack of components.
- Cards live in the primary column (`wc-control__inputs`) and use our spacing utilities; the showcase provides canonical spacing.
- When a control has multiple logical sub-sections (e.g. Batch Runner intake/validation), use multiple cards.

### 1.3 Status & Stacktrace
- Located inside the shell sidebar; should not be re-implemented inside individual controls.
- `status_panel` standardizes the markup for logs, adds optional header/footer slots, and exposes the `[data-status-log]` target consumed by `StatusStream`.
- `stacktrace_panel` wraps the disclosure used for exception payloads. It stays collapsed/hidden until `StatusStream` hydrates new trace text, then opens automatically.
- Run controls currently rely on legacy IDs in `_pure_base.htm`; console dashboards already use the new macros. ControlBase will migrate once the shared JS adopts `StatusStream`.

---

## 2. Component Contracts

### 2.1 `control_shell`
**Purpose**
- Provides the structural scaffolding for WEPP controls and console forms: a header, description/toolbar row, input column, and side-panel column.
- Ensures every control uses consistent spacing, typography, and accessibility wiring without re-implementing wrapper markup.

**Arguments**
| Argument | Type | Notes |
| --- | --- | --- |
| `form_id` | str (required) | Used for the `<form id="...">` and as the anchor run controllers attach to. |
| `title` | str (required) | Rendered in the summary/header line. |
| `toolbar` | HTML | Placed in the header beside the description. |
| `description` | HTML | Appears above the inputs column; accepts markup (e.g., `<p>`). |
| `meta` | HTML | Renders under the title (e.g., run metadata pills). |
| `collapsible` | bool (default `True`) | When `True`, wraps the control in `<details>` with a clickable summary; set `False` for console-style pages. |
| `open` | bool (default `True`) | Controls the initial open state when `collapsible` is enabled. |
| `form_class` | str | Extra class names appended to `wc-control__form` (e.g., `pure-form-aligned`). |
| `form_attrs` | dict | Arbitrary attributes injected on the `<form>` element (`{'novalidate': True}`, autocomplete hints, etc.). |
| `status_panel_override` | HTML or `''` | Custom markup for the first side panel. Provide a `status_panel(...)` call or `''` to suppress the default legacy status block. |
| `summary_panel_override` | HTML or `''` | Custom or suppressed summary panel. Leave `None` to fall back to the legacy summary panel. |
| `stacktrace_panel_override` | HTML or `''` | Custom or suppressed stack trace panel. |

**Behaviour**
- Supply inputs using `{% call control_shell(...) %} ... {% endcall %}`. Content inside the block is rendered within `.wc-control__inputs`.
- Override hooks can swap or remove panels; omitting them renders the legacy status/summary/stacktrace blocks for backward compatibility.
- Pass `''` (empty string) to an override to skip rendering that panel entirely.

**Examples**
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

### 2.2 `status_panel`
- Purpose: reusable log viewport for controls and console dashboards.
- DOM contract: `<section class="wc-status-panel" data-status-panel data-variant="...">` containing a `<div class="wc-status-panel__log" data-status-log role="log">`.
- Key arguments: `id`, `variant` (`compact` or `console`), `meta`, `description`, `actions`, `footer`, `log_id`, `aria_live`, `initial`, `height`.
- `height` sets both `--wc-status-height` and `--wc-status-min-height`; defaults are 20rem/12rem. Use ~`3.25rem` for single-line status, larger values for streaming consoles.
- Automatically preserves scroll-to-bottom behaviour when the user is already at the end (< 12 px).
- Accessibility: `role="log"` plus `aria-live` (default `polite`) ensure screen readers announce new lines without changing focus.

### 2.3 `stacktrace_panel`
- Renders `<details class="wc-stacktrace" data-stacktrace-panel>` with `<summary>` + `<pre data-stacktrace-body>`.
- Arguments: `id`, `summary`, `collapsed`, `description`, `actions`, `body_id`, `empty_state`.
- When stack trace text arrives, set `panel.hidden = false; panel.open = true;` so the disclosure is accessible.

### 2.4 StatusStream integration
- `StatusStream` ships inside `/static/js/controllers.js`; templates must load that bundle (and the jQuery vendor script) before inline scripts that call `StatusStream.attach`.
- `attach({ element, channel, runId, logLimit, onTrigger, stacktrace })` expects the `status_panel` element (or selector) and the Redis status channel.
- Dispatches: `status:append`, `status:trigger`, `status:error`, `status:connected`, `status:disconnected`. Use event listeners for bespoke automation if callbacks are insufficient.
- Example:
```javascript
const statusPanel = document.getElementById('archive_status_panel');
const stacktracePanel = document.getElementById('archive_stacktrace_panel');

StatusStream.attach({
  element: statusPanel,
  channel: 'archive',
  runId: runid,
  logLimit: 3000,
  stacktrace: { element: stacktracePanel },
  onTrigger(detail) {
    if (detail.event === 'ARCHIVE_COMPLETE') archiveFinished();
  }
});
```

### 2.5 Migration guidance
- Prefer the new macros whenever you refactor a console or build a fresh control. Only fall back to `legacy_*` panels when the surrounding JS still depends on the old IDs.
- Conversion checklist:
  1. Import `controls/_pure_macros.html`.
  2. Wrap markup in `control_shell`; pass `collapsible=False` for non-collapsible consoles.
  3. Supply `status_panel` / `stacktrace_panel` overrides (or `''` to omit panels).
  4. Ensure `/static/js/controllers.js` is included so `StatusStream` is available.
  5. Call `StatusStream.attach` with the new IDs (`status_panel`, custom `log_id`, etc.).
  6. Verify query selectors in existing JS still match the rendered IDs (`status`, `stacktrace`, etc.).
- Live examples: `rq-fork-console.htm`, `rq-archive-dashboard.htm`, `query_console.html`.
- Run controls still rely on the legacy `_pure_base.htm` panels; migrate them once `controlBase` is StatusStream-aware.

---

## 3. Runs Page Layout (context)
- **Header**: fixed Pure header (run-specific variant includes name/scenario inputs, power user tools, readonly/public toggles).
- **Navigation**: left column Table of Contents (roughly 1/5 width) controlling tabs/anchors (`wc-run-layout__toc`, sticky on large screens).
- **Main content**: right column (≈4/5 width) containing controls stacked vertically inside `wc-run-layout__content`.
- **Footer**: command bar anchored to the bottom (full width).
- The new control shell must coexist with this layout; when embedded in other pages (e.g. batch runner) the same shell creates consistent styling.

---

## 4. Run Header Components
- Name and Scenario inputs use the `wc-run-header__field` pattern (see CSS). The forthcoming `header_text_field` macro abstracts the label/input layout.
- Action buttons (Readme, Fork, Archive, etc.) remain in the header toolbar; macros should not recreate them.
- Dropdown entries (`PowerUser`, `Browse`, `Unitizer`, `Readonly`, `Public`, `Access log`) remain accessible via header menu; layout guidance is captured in `header/_run_header_fixed.htm`.

---

## 5. Component Catalogue (macro inventory)
Every macro below now lives in `controls/_pure_macros.html` and is showcased inside `/ui/components/` (`component_gallery.htm`). Update both the macro and the gallery in tandem whenever arguments or markup change so reviewers can trace behaviour end-to-end.

- All field-style macros now accept an optional `error` argument. When provided, the macro flags the control as invalid (`aria-invalid="true"` on inputs or radiogroups), appends the error id to `aria-describedby`, and emits a `.wc-field__message.wc-field__message--error` block announced via `role="alert"`.

### 5.1 `header_text_field`
- **Purpose**: Run header inputs (Name, Scenario).
- **Layout**: `wc-run-header__field` – label and input stacked vertically on narrow screens, two-column on wide.
- **Args**: `field_id`, `label`, `value`, `placeholder`, optional `help`, `attrs`, optional `extra_class` for additional input classes.
- **Notes**: Debounced updates still handled by `Project` JS; macro simply renders markup/class names.
- **Status**: Implemented; see “Run Header Fields” section of the showcase.
- Secondary actions (Unitizer, PowerUser, Readonly/Public toggles, Access Log) live inside the `wc-run-header__menu` dropdown so the primary row stays compact.

### 5.2 `text_field`
- **Purpose**: Generic text input inside a card.
- **Layout**: Label above input; responsive width 100%. (Older 1/5 + 1/5 ratio replaced with Pure container widths.)
- **Args**: `field_id`, `label`, `value`, optional `help`, `placeholder`, `type` (default `text`), `attrs` (dict of extra HTML attributes).
- **Status**: Implemented; helper text now wires through `aria-describedby`.

### 5.3 `numeric_field`
- **Purpose**: Number input with optional unit display.
- **Layout**: Label, number input, optional unit suffix (e.g. `mm`, `mg/L`).
- **Args**: `field_id`, `label`, `value`, `unit_label`, optional `precision`, `min`, `max`, `required`, `nullable`, optional `unit_category`, optional `unit_name` (canonical unit string, e.g. `kg/ha`).
- **Notes**: When `unit_category` is provided the macro emits `data-unitizer-*` attributes (`data-unitizer-category`, `data-unitizer-unit`, `data-unitizer-label`) so `UnitizerClient` can keep labels in sync with user preferences.
- **Status**: Implemented with `data-precision` + `data-nullable`; unit label renders inside `.wc-field__unit` and now auto-updates via the static unitizer map.

### 5.4 `file_upload`
- **Purpose**: Upload control with help text and existing filename.
- **Layout**: Label above `<input type="file">`, help below, optional “current file” display.
- **Args**: `field_id`, `label`, `accept`, optional `help`, `current_filename`, `attrs`.
- **Notes**: Macro should include accessible description linking input to help text.
- **Status**: Implemented with `.wc-field__meta` for current filename display.

### 5.5 `radio_group`
- **Purpose**: Mode selectors (e.g. landuse mode, climate mode). Supports horizontal/vertical layouts.
- **Layout**: Option list plus optional static or mode-specific help block.
- **Args**: `name`, `layout` (`horizontal`/`vertical`), `options` (list of dicts: label, value, description, selected, disabled), optional `mode_help` (mapping value → help HTML).
- **Notes**: Should expose data attributes for HTMX or JS toggles.
- **Status**: Implemented with `.wc-choice-group`, per-option `attrs`, and `data-choice-help-*` hooks for JS toggles.

### 5.6 `select_field`
- **Purpose**: Standard `<select>` element with label/help.
- **Args**: `field_id`, `label`, `options` (list of `(value, text)`), `selected`, optional `help`, `attrs`.
- **Status**: Implemented and wired into the gallery as a legacy select comparison.

### 5.7 `checkbox_field`
- **Purpose**: Single checkbox with help text (e.g. `readonly`/`public`, `clip hillslopes`).
- **Layout**: Checkbox aligned with label; help text below.
- **Args**: `field_id`, `label`, `checked`, optional `help`, `attrs`.
- **Status**: Implemented with `.wc-choice--checkbox` styling.

### 5.8 `textarea_field`
- **Purpose**: Multi-line text (notes, CSV paste).
- **Args**: `field_id`, `label`, `value`, `rows`, optional `help`, `placeholder`.
- **Status**: Implemented.

### 5.9 `text_display`
- **Purpose**: Read-only block within a card (summaries, inline reports).
- **Layout**: Label in bold, content stacked below; may include HTML.
- **Args**: `label`, `content`, optional `variant` (info/success/warning), `actions` (links/buttons).
- **Status**: Implemented with `.wc-text-display--*` variants and optional action row.

### 5.10 `table_block`
- **Purpose**: Render tabular data (landuse, soils summaries).
- **Plan**: Macro will accept column definitions + rows, emit a Pure table with optional caption.
- **Next steps**: Prototype in showcase before migrating real tables.
- **Status**: First pass implemented using `wc-table`; still refine sortable/hybrid tables after we migrate landuse/soils panels.

### 5.11 `dynamic_slot`
- **Purpose**: Placeholder `<div>` for controller-managed DOM (e.g. map overlays, JS builders).
- **Layout**: Macro wraps a `<div>` with consistent padding/spacing so dynamic content blends with cards.
- **Args**: `slot_id`, optional `help`.
- **Notes**: Document which controls rely on custom JS so designers know what to expect.
- **Status**: Implemented; renders `.wc-dynamic-slot` with optional helper copy.

### 5.12 `collapsible_card`
- **Purpose**: Hide advanced/optional sections (filters, expert settings) behind an accessible toggle.
- **Layout**: `<details>` + styled `<summary>` header with rotating chevron and optional description; content area stacks children with standard spacing.
- **Args**: `title`, optional `description`, optional `expanded` (default false).
- **Status**: Implemented; `/ui/components/` demo wraps advanced options in the new card.

### 5.13 `status_panel`
- **Purpose**: Standard log surface for controls and console dashboards.
- **Layout**: `<section class="wc-status-panel" data-status-panel>` with optional header actions, descriptive text, and a monospace log body (`[data-status-log]`). CSS custom property `--wc-status-height` defaults to `20rem` (console variant) while `--wc-status-min-height` clamps to `12rem`; both can be overridden per panel.
- **Args**: `id`, optional `title`, `variant`, `meta` (HTML block above the log for job metadata or state chips), `description`, `actions`, `footer`, `log_id`, `aria_live`, `initial`. `height` accepts any CSS length (px, rem, etc.) and sets both custom properties (`--wc-status-height` and `--wc-status-min-height`) to keep the viewport fixed (for compact run controls, use ~`3.25rem`). Invoking the macro with `call` renders the caller block inside `wc-status-panel__slot` (useful for legacy IDs during migration).
- **Status**: Implemented; showcased with both variants. `StatusStream.attach({ element, channel, runId })` streams updates into `[data-status-log]`. Legacy helpers remain available as `legacy_status_panel()` until ControlBase is updated.

### 5.14 `stacktrace_panel`
- **Purpose**: Shared disclosure for exception payloads emitted by RQ jobs.
- **Layout**: `<details class="wc-stacktrace" data-stacktrace-panel>` with summary copy, optional actions, description, and a `<pre data-stacktrace-body>` target.
- **Args**: `id`, `summary`, optional `collapsed` (default true), `description`, `actions`, `body_id`, `empty_state`.
- **Status**: Implemented; paired with `StatusStream` stacktrace enrichment on the fork console and archive dashboard. Legacy `#stacktrace` panels remain until run controls migrate.

---

## 6. Showcase Expectations
- The `/ui/components/` gallery must demonstrate every macro and layout pattern. Treat it as the canonical example for contributors and reviewers.
- Before migrating production controls:
  1. Implement new/updated macros.
  2. Document usage here.
  3. Add an example to the showcase.
- Only after those steps should we refactor real controls (starting with a low-risk panel).
- Gallery callouts now cover header fields, numeric/unit patterns, radio groups, file uploads, text displays, tables, dynamic slots, and the collapsible advanced options container. Update the gallery snippet when adding new args (e.g., validation state, error messaging) so accessibility/layout regressions surface quickly.
- Dark-mode styling is intentionally deferred; stay focused on light theme polish and accessible contrast in `ui-foundation.css`.

---

## 7. Next Steps
1. Pilot the new macros on a low-risk production control (e.g. channel delineation) and document migration lessons in the inventory.
2. Finalise metadata contracts (what each macro expects from NoDb controllers: labels, units, validation rules).
3. Define validation/error state patterns (visual + ARIA) and extend macros once the contract is agreed.
4. Keep this document and the showcase in sync as each production control migrates.
