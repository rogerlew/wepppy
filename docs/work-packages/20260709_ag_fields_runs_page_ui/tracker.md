# Tracker - AgFields Runs-Page UI

> Living document tracking progress, decisions, risks, validation, and handoffs for the AgFields pure-CSS runs-page control implementation.

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-09 23:21 UTC
**Current phase**: Acceptance pending (Milestones 1-5 complete)
**Last updated**: 2026-07-10 21:52 UTC
**Next milestone**: Milestone 6 acceptance with `wepp_dcc52a6`
**Security impact**: `low` — no new backend surface; browser client reuses existing rq-engine session bearer tokens
**Dedicated security review**: `no`
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] Milestone 6: rerun Stage 4 on `sacral-self-discipline` with
  `wepp_dcc52a6` and record full-project output evidence.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Package scaffold created with package brief, tracker, active ExecPlan, and root tracker registration (2026-07-09 23:21 UTC).
- [x] Milestone 1: four-stage `ag_fields_pure.htm` control and accessible rotation mapping modal (2026-07-09 23:53 UTC).
- [x] Milestone 2: dynamic-safe `ag_fields.js` controller, snapshot-only gating, uploads, mapping, job streams/poll fallback, exact job keys, and 409 retention (2026-07-09 23:53 UTC).
- [x] Milestone 3: initial/dynamic runs-page wiring, real registry template, `experimental` maturity, and user visibility (2026-07-09 23:53 UTC).
- [x] Milestone 4: authenticated named sub-fields overlay and rebuild refresh through `addGeoJsonOverlay` (2026-07-09 23:53 UTC).
- [x] Milestone 5: focused/full frontend tests, Python render/registry/bootstrap coverage, lint, and bundle rebuild (2026-07-09 23:53 UTC).
- [x] Follow-up: persisted uploaded-boundary-filename display and additive state hydration contract (2026-07-10 16:38 UTC).
- [x] Follow-up: explicit project-UTM support/precision contract, actionable ambiguous-CRS diagnostics, and regression coverage (2026-07-10 16:57 UTC).
- [x] Follow-up: persisted WEPP Exec selector, `wepp_dcc52a6` new-project default, pinned RQ propagation, automatic UI worker sizing, and content-width clear action (2026-07-10 21:52 UTC).

## Timeline

- **2026-07-09 23:21 UTC** - Package scaffolded as the successor to `20260709_ag_fields_backend_readiness` (closed same day). Sequencing decision: UI ships first, then a fresh project (copacetic-note no longer exists) provides the acceptance walkthrough that also closes the backend package's real-binary E2E gap.
- **2026-07-09 23:53 UTC** - Milestones 1-5 implemented. Dynamic mod loading now resolves the real template/controller; the user guide documents the four-stage UI; registry maturity is `experimental`.
- **2026-07-09 23:53 UTC** - Focused AgFields Jest passes 10 tests; affected Python render/registry/bootstrap group passes 135 tests; frontend lint and full Jest pass; controller bundle rebuild succeeds.
- **2026-07-09 23:53 UTC** - Full Python sweep stopped at an unrelated deterministic Batch Runner failure after 2070 passes and 41 skips. Isolated rerun reproduced the same missing `/wc1/batch/...` fixture path; no Batch Runner changes were made under this package.
- **2026-07-10 16:38 UTC** - Stage 1 gained a dedicated current-file display hydrated from optional `boundary.filename`. New uploads persist the source basename; historical projects fall back to `fields.WGS.geojson`; canonical artifact names remain unchanged.
- **2026-07-10 16:57 UTC** - Fresh-project acceptance reached Stage 2 on `sacral-self-discipline`. DEM is `EPSG:32611`; uploaded bounds are incompatible with WGS84/project UTM and appear consistent with unlabeled `EPSG:5070`. Rasterization now explicitly recognizes unlabeled project-UTM coordinates and reports project EPSG/bounds for ambiguous inputs; acceptance awaits a corrected export.
- **2026-07-10 20:06 UTC** - Corrected `EPSG:32611` boundaries advanced the
  walkthrough to Stage 4. The first run exposed `ncrop=50`; the management
  hardening package reduced p3733 to 3 plants/10 operations and added ADR-0016
  ingestion normalization for Jim-interface residue-only `hmax=0`. Wired replay
  clears both validation errors and next fails at `frcfac.for:184` because the
  residue operation leaves random roughness at zero.
