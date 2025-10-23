# Disturbed Controller Refactor Plan
> Status: Completed (helper-first controller migration). See [controllers_js Modernization Retrospective](./controllers_js_jquery_retro.md).

> Migration notes and post-refactor contract for the disturbed SBS control.

## Snapshot (2025-10-22)
- `controllers_js/disturbed.js` now adheres to the helper-first pattern: it boots through `controlBase`, `WCDom`, `WCForms`, `WCHttp`, and `WCEvents`, wires delegated handlers for every `data-sbs-*` / `data-disturbed-action` hook, and re-emits lifecycle telemetry alongside the inherited `job:started|completed|error` events.
- Power-user buttons (`Reset Disturbed Parameters`, `Load Extended Disturbed Parameters`) route through delegated handlers instead of inline JavaScript, with success/failure surfaced via the control panels.
- `has_sbs` is cached via the run bootstrap and refreshed asynchronously; consumers should subscribe to the `disturbed:sbs:state` domain event (or the legacy DOM `disturbed:has_sbs_changed` `CustomEvent`) instead of forcing synchronous checks.
- Flask routes accept native JSON payloads (`tasks/build_uniform_sbs`, `tasks/set_firedate`) and run through `parse_request_payload`. Uniform builds still honour the legacy `<value>` path while the controller prefers the JSON body.

## Event & Payload Contract
- **Domain emitter (plus controlBase job events)**
  - `disturbed:mode:changed` — fired whenever the SBS mode radios toggle.
  - `disturbed:sbs:state` — payload `{ hasSbs, source }`, mirrored via `CustomEvent('disturbed:has_sbs_changed')`.
  - `disturbed:lookup:reset`, `disturbed:lookup:extended`, `disturbed:lookup:error` — power-user lookup actions.
  - `disturbed:upload:*`, `disturbed:remove:*`, `disturbed:uniform:*`, `disturbed:firedate:*` — task-level lifecycle, emitted in parallel with `job:*` (`task` identifiers: `disturbed:upload`, `disturbed:remove`, `disturbed:uniform`, `disturbed:firedate`, `disturbed:lookup:reset`, `disturbed:lookup:extended`).
- **HTTP surfaces**
  - `tasks/reset_disturbed` — `POST`, empty body; resets the lookup CSV to defaults.
  - `tasks/load_extended_land_soil_lookup` — `POST`, empty body; hydrates extended lookup rows.
  - `tasks/upload_sbs/` — `POST FormData` (expects `input_upload_sbs`); returns WEPP validation metadata.
  - `tasks/remove_sbs` — `POST`, empty body; clears SBS rasters from Disturbed/BAER.
  - `tasks/build_uniform_sbs` — `POST JSON {"value": <int>}`; legacy `tasks/build_uniform_sbs/<value>` remains supported for older clients.
  - `tasks/set_firedate/` — `POST JSON {"fire_date": <str|null>}`; empty/null clears the value.
  - `api/disturbed/has_sbs/` — `GET`; response `{ "has_sbs": bool }`.
- **DOM hooks**
  - Control shell: `#sbs_upload_form` with `#info`, `#status`, `#stacktrace`, `#rq_job` plus hint nodes (`#hint_upload_sbs`, `#hint_remove_sbs`, `#hint_low_sbs`, `#hint_moderate_sbs`, `#hint_high_sbs`).
  - Buttons expose `data-sbs-action="upload|remove|set-firedate"`, uniform presets use `data-sbs-uniform`, and power-user buttons carry `data-disturbed-action="reset-lookup|load-extended-lookup"`.

## Testing Checklist
- **Jest** — `controllers_js/__tests__/disturbed.test.js` validates delegated events, event emission, cache refresh, and HTTP payload wiring (`wctl run-npm test -- disturbed`).
- **Pytest** — `tests/weppcloud/routes/test_disturbed_bp.py` now leans on `tests/factories.singleton_factory` + `tests/factories.rq_environment` to cover payload parsing and controller interactions (`wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py`).
- **Bundle** — `python wepppy/weppcloud/controllers_js/build_controllers_js.py`.
- **Final gate** — `wctl run-pytest tests --maxfail=1` when shared modules change.

## Follow-ups
- Update the Omni controller to consume `disturbed:sbs:state` instead of calling `has_sbs()` synchronously; this refactor unlocks full async behaviour.
- Consider extracting shared SBS hint helpers so BAER and Disturbed share status text styling.
- When introducing new SBS workflows (batch ingestion, advanced map validation), extend this contract first so future migrations stay aligned.
