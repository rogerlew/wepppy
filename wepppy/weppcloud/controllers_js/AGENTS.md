# controllers_js Agent Playbook

> Audience: AI coding agents working inside `wepppy/weppcloud/controllers_js/`.

## Mission Snapshot
- Maintain the run-controller bundle that powers WEPPcloud dashboards.
- Keep every controller aligned with the modernization program (helpers, unified payloads, documented contracts).
- Ensure the bundle build pipeline (`build_controllers_js.py`) and Jest suite stay green after every change.

## Foundations (read before coding)
See `docs/dev-notes/controller_foundations.md` for the canonical vision. Key pillars:
- **Shared UI primitives**: structure markup around `data-*` hooks so `WCDom`/`WCEvents` manage toggles, buttons, and lifecycle events consistently.
- **Unified payload schemas**: every controller/route pair runs through `parse_request_payload`; NoDb `parse_inputs` now expect native booleans/ints/floats (never `"on"` strings). Keep per-domain docs up to date.
- **Evolving `controlBase`**: treat it as the declarative job runner—prefer its lifecycle events (`job:started`, `job:completed`, `job:error`) over ad-hoc polling.
- **Documentation alignment**: when you add primitives or change payloads/events, update `controllers_js/README.md`, this playbook, and the domain contract doc.
- **Tooling expectations**: lint (`wctl run-npm lint`), test (`wctl run-npm test`), rebuild bundle, and run targeted pytest suites before handoff. Add Jest coverage when primitives or controller patterns evolve.

> Controllers should focus on domain logic while helpers + documented contracts handle the boilerplate. If you find yourself re-implementing plumbing, improve the shared primitives instead.

## Primary Assets
- Helpers: `dom.js`, `events.js`, `forms.js`, `http.js` (global namespaces exposed via IIFEs).
- Infrastructure: `control_base.js`, `status_stream.js`, `ws_client.js`, `unitizer_client.js`.
- Controllers: one file per control (`project.js`, `path_ce.js`, etc.).
- Template: `templates/controllers.js.j2` (rendered by `build_controllers_js.py`).
- Tests: `__tests__/` directory (Jest, jsdom environment).

## Standard Workflow
Follow `docs/dev-notes/module_refactor_workflow.md` for end-to-end instructions. Highlights:
1. **Scope**: audit jQuery usage, templates, backend routes, and domain documentation before editing.
2. **Plan**: decide which helpers (`WCDom`, `WCForms`, `WCHttp`, `WCEvents`, `controlBase`) you need and whether payloads switch to JSON.
3. **Implement**:
   - Use helper namespaces instead of direct DOM APIs; keep controllers wrapped in IIFEs that attach to `window`.
   - Update paired Flask routes in the same change using `parse_request_payload`; normalize booleans/arrays and adjust NoDb methods to read native types.
   - Remove inline jQuery bootstrap from templates; rely on module-level init or `DOMContentLoaded`.
4. **Document**: update `README.md`, this playbook, and any domain contract doc when behavior or payloads change.
5. **Validate**:
   - `wctl run-npm lint`, `wctl run-npm test` (or `wctl run-npm check`)
   - `python wepppy/weppcloud/controllers_js/build_controllers_js.py`
   - `wctl run-pytest tests/weppcloud/...` (targeted) and `wctl run-pytest tests --maxfail=1` when broad changes land.
   - Manual smoke test in the dev environment when practical.

## Controller Migration Tips
- Replace `$(selector)` with `WCDom.qs/qsa`, `delegate` for event delegation, and `toggle/hide/show` for visibility flips.
- Swap `$.ajax` or `$.get` with `WCHttp.request/getJson/postForm`.
- Use `WCForms.serializeForm` instead of `form.serialize()` and `WCForms.applyValues` for hydration.
- When controllers need event buses, prefer `WCEvents.createEmitter` or `WCEvents.emitDom`; `wepp.js` now emits `wepp:run:*` and `wepp:report:loaded` so neighbouring modules subscribe without polling DOM state.
- After refactoring, search for leftover `$(` in the module to ensure the jQuery dependency was removed.

