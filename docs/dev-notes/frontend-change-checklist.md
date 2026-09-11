# Frontend Change Checklist

Unified checklist for changing WEPPcloud controller JavaScript (`wepppy/weppcloud/controllers_js/`) and the paired backend/tests.

## 1. Pre-edit orientation
- [ ] Read the local playbooks and architecture notes:
  - `wepppy/weppcloud/controllers_js/AGENTS.md`
  - `wepppy/weppcloud/controllers_js/README.md`
  - `docs/dev-notes/controller_foundations.md`
  - `docs/dev-notes/module_refactor_workflow.md`
  - `docs/ui-docs/controller-contract.md` (controller invariants / required patterns)
- [ ] Identify the affected page templates under `wepppy/weppcloud/templates/` and confirm the existing `data-*` DOM hooks.
- [ ] Identify the paired Flask endpoints under `wepppy/weppcloud/routes/` and the current request/response payload expectations.
- [ ] Locate the current Jest suite(s) under `wepppy/weppcloud/controllers_js/__tests__/` and the current pytest coverage under `tests/weppcloud/`.
- [ ] If the controller can be enabled dynamically (mods dialog), review `docs/dev-notes/dynamic-mod-loading-patterns.md` before editing.
- [ ] Identify a comparable controller and shared macro for each presentation need using the [presentation contract](../ui-docs/controller-contract.md#established-presentation-conventions). Record the reference; reuse its conventions instead of inventing a one-off view.
## 2. Implementation steps
- [ ] Prefer the helper stack (`WCDom`, `WCEvents`, `WCHttp`, `WCForms`) plus `controlBase`/`StatusStream`; do not reintroduce jQuery or bespoke polling/WebSocket clients.
- [ ] Keep controllers and helpers as IIFEs that attach their intended public surface to `window` (consistent global namespaces and ordering assumptions).
- [ ] Wire UI via `data-*` hooks + delegated handlers; avoid inline `on*` handlers and template-embedded bootstrap scripts.
- [ ] Maintain/extend the controller’s event surface (domain events + `job:*` lifecycle) so other modules can subscribe without scraping DOM state.
- [ ] If outbound requests or payload shapes change, update the paired Flask routes in the same change (use `parse_request_payload` and preserve legacy behavior).
- [ ] Add or update Jest + pytest coverage for the changed behavior, payload coercion, and error paths.

### Mods-menu integration (required for selectable controls)

- [ ] Complete the [new-mod integration checklist](dynamic-mod-loading-patterns.md#required-integration-checklist), including hidden nav/section placeholders, full-page and dynamic bootstrap, and replacement-form binding.
- [ ] Verify declared enable dependencies and server visibility gates remain consistent during dynamic activation; place prerequisite controls before consumers.
- [ ] Test the actual disabled run template and `Project.set_mod` insertion/bootstrap, rather than only a controller fixture with its form already present.

## 3. Bundle rebuild (`build_controllers_js.py`)
- [ ] Rebuild the bundle: `python wepppy/weppcloud/controllers_js/build_controllers_js.py`.
- [ ] Confirm the updated output(s) are on disk (especially `wepppy/weppcloud/static/js/controllers-gl.js`) and reload the affected pages.
- [ ] If the “stale bundle” banner appears, confirm the bundle was rebuilt and the browser cache was bypassed.

## 4. Linting (`wctl run-npm lint`)
- [ ] Run: `wctl run-npm lint` (use `-- --fix` only when appropriate).

## 5. Jest tests (`wctl run-npm test`)
- [ ] Run: `wctl run-npm test` (target a single suite only while iterating; keep the full run green before handoff).

## 6. Pytest route tests (`wctl run-pytest tests/weppcloud/...`)
- [ ] Run the pytest module(s) that exercise the endpoint(s) you touched: `wctl run-pytest tests/weppcloud/...`.
- [ ] If shared helpers, common routes, or request parsing changed, finish with: `wctl run-pytest tests --maxfail=1`.

## 7. Stub/API surface checks (when exports changed)
- [ ] If Python import surfaces changed (new symbols, changed `__all__`, moved modules), run: `wctl run-stubtest <module>` and `wctl check-test-stubs`, then update any `sys.modules` stubs to match the real public API.
- [ ] If JS public surfaces changed (`window.*` namespaces, event names, `data-*` contracts), update the relevant Jest assertions and documentation in the same change.

## 8. Manual smoke test guidance
- [ ] Rebuild the bundle, reload with cache bypass, and exercise the primary flows end-to-end (click actions, submit forms, file uploads if applicable).
- [ ] Watch browser devtools for runtime errors and failed requests; verify `controlBase` + StatusStream telemetry (status panels, spinners, stacktraces) still behaves correctly.

- [ ] For selectable controls, start with an eligible never-used/off project: enable through the actual Mods checkbox without reload, verify a working action/readiness, disable/re-enable and act again, then reload to check persisted selection. Follow the [full validation matrix](dynamic-mod-loading-patterns.md#required-validation).

## 9. Documentation updates required
- [ ] Update `wepppy/weppcloud/controllers_js/README.md` and `wepppy/weppcloud/controllers_js/AGENTS.md` when helper usage, bundling, or workflow expectations change.
- [ ] Update the current canonical controller/domain contract when payload schema, events, or `data-*` hooks change. Keep active work-package evidence in sync; closed packages are history, not contract authority.
- [ ] If templates or route contracts changed, update the relevant route/blueprint notes you relied on so future edits follow the same workflow.
