# Tracker - AgFields Runs-Page UI

> Living document tracking progress, decisions, risks, validation, and handoffs for the AgFields pure-CSS runs-page control implementation.

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-09 23:21 UTC
**Closed**: 2026-07-10 22:40 UTC
**Current phase**: Complete
**Last updated**: 2026-07-11 02:28 UTC
**Next milestone**: None; one follow-up filed (persisted `_wepp_bin` gap on the acceptance project, see Handoffs)
**Security impact**: `low` — no new backend surface; browser client reuses existing rq-engine session bearer tokens
**Dedicated security review**: `no`
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Package scaffold created with package brief, tracker, active ExecPlan, and root tracker registration (2026-07-09 23:21 UTC).
- [x] Milestone 6: full Stage 4 run on `sacral-self-discipline` completed and maintainer-validated (2026-07-10; evidence in Validation).
- [x] Milestone 1: four-stage `ag_fields_pure.htm` control and accessible rotation mapping modal (2026-07-09 23:53 UTC).
- [x] Milestone 2: dynamic-safe `ag_fields.js` controller, snapshot-only gating, uploads, mapping, job streams/poll fallback, exact job keys, and 409 retention (2026-07-09 23:53 UTC).
- [x] Milestone 3: initial/dynamic runs-page wiring, real registry template, `experimental` maturity, and user visibility (2026-07-09 23:53 UTC).
- [x] Milestone 4: authenticated named sub-fields overlay and rebuild refresh through `addGeoJsonOverlay` (2026-07-09 23:53 UTC).
- [x] Milestone 5: focused/full frontend tests, Python render/registry/bootstrap coverage, lint, and bundle rebuild (2026-07-09 23:53 UTC).
- [x] Follow-up: persisted uploaded-boundary-filename display and additive state hydration contract (2026-07-10 16:38 UTC).
- [x] Follow-up: explicit project-UTM support/precision contract, actionable ambiguous-CRS diagnostics, and regression coverage (2026-07-10 16:57 UTC).
- [x] Follow-up: persisted WEPP Exec selector, `wepp_dcc52a6` new-project default, pinned RQ propagation, automatic UI worker sizing, and content-width clear action (2026-07-10 21:52 UTC).
- [x] Post-close follow-up: explicit Stage 1 projection requirements and conditional project-EPSG pills in runs-page/report title rows (2026-07-10 22:43 UTC).
- [x] Post-close documentation reconciliation: canonical UI specification aligned with the accepted implementation and validation evidence (2026-07-10 23:06 UTC).
- [x] Post-close overlay follow-up: automatic sub-field map loading, removal of the Stage 2 map button, and registry-preserving layer-control hiding (2026-07-10 23:17 UTC).
- [x] Post-close overlay re-show fix: reconstruct retained remote GeoJSON overlays from cached features and preserve existing-run automatic loading (2026-07-10 23:40 UTC).
- [x] Post-close preflight integration: `run_ag_fields`/🌽 task, success-only stamping, invalidation/freshness, TOC mapping, and behavior documentation (2026-07-11 00:04 UTC).
- [x] Post-close lifecycle disposition: reclassified AgFields as an internal beta and restricted initial/dynamic runs-page visibility to Dev-role users (2026-07-11 02:15 UTC).

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
- **2026-07-11 00:21 UTC** - Dispositioned the Batch Runner failure as a unit-fixture isolation defect. The workspace-preservation test now stubs the cache/lock reset boundary, asserts the canonical batch run id passed to both calls, and leaves production path resolution unchanged. The subsequent canonical full sweep passed 4,817 tests with 60 skips.
- **2026-07-11 02:15 UTC** - Reclassified AgFields from user-visible
  experimental to internal beta while continued operational hardening is in
  progress. The registry now requires the Dev role, and both initial and dynamic
  section rendering enforce that policy; the implemented control, routes, and
  existing project data remain unchanged.

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

