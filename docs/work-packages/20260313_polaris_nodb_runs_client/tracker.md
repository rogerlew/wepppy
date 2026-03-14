# Tracker - POLARIS NoDb Runs Client for Project-Aligned Raster Layers

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-03-13  
**Current phase**: Complete (closed 2026-03-14)  
**Last updated**: 2026-03-14  
**Next milestone**: None  
**Implementation plan**: `docs/work-packages/20260313_polaris_nodb_runs_client/prompts/completed/polaris_nodb_runs_client_execplan.md`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Created work-package scaffold (`package.md`, `tracker.md`, `prompts/active`, `prompts/completed`, `notes`, `artifacts`) (2026-03-13).
- [x] Authored active ExecPlan with milestone breakdown and acceptance criteria (2026-03-13).
- [x] Captured initial POLARIS endpoint inventory and technical discovery notes (2026-03-13).
- [x] Registered package in `PROJECT_TRACKER.md` as in progress (2026-03-13).
- [x] Closed initial open questions with user decisions (defaults/config/endpoint/format/cache/scope) (2026-03-13).
- [x] Added POLARIS NoDb mod scaffold and retrieval/alignment implementation (`wepppy/nodb/mods/polaris/*`) (2026-03-13).
- [x] Added rq-engine enqueue endpoint `/api/runs/{runid}/{config}/acquire-polaris` and RQ task wiring (2026-03-13).
- [x] Added `[polaris]` config section to `wepppy/nodb/configs/disturbed9002_wbt.cfg` with top-horizon defaults (2026-03-13).
- [x] Added focused tests for POLARIS helpers and rq-engine route enqueue behavior (2026-03-13).
- [x] Regenerated RQ dependency graph artifacts and verified drift check clean (2026-03-13).
- [x] Re-ran focused tests and changed-file quality gates after final wiring verification (2026-03-13).
- [x] Added direct `Polaris.acquire_and_align()` unit coverage for skip/force-refresh behavior (2026-03-13).
- [x] Added POLARIS NoDb to `/wc1/runs/in/insightful-peacock/` and verified aligned raster parity against run DEM (2026-03-13).
- [x] Captured closeout artifact summary in `artifacts/final_validation_summary.md` (2026-03-13).
- [x] Updated endpoint inventory + route contract freeze artifacts for `acquire-polaris` (`endpoint_inventory_freeze_20260208.md`, `route_contract_checklist_20260208.md`, OpenAPI frozen route count) (2026-03-14).
- [x] Completed full-suite sanity validation (`wctl run-pytest tests --maxfail=1`) and closed the package (2026-03-14).

## Timeline

- **2026-03-13** - Package created and scoped.
- **2026-03-13** - Active ExecPlan drafted and discovery notes captured.
- **2026-03-13** - Open questions queued for human review before implementation milestone lock.
- **2026-03-13** - Phase-1 implementation landed (POLARIS mod + endpoint + task + config + focused tests).
- **2026-03-13** - Focused validation rerun complete (`pytest`, broad-exception gate, rq-graph check, docs lint).
- **2026-03-14** - Full-suite sanity check passed and closeout artifacts synchronized.

## Decisions

### 2026-03-13: Make layer support catalog-driven instead of hardcoded
**Context**: The requirement is broad support across POLARIS variables, stats, and depths.

**Options considered**:
1. Hardcode a small starter set and expand later.
2. Build a catalog-driven selector that can target any available layer.

**Decision**: Choose option 2.

**Impact**: Avoids repeated refactors and keeps RUSLE/WEPP follow-ups unblocked by missing layers.

---

### 2026-03-13: Use run raster grid as the canonical output target
**Context**: Outputs must match existing project map rasters in extent, projection, and size.

**Options considered**:
1. Keep POLARIS native EPSG:4326 rasters in run outputs and align later.
2. Align immediately to run grid during acquisition.

**Decision**: Choose option 2.

**Impact**: Downstream consumers (RUSLE and soil builders) can use outputs directly without secondary reprojection steps.

---

### 2026-03-13: Lock initial phase requirements from user decision set
**Context**: Milestone 1 required human decisions before implementation.

**Decision**:
1. Default layer set = top-horizon mean rasters for `sand`, `clay`, `bd`, `om`.
2. Initial config target file = `wepppy/nodb/configs/disturbed9002_wbt.cfg`.
3. Add rq-engine endpoint now (`acquire-polaris`).
4. Output format = GeoTIFF only.
5. Keep only aligned outputs by default; retain optional debug flag to keep intermediates.
6. Phase 1 scope = retrieval/alignment only (no derived RUSLE/WEPP products yet).

