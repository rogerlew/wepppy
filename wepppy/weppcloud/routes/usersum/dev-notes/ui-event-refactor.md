# UI Event Binding Refactor Plan

## Why this refactor
- The run page (and related viewer templates) still rely on a large, monolithic `on_document_ready.js.j2` script.
- Most UI events (button clicks, `input`/`change` handlers, map actions) are routed through jQuery code in that file, which then forwards to controller singletons.
- This pattern forces developers to touch three places—template markup, `on_document_ready`, and the relevant controller—to understand or change behaviour.
- Moving interaction logic closer to the templates/controllers improves discoverability, reduces boilerplate, and eases maintenance.

## Goals
1. **Inline controller hooks**: templates should call controller methods directly via `onclick`, `oninput`, or controller-specific helper functions, removing indirection from `on_document_ready`.
2. **Explicit controller APIs**: each controller exposes public methods (with validation/debouncing as needed) to handle its UI interactions.
3. **Eliminate duplicate wiring**: `on_document_ready` should shrink to global bootstrapping only (e.g., shared helpers, one‑time setup).
4. **Preserve cross-controller behaviour**: existing side effects (enabling colour maps, refreshing data, toggling modes) move into the controller methods where they are easier to reason about.
5. **Incremental safety**: carry out the refactor in auditable phases so we can verify behaviour at each step and roll back narrowly if needed.

## Implementation Overview
1. **Controller API audit**: document which DOM events map to which controller methods today. Identify missing public methods (e.g., debounced `Project.setNameFromInput`).
2. **Template updates**: for each form or control, replace jQuery bindings with inline `Controller.getInstance().method(...)` calls. Add data attributes or `addEventListener` code in templates where inline handlers aren’t suitable.
3. **Controller enhancements**: implement or adjust controller methods to encapsulate logic currently in `on_document_ready` (validation, debouncing, cross-controller notifications).
4. **Global helper cleanup**: migrate shared utilities (unit converters, find-and-flash, etc.) into dedicated static JS modules; keep `on_document_ready` for global boot only.
5. **Testing per phase**: after each migration phase, exercise the affected UI areas (unit tests/manual smoke tests) before moving on.

## Phased Plan
### Phase 1 – Project Metadata & Map Controls
- Implement debounced `setNameFromInput` / `setScenarioFromInput` in `Project` controller (including blur handling).
- Inline handlers for unitizer preference radios and “apply units” button.
- Move map “Go”, Topaz/Wepp search buttons, and Enter-to-search behaviour into template/controller methods using the `WEPP_FIND_AND_FLASH` helper.
- Trim corresponding sections out of `on_document_ready`.

### Phase 2 – Channel/Subcatchment Interactions
- Expose controller methods for channel build buttons (metric/imperial) with validation prompts.
- Inline colour-map radio bindings, slider updates, and cross-controller enablement into `ChannelDelineation` / `SubcatchmentDelineation`.
- Remove the map status updates/lockouts from `on_document_ready` into controller or map module as appropriate.

### Phase 3 – Landuse, Soils, Rangeland Cover
- Migrate landuse mode selection, single-selection dropdowns, and modify checkboxes to controller methods.
- Do the same for soils mode, database selection, rangeland cover modes, and modify toggles.
- Ensure controller trigger overrides (added earlier) perform any post-build enablement that used to happen in `on_document_ready`.

### Phase 4 – Climate & Unitizer Modal
- Add controller methods for climate station mode changes, station selection, precipitation scaling toggles, and single-storm fields (leveraging the new unit converter helper).
- Inline Unitizer modal controls (global preference + per-unit radios) and remove the generic `name^=unitizer_` binding from `on_document_ready`.

### Phase 5 – Remaining Controllers (Wepp, Omni, DSS, Ash, RHEM, Debris Flow, RAP TS)
- Move run/submit buttons, sliders, and other event handlers into templates referencing the existing controller methods (or create new ones where only jQuery logic exists).
- Ensure controller `triggerEvent` overrides still capture job completion behaviour.

### Phase 6 – Final Cleanup & Validation
- Strip any leftover event bindings from `on_document_ready`; the file should mainly initialize global helpers (unit converters, find/flash helper, etc.).
- Rebuild `static/js/controllers.js` and run `python -m compileall` for touched modules.
- Perform smoke tests across each controller pane (project name/scenario, map interactions, channel/subcatchment workflows, landuse/soil/climate, run/export flows).

## Notes
- Inline handlers should favour calling small, well-named controller methods rather than duplicating logic in markup.
- Where multiple controls share behaviour (e.g., metric/imperial pairs), consider data-driven helpers or controller utility functions to avoid repeated inline scripts.
- Keep accessibility in mind: keyboard interactions (Enter key, focus/blur) still need to be wired through the new controller methods.
- After each phase, re-run the controller bundle build (`wepppy/weppcloud/controllers_js/build_controllers_js.py`) and ensure the minified output ships with the deployment.

---
Document owner: Codex (draft). Please adjust/extend as we progress through the phases.