### 2026-07-11: Supersede public experimental availability with internal beta

**Context**: The control and end-to-end workflow are implemented, but AgFields
is still undergoing operational hardening after the acceptance findings.

**Decision**: Preserve the real section template and reclassify AgFields as
`maturity: internal`, `internal_reason: beta`, and `min_role: dev`. This
supersedes the 2026-07-09 availability decision: Dev-role users retain the
working control, while ordinary users no longer receive its registry navigation
or section. No NoDb schema, run artifact, route, or existing-project mutation is
part of this visibility-only disposition.

### 2026-07-09: Defer controller-module splitting until acceptance
**Context**: The complete four-stage controller is about 1,700 lines, entering the repository's observe-only yellow band for JavaScript file size.

**Decision**: Preserve the established one-controller-per-control structure for v1 because all sections share one snapshot and job lifecycle. Reassess extraction after the manual walkthrough if concrete maintenance friction appears; do not invent helper boundaries before the first real UI run.

### 2026-07-10: Use an AgFields-owned WEPP executable
**Context**: The repaired p3733 input completes under `wepp_dcc52a6`, while both tested newer binaries fail in the same `frcfac` arithmetic path. The parent watershed executable is not necessarily safe for imported agricultural managements.

**Decision**: Add an independent, persisted AgFields WEPP executable. New `ag-fields.cfg` projects default to `wepp_dcc52a6`; historical payloads without the additive field continue using the parent WEPP executable until explicitly changed. Remove worker tuning from the browser while retaining the optional backend argument for compatibility. See ADR-0017.

### 2026-07-10: Auto-load and retain the sub-field overlay

**Context**: Building sub-fields already creates the review geometry, while the separate "Show on Map" action deferred an expected consequence and left no reload-safe path once removed.

**Decision**: Register and display current sub-fields during hydration and force a refreshed overlay visible after successful builds. The shared layer-control checkbox hides only the visible Deck layer and retains its overlay registration, so users can show it again without re-registration; ordinary hydration respects the hidden state.

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
- Projection-pill follow-up: 73 passed, 3 skipped across the full Ron map and pure-template suites; `stubtest wepppy.nodb.core.ron` and `check-test-stubs` passed. Live container verification returned `RonViewModel(sacral-self-discipline).srid == 32611` after the targeted `weppcloud` restart.
- Specification reconciliation: `uk2us` previews were clean and `wctl doc-lint` passed for the canonical UI specification, package, tracker, and active ExecPlan.
- Overlay follow-up: `wctl run-npm test -- ag_fields map_gl` passed 48 tests (10 AgFields, 38 map), including automatic authenticated loading/rebuild refresh and hide-without-unregister coverage.
- Overlay follow-up: frontend lint passed, the rebuilt controller bundle passed its stale check, the full Jest suite passed 85 suites / 620 tests, and the focused AgFields template render test passed.
- Overlay re-show fix: focused AgFields/map tests passed 48 tests with a non-empty feature collection; the test proves hide preserves registration and re-show installs a fresh visible Deck layer without another load.
- Overlay re-show fix: frontend lint, controller bundle rebuild/stale check, and the full 85-suite / 620-test Jest run passed after the descriptor reconstruction change.
- AgFields preflight integration: `wctl run-preflight-tests` passed all Go packages; focused RQ/rq-engine/run-page Python coverage passed 78 tests, followed by 28 passing rq-engine tests after enforcing required RedisPrep invalidation; `check-test-stubs` passed.
- The focused RQ failure contract passed 5 tests after adding an explicit assertion that failed Stage 4 jobs clear but never stamp `run_ag_fields`. Direct `stubtest wepppy.nodb.redis_prep` remains blocked before module comparison by existing repository-wide mypy build errors.
- AgFields preflight documentation: all seven affected behavior/specification/work-package/end-user Markdown files passed scoped `wctl doc-lint`; `uk2us` previews were clean.
- Batch Runner fixture-path disposition: the isolated regression and all 4 tests in `tests/nodb/test_batch_runner.py` passed. The test now isolates `clear_nodb_file_cache`/`clear_locks` and verifies both receive `batch;;batch-demo;;leaf-run`; no production behavior changed. The final canonical `wctl run-pytest tests --maxfail=1` sweep passed 4,817 tests with 60 skips.
- Internal-beta disposition: the registry/initial-render/dynamic-route/control-render group passed 172 tests. The final canonical `wctl run-pytest tests --maxfail=1` sweep passed 4,818 tests with 60 skips; all five updated Markdown files passed scoped `wctl doc-lint`, and their `uk2us` previews were clean.
- **Milestone 6 acceptance evidence (2026-07-10)**: full Stage 4 run on `sacral-self-discipline` completed and the maintainer validated the interface. Artifact inspection: 2,177 fields → 6,626 sub-fields; 6,626 `p*.run` files under `wepp/ag_fields/runs/`; 46,382 output files under `wepp/ag_fields/output/`, last written 2026-07-10 ~22:05 UTC; spot-checked `H1000.loss.dat` completes with final-year annual summary and carries the `VERSION 2020.500` stamp consistent with `wepp_dcc52a6` (the job-pinned executable), not a 2025-series build.

