# Map Control Migration Plan

## 1. Goals
- Realign the map control with the Pure/Pure-derived architecture outlined in `control-components.md`.
- Eliminate Bootstrap grid/tab dependencies and inline styling; rely on the shared `ui-foundation.css` tokens and macros.
- Improve composability so the map can be embedded outside `runs0` without bespoke wrappers.
- Surface a clearer contract for JS integrations (`map.js`, legend rendering, drilldown queries) and identify where HTMX can replace custom jQuery wiring.

## 2. Current State Assessment
| Area | Findings |
| --- | --- |
| Layout wrapper | `div.col-md-11.controller-section` with nested Bootstrap grids. Status/summary blocks from `_base.htm` are bypassed entirely. |
| Go-to form | Raw `<form>` with Bootstrap classes, inline handlers (`onclick="MapController..."`). No use of `text_field`/`button_row`. |
| Map canvas | Hard-coded `<div id="mapid">` with adjacent `.row` for status/elevation text. Inline `&nbsp;` used for spacing. |
| Side panel tabs | Bootstrap nav tabs + `.tab-pane` content; JS relies on `new bootstrap.Tab(...)`. Content mixes markup and includes (modify landuse, rangeland, results). Legends and sliders use Bootstrap grid for alignment. |
| JS contracts | `map.js` manipulates DOM through IDs (`#mapstatus`, `#mouseelev`, `#drilldown`, `#sub_legend`, etc.) and instantiates Bootstrap tabs. Queries use jQuery AJAX. |
| Visual styling | Inline styles for icons, canvases, legends; inconsistent typography; no reuse of `wc-panel` or spacing tokens. |

## 3. Target Architecture
### 3.1 Shell selection
- Extend `control_shell` with a `show_panels=False` (or similar) option so it can render without the status/summary/stacktrace column when a control only needs its own layout. The map caller can then lay out the map canvas + inspector within the shell body using Pure grid utilities; no separate `map_shell` macro is needed.
  - Header (Map title, instructions, toolbar actions).
  - Primary split layout: left column map canvas, right column tabbed inspector.
  - Optional status footer (center/zoom text, elevation readout).
- Consider building `map_shell` on top of `control_shell` with `collapsible=False`, leveraging `status_panel_override=''` and `stacktrace_panel_override=''`, while providing a custom grid inside the caller block for the map + tabs. Alternative: add a new macro `split_shell(left, right)` so map and inspector stay composable.

### 3.2 Form + control macros
- Replace the “go to location” row with macros:
  - `text_field('centerloc', ...)` for the coordinate input (attach JS via `attrs={'data-action': 'enter'}` or event listeners).
  - `button_row()` for Go/Find buttons, using `wc-inline` utilities to align icons (swap raw `🔍` text with `<span class="wc-icon">` or the shared icon macro once available).
- Expose ARIA labels and placeholder text via macro parameters; keep IDs (`input_centerloc`, `btn_setloc`) for JS compatibility.

### 3.3 Map canvas + status
- Wrap `<div id="mapid">` in a `.wc-map` container with dimensions controlled in CSS (`ui-foundation.css`).
- Use a small `status_panel` with `height="3.25rem"` or a dedicated `.wc-status` row to display center/zoom/elevation. Provide JS hooks via IDs (`mapstatus`, `mouseelev`).

### 3.4 Tab system
- Bootstrap tabs must be replaced. Add a new macro pair:
  - `ui.tab_nav(tabs=[{id, icon, label, active}])`
  - `ui.tab_content(id, active=False)` or a higher-level `ui.tabs` macro to manage ARIA attributes and keyboard behaviour.
- Tabs should be accessible (role="tablist" / `aria-controls` / `aria-selected`). Consider the WAI-ARIA Authoring Practice (manual arrow key nav). Provide minimal JS helper (could be Pure/vanilla) to handle activation.
- Each tab body can still include existing templates (`modify_landuse.htm`, etc.), but the wrapper should expose `wc-tab` classes for consistent spacing.