**Impact**: Implementation can proceed without additional contract ambiguity.

---

### 2026-03-13: Keep POLARIS execution manual for phase 1
**Context**: Follow-up user decision after endpoint delivery.

**Decision**: Keep `/api/runs/{runid}/{config}/acquire-polaris` manual/on-demand only; do not auto-trigger from run pipeline stages in phase 1.

**Impact**: Avoids hidden runtime/storage costs and keeps retrieval explicit while contracts stabilize.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Remote POLARIS endpoint instability/latency | High | Medium | Add retries, clear errors, optional per-run caching strategy | Open |
| Incorrect raster alignment to run grid | High | Medium | Validate CRS/transform/shape parity against template rasters in tests | Open |
| Over-fetching all 390 layers by default causes high runtime/storage | Medium | High | Keep defaults small; support full catalog via explicit config | Open |
| Units/log transforms misunderstood in downstream models | Medium | Medium | Include units/log-space flags in per-layer metadata + README | Open |
| Unknown policy for where config should live (run cfg vs static file) | Medium | Low | Locked to `wepppy/nodb/configs/disturbed9002_wbt.cfg` for phase 1 | Mitigated |

## Verification Checklist

### Planning/Docs
- [x] Work package scaffold created.
- [x] Active ExecPlan authored.
- [x] Discovery notes captured with source inventory.
- [x] Open questions resolved and recorded in Decision Log.

### Code Quality (for implementation phase)
- [x] Targeted tests for POLARIS mod and RQ route pass.
- [x] `wctl run-pytest tests --maxfail=1` passes or deviations documented.
- [x] `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` passes for changed files.
- [x] Relevant docs lint clean for touched markdown files.

## Progress Notes

### 2026-03-13: Work-package setup, discovery baseline, and decision lock
**Agent/Contributor**: Codex

**Work completed**:
- Created package scaffold and active ExecPlan.
- Inspected POLARIS endpoint index and readme metadata.
- Confirmed endpoint combinatorics: 13 properties x 5 statistics x 6 depth intervals = 390 published VRT layers.
- Reviewed run-map alignment contracts (`Ron.map`, `raster_stacker`) and reference mod patterns (`openet_ts`, `shrubland`).
- Added package entry to the root project tracker.
- Captured user decisions for all six open questions and locked phase-1 contract.

**Blockers encountered**:
- No hard blocker.

**Next steps**:
1. Implement POLARIS mod + rq-engine endpoint based on locked contract.
2. Add focused tests for layer parsing and endpoint enqueue behavior.
3. Validate alignment path against run DEM grid in integration follow-up.

**Test results**:
- Planning/documentation setup only (no code tests run yet).

### 2026-03-13: Implementation wave 1 (mod + endpoint + tests)
**Agent/Contributor**: Codex

**Work completed**:
- Implemented `wepppy/nodb/mods/polaris/polaris.py` and module exports under `wepppy/nodb/mods/polaris/`.
- Added config wiring in `wepppy/nodb/configs/disturbed9002_wbt.cfg` with defaults:
  - properties: `sand`, `clay`, `bd`, `om`
  - statistics: `mean`
  - depths: `0_5`
  - GeoTIFF output path under `polaris/`
  - `keep_source_intermediates` debug flag.
- Added rq-engine route `wepppy/microservices/rq_engine/polaris_routes.py` and app registration in `rq_engine/__init__.py`.
- Added RQ task `fetch_and_align_polaris_rq` in `wepppy/rq/project_rq.py`.
- Added `TaskEnum.fetch_polaris` to `wepppy/nodb/redis_prep.py`.
- Added tests:
  - `tests/nodb/mods/polaris/test_polaris.py`
  - `tests/microservices/test_rq_engine_polaris_routes.py`
- Regenerated dependency graph artifacts:
  - `wepppy/rq/job-dependency-graph.static.json`
  - `wepppy/rq/job-dependencies-catalog.md`

**Blockers encountered**:
- Changed-file broad-exception enforcement initially failed due a new broad catch in `project_rq.py`; resolved by removing the broad boundary handler in the new task and relying on the existing decorator.

**Next steps**:
1. Add run-level integration validation on a real project to verify end-to-end raster alignment outputs.
2. Add targeted test coverage for `Polaris.acquire_and_align()` behavior under mocked raster alignment.
3. Run broader test sweep as needed for handoff confidence.