- **2026-07-10 21:43 UTC** - Exact normalized p3733 comparison established that
  `wepp_dcc52a6` completes all 17 years while `wepp_260430` and `wepp_260606`
  SIGFPE at `frcfac.for:184`. Stage 4 follow-up started to make the AgFields
  executable explicit and persisted; ADR-0017 records the new-project default.
- **2026-07-10 21:52 UTC** - Stage 4 follow-up completed. The state snapshot
  hydrates `wepp.wepp_bin`; run submission validates and pins the installed
  executable; the worker persists it before automatic parallel execution. The
  Maximum workers control is removed, and the clear action uses intrinsic width.

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

### 2026-07-10: Use an AgFields-owned WEPP executable
**Context**: The repaired p3733 input completes under `wepp_dcc52a6`, while both tested newer binaries fail in the same `frcfac` arithmetic path. The parent watershed executable is not necessarily safe for imported agricultural managements.

**Decision**: Add an independent, persisted AgFields WEPP executable. New `ag-fields.cfg` projects default to `wepp_dcc52a6`; historical payloads without the additive field continue using the parent WEPP executable until explicitly changed. Remove worker tuning from the browser while retaining the optional backend argument for compatibility. See ADR-0017.

## Validation

- `wctl run-npm lint` — passed.
- `wctl run-npm test -- ag_fields` — 10 passed.
- `wctl run-pytest tests/nodb/mods/test_ag_fields_backend_contract.py tests/microservices/test_rq_engine_ag_fields_routes.py tests/weppcloud/routes/test_pure_controls_render.py::test_ag_fields_control_renders_required_dom_contract` — 47 passed after the current-file follow-up.
- `wctl run-pytest tests/nodb/mods/test_ag_fields_rasterize_crs.py` — 3 passed; covers unlabeled project-UTM acceptance, correctly declared alternate-projection reprojection, and actionable ambiguous-projection failure.
- `wctl run-npm test -- map_gl` — 37 passed.
- `wctl run-npm test -- project` — 25 passed.
- `wctl run-npm test` — 85 suites, 619 tests passed.
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py tests/weppcloud/routes/test_feature_registry_runtime.py tests/weppcloud/routes/test_run_0_openet_admin_gate.py` — 135 passed, 5 warnings.
- `python wepppy/weppcloud/controllers_js/build_controllers_js.py` — passed; generated bundle contains `AgFields`.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` — passed, net broad-exception delta `+0`.
- `wctl check-test-stubs` — passed. `wctl run-stubtest wepppy.nodb.mods.ag_fields.ag_fields` still reports 21 preexisting AgFields stub-surface omissions; none names the new source-filename property or updated validation signature.
- Focused executable follow-up Python suite — 61 passed (NoDb initialization/persistence/historical fallback, RQ propagation, route validation/state, and template contract).
- `wctl run-npm test -- ag_fields` — 10 passed after selector hydration/submission coverage.
- `wctl run-npm test` — 85 suites, 619 tests passed after the Stage 4 follow-up.
- `wctl run-npm lint` — passed after the Stage 4 follow-up.
- `wctl check-rq-graph` — passed after regenerating the canonical RQ graph/catalog for the pinned `wepp_bin` job argument.
- Scoped documentation lint — passed for the work package, ADR-0017, AgFields README, and end-user guide.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` — passed with net delta `+0`.
- `wctl run-pytest tests --maxfail=1` — repository gate failed outside package scope after `2070 passed, 41 skipped`: `tests/nodb/test_batch_runner.py::test_run_batch_project_does_not_delete_workspace_when_rmtree_disabled`; isolated rerun failed identically.
- Acceptance walkthrough evidence (Milestone 6) remains required: stage-by-stage notes plus output listing under `wepp/ag_fields/output/`.

## Handoffs

- Fresh AgFields project creation (Roger): small agricultural watershed; `ag-fields` config; observed climate years must match the boundary GeoJSON's crop-year columns; boundary file needs a literal `field_id` column; plant zip from the USDA rotation builder or weppcloud management ids for the mapping.
- On acceptance completion, update `20260709_ag_fields_backend_readiness` closure notes to record that the real-binary E2E limitation is closed.
- Do not archive the active ExecPlan or close this package until the fresh-project walkthrough is recorded.