### 3.5 Legend and visualization controls
- Create macros for repeated structures:
  - `ui.color_scale(id_base, title, range_id, canvas_id, min_id, max_id, units_id=None)` to encapsulate slider + canvas + min/max labels.
  - `ui.radio_inline` for the radio clusters (hillslope visualizations, ash transport, etc.).
- Replace inline `<div class="row">` alignments with flex utilities (`wc-flex`, `wc-space-between`). Introduce small utility classes in `ui-foundation.css` if needed (e.g., `.wc-colorbar`, `.wc-slider-group`).

### 3.6 Drilldown panel & results
- The “drilldown” tab currently injects HTML via jQuery and `bootstrap.Tab`. After migrating tabs, adjust `MapController.hillQuery` to call the new tab activation helper.
- Opportunity: replace manual jQuery `.get` with HTMX `<div hx-get="..." hx-trigger="selectmap" hx-target="#drilldown">`. The JS could dispatch a custom event when a feature is clicked; HTMX listens and loads the partial. Evaluate feasibility:
  - For first pass, keep existing AJAX logic but ensure tab activation works without Bootstrap.
  - Document HTMX option for future iteration (e.g., `hx-post` for `goToEnteredLocation`).

## 4. JavaScript Considerations
- Remove Bootstrap tab dependency (`bootstrap.Tab`). Replace with a lightweight controller that toggles `aria-selected`/`hidden`. Provide helper `MapTabs.activate(tabId)`.
- Ensure existing selectors (`#mapstatus`, `#mouseelev`, `#sub_legend`, `#sbs_legend`, `#drilldown`) remain intact or update `map.js` accordingly.
- Add data attributes for new macro-based markup (e.g., `<div data-map-status>`). Bind events using `document.querySelector('[data-map-status]')` to decouple from IDs if desired.
- If HTMX adoption is pursued, update endpoints to return partial fragments (existing templates might already be partial-compatible). Add CSRF tokens if necessary.

## 5. Proposed Macros / Utilities
| Macro/Utility | Purpose | Notes |
| --- | --- | --- |
| `ui.map_shell` (new) | Layout wrapper for map & inspector | Accepts slots for map pane, status footer, right-column content. Could be implemented via `control_shell` + custom CSS. |
| `ui.tabset` & `ui.tab_panel` (new) | Pure-based tabs | Inline JS or Alpine snippet for activation; apply `role="tablist"`. |
| `ui.color_scale` (new) | Slider + canvas + min/max labels | Accepts IDs to keep JS in sync. |
| `.wc-map`, `.wc-map__status` (CSS) | Map container + status row | Define height, border, spacing using tokens. |
| `.wc-tab`, `.wc-tab__nav`, `.wc-tab__panel` (CSS) | Tab system styling | Replace Bootstrap `.nav-tabs` / `.tab-pane`. |
| `.wc-legend`, `.wc-legend__canvas`, `.wc-legend__labels` (CSS) | Align colorbars | Simplify repeated inline styles. |


## 7. Implementation Phases
1. **Prep & Macro work**
   - Implement `ui.tabset`, `ui.map_shell`, `ui.color_scale` macros + supporting CSS.
   - Add documentation/examples to `/ui/components/` showcase and `control-components.md`.
2. **Template migration**
   - Refactor `controls/map.htm` to use new macros, removing Bootstrap classes and inline styles.
   - Update included partials (`map/wepp_hillslope_visualizations.htm`, etc.) to use macros (`ui.radio_inline`, `ui.color_scale`).
3. **JavaScript alignment**
   - Replace Bootstrap Tab usage in `map.js` with new activation helper.
   - Update selectors to match macro-generated markup; ensure overlay/legend hooks still function.
   - Optionally introduce HTMX scaffolding for drilldown; otherwise, adapt existing jQuery AJAX to new DOM.
4. **Styling & QA**
   - Verify map layout responsiveness (large desktop vs. tablets).
   - Ensure legends, sliders, and tab icons align with tokens (`wc-text-muted`, spacing utilities).
   - Run lint/test suite where applicable; perform manual smoke tests (center search, Topaz/Wepp ID search, drilldown, overlay toggles).

