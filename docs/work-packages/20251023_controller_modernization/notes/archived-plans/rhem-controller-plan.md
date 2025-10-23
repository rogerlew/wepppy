# RHEM Controller Modernization Plan
> Status: Completed (helper-first controller migration). See [controllers_js Modernization Retrospective](./controllers_js_jquery_retro.md).

> Helper-first migration blueprint for the Rangeland Hydrology and Erosion Model workflow.

## 1. Current Status (2025 refresh)
- **Controller**: `wepppy/weppcloud/controllers_js/rhem.js` now boots via `controlBase()` and the helper stack (`WCDom`, `WCForms`, `WCHttp`, `WCEvents`). Lifecycle signals surface through `rhem.events = WCEvents.useEventMap(['rhem:config:loaded', 'rhem:run:started', 'rhem:run:queued', 'rhem:run:completed', 'rhem:run:failed', 'rhem:status:updated'])` plus the inherited `job:*` events.
- **Telemetry**: The controller now calls `controlBase.attach_status_stream` so log/stacktrace panels attach through the shared helper. `appendStatus` fans updates to both the DOM and the helper emitter so dashboards stay synchronised.
- **Templates**: `controls/rhem_pure.htm` and `controls/rhem.htm` expose `data-rhem-action="run"` on the command button, keep status/stacktrace/hint/job nodes under `#rhem_form`, and render report results inside `#rhem-results`. Optional stage toggles bind to checkbox inputs (`name="clean"`, `name="prep"`, `name="run"`).
- **Backend**: `/rq/api/run_rhem_rq` now runs requests through `parse_request_payload`, coercing the stage booleans before enqueuing `run_rhem_rq(payload=…)`. The RQ task honours those flags—skipping `clean()`, `prep_hillslopes()`, or `run_hillslopes()` when instructed—while continuing to publish StatusStream output. Reporting endpoints (`rhem_bp.py`) still authorize and render templates without modification.
- **Tests**: Helper behaviour is covered by `controllers_js/__tests__/rhem.test.js`. Backend endpoints are exercised by `tests/weppcloud/routes/test_rhem_bp.py` and `tests/weppcloud/routes/test_rq_api_rhem.py`, both relying on `tests.factories.singleton_factory` + `tests.factories.rq`.

## 2. Target Architecture & Event Contract
- Depend exclusively on `WCDom`, `WCForms`, `WCHttp`, `WCEvents`, and `controlBase` for setup.
- Publish scoped events to describe lifecycle transitions:
  - `rhem:config:loaded` — fired after bootstrapping DOM references/state.
  - `rhem:run:started` / `rhem:run:completed` / `rhem:run:failed` — include `{ jobId, runId }`.
  - `rhem:status:updated` — whenever status/stacktrace panes change.
- Leverage `controlBase` job helpers instead of overriding `triggerEvent`; rely on `StatusStream` hooks for telemetry.

## 3. Front-End Refactor Outline
- Controller initialisation now resolves DOM nodes via `WCDom.ensureElement/qs`, wraps legacy panels with lightweight adapters, and wires delegated interactions through `WCDom.delegate("[data-rhem-action='run']")`.
- Payload submission relies on `WCForms.serializeForm(form, { format: "object" })` to capture native booleans before calling `WCHttp.postJson("rq/api/run_rhem_rq", payload, { form })`.
- Status updates flow through `StatusStream.attach` via `controlBase.attach_status_stream`. Both paths invoke `rhem.triggerEvent` so helper subscribers and `controlBase` telemetry stay aligned.
- `rhem.report()` now pulls HTML via `WCHttp.request(url_for_run(...))`, refreshes the info/results panels, emits `rhem:run:completed`, and triggers the `job:completed` lifecycle for `controlBase`.

## 4. Backend Alignment Tasks
- `/rq/api/run_rhem_rq` now consumes JSON or legacy form posts via `parse_request_payload`, coercing `clean`, `prep`, and `run` booleans. Non-empty payloads are forwarded to `run_rhem_rq` as `payload=…`.
- `run_rhem_rq` accepts the optional payload and honours flags by skipping the relevant stages while logging skips to the StatusStream channel.
- Reporting/query endpoints in `rhem_bp.py` continue to authorize, fetch NoDb instances, and render templates. Future updates should keep IDs/data attributes in sync with the helper-based controller.

## 5. Testing Strategy
- **Jest**: `controllers_js/__tests__/rhem.test.js` asserts helper bootstrap, delegated actions, lifecycle emissions, and error handling (HTTP failure + non-success payloads). Keep this suite up to date when events or payload semantics change.
- **Pytest**:
  - `tests/weppcloud/routes/test_rhem_bp.py` verifies authorisation, template rendering, and JSON responses from the query endpoints.
  - `tests/weppcloud/routes/test_rq_api_rhem.py` ensures the queue wiring honours payload booleans and maintains RedisPrep bookkeeping.

Recommended command set before handoff:
```bash
wctl run-npm lint
wctl run-npm test -- rhem
python wepppy/weppcloud/controllers_js/build_controllers_js.py
wctl run-pytest tests/weppcloud/routes/test_rhem_bp.py
wctl run-pytest tests/weppcloud/routes/test_rq_api_rhem.py
```

## 6. Template Updates
- Run buttons rely on `data-rhem-action="run"`; keep this attribute when modifying templates.
- Status, stacktrace, hint, and job nodes must stay scoped to `#rhem_form` so `controlBase`/`StatusStream` wiring continues to function.
- Optional stage toggles should remain native checkboxes (`name="clean"`, `name="prep"`, `name="run"`) to preserve boolean coercion. Document any additional payload fields in this plan and the controller README.

## 7. Follow-Ups & Open Questions
- Determine whether future UX needs to expose stage toggles in the UI (currently checkboxes are optional). If so, document the payload contract and update Jest/Pytest coverage accordingly.
- Identify downstream consumers that should subscribe to `rhem:run:*` or `rhem:status:updated` and document expectations (dashboards, notifications).
- Historical note: the legacy shim emitted TRIGGER tokens; the alias has now been removed.