### Project controller reference
- DOM hooks live on `data-project-field`, `data-project-toggle`, `data-project-action`, and `data-project-unitizer`. When the UI grows, add new `data-*` attributes and wire them through `WCDom.delegate` rather than binding inline handlers.
- `Project.getInstance().events` exposes a `WCEvents` emitter. Emitters currently surface `project:name:*`, `project:scenario:*`, `project:readonly:*`, `project:public:*`, and `project:unitizer:*` lifecycle events—subscribe instead of reading private state like `_currentName`.
- Unitizer integration now posts JSON payloads to `/tasks/set_unit_preferences/` and the backend returns the persisted preferences in `Content.preferences`. The global `window.setGlobalUnitizerPreference` helper simply forwards to `Project.handleGlobalUnitPreference`, so external scripts continue to function.
- Jest coverage for the controller lives in `__tests__/project.test.js`. When events, payloads, or data hooks change, expand that suite alongside template updates to lock in behaviour.

### Climate controller reference
- DOM hooks rely on `data-climate-action`, `data-climate-section`, and `data-precip-section` attributes plus the JSON seed embedded in `#climate_catalog_data`. Keep templates free of inline `on*` handlers—delegate through the controller instead.
- `Climate.getInstance().events` wraps `WCEvents.useEventMap` and currently publishes `climate:dataset:changed`, `climate:dataset:mode`, `climate:station:mode`, `climate:station:selected`, `climate:station:list:loading`, `climate:station:list:loaded`, `climate:build:started`, `climate:build:completed`, `climate:build:failed`, `climate:precip:mode`, `climate:upload:completed`, `climate:upload:failed`, and `climate:gridmet:updated`. Use these signals for dashboards and downstream automation.
- Network flows run through `WCHttp.postJson`/`request`; paired Flask routes now call `parse_request_payload` so JSON and form submissions behave the same. Update `wepppy/weppcloud/routes/nodb_api/climate_bp.py` alongside controller changes.
- Jest coverage lives in `controllers_js/__tests__/climate.test.js`; pytest coverage for the routes sits in `tests/weppcloud/routes/test_climate_bp.py`. Run both suites when editing climate code: `wctl run-npm test -- climate` (or the full suite) and `wctl run-pytest tests/weppcloud/routes/test_climate_bp.py`.
- After touching the controller, rebuild the bundle with `python wepppy/weppcloud/controllers_js/build_controllers_js.py` so the dev container picks up changes before you reload the UI.

### Ash controller reference
- DOM hooks rely on `data-ash-*` attributes (`data-ash-depth-mode`, `data-ash-action`, `data-ash-upload`) plus the JSON seed in `#ash-model-params-data`. Remove inline `on*` handlers—delegate through `WCDom`.
- `Ash.getInstance().events = WCEvents.useEventMap([...])` emits `ash:mode:changed`, `ash:model:changed`, `ash:transport:mode`, `ash:run:started`, `ash:run:completed`, and `ash:model:values:capture`. Emit new signals instead of mutating controller internals so dashboards can subscribe cleanly.
- The `/rq/api/run_ash` route now runs everything through `parse_request_payload` and `Ash.parse_inputs` consumes native booleans/ints/floats. Keep routes and NoDb signatures aligned when payloads evolve.
- Lint/test cadence: `wctl run-npm lint`, `wctl run-npm test -- ash`, `python wepppy/weppcloud/controllers_js/build_controllers_js.py`, and `wctl run-pytest tests/weppcloud/routes/test_rq_api_ash.py`. The Jest suite exercises depth-mode toggles, cache persistence, run submission, and error handling; pytest covers payload normalisation and RQ enqueue logic.


## Testing & Tooling Notes
- Jest config lives in `static-src/jest.config.mjs` (jsdom + ESM). Execute via `wctl run-npm test`; the script sets `NODE_OPTIONS=--experimental-vm-modules` automatically.
- ESLint config lives in `.eslintrc.cjs`. Run `wctl run-npm lint` (add `-- --fix` for auto-fixes) and prefer `wctl run-npm check` before handoff.
- Add new suites under `controllers_js/__tests__/` and keep them self-contained (each suite should import the helper(s) it exercises).
- If the bundle grows new helpers, document both usage and ordering in `README.md` and extend test coverage to guard the public API.
- `__tests__/landuse.test.js`, `__tests__/soil.test.js`, and `__tests__/wepp.test.js` exercise helper-based controllers; mirror their setup when migrating additional controls away from jQuery (stub helpers, bootstrap DOM, assert on helper calls, and verify lifecycle events).

## Communication
- If a change affects other repos (e.g., static assets build), annotate the summary so downstream maintainers can align.
- When you discover missing specs or conflicting docs, update this playbook and `README.md` together to keep humans and agents synchronized.
- Capture new primitives or helper upgrades in `docs/dev-notes/controller_foundations.md` so future agents inherit the context automatically.
