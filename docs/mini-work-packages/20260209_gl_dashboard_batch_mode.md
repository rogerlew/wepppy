# Mini Work Package: GL Dashboard Additive Batch Mode With Composite Hillslope Keys
Status: Implemented (Batch Map MVP; Phase 6 Deferred)
Last Updated: 2026-02-10
Primary Areas: `wepppy/weppcloud/routes/gl_dashboard.py`, `wepppy/weppcloud/templates/gl_dashboard.htm`, `wepppy/weppcloud/static/js/gl-dashboard.js`, `wepppy/weppcloud/static/js/gl-dashboard/state.js`, `wepppy/weppcloud/static/js/gl-dashboard/layers/detector.js`, `wepppy/weppcloud/static/js/gl-dashboard/map/layers.js`, `wepppy/weppcloud/static/js/gl-dashboard/graphs/graph-loaders.js`, `wepppy/weppcloud/static/js/gl-dashboard/graphs/timeseries-graph.js`, `wepppy/weppcloud/static/js/gl-dashboard/data/*.js`, `tests/weppcloud/routes/*`, `wepppy/weppcloud/static/js/gl-dashboard/__tests__/*`, `wepppy/weppcloud/static-src/tests/smoke/*`

## Objective
Enable `gl-dashboard` to render a batch project (collection of runs) as one grouped watershed view by introducing an additive batch mode with string-normalized feature keys:

- Canonical key format: `<runid>-<topaz_id>`
- Canonical usage: all hillslope and channel joins, graph highlighting, and per-feature caches in batch mode

This work must preserve existing single-run behavior and minimize regression risk.

## Current State (As Built)
Batch mode currently supports:
- merged geometry: `resources/subcatchments.json`, `resources/channels.json`
- merged summaries (keyed by `feature_key`): landuse, soils, watershed/hillslopes
- run-aware tooltips and label de-dupe (no `TopazID` collisions)
- string-safe hover highlight (map <-> graph highlight IDs are strings)
- readiness gate: exclude runs missing required geometry; surface degraded optional endpoints in UI
- batch mode short-circuits async detection when no runs are ready (avoid accidental run-scoped fetches against `_base`)
- batch mode hides OpenET month slider (OpenET remains run-scoped)

Batch mode currently does not support:
- batch Query Engine fan-out (WEPP, RAP, OpenET, WATAR remain run-scoped)
- batch graphs beyond string-safe highlight plumbing (graph data remains run-scoped)
- Playwright batch smoke specs and performance telemetry (Phase 6)

## Problem Summary
- Batch projects contain multiple runs with overlapping `TopazID` / `topaz_id` values.
- Current `gl-dashboard` logic keys map and graph data by `topaz_id` only.
- Query Engine is run-scoped and does not support cross-run queries in one request, so grouped batch data requires per-run fan-out and merge.
- Current graph hover highlight path converts IDs with `parseInt`, which breaks string composite keys.

## Locked Decisions
1. Additive mode only: existing `/runs/<runid>/<config>/gl-dashboard` behavior remains unchanged.
2. Batch mode gets a separate route/context and provider path.
3. Batch feature identity is string-based and run-aware: `<runid>-<topaz_id>`.
4. Batch data loading uses bounded per-run fan-out and merge (no Query Engine cross-run change in this package).
5. Rollout is feature-flagged and reversible.

## Scope
- Add batch-specific dashboard entrypoint and bootstrap context.
- Add batch data provider that merges geometry and summaries across runs.
- Normalize all batch joins/highlight IDs to composite string keys.
- Add readiness/sync validation for runs in the batch.
- Add comprehensive automated test coverage and staged rollout checks.

## Non-goals
- No Query Engine protocol redesign for cross-run SQL.
- No breaking changes to current single-run omni/comparison route behavior.
- No broad UI redesign; only batch-mode compatibility and clarity additions.

## Batch Key Contract

### Canonical Key
- `feature_key = "<runid>-<topaz_id>"`
- Both `runid` and `topaz_id` are normalized with `String(...)` before concatenation.