## 8. Risks & Dependencies
- **Prerequisites:** Ensure `ui.tabset`, `color_scale`, and supporting CSS land (along with any map-specific utilities such as `.wc-map`, `.wc-map__status`) before starting the template migration.
- **Leaflet resize quirks**: changing the surrounding layout may require calling `map.invalidateSize()` after tab activation/resizing.
- **Canvas/legend dimensions**: macros must output predictable widths for colorbars; double-check with dynamic data.
- **JS selectors**: keep `map.js` hooks (for example `#mapstatus`, `#mouseelev`, `#drilldown`) intact or update the controller in the same change to avoid regressions.
- **Embedded includes**: `modify_landuse.htm` and rangeland templates also contain Bootstrap markup—plan separate migrations or wrap them with new macros.
  - Refactor `modify_landuse.htm` using the shared macros: wrap it in `control_shell(collapsible=False, show_panels=False)` (or an equivalent lightweight wrapper) and render the checkbox via `ui.checkbox_field`, the Topaz ID textarea via `ui.textarea_field`, the landuse select via `ui.select_field`, and the submit button inside `button_row()`.
  - Add a compact status region with `status_panel(height="3.25rem", log_id='status')` and a `stacktrace_panel(body_id='stacktrace')` so `LanduseModify` continues to target the same elements.
  - Preserve existing element IDs by passing `attrs={'id': 'checkbox_modify_landuse'}` (and similar) when calling the macros, ensuring `LanduseModify` JS hooks remain valid.
  - Replace inline styles and Bootstrap classes (`form-group`, `.btn`) with `wc-stack` spacing utilities and `.pure-button` variants, leaning on `ui-foundation.css` tokens.
- **HTMX adoption**: optional follow-up; keep the existing jQuery flow operational until a dedicated event/data contract is defined.

## 9. References
- `wepppy/weppcloud/controllers_js/map.js`
- `wepppy/weppcloud/templates/controls/map.htm`
- `wepppy/weppcloud/templates/controls/map/wepp_hillslope_visualizations.htm`
- `docs/ui-docs/control-ui-styling/control-components.md`
- `docs/ui-docs/ui-style-guide.md`
- `docs/ui-docs/control-ui-styling/final-implementation-blueprint.md`

## 10. Next Steps
- Confirm macro naming and placement (`_pure_macros.html` vs. dedicated map macro file).
- Draft the new macros + CSS scaffolding.
- Iterate on the template conversion in a feature branch; validate JS interactions and consider HTMX enhancements as a follow-up if time allows.

## 11. Implementation Notes (2025-10-19)
- Map control now renders through `control_shell(collapsible=False)` with the panel column suppressed when overrides resolve to empty strings.
- Introduced `.wc-map-*` layout helpers, `wc-map-controls`, and `wc-map-grid` utilities in `ui-foundation.css` to replace Bootstrap rows/columns. Status text lives inside `.wc-map-status` with the legacy IDs intact.
- Replaced Bootstrap nav-tabs with `ui.tabset`; a lightweight `createTabset` helper in `map.js` handles activation, keyboard navigation, and fires `wc-tabset:change`.
- All legacy inline event handlers were removed. `map.js`, `landuse_modify.js`, and `rangeland_cover_modify.js` now bind the necessary listeners during controller initialisation.
- `modify_landuse` and `modify_rangeland_cover` partials use shared field macros plus compact `status_panel`/`stacktrace_panel` overrides, keeping `#status`/`#stacktrace` endpoints for existing JS.
- WEPP/RHEM hillslope visualisation templates swapped ad-hoc markup for `radio_group` + `color_scale` macros. Legends use the new `.wc-map-scale` wrapper and retain the IDs consumed by `SubcatchmentDelineation`.
- Component gallery documents the tabset and color scale macros (gradient demo included); `control-components.md` captures the new arguments and map layout helpers.