**Test results**:
- `wctl run-pytest tests/nodb/mods/polaris/test_polaris.py tests/microservices/test_rq_engine_polaris_routes.py -q` -> `6 passed`.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` -> `PASS`.
- `wctl check-rq-graph` -> clean after regeneration.
- `wctl doc-lint --path docs/work-packages/20260313_polaris_nodb_runs_client` -> clean.
- `wctl doc-lint --path PROJECT_TRACKER.md` -> clean.

### 2026-03-13: Validation refresh and closeout alignment
**Agent/Contributor**: Codex

**Work completed**:
- Re-ran focused test targets for newly added POLARIS module and endpoint route.
- Re-ran changed-file broad-exception enforcement and queue dependency drift checks.
- Re-ran docs lint on package docs and related tracker/dependency markdown.
- Updated tracker status to reflect Milestone 5 closeout state and remaining validation work.

**Blockers encountered**:
- No blocker. Remaining work is planned integration validation depth, not a contract or tooling issue.

**Next steps**:
1. Execute a real-run integration check that verifies aligned POLARIS outputs against run DEM grid parity.
2. Add direct `acquire_and_align` unit coverage for skip/force-refresh paths.
3. Capture closeout validation artifact in `artifacts/final_validation_summary.md`.

**Test results**:
- `wctl run-pytest tests/nodb/mods/polaris/test_polaris.py tests/microservices/test_rq_engine_polaris_routes.py -q` -> `6 passed`.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` -> `PASS`.
- `wctl check-rq-graph` -> `RQ dependency graph artifacts are up to date`.
- `wctl doc-lint --path docs/work-packages/20260313_polaris_nodb_runs_client` -> clean.
- `wctl doc-lint --path PROJECT_TRACKER.md` -> clean.
- `wctl doc-lint --path wepppy/rq/job-dependencies-catalog.md` -> clean.

### 2026-03-13: User-directed validation expansion (manual endpoint + run integration)
**Agent/Contributor**: Codex

**Work completed**:
- Confirmed endpoint policy: manual trigger retained for phase 1.
- Added direct unit coverage for `Polaris.acquire_and_align()` idempotent skip and `force_refresh` paths.
- Ran real-run integration validation on `insightful-peacock`; created `polaris.nodb` and fetched/aligned `sand_mean_0_5`.
- Verified output grid parity against `/wc1/runs/in/insightful-peacock/dem/dem.tif` (`crs`, `transform`, `shape` all match).
- Wrote final validation artifact summary.

**Blockers encountered**:
- No blocker.

**Next steps**:
1. Run full suite sanity pass (`wctl run-pytest tests --maxfail=1`) if we want to fully close Milestone 5 in this package.

**Test results**:
- `wctl run-pytest tests/nodb/mods/polaris/test_polaris.py tests/microservices/test_rq_engine_polaris_routes.py -q` -> `7 passed`.
- Integration script on `/wc1/runs/in/insightful-peacock` -> `polaris.nodb` created and `sand_mean_0_5.tif` aligned with DEM grid parity.

### 2026-03-14: Full-suite completion and package closure
**Agent/Contributor**: Codex

**Work completed**:
- Ran mandatory full-suite sanity gate and resolved discovered contract freeze drift for the new endpoint.
- Updated route freeze artifacts:
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`
  - `tests/microservices/test_rq_engine_openapi_contract.py` (frozen agent-route count).
- Closed package docs and moved ExecPlan to completed prompts folder.

**Blockers encountered**:
- Initial full-suite run surfaced two frozen-contract drifts (inventory and checklist) introduced by the new endpoint; both were corrected and revalidated.

**Next steps**:
1. Follow-up package: POLARIS-to-WEPP soil translation.
2. Follow-up package: POLARIS-backed gridded RUSLE detachment integration.

**Test results**:
- `wctl run-pytest tests --maxfail=1` -> `2321 passed, 34 skipped`.
- `wctl run-pytest tests/tools/test_endpoint_inventory_guard.py -q` -> `1 passed`.
- `wctl run-pytest tests/tools/test_route_contract_checklist_guard.py -q` -> `1 passed`.

## Communication Log

### 2026-03-13: Package setup request
**Participants**: User, Codex  
**Question/Topic**: Set up a work package and ExecPlan for a POLARIS NoDb/mods runs client with broad layer support and run-aligned rasters.  
**Outcome**: Package scaffolded with active ExecPlan, discovery notes captured, and open questions prepared for review.