### Required Stored Fields (Batch Mode)
- Geometry feature properties must carry:
  - `runid`
  - `topaz_id`
  - `feature_key`
- Summary maps must be keyed by `feature_key`, not raw `topaz_id`.
- Highlight state must carry `feature_key` as string end-to-end.

### Important Gotchas
- Do not parse the key with `parseInt` or numeric coercion at any point.
- Preserve `runid` and `topaz_id` separately for display/tooltips; do not rely on parsing `feature_key`.
- Label dedupe sets must use `feature_key` in batch mode to avoid cross-run suppression.
- Treat `ctx.mode === "batch"` as authoritative; do not use `ctx.batch.runs.length` to decide batch vs run behavior.

## Architecture Changes (Additive)

### Route and Context
- Add a batch dashboard route (for example `/batch/_/<batch_name>/gl-dashboard`) with:
  - `mode: "batch"`
  - batch run list and display labels
  - readiness metadata per run
- Keep current run route/context unchanged.

### Data Provider
- Add a batch provider layer responsible for:
  - loading per-run geometry (`resources/subcatchments.json`, `resources/channels.json`)
  - loading per-run summaries (landuse, soils, watershed/hillslopes)
  - merging outputs into batch-wide state keyed by `feature_key`
- Apply bounded concurrency and fail-soft behavior per run with explicit status reporting.

### Rendering/Graph Integration
- Batch mode map fill functions read `feature_key` from feature properties.
- Batch mode graph series IDs are `feature_key`.
- Map hover and graph hover both use string `feature_key` without numeric conversion.
- Tooltips show `Run` and `TopazID` fields for operator clarity.

## Multi-phase Implementation Plan

### Phase 0: Contract and Guard Rails
- Add a dedicated key utility contract for batch mode.
- Define strict invariants for ID handling (string-only, no numeric coercion).
- Add feature flag scaffolding (`GL_DASHBOARD_BATCH_ENABLED`).

Deliverables:
- Contract notes and helper signatures in gl-dashboard modules.
- Initial unit tests for key construction and identity invariants.

### Phase 1: Batch Route and Bootstrap
- Add batch dashboard route/context payload.
- Add template/bootstrap branch for `mode === "batch"`.
- Keep existing route/template context untouched in single-run mode.

Deliverables:
- New route handler and context serializer.
- Route tests for auth, context shape, and no regression on existing run route.

### Phase 2: Batch Data Adapter and Merge
- Implement per-run fan-out loader with bounded concurrency.
- Merge subcatchments/channels into one `FeatureCollection`.
- Inject `runid`, `topaz_id`, and `feature_key` into merged geometry.
- Re-key supported summary dictionaries by `feature_key` (landuse/soils/hillslopes).

Deliverables:
- Batch provider module and orchestrator wiring.
- Merge correctness tests (collision, missing artifacts, partial failures).

### Phase 3: Map Layer and Tooltip Compatibility
- Update batch-mode layer lookups to use `feature_key`.
- Update tooltip builders to surface run-aware metadata.
- Update label dedupe to use run-aware keys.

Deliverables:
- Batch-safe map layer rendering paths.
- Tooltip and label tests for duplicated `topaz_id` across runs.

### Phase 4: Graph and Highlight Pipeline
- Remove numeric ID coercion from graph hover/highlight path.
- Ensure series IDs and highlight callbacks are string-safe.
- Namespace graph caches by run-aware scenario identity.

Deliverables:
- String-safe highlight round-trip between map and graph.
- Tests covering hover/click highlight for composite IDs.

### Phase 5: Scenario/Sync Readiness Gates
- Validate run readiness before batch render (required datasets and outputs).
- Surface explicit statuses for excluded or degraded runs.
- Guard comparison paths against scenario mismatch across runs. (Deferred: comparison is currently not exposed in batch mode.)

Deliverables:
- Readiness checker and UI state messaging.
- Tests for mismatch, partial coverage, and graceful degradation.

