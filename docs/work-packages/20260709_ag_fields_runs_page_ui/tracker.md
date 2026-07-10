# Tracker - AgFields Runs-Page UI

> Living document tracking progress, decisions, risks, validation, and handoffs for the AgFields pure-CSS runs-page control implementation.

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-09 23:21 UTC
**Current phase**: Acceptance pending (Milestones 1-5 complete)
**Last updated**: 2026-07-09 23:53 UTC
**Next milestone**: Milestone 6 — manual walkthrough on a fresh AgFields project
**Security impact**: `low` — no new backend surface; browser client reuses existing rq-engine session bearer tokens
**Dedicated security review**: `no`
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] Milestone 6: manual four-stage walkthrough on a fresh small-watershed `ag-fields` project. It waits on maintainer project creation because `copacetic-note` no longer exists; completion closes this package's acceptance and the backend package's real-binary E2E limitation.

### Done
- [x] Package scaffold created with package brief, tracker, active ExecPlan, and root tracker registration (2026-07-09 23:21 UTC).
- [x] Milestone 1: four-stage `ag_fields_pure.htm` control and accessible rotation mapping modal (2026-07-09 23:53 UTC).
- [x] Milestone 2: dynamic-safe `ag_fields.js` controller, snapshot-only gating, uploads, mapping, job streams/poll fallback, exact job keys, and 409 retention (2026-07-09 23:53 UTC).
- [x] Milestone 3: initial/dynamic runs-page wiring, real registry template, `experimental` maturity, and user visibility (2026-07-09 23:53 UTC).
- [x] Milestone 4: authenticated named sub-fields overlay and rebuild refresh through `addGeoJsonOverlay` (2026-07-09 23:53 UTC).
- [x] Milestone 5: focused/full frontend tests, Python render/registry/bootstrap coverage, lint, and bundle rebuild (2026-07-09 23:53 UTC).

## Timeline

- **2026-07-09 23:21 UTC** - Package scaffolded as the successor to `20260709_ag_fields_backend_readiness` (closed same day). Sequencing decision: UI ships first, then a fresh project (copacetic-note no longer exists) provides the acceptance walkthrough that also closes the backend package's real-binary E2E gap.
- **2026-07-09 23:53 UTC** - Milestones 1-5 implemented. Dynamic mod loading now resolves the real template/controller; the user guide documents the four-stage UI; registry maturity is `experimental`.
- **2026-07-09 23:53 UTC** - Focused AgFields Jest passes 10 tests; affected Python render/registry/bootstrap group passes 135 tests; frontend lint and full Jest pass; controller bundle rebuild succeeds.
- **2026-07-09 23:53 UTC** - Full Python sweep stopped at an unrelated deterministic Batch Runner failure after 2070 passes and 41 skips. Isolated rerun reproduced the same missing `/wc1/batch/...` fixture path; no Batch Runner changes were made under this package.

## Decisions Log

### 2026-07-09: UI before fresh-project creation
**Context**: No seeded AgFields project exists; both the UI and the backend's real-binary E2E need one. The project could be created first (validating the backend by scripting JWT routes) or after the UI ships.

**Decision**: Implement the UI first. A single manual walkthrough on the new project then validates UI, backend routes, Peridot on a fresh watershed, and the real WEPP binary in one pass — no throwaway API scripting. UI development itself needs no seeded data (Jest + fixture-driven hydration). Risk accepted: latent backend defects reachable only in real runs surface late, but they sit behind a tested HTTP contract, so fixes are internal and will not churn the UI.

### 2026-07-09: Backend defects found during UI work are findings, not scope
**Context**: The backend package is closed; UI integration is the first real consumer of its surface.

**Decision**: Defects surfaced by UI work are recorded here as findings and fixed in scoped follow-up commits referencing this package. This package's own scope stays template/controller/wiring.

### 2026-07-09: Preserve overlay authentication through an injected loader
**Context**: The overlay resource requires `rq:status`, while the shared map helper previously used unauthenticated `getJson` only.

**Decision**: Add an optional `loadJson` callback to `addGeoJsonOverlay` and supply an AgFields callback backed by `requestWithSessionToken`. Do not put tokens in URLs and do not add a public backend alias.

### 2026-07-09: Experimental means user-visible for this shipped control
**Context**: The registry entry was an internal Dev-only placeholder even though the package objective is to ship an experimental runs-page control.

**Decision**: Set the real section template, `maturity: experimental`, `internal_reason: null`, and `min_role: user`. Wire both initial render and dynamic enablement.

### 2026-07-09: Defer controller-module splitting until acceptance
**Context**: The complete four-stage controller is about 1,700 lines, entering the repository's observe-only yellow band for JavaScript file size.

**Decision**: Preserve the established one-controller-per-control structure for v1 because all sections share one snapshot and job lifecycle. Reassess extraction after the manual walkthrough if concrete maintenance friction appears; do not invent helper boundaries before the first real UI run.

## Validation

- `wctl run-npm lint` — passed.
- `wctl run-npm test -- ag_fields` — 10 passed.
- `wctl run-npm test -- map_gl` — 37 passed.
- `wctl run-npm test -- project` — 25 passed.
- `wctl run-npm test` — 85 suites, 619 tests passed.
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py tests/weppcloud/routes/test_feature_registry_runtime.py tests/weppcloud/routes/test_run_0_openet_admin_gate.py` — 135 passed, 5 warnings.
- `python wepppy/weppcloud/controllers_js/build_controllers_js.py` — passed; generated bundle contains `AgFields`.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` — passed, net broad-exception delta `+0`.
- `wctl run-pytest tests --maxfail=1` — repository gate failed outside package scope after `2070 passed, 41 skipped`: `tests/nodb/test_batch_runner.py::test_run_batch_project_does_not_delete_workspace_when_rmtree_disabled`; isolated rerun failed identically.
- Acceptance walkthrough evidence (Milestone 6) remains required: stage-by-stage notes plus output listing under `wepp/ag_fields/output/`.

## Handoffs

- Fresh AgFields project creation (Roger): small agricultural watershed; `ag-fields` config; observed climate years must match the boundary GeoJSON's crop-year columns; boundary file needs a literal `field_id` column; plant zip from the USDA rotation builder or weppcloud management ids for the mapping.
- On acceptance completion, update `20260709_ag_fields_backend_readiness` closure notes to record that the real-binary E2E limitation is closed.
- Do not archive the active ExecPlan or close this package until the fresh-project walkthrough is recorded.
