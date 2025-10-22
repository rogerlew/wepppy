# controllers_js Agent Playbook

> Audience: AI coding agents working inside `wepppy/weppcloud/controllers_js/`.

## Mission Snapshot
- Maintain the run-controller bundle that powers WEPPcloud dashboards.
- Continue the migration away from jQuery towards the vanilla helper namespaces (`WCDom`, `WCHttp`, `WCForms`, `WCEvents`).
- Keep the bundle build pipeline (`build_controllers_js.py`) and Jest suite green whenever controllers or helpers change.

## Primary Assets
- Helpers: `dom.js`, `events.js`, `forms.js`, `http.js` (global namespaces exposed via IIFEs).
- Infrastructure: `control_base.js`, `status_stream.js`, `ws_client.js`, `unitizer_client.js`.
- Controllers: one file per control (`project.js`, `path_ce.js`, etc.).
- Template: `templates/controllers.js.j2` (rendered by `build_controllers_js.py`).
- Tests: `__tests__/` directory (Jest, jsdom environment).

## Standard Workflow
1. **Survey dependencies**: use `build_controllers_js.py` to confirm load order and make sure new helpers or controllers are added to `PRIORITY_MODULES` when needed.
2. **Implement / refactor**: prefer the helper namespaces instead of direct DOM APIs; keep modules wrapped in IIFEs that attach to `window`.
3. **Keep exports global**: work with existing singleton pattern (`var Foo = function () { … }();`) unless refactoring plan says otherwise.
4. **Update documentation**: adjust `README.md` when architectural or usage patterns change.
5. **Validate**:
   - Build bundle: `python wepppy/weppcloud/controllers_js/build_controllers_js.py`
   - Run tests from static sources: `cd wepppy/weppcloud/static-src && npm test`
   - Re-run bundle if helper ordering changed.

## Controller Migration Tips
- Replace `$(selector)` with `WCDom.qs/qsa`, `delegate` for event delegation, and `toggle/hide/show` for visibility flips.
- Swap `$.ajax` or `$.get` with `WCHttp.request/getJson/postForm`.
- Use `WCForms.serializeForm` instead of `form.serialize()` and `WCForms.applyValues` for hydration.
- When controllers need event buses, prefer `WCEvents.createEmitter` or `WCEvents.emitDom`.
- After refactoring, search for leftover `$(` in the module to ensure the jQuery dependency was removed.

## Testing & Tooling Notes
- Jest config lives in `static-src/jest.config.mjs` (jsdom + ESM). `npm test` already sets `NODE_OPTIONS=--experimental-vm-modules`.
- Add new suites under `controllers_js/__tests__/` and keep them self-contained (each suite should import the helper(s) it exercises).
- If the bundle grows new helpers, document both usage and ordering in `README.md` and extend test coverage to guard the public API.

## Communication
- If a change affects other repos (e.g., static assets build), annotate the summary so downstream maintainers can align.
- When you discover missing specs or conflicting docs, update this playbook and `README.md` together to keep humans and agents synchronized.
