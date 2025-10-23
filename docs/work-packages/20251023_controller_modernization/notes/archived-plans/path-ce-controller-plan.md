# Path CE Controller Modernization Plan
> Status: Completed (helper-first controller migration). See [controllers_js Modernization Retrospective](./controllers_js_jquery_retro.md).

> Working notes for migrating the PATH Cost-Effective control to the helper-first architecture.

## Current State (Oct 2025)
- `wepppy/weppcloud/controllers_js/path_ce.js` now uses the shared helper stack (`WCDom`, `WCForms`, `WCHttp`, `WCEvents`, `controlBase`) with scoped emitters, delegated events, and helper-driven polling.
- Templates (`controls/path_cost_effective_pure.htm`) expose `data-pathce-action`/`data-pathce-field` hooks so the controller wires behaviour without inline handlers; the run page bootstrap simply instantiates the singleton.
- The Flask blueprint (`routes/nodb_api/path_ce_bp.py`) normalises payloads through `parse_request_payload`, coerces floats/arrays/severity filters, and persists typed values into `PathCostEffective.config`.
- Jest coverage lives in `controllers_js/__tests__/path_ce.test.js`; backend assertions live in `tests/weppcloud/routes/test_path_ce_bp.py`, both relying on shared factories (`singleton_factory`, `rq_environment`).
- Telemetry flows through `controlBase` job lifecycle events with domain-specific signals (`pathce:*`) for dashboards and neighbouring controls.

## Target Architecture
- Controller should depend exclusively on helper primitives:
  - `WCDom` for DOM lookups, templated row rendering, delegated events.
  - `WCForms` to serialize threshold/treatment inputs.
  - `WCHttp` for fetch + JSON handling, aligned with centralized error handling.
  - `WCEvents` to expose domain events (`pathce:*`) and consume `controlBase` job lifecycle (`job:*`).
  - `controlBase` to orchestrate RQ job wiring, stacktrace/status updates, and lifecycle telemetry.
- Templates move to data-driven hooks:
  - Replace inline `onclick` with `data-action` triggers (`data-pathce-action="save"`, etc.).
  - Table rows rendered via `<template>` or string builder using helper-friendly structure.
  - Status/summary sections remain but use predictable IDs for helper writing (`data-status-target`, `data-summary-target`).
- Flask routes normalize inputs through `parse_request_payload` and pass native types to `PathCostEffective.config`.
  - Boolean, numeric, and list fields should be typed (`severity_filter: list[str] | None`, `slope_range: tuple[float | None, float | None] | None`).
  - Ensure responses follow unified `{ "config": ... }` / `{ "results": ... }` schema.

## Implementation Tasks
1. **Controller Rewrite**
   - Rebuild singleton to cache DOM targets (`form`, `summary`, `hint`, `treatments tbody`).
   - Implement treatment row rendering via helper-managed document fragments.
   - Move polling to `controlBase` job lifecycle: poll status/results until terminal state.
   - Emit events:
     - `pathce:config:loaded` after GET.
     - `pathce:treatment:added/removed/updated` as edits occur.
     - `pathce:run:started/completed/error` around job submissions.
2. **Template Alignment**
   - Swap inline handlers for delegated buttons.
   - Add data attributes (`data-pathce-role`, `data-pathce-action`) to inputs/buttons for WCDom selectors.
   - Ensure bootstrap snippet simply instantiates controller via DOM-ready helper (no inline `PathCE.getInstance()` duplication).
3. **Backend Updates**
   - Replace raw JSON parsing with `parse_request_payload(request)`.
   - Validate/shape payload before assigning to controller.
   - Extend blueprint responses to include job metadata (`job_id`) consistent with other modules.
   - Confirm NoDb controller already handles floats; extend if mixed types appear during testing.
4. **Testing**
   - Add Jest suite covering:
     - Config load hydrates DOM.
     - Add/remove treatments updates state + events.
     - Save/run actions call `WCHttp` with expected payloads.
     - Polling path handles success/error.
   - Pytest: expand `tests/weppcloud/routes/test_path_ce*.py` to cover config POST normalization via `parse_request_payload` and result/status GETs.
   - Use shared factories (`tests/factories/rq_environment.py`, `singleton_factory.py`) for route scaffolding.

## Risks & Follow-Ups
- **Available scenario list** currently derived from config defaults; verify Omni scenario naming remains consistent post-migration.
- **Severity filter**: ensure `None` vs empty list semantics remain unchanged for solver defaults.
- **Polling interval**: align with `controlBase` defaults to avoid spamming API (~800ms vs current 5s). Might need throttle adjustments—capture metrics after migration.
- **Docs/README**: Update `controllers_js/README.md`, `AGENTS.md`, and this note once refactor lands to reflect new payload/event contracts.

## Acceptance Checklist
- [x] Controller free of jQuery usage.
- [x] Templates wired via helper-friendly `data-*` hooks.
- [x] Flask routes accept typed payloads through `parse_request_payload`.
- [x] Jest + pytest suites cover new flows.
- [x] Documentation updated (controller README/AGENTS, this plan).
- [x] Final handoff logs commands executed (`wctl run-npm lint/test`, bundle rebuild, pytest runs).

_Last updated: 2025-10-22_
