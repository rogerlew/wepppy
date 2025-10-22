# Debris Flow Controller Plan
> Modernization notes captured prior to refactoring the debris flow control stack.

## Current State
- `wepppy/weppcloud/controllers_js/debris_flow.js` still depends on jQuery for DOM lookup, click handlers, and AJAX job submission.
- Templates (`debris_flow*.htm`) wire command buttons via inline `onclick=` attributes and legacy IDs.
- The RQ API endpoint (`run_debris_flow`) ignores the request body and still expects jQuery-style POSTs.
- No dedicated Jest or pytest coverage exists for the control; route tests only exercise the read-only report view.

## Modernization Targets
- Replace jQuery usage with helper primitives: `WCDom`, `WCHttp`, `WCEvents`, and `controlBase`.
- Delegate DOM wiring through `data-debris-*` hooks to remove inline handlers and support partial render updates.
- Introduce a scoped event emitter that publishes lifecycle signals:
  - `debris:run:started`
  - `debris:run:completed`
  - `debris:run:error`
- Normalize outbound payloads to JSON (even if currently empty) so the backend can extend inputs without further template churn.

## Backend Alignment
- Update `run_debris_flow` to call `parse_request_payload` and accept structured booleans/numbers in the future.
- Ensure `RedisPrep` bookkeeping and exception handling remain unchanged while moving job metadata onto native types.
- Backfill pytest coverage using the shared factories:
  - `tests/factories/rq.py` (queue/Redis stubs)
  - `tests/factories/singleton.py` (NoDb-like stubs)

## Testing Checklist
- `wctl run-npm lint`
- `wctl run-npm test`
- `python wepppy/weppcloud/controllers_js/build_controllers_js.py`
- `wctl run-pytest tests/weppcloud/routes/test_debris_flow*.py`
- `wctl run-pytest tests --maxfail=1` if shared modules are touched.

## Documentation Touchpoints
- `wepppy/weppcloud/controllers_js/README.md` — describe the new event contract + data attributes.
- `wepppy/weppcloud/controllers_js/AGENTS.md` — add helper usage notes and testing expectations.
- `docs/god-tier-prompting-strategy.md` — mark the controller as modernized in Appendix A.

Keep this note updated if helper limitations or follow-up tasks surface during implementation.

## Implementation Notes (2025 helper migration)
- Controller now relies exclusively on `WCDom`, `WCHttp`, `WCEvents`, and `controlBase`, emitting lifecycle signals (`debris:run:started|completed|error`) alongside the existing `job:*` hooks. Delegated listeners watch `data-debris-action="run"` so the form remains script-free.
- Templates (`debris_flow.htm`, `debris_flow_pure.htm`) dropped inline handlers in favour of the data hook; status, stacktrace, and hint panels continue to use the shared control shell.
- Backend route `run_debris_flow` calls `parse_request_payload`, normalises optional `clay_pct`, `liquid_limit`, and `datasource` values, and forwards them to `run_debris_flow_rq(payload=...)`.
- `run_debris_flow_rq` now accepts the optional payload and passes native types to `DebrisFlow.run_debris_flow(cc=…, ll=…, req_datasource=…)`, preserving Redis timestamps and status broadcasts.
- Test coverage: Jest suite `controllers_js/__tests__/debris_flow.test.js`, route regression `tests/weppcloud/routes/test_rq_api_debris_flow.py`, and task coverage `tests/rq/test_project_rq_debris_flow.py`.

## Follow-ups
- `WSClient` still updates DOM via jQuery selectors; modernise the status/stacktrace bridge once the shared WebSocket client migrates.
- Surface optional payload fields (clay %, liquid limit, datasource preference) in the UI when product requirements solidify, then extend the controller and route validation accordingly.