### Phase 6: Hardening, Performance, and Rollout
- Add fan-out telemetry and timings.
- Validate target performance envelopes on representative batch sizes.
- Ship behind feature flag and stage rollout.

Deliverables:
- Performance baseline notes and rollout checklist.
- Smoke tests for batch mode happy path and partial-failure path.

## Thorough Test Plan

### A. JavaScript Unit Tests (gl-dashboard core)
- Add/extend tests under `wepppy/weppcloud/static/js/gl-dashboard/__tests__/`:
  - `batch-keys.test.js`: key normalization, uniqueness, and string invariants.
  - `batch-detector.test.js`: geometry + summary merge with repeated `topaz_id`.
  - `batch-tooltips.test.js`: tooltip includes run + TopazID and looks up by `feature_key`.
  - `batch-readiness.test.js`: required geometry exclusion + optional endpoint reporting.
  - `timeseries-graph-highlight.test.js`: no numeric coercion; highlight IDs remain strings.

Assertions:
- Two runs with same `topaz_id` produce two distinct rendered features.
- Hovering a graph series emits the correct string ID (batch composite keys supported).
- Tooltip includes both run and topaz identifiers.

### B. Python Route/Context Tests
- Add route tests under `tests/weppcloud/routes/`:
  - batch route returns batch context shape and run list.
  - unauthorized request behavior mirrors existing policy.
  - existing single-run route payload is unchanged.

Assertions:
- Single-run context keys remain backward compatible.
- Batch route only enabled when feature flag is on.

### C. Integration Tests (Data/Readiness)
Deferred (Phase 6): readiness coverage for WEPP outputs, scenario mismatch, and larger batch sizes.

Assertions:
- Missing runs are explicitly flagged.
- Available runs still render without silent key collisions.

### D. Frontend Smoke Tests (Playwright)
Deferred (Phase 6): batch smoke specs in `wepppy/weppcloud/static-src/tests/smoke/`.

### E. Performance/Scalability Checks
- Define benchmark scenarios (for example 2, 10, 25 runs in batch).
- Verify fan-out completes within acceptable startup budget and UI remains interactive.
- Validate bounded concurrency and retry/failure handling.

### F. Regression Gates (must pass before merge)
1. `wctl run-npm lint`
2. `wctl run-npm test`
3. `wctl run-pytest tests/weppcloud/routes --maxfail=1`
4. `wctl run-pytest tests --maxfail=1`
5. `wctl check-test-stubs` (if new stubs/import paths are introduced)

## Risk Register and Mitigations
- Key collision regression:
  - Mitigation: batch-only `feature_key` contract, collision-focused tests.
- Single-run regression:
  - Mitigation: additive route/provider split, explicit compatibility tests.
- Highlight mismatch:
  - Mitigation: remove numeric coercion; enforce string ID invariant tests.
- Performance regression from fan-out:
  - Mitigation: bounded concurrency, phased load, baseline benchmarks.
- Partial batch failures hidden from users:
  - Mitigation: readiness panel and explicit excluded-run reporting.

## Acceptance Criteria
- Batch mode renders grouped watersheds with no cross-run key collisions.
- Batch highlight, tooltip, and graph interactions are run-aware and string-safe.
- Single-run `gl-dashboard` behavior remains unchanged.
- Readiness mismatch/failure states are explicit and non-silent.
- All regression gates and new batch-mode tests pass.

## Suggested Execution Order
1. Implement Phase 0 + Phase 1 and lock contracts with tests.
2. Implement Phase 2 + Phase 3 with map-level correctness tests.
3. Implement Phase 4 for graph/highlight string safety.
4. Implement Phase 5 + Phase 6 for readiness, performance, and rollout hardening.

## Validation (As Run)
- `wctl run-npm lint`
- `wctl run-npm test`
- `wctl run-pytest tests/weppcloud/routes/test_gl_dashboard_route.py tests/weppcloud/routes/test_gl_dashboard_batch_route.py`
