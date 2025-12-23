# WEPP Controller Migration Plan
> Status: Completed (helper-first controller migration). See [controllers_js Modernization Retrospective](../../../../dev-notes/controllers_js_jquery_retro.md).

> Checklist and findings for migrating `wepp.js` and related routes to the helper-driven architecture. Pair this with [docs/dev-notes/controller_foundations.md](../../../../dev-notes/controller_foundations.md) for shared UI and payload guidance.

## Controller Surface Audit
- Replace legacy DOM hooks (`addEventListener`, inline scripts, jQuery-era adapters) with helper delegates:
  - `WCDom.delegate` now powers `[data-wepp-action]` buttons, `[data-wepp-routine]` toggles, and cover transform uploads.
  - A scoped `WCEvents` emitter exposes `wepp:run:started`, `wepp:run:queued`, `wepp:run:completed`, `wepp:run:error`, and `wepp:report:loaded` so neighbouring controllers subscribe without reading DOM state.
- Status plumbing stays on `controlBase` + `StatusStream`; run submission swaps to `WCHttp.postJson` with `WCForms.serializeForm(..., { format: 'json' })`.
- ✅ Controller code now operates entirely on helper namespaces; lifecycle signals are emitted through the new event map and cover transform UI reacts via helper delegation.

## Template Contract
- Run button and advanced options live within `wepp_form`; data attributes (`data-wepp-action`, `data-wepp-routine`, `data-wepp-role="reveg-scenario"`) drive delegation.
- Inline `<script>` blocks removed from `wepp_pure_advanced_options/revegetation.htm`; visibility toggled by controller logic. The user-defined container retains its `hidden` attribute unless the saved scenario is `user_cover_transform`.
- ✅ Template markup exposes consistent IDs (`#wepp_form`, `#wepp_status_panel`, etc.) and only minimal `data-*` additions were required for delegation.

## Backend Touchpoints
- `wepp_bp.tasks.set_run_wepp_routine` already relied on `parse_request_payload`; no additional changes beyond JSON posts were required.
- `/rq/api/run_wepp` now:
  - normalises JSON/Form data via `parse_request_payload`,
  - strips run-control booleans before forwarding remaining fields to `Wepp.parse_inputs`,
  - converts numeric/boolean toggles for Soils/Watershed settings, and
  - preserves descriptive errors from `exception_factory`.
- `Wepp.parse_inputs` accepts native numbers, booleans, and list payloads (`chn_topaz_ids_of_interest`, `kslast`) while safely ignoring unsupported sentinel values.
- ✅ Added `tests/weppcloud/routes/test_wepp_bp.py::test_run_wepp_accepts_json_payload` coverage for typed inputs and Redis job wiring. No additional stubs required for downstream RQ flow.

## Testing & Tooling
- Jest (`controllers_js/__tests__/wepp.test.js`):
  - Verifies lifecycle events, delegated routine toggles, cover transform uploads, report refreshes, and error propagation.
- Pytest:
  - `tests/weppcloud/routes/test_wepp_bp.py` exercises JSON payloads, Soils/Watershed toggles, cover transform loading, and Redis queue setup.
- Tooling expectations remain:
  - `python wepppy/weppcloud/controllers_js/build_controllers_js.py`
  - `wctl run-npm lint`
  - `wctl run-npm test`
  - `wctl run-pytest tests/weppcloud/routes/test_wepp_bp.py`
  - (broader) `wctl run-pytest tests --maxfail=1`
- ✅ Updated playbooks (`controllers_js/README.md`, `controllers_js/AGENTS.md`) call out the WEPP event emitter, lint/test commands, and Jest suite location.

## Rollback Guidance
- Reverting controller changes restores the previous helper-light implementation; ensure `controllers_js/build_controllers_js.py` re-runs so `controllers-gl.js` reflects the rollback.
- Backend rollback requires undoing `api_run_wepp`/`Wepp.parse_inputs` changes; tests above will fail if typed payload support is removed, signalling any mismatch.
- Monitor `wepp:run:*` event consumers and Redis TaskEnum hooks when toggling between versions; both surfaces provide quick regression signals.