## Timeline (closure)

- **2026-07-10 22:40 UTC** - Milestone 6 recorded and package closed. ENDUSER.md updated with the WEPP-executable guidance (keep `wepp_dcc52a6`), the 20-plant-scenario limit, and the residue `hmax` normalization wording. Backend package closure notes updated: the real-binary E2E limitation is closed by this walkthrough.
- **2026-07-10 22:43 UTC** - Post-close projection UX follow-up completed. Stage 1 now states the preferred project-EPSG, WGS84, and alternate-projected-CRS metadata rules. `RonViewModel` carries the optional assigned-map SRID, and runs-page/report headers show `EPSG:<srid>` only when it exists; focused view-model and rendering coverage passes.
- **2026-07-10 23:06 UTC** - Reconciled the canonical UI specification with the shipped control, controller, route/state contracts, accepted management hardening, executable behavior, automated regression scope, and completed fresh-project evidence. Removed obsolete pending-acceptance, internal-maturity, worker-control, and unimplemented-staleness statements.
- **2026-07-10 23:17 UTC** - Removed "Show on Map" from Stage 2. Current sub-fields now load automatically on hydration and successful build completion; the map layer control hides them without dropping their registration. Focused controller/map tests pass and the UI specification records the lifecycle.
- **2026-07-10 23:40 UTC** - Fixed the observed layer-control re-show failure. Remote GeoJSON overlays now retain their loaded feature collection and construct a fresh Deck descriptor when checked again, avoiding reuse of a finalized hidden descriptor. Loading an existing run with current sub-fields still auto-registers and displays the layer.
- **2026-07-11 00:04 UTC** - Wired AgFields into preflight. `TaskEnum.run_ag_fields` owns the 🌽 emoji; successful Stage 4 completion stamps it, input/artifact mutations and job starts clear it, and `preflight2` requires it to be newer than parent WEPP, watershed abstraction, landuse, soils, and climate. The `ag_fields` checklist key targets `#ag-fields`.

## Handoffs

- **Follow-up (Codex)**: the acceptance run predates or raced the persist-before-execution change — `sacral-self-discipline`'s `ag_fields.nodb` has no `_wepp_bin` key (verified 2026-07-10 22:40 UTC), so its next Stage 4 hydration falls back to the parent `wepp_250915`. Either the maintainer sets **WEPP Exec** once in Stage 4 to persist `wepp_dcc52a6`, or a small migration/default lands for pre-ADR-0017 AgFields projects. Verify persist-before-execution works on the next real submission.
- Controller-module splitting (deferred at 1,700 lines): acceptance is done; reassess only if maintenance friction appears.
