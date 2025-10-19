# Control Components (Pure UI Draft)

This note captures the design contract for the new Pure.css-based control shell and component macros.  
Use it alongside:
- `docs/ui-docs/control-ui-styling/control-inventory.md` – catalog of every production control and the data each field exposes.
- `/ui/components/` showcase route – living gallery that demonstrates each macro in isolation. The showcase must be updated whenever we change or add components.

Goal: define a consistent, minimal component set that we can apply to existing controls with zero ambiguity.

---

## 1. Control Architecture

### 1.1 Shell (`controls/_pure_base.htm`)
- Wraps an entire control (title, optional toolbar, inputs, status panels).
- Renders a two-column grid on wide screens: left for form content, right for status/summary/stacktrace panels. On small screens it collapses to single column.
- Default sidebar:
  - **Status panel** (`#rq_job`, `#status`, `#braille`).
  - **Summary panel** (`#info`).
  - **Details panel** (`#stacktrace`, hidden until populated).
- Controls can override sidebar sections by redefining `control_sidebar` block.
- Macros in `_pure_macros.html` emit the same structure when a block-based approach is more convenient.

### 1.2 Card Layout
- Each control should group related inputs into “cards”. A card is a simple section containing a heading (optional) and a stack of components.
- Cards live in the primary column (`wc-control__inputs`) and use our spacing utilities; the showcase provides canonical spacing.
- When a control has multiple logical sub-sections (e.g. Batch Runner intake/validation), use multiple cards.

### 1.3 Status & Stacktrace
- Located inside the shell sidebar; should not be re-implemented inside individual controls.
- Stacktrace panel is hidden by default; ControlBase JS toggles it when data arrives. Mimics existing behavior from run0, RQ console, archive dashboard.

---

## 2. Runs Page Layout (context)
- **Header**: fixed Pure header (run-specific variant includes name/scenario inputs, power user tools, readonly/public toggles).
- **Navigation**: left column Table of Contents (roughly 1/5 width) controlling tabs/anchors.
- **Main content**: right column (≈4/5 width) containing controls stacked vertically; controls scroll.
- **Footer**: command bar anchored to the bottom (full width).
- The new control shell must coexist with this layout; when embedded in other pages (e.g. batch runner) the same shell creates consistent styling.

---

## 3. Run Header Components
- Name and Scenario inputs use the `wc-run-header__field` pattern (see CSS). The forthcoming `header_text_field` macro abstracts the label/input layout.
- Action buttons (Readme, Fork, Archive, etc.) remain in the header toolbar; macros should not recreate them.
- Dropdown entries (`PowerUser`, `Browse`, `Unitizer`, `Readonly`, `Public`, `Access log`) remain accessible via header menu; layout guidance is captured in `header/_run_header_fixed.htm`.

---

## 4. Component Catalogue (planned macros)
Each macro will live in `controls/_pure_macros.html` (or an adjacent module once the API stabilises). Until the macro exists, treat the description as the contract we’ll implement in the showcase before migrating production controls.

### 4.1 `header_text_field`
- **Purpose**: Run header inputs (Name, Scenario).
- **Layout**: `wc-run-header__field` – label and input stacked vertically on narrow screens, two-column on wide.
- **Args**: `field_id`, `label`, `value`, `placeholder`, optional `help`, `attrs`.
- **Notes**: Debounced updates still handled by `Project` JS; macro simply renders markup/class names.

### 4.2 `text_field`
- **Purpose**: Generic text input inside a card.
- **Layout**: Label above input; responsive width 100%. (Older 1/5 + 1/5 ratio replaced with Pure container widths.)
- **Args**: `field_id`, `label`, `value`, optional `help`, `placeholder`, `type` (default `text`), `attrs` (dict of extra HTML attributes).

### 4.3 `numeric_field`
- **Purpose**: Number input with optional unit display.
- **Layout**: Label, number input, optional unit suffix (e.g. `mm`, `mg/L`).
- **Args**: `field_id`, `label`, `value`, `unit_label`, optional `precision`, `min`, `max`, `required`, `nullable`.
- **Notes**: Macro should include a slot/hook for unitizer integration (data attributes).

### 4.4 `file_upload`
- **Purpose**: Upload control with help text and existing filename.
- **Layout**: Label above `<input type="file">`, help below, optional “current file” display.
- **Args**: `field_id`, `label`, `accept`, optional `help`, `current_filename`, `attrs`.
- **Notes**: Macro should include accessible description linking input to help text.

### 4.5 `radio_group`
- **Purpose**: Mode selectors (e.g. landuse mode, climate mode). Supports horizontal/vertical layouts.
- **Layout**: Option list plus optional static or mode-specific help block.
- **Args**: `name`, `layout` (`horizontal`/`vertical`), `options` (list of dicts: label, value, description, selected, disabled), optional `mode_help` (mapping value → help HTML).
- **Notes**: Should expose data attributes for HTMX or JS toggles.

### 4.6 `select_field`
- **Purpose**: Standard `<select>` element with label/help.
- **Args**: `field_id`, `label`, `options` (list of `(value, text)`), `selected`, optional `help`, `attrs`.

### 4.7 `checkbox_field`
- **Purpose**: Single checkbox with help text (e.g. `readonly`/`public`, `clip hillslopes`).
- **Layout**: Checkbox aligned with label; help text below.
- **Args**: `field_id`, `label`, `checked`, optional `help`, `attrs`.

### 4.8 `textarea_field`
- **Purpose**: Multi-line text (notes, CSV paste).
- **Args**: `field_id`, `label`, `value`, `rows`, optional `help`, `placeholder`.

### 4.9 `text_display`
- **Purpose**: Read-only block within a card (summaries, inline reports).
- **Layout**: Label in bold, content stacked below; may include HTML.
- **Args**: `label`, `content`, optional `variant` (info/success/warning), `actions` (links/buttons).

### 4.10 `table_block` *(WIP)*
- **Purpose**: Render tabular data (landuse, soils summaries).
- **Plan**: Macro will accept column definitions + rows, emit a Pure table with optional caption.
- **Next steps**: Prototype in showcase before migrating real tables.

### 4.11 `dynamic_slot`
- **Purpose**: Placeholder `<div>` for controller-managed DOM (e.g. map overlays, JS builders).
- **Layout**: Macro wraps a `<div>` with consistent padding/spacing so dynamic content blends with cards.
- **Args**: `slot_id`, optional `help`.
- **Notes**: Document which controls rely on custom JS so designers know what to expect.

---

## 5. Showcase Expectations
- The `/ui/components/` gallery must demonstrate every macro and layout pattern. Treat it as the canonical example for contributors and reviewers.
- Before migrating production controls:
  1. Implement new/updated macros.
  2. Document usage here.
  3. Add an example to the showcase.
- Only after those steps should we refactor real controls (starting with a low-risk panel).

---

## 6. Next Steps
1. Finish implementing outstanding macros (`numeric_field`, `radio_group`, `table_block`, etc.) and wire them into the showcase.
2. Finalise metadata contracts (what each macro expects from NoDb controllers: labels, units, validation rules).
3. Decide migration order (likely static forms first, then file uploads, then dynamic builders).
4. Update this document as macros land to keep reviewers informed.
