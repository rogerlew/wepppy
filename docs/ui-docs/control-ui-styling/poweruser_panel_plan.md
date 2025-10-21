# PowerUser Panel Pure UI Migration Plan

## 1. Assessment Snapshot (2025-10-21)
- **Template**: `templates/controls/poweruser_panel.htm` currently relies on a Bootstrap modal (`.modal`, `.row`, `.col-md-6`) with inline `<style>` for sizing and layout.
- **Functionality**:
  - Lists NoDb/Log resources per controller and surfaces lock icons toggled by `preflight.js` (`updateLocks`).
  - Provides directory browse links, parquet dataset shortcuts, Disturbed actions, Omni migration button, and (hidden) system notification toggle that wires into web push helpers.
  - Uses `browse_url` helper macro to build run-scoped URLs and conditional sections guarded by `ron.mods`.
- **Pain Points**:
  - Bootstrap/inline CSS bloats markup and conflicts with Pure-first strategy.
  - Resource sections duplicate markup for each controller (no macro abstraction).
  - Modal structure diverges from Pure modal exemplar (`unitizer_modal.htm`), complicating shared styling and accessibility.
  - Action links/buttons mix Bootstrap classes (`btn`, `list-group`) with legacy affordances.

## 2. Migration Goals
1. **Pure Modal Scaffold**: Rebuild panel using modal patterns from `templates/controls/unitizer_modal.htm` and `ui-foundation.css` (flat borders, consistent padding).
2. **Responsive 4-Column Layout**:
   - Two columns for NoDb/Log resource groups (using new resource macro for consistent markup).
   - One column dedicated to directory/data links.
   - One column for action buttons (Disturbed, Omni migration, clear locks, etc.).
   - Desktop target: ~80% viewport width/height; stack columns gracefully on narrow viewports via Pure grid utilities (`pure-g`, `pure-u-md-*`).
3. **Component Macros**:
   - Introduce a Jinja macro (within `poweruser_panel.htm` or shared control macros) to render a resource block: header, optional lock icon, `NODB` & `LOG` buttons styled as `.pure-button.pure-button-secondary`.
   - Leverage existing link/button tokens: `wc-run-header__field` for headings, `.wc-link wc-link--file` for browse links, `.pure-button` variants for actions.
4. **Accessibility & Semantics**:
   - Ensure modal carries `role="dialog"` attributes from exemplar; keep close button semantics.
   - Use unordered lists for link groupings; convert legacy `.list-group` to semantic lists with `.wc-list`.
5. **JavaScript Compatibility**:
   - Preserve element IDs required by existing JS (`pu_*_lock`, action onclick handlers).
   - Keep notification toggle wiring intact but hidden unless flagged (match existing behaviour).

## 3. Implementation Outline
1. **Scaffold**:
   - Reuse modal wrapper from `unitizer_modal.htm` (Pure-compatible structure, minimal inline styles).
   - Apply `.wc-modal` classes (if available) or align custom wrapper with `ui-foundation` tokens.
2. **Macro Definition**:
   - Define `{% macro resource_block(id_prefix, label, nodb_path, log_path, show_condition=True) %}` within template.
   - Macro renders heading (`<div class="wc-run-header__field">`) and button row.
   - Include `<span id="pu_<id>_lock" data-poweruser-lock>` for JS toggles; keep `style="display:none;"` for backwards compatibility.
3. **Layout**:
   - Use a responsive CSS grid (`.pu-modal__grid`) that collapses to one column on mobile, two columns on medium screens, and four columns on wide desktops.
   - Column ordering:
     1. `Resources A-L` (Ron → Climate, conditional modules) via the macro.
     2. `Resources M-Z` (WEPP → Omni).
     3. `Browse & Data` (directory tree, parquet links) with `.wc-link wc-link--file`.
     4. `Actions` (Clear Locks, Disturbed, Omni migration, documentation) using `.pure-button` classes.
4. **Styling Hooks**:
   - Add minimal inline style block only for modal sizing (`height: 80vh`, `width: 80vw`) and component gaps, preferring existing tokens where possible.
   - For header fields, wrap label + run field with `.wc-run-header__field`.
5. **Content Parity Check**:
   - Ensure all conditional sections (`ron.mods` checks) preserved.
   - Keep `browse_url` macro for path generation.
   - Retain Disturbed/Omni `onclick` handlers and ensure they are buttons or `<a>` with `role="button"` styled appropriately.

## 4. Dependencies & Follow-Up
- **Docs**: After implementation, update `control-inventory.md` to mark PowerUser panel as Pure-converted.
- **JS**: Consider future enhancement to move lock toggle wiring into dedicated module (out of scope for this pass).
- **Accessibility**: Evaluate focus trapping and Escape handling shared with modal controller (`modal.js`).
- **Testing**:
  - Manual: open PowerUser panel, verify layout at ≥1280px and ≤768px widths, exercise links and actions.
  - Automated: none currently; explore Playwright smoke test once modal conversions accumulate.

## 5. Open Questions
1. Should the NoDb/Log buttons fire within same tab or new tab? (Legacy used `target="_blank"`; maintain for now.)
2. Where should shared resource macro live if reused elsewhere? (Short-term keep local; future iteration could add to `_pure_macros.html` if another control needs it.)
