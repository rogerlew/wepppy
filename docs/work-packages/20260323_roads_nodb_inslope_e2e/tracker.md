# Tracker - Roads NoDb Inslope End-to-End Implementation

> Living document tracking progress, decisions, risks, and verification for Roads phase-1 implementation.

## Quick Status

**Started**: 2026-03-23
**Current phase**: Comprehensive review closeout + handoff packaging
**Last updated**: 2026-03-24
**Active ExecPlan**: `prompts/active/roads_nodb_inslope_e2e_execplan.md`
**Next milestone**: Finalize rollback notes and close package handoff

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Reviewed canonical Roads spec and current implementation surfaces across NoDb, WEPPcloud routes/templates/controllers, preflight2, rq-engine, and queue governance docs (2026-03-23).
- [x] Created package scaffold (`package.md`, `tracker.md`, active ExecPlan, `artifacts/.gitkeep`, `notes/.gitkeep`) (2026-03-23).
- [x] Authored implementation-ready ExecPlan with file-level edit map and `clogging-starch`-default validation flow (2026-03-23).
- [x] Updated `PROJECT_TRACKER.md` and root `AGENTS.md` active ExecPlan pointer for this package (2026-03-23).
- [x] Milestone 1 complete: implemented `Roads(NoDbBase)` scaffold, exported Roads module, added deterministic inslope lowpoint mapping parity, and added `tests/nodb/mods/test_roads_controller.py` (2026-03-23).
- [x] Milestone 2 complete: wired Roads mod registration/header/run-page order/TaskEnum/preflight mappings and preflight2 checklist logic (`roads` gated on `run_wepp`) (2026-03-23).
- [x] Milestone 3 complete: implemented Roads blueprint/API routes, rq-engine Roads routes, RQ workers, and targeted route/worker tests (2026-03-23).
- [x] Milestone 4 complete: implemented Rust pass combiner (`combine_hillslope_pass_files`) in `wepppyo3`, exported Python bindings, and wired Roads pass injection to use staged segment pass paths (2026-03-23).
- [x] Milestone 5 complete: updated queue governance artifacts, synchronized route-freeze docs/checks, executed fixture-backed e2e command flow, and passed final validation gates (2026-03-23).
- [x] Post-closeout fix: resolved prepare-stage WBT raster path bug (`dem/dem.vrt` adjacency mismatch), added lowpoint decision diagnostics/counts, and aligned Roads upload UX copy with style guide workflow language (2026-03-24).
- [x] Revalidated Roads + full repository gates after regression fix (`wctl run-pytest tests --maxfail=1`, npm lint/test, queue/route governance checks) (2026-03-24).
- [x] Replaced placeholder segment pass staging with real single-OFE segment WEPP execution (legacy-derived soil/management/slope assets), including road-only OFE soil output contract enforcement (2026-03-24).
- [x] Hardened Roads run observability with per-step `roads.log` events through watershed boundary and persisted failed `last_run_summary` payloads (`failed_stage=watershed_rerun`) when watershed execution fails (2026-03-24).
- [x] Revalidated post-fidelity changes with targeted Roads suites, `wctl check-rq-graph`, and full test gate (`wctl run-pytest tests --maxfail=1` => `2491 passed, 34 skipped`) (2026-03-24).
- [x] Resolved watershed rerun runtime blocker by fixing pass-staging symlink overwrite semantics, updating `wepppyo3` pass writer to WEPP Fortran fixed-format grouping/continuation output, and rebuilding `wepp_interchange_rust.so` (2026-03-24).
- [x] Expanded Roads observability to append-only lifecycle/config/upload/query/run logging and verified fixture rerun success on `clogging-starch` (`status=completed`, `executed_segment_count=23`, `targeted_hillslope_count=14`) (2026-03-24).
- [x] Completed componentized comprehensive review (UI controller, NoDb controller, API/queue surfaces, `wepppyo3` combiner), resolved all high/medium findings, and revalidated full repository gates (`wctl run-pytest tests --maxfail=1` => `2499 passed, 34 skipped`) (2026-03-24).

## Timeline

- **2026-03-23** - Package created and planning docs authored.
- **2026-03-23** - Milestone 1 implemented and validated.
- **2026-03-23** - Milestone 2 implemented and validated.
- **2026-03-23** - Milestone 3 implemented and validated.
- **2026-03-23** - Milestone 4 implemented and validated (Rust combiner + Roads wiring).
- **2026-03-23** - Milestone 5 governance sync, fixture e2e command validation, and full-gate closeout completed.
- **2026-03-24** - Regression fix + observability patch applied; fixture prepare now maps eligible segments with explicit decision-point diagnostics.
- **2026-03-24** - Fidelity closeout complete: fixture Roads run executes mapped single-OFE segments, writes merged hillslope pass artifacts, and now persists failed run summaries when watershed rerun errors.
- **2026-03-24** - Runtime closeout complete: pass combine writer + staging fixes remove `forrtl severe(64)` blocker and fixture Roads watershed rerun now completes.
- **2026-03-24** - Componentized comprehensive review complete: medium/high findings remediated across UI/NoDb/API-RQ/Rust combiner with full-gate revalidation.

## Decisions

### 2026-03-23: Use `clogging-starch` as the default fixture run for all examples and validation
**Context**: The request requires one canonical run for planning, examples, and e2e verification.

**Options considered**:
1. Use synthetic temporary runs generated during testing.
2. Use mixed historical runs depending on subsystem.
3. Use one fixed disturbed WBT run (`clogging-starch`) across all docs and checks.

**Decision**: Use option 3 and require explicit justification if any command/example deviates.

**Impact**: Keeps plan execution reproducible for novice implementers and reviewers.

---

### 2026-03-23: Keep Roads enablement on canonical `set_mod` path with explicit WBT guard
**Context**: Existing optional mods are toggled through `/tasks/set_mod`; Roads spec requires backend gating and explicit failure on non-WBT.

**Options considered**:
1. Add a custom enable endpoint for Roads.
2. Reuse `/tasks/set_mod` and add Roads guard in existing toggle contract.

**Decision**: Use option 2.

**Impact**: Preserves a single mod lifecycle contract and avoids hidden enable paths.

---

### 2026-03-23: Include cross-repo `wepppyo3` pass combiner work in this package
**Context**: Roads watershed injection requires pass combination rules defined in the Roads specification.

**Options considered**:
1. Implement an in-repo Python combiner first.
2. Implement directly in `wepppyo3/wepp_interchange` and wire from WEPPpy.

**Decision**: Use option 2 as phase-1 canonical implementation, with explicit tests and diagnostics.

**Impact**: Aligns with performance/stack ownership standards and avoids temporary duplicate implementations.

---

### 2026-03-23: Use `wepp/roads/{segments,runs,output}` for Roads execution artifacts
**Context**: Initial planning/spec text used `_pups/roads/*`, but Roads phase 1 is an in-run module workflow, not an Omni-style child-run clone.

**Options considered**:
1. Keep `_pups/roads/*`.
2. Move execution artifacts to `wepp/roads/*`.

**Decision**: Use option 2, with watershed reruns executed from `wepp/roads/runs/pw0.run` and pass files resolved from `wepp/roads/output`.

**Impact**: Aligns with existing module layout patterns (`wepp/ag_fields/*`), avoids unnecessary `_pups` coupling, and keeps pass-path handling simpler for untouched vs combined hillslopes.

---

### 2026-03-23: Use relative pass roots (`../output/H<wepp_id>`) when building Roads watershed reruns
**Context**: Initial Roads run assembly passed absolute `wepp/roads/output/H<id>` paths to `make_watershed_omni_contrasts_run`, and fixture e2e failed with truncated pass filenames in `pw0.err`.

**Options considered**:
1. Keep absolute paths and rely on downstream path handling.
2. Use relative pass roots rooted at `wepp/roads/runs` as intended by the run template.

**Decision**: Use option 2.

**Impact**: Fixes WEPP path truncation/file-not-found failures and aligns with Roads spec path contract.

---

### 2026-03-23: Stage deterministic segment pass artifacts from mapped baseline hillslope passes for phase 1
**Context**: Roads pass combiner wiring required concrete segment pass inputs before full single-OFE segment input synthesis assets were available.

**Options considered**:
1. Block Milestone 4 until full single-OFE segment run asset generation is complete.
2. Stage deterministic per-segment pass artifacts by cloning mapped baseline hillslope pass files and continue with combiner/watershed integration.

**Decision**: Use option 2 for phase 1.

**Impact**: Enables end-to-end queue/e2e wiring and pass-combiner integration now; Roads-specific hydrologic deltas remain limited by segment mapping coverage in current fixtures.

---

### 2026-03-24: Resolve Roads prepare rasters explicitly from Watershed WBT artifacts
**Context**: `Roads.prepare_segments()` used `ron.dem_fn` plus adjacency auto-discovery, which missed `dem/wbt/netful.tif` and `dem/wbt/subwta.tif` on `clogging-starch`, yielding zero mapped lowpoints.

**Options considered**:
1. Keep DEM-adjacent auto-discovery and document fixture caveat.
2. Resolve `relief/netful/subwta` explicitly from `watershed_instance` and fail if missing.

**Decision**: Use option 2.

**Impact**: Restores real lowpoint mapping (`eligible_with_lowpoint_ids` now non-zero) and removes hidden path assumptions.

---

### 2026-03-24: Supersede baseline-pass cloning and run mapped roads as real single-OFE WEPP segments
**Context**: Placeholder segment pass cloning satisfied queue wiring but did not satisfy execution fidelity and left segment-run decision points under-observed.

**Options considered**:
1. Keep baseline pass cloning and rely on pass combiner-only validation.
2. Execute mapped segments as true single-OFE runs with legacy-derived one-OFE soil/management/slope assets.

**Decision**: Use option 2.

**Impact**: Roads now runs mapped segments directly, produces real segment pass artifacts, and satisfies the road-only soil OFE contract.

---

### 2026-03-24: Persist failed Roads run summaries on watershed-rerun exceptions
**Context**: Watershed rerun failures set Roads status to failed but left `_last_run_summary` null, reducing UI/report observability.

**Options considered**:
1. Keep exception-only status/error updates.
2. Persist structured failed summary with counts and `failed_stage` before propagating the exception.

**Decision**: Use option 2.

**Impact**: Query/report consumers retain segment execution context under failure while preserving explicit error propagation.

---

### 2026-03-24: Enforce append-only Roads logging and explicit symlink-safe pass combination
**Context**: `roads.log` visibility was incomplete and targeted pass combine writes followed staged symlinks, mutating baseline pass files and contributing to watershed rerun failures.

**Options considered**:
1. Keep stage-reset log behavior and symlink staging while debugging runtime externally.
2. Make `roads.log` append-only across lifecycle/config/upload/query/run actions, unlink targeted staged outputs before combine, and emit strict WEPP Fortran pass formatting from `wepppyo3`.

**Decision**: Use option 2.

**Impact**: End-to-end observability is preserved in a single log timeline, baseline pass files are no longer mutated by targeted combines, and fixture watershed reruns complete successfully.

---

### 2026-03-24: Resolve medium/high findings from componentized Roads review
**Context**: A comprehensive review split across UI controller, NoDb controller, API/queue, and `wepppyo3` pass combiner surfaced correctness and governance defects that required immediate remediation.

**Options considered**:
1. Close the package with known review findings and defer remediation.
2. Resolve medium/high findings immediately, update queue/docs governance artifacts, and re-run full validation gates.

**Decision**: Use option 2.

**Impact**: Roads now enforces multipart-only uploads, stale-prepare guards, strict defaults/input CRS validation, queue single-flight semantics (`409` conflicts on concurrent attempts), UI active-job correlation, and corrected combiner `NO EVENT` groundwater merge/header/calendar checks.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Pass combination semantics (especially hydrograph-shape fields) drift from expected behavior | High | Medium | Follow spec formulas exactly, add synthetic multi-source tests, and keep explicit diagnostics in outputs | Open |
| UI/TOC ordering regressions when adding Roads after Debris Flow | Medium | Medium | Add direct template/order tests and run mod-menu smoke checks | Mitigated (Milestone 2 route/template tests passing) |
| Roads preflight completion becomes true without WEPP freshness dependency | High | Medium | Add checklist tests for WEPP-gated Roads timestamps and stale scenarios | Mitigated (preflight checklist tests added/passing) |
| Queue graph/catalog drift after new Roads jobs | Medium | High | Update `wepppy/rq/job-dependencies-catalog.md`, run `wctl check-rq-graph`, regenerate if needed | Mitigated (`python tools/check_rq_dependency_graph.py --write` + `wctl check-rq-graph` passing) |
| Agent-route freeze artifacts drift after new rq-engine Roads endpoint(s) | Medium | High | Update endpoint inventory + checklist freeze docs and associated tests in same changeset | Mitigated (`check_endpoint_inventory` + `check_route_contract_checklist` passing) |
| Fixture run has zero mapped eligible segments, limiting observed Roads pass deltas in e2e | Medium | Medium | Keep fixture e2e command-path validation in place and add a mapped-segment fixture/run in follow-up validation package | Mitigated (`clogging-starch` prepare now maps 23/70 eligible segments) |
| Fixture watershed reruns fail with `forrtl: severe (64)` input conversion on existing `H1.pass.dat` | High | Medium | Fixed by symlink-safe staging + WEPP fixed-format pass writer; validated successful fixture rerun on `clogging-starch` | Mitigated |

## Verification Checklist

### Code Quality
- [x] Targeted Python/Go/JS tests for touched Roads surfaces pass (Milestones 1-5 suites).
- [x] `wctl check-rq-graph` passes (graph regenerated and committed).
- [x] Route-freeze drift guards pass (`python tools/check_endpoint_inventory.py`, `python tools/check_route_contract_checklist.py`).
- [x] Changed-file broad exception guard passes (`python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`).

### Documentation
- [x] Roads spec reviewed against implemented contracts for Milestones 1-5.
- [x] Package docs (`package.md`, `tracker.md`, ExecPlan) reflect current implementation state.
- [x] Updated docs pass `wctl doc-lint --path <file>`.

### Testing
- [x] `tests/nodb/mods/test_roads_monotonic_segments.py` plus Roads controller tests pass.
- [x] WEPPcloud route/template/controller tests for Roads registration and ordering pass.
- [x] rq-engine/RQ tests for Roads queue paths pass.
- [x] preflight2 checklist tests include Roads WEPP dependency behavior.
- [x] `clogging-starch` prepare command-path run now demonstrates mapped segments and observable lowpoint decisions.
- [x] `clogging-starch` run command path executes mapped segments as single-OFE runs (`executed_segment_count=23`) and writes per-segment manifest/log diagnostics.
- [x] Failed watershed reruns now persist `last_run_summary.status=failed` and `failed_stage=watershed_rerun` for UI/report observability.
- [x] `clogging-starch` watershed rerun now completes after pass-writer/staging fixes (`run_roads_wepp.status=completed`).

### Deployment/Operations
- [x] Local stack validation completed with canonical compose/wctl workflows.
- [ ] Rollback steps validated (mod disable, artifact isolation under `wepp/roads`, queue rollback).

## Progress Notes

### 2026-03-24: Componentized comprehensive review remediation pass
**Agent/Contributor**: Codex

**Work completed**:
- Applied medium/high review fixes across:
  - UI: active task/job correlation + duplicate submission/ambiguous completion guardrails.
  - NoDb: strict enum/input CRS validation, WBT enable guard, stale prepare signature checks, fail-fast segment run failures with persisted failed summaries.
  - API/RQ/rq-engine: multipart upload-only contract, preflight timestamp invalidation on Roads mutations, submit/runtime single-flight lock enforcement, and `202` enqueue semantics with `409` conflicts on contention.
  - `wepppyo3`: corrected `NO EVENT` groundwater accumulation, added header/calendar compatibility validation, and explicit exponent overflow rejection.
- Regenerated queue graph/catalog after enqueue-edge updates and kept route governance checks green.

**Blockers encountered**:
- None.

**Test/validation results**:
- `wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1` (pass)
- `wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1` (pass)
- `wctl run-pytest tests/microservices/test_rq_engine_roads_routes.py --maxfail=1` (pass)
- `wctl run-pytest tests/rq/test_roads_rq.py --maxfail=1` (pass)
- `wctl run-npm test -- roads` (pass)
- `/workdir/wepppyo3`: `cargo test -p wepp_interchange_rust -- --nocapture` (pass)
- `wctl check-rq-graph` (initial drift detected, then pass after `python tools/check_rq_dependency_graph.py --write`)
- `python tools/check_endpoint_inventory.py` (pass)
- `python tools/check_route_contract_checklist.py` (pass)
- `wctl run-npm lint` (pass)
- `wctl run-npm test` (pass)
- `wctl run-preflight-tests ./internal/checklist` (pass)
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` (pass)
- `wctl run-pytest tests --maxfail=1` (pass; `2499 passed, 34 skipped`)

### 2026-03-23: Package authoring and execution plan setup
**Agent/Contributor**: Codex

**Work completed**:
- Audited current Roads spec and integration seams (NoDb, WEPPcloud, preflight2, rq-engine, RQ, and queue governance).
- Created package scaffold and authored implementation-ready plan/tracker docs.
- Updated top-level trackers/pointers so other agents can discover this active package.

**Blockers encountered**:
- None at planning stage.

**Next steps**:
- Start Milestone 1 from the ExecPlan and keep `Progress`, `Decision Log`, and `Surprises & Discoveries` synchronized.

**Test results**: Not run (documentation-only planning session).

### 2026-03-23: Artifact-layout reassessment and docs realignment
**Agent/Contributor**: Codex

**Work completed**:
- Assessed `_pups/roads` vs `wepp/roads` against current NoDb patterns and run-assembly mechanics.
- Updated Roads spec + package docs to standardize on `wepp/roads/{segments,runs,output}`.
- Updated watershed-run contract so `wepp/roads/runs/pw0.run` references pass files from `wepp/roads/output` for both untouched and Roads-targeted hillslopes.

**Blockers encountered**:
- None.

**Next steps**:
- Implement Milestone 1 using the revised artifact contract.

**Test results**: Pending (docs-only update session).

### 2026-03-23: Milestones 1-2 implementation and validation
**Agent/Contributor**: Codex

**Work completed**:
- Completed Milestone 1 (`Roads` controller/state scaffold, Roads package export, inslope lowpoint parity updates, new Roads controller unit tests).
- Completed Milestone 2 (`roads` mod registration and WBT guard in `set_mod`, header/run-page placement after Debris Flow, bootstrap/preflight mappings, `TaskEnum.run_roads`, preflight2 `roads` checklist key + tests).
- Added a minimal `controls/roads_pure.htm` to keep dynamic `/view/mod/roads` rendering valid before API/queue routes land.

**Blockers encountered**:
- None.

**Next steps**:
- Implement Milestone 3 (`roads_bp`, rq-engine roads routes, RQ workers, and queue-path tests).

**Test results**:
- `wctl run-pytest tests/nodb/mods/test_roads_monotonic_segments.py --maxfail=1` (pass)
- `wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1` (pass)
- `wctl run-pytest tests/weppcloud/routes/test_project_bp.py --maxfail=1` (pass)
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1` (pass)
- `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py --maxfail=1` (pass)
- `wctl run-preflight-tests ./internal/checklist` (pass)

### 2026-03-23: Milestones 3-5 implementation, governance sync, and closeout validation
**Agent/Contributor**: Codex

**Work completed**:
- Implemented Milestone 3 API/queue surfaces (`roads_bp`, rq-engine Roads routes, `roads_rq` workers) and registration wiring.
- Implemented Milestone 4 `wepppyo3` pass combiner (`combine_hillslope_pass_files`) with Rust unit tests and Python export, then wired Roads pass combination inputs.
- Added phase-1 segment pass artifact staging + manifest under `wepp/roads/segments/`.
- Fixed watershed rerun path contract to use `../output/H<id>` roots (resolved fixture e2e path truncation failure seen in `pw0.err`).
- Completed Milestone 5 governance sync:
  - queue graph/catalog regeneration,
  - endpoint inventory freeze updates,
  - route contract checklist updates,
  - OpenAPI frozen-route contract test updates.
- Executed fixture-backed `clogging-starch` e2e command path; run completed and wrote expected Roads artifacts.

**Blockers encountered**:
- Initial `clogging-starch` e2e run failed due absolute pass path truncation in watershed run assembly (`forrtl: file not found .../H1.`).
- Full-suite gate initially failed on frozen route-count and OpenAPI metadata checks after adding Roads rq-engine routes.

**Resolutions**:
- Switched watershed run pass roots to relative `../output/H<id>`.
- Updated route-freeze artifacts + OpenAPI frozen route expectations/metadata.

**Test/validation results**:
- `wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1` (pass)
- `wctl run-pytest tests/microservices/test_rq_engine_roads_routes.py --maxfail=1` (pass)
- `wctl run-pytest tests/rq/test_roads_rq.py --maxfail=1` (pass)
- `cargo test -p wepp_interchange_rust -- --nocapture` in `/workdir/wepppyo3` (pass)
- `wctl check-rq-graph` (initial drift detected, then pass after regenerate)
- `python tools/check_rq_dependency_graph.py --write` (pass; graph/catalog regenerated)
- `python tools/check_endpoint_inventory.py` (pass after freeze update)
- `python tools/check_route_contract_checklist.py` (pass after freeze update)
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` (pass)
- Fixture e2e command path via `wctl exec weppcloud ... Roads.prepare_segments()/run_roads_wepp()` on `clogging-starch` (pass; `targeted_hillslope_count=0`, artifacts present)
- `wctl run-npm lint` (pass)
- `wctl run-npm test` (pass)
- `wctl run-preflight-tests ./internal/checklist` (pass)
- `wctl run-pytest tests --maxfail=1` (pass)
- `wctl doc-lint --path docs/work-packages/20260323_roads_nodb_inslope_e2e/package.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260323_roads_nodb_inslope_e2e/tracker.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260323_roads_nodb_inslope_e2e/prompts/active/roads_nodb_inslope_e2e_execplan.md` (pass)

### 2026-03-24: Prepare mapping regression fix + decision observability hardening
**Agent/Contributor**: Codex

**Work completed**:
- Fixed prepare-stage raster resolution to pass explicit WBT paths (`relief`, `netful`, `subwta`) into monotonic conversion.
- Added per-segment decision diagnostics (`_roads_lowpoint_decision` and channel/hillslope search metadata) and rolled up counts into prepare summary.
- Updated Roads control copy to upload-first workflow language and surfaced decision-count summaries in controller info panels.
- Rebuilt `controllers-gl.js` and revalidated targeted + full validation gates.

**Blockers encountered**:
- Watershed reruns currently fail in fixture/runtime with `forrtl: severe (64)` on `H1.pass.dat` in both baseline and Roads rerun directories; this is independent of lowpoint mapping fix.

**Next steps**:
- Handoff with mapped-segment evidence + decision observability details; queue follow-up for watershed pass parsing/runtime investigation.

**Test/validation results**:
- `wctl run-pytest tests/nodb/mods/test_roads_monotonic_segments.py --maxfail=1` (pass)
- `wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1` (pass)
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1` (pass)
- `wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1` (pass)
- `wctl run-npm test -- roads` (pass)
- `python3 wepppy/weppcloud/controllers_js/build_controllers_js.py` (pass)
- `wctl run-npm lint` (pass)
- `wctl run-npm test` (pass)
- `python tools/check_endpoint_inventory.py` (pass)
- `python tools/check_route_contract_checklist.py` (pass)
- `wctl check-rq-graph` (drift detected, then pass after regenerate)
- `python tools/check_rq_dependency_graph.py --write` (pass; graph/catalog rewritten)
- `wctl run-preflight-tests ./internal/checklist` (pass)
- `wctl run-pytest tests --maxfail=1` (pass)
- `wctl exec weppcloud python - <<'PY' ... Roads.prepare_segments() ...` on `clogging-starch` (pass; `eligible=70`, `mapped=23`, decision counts emitted)
- `wctl exec weppcloud python - <<'PY' ... Roads.run_roads_wepp() ...` on `clogging-starch` (fails with `forrtl: severe (64)`; same failure reproducible on baseline `run_watershed('/wc1/runs/cl/clogging-starch/wepp/runs')`)

### 2026-03-24: Single-OFE execution fidelity + failed-summary observability closeout
**Agent/Contributor**: Codex

**Work completed**:
- Replaced placeholder segment pass staging with real single-OFE segment execution in `Roads.run_roads_wepp()` (legacy template-derived one-OFE soil/management/slope assembly).
- Added `roads.log` step-level observability for segment runs, pass combining, and watershed rerun failures.
- Persisted failed `last_run_summary` payloads with `failed_stage=watershed_rerun` so query/report consumers retain execution counts after rerun exceptions.
- Verified fixture artifact contract: `/wc1/runs/cl/clogging-starch/wepp/roads/runs/p900001.sol` contains only one road OFE (`1 0`, `'Road' ...`).

**Blockers encountered**:
- Watershed rerun remains blocked by existing fixture/runtime pass parsing failure (`forrtl: severe (64)` on `H1.pass.dat`) in both baseline and Roads rerun directories.

**Test/validation results**:
- `wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1` (pass)
- `wctl run-pytest tests/nodb/mods/test_roads_monotonic_segments.py --maxfail=1` (pass)
- `wctl run-pytest tests/rq/test_roads_rq.py --maxfail=1` (pass)
- `wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1` (pass)
- `wctl run-pytest tests/microservices/test_rq_engine_roads_routes.py --maxfail=1` (pass)
- `wctl check-rq-graph` (pass)
- `wctl run-pytest tests --maxfail=1` (pass; `2491 passed, 34 skipped`)
- `wctl run-npm lint` (pass)
- `wctl run-npm test` (pass; 70 suites / 430 tests)
- `wctl run-preflight-tests ./internal/checklist` (pass)
- `python tools/check_endpoint_inventory.py` (pass)
- `python tools/check_route_contract_checklist.py` (pass)
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` (pass)
- `wctl doc-lint --path docs/work-packages/20260323_roads_nodb_inslope_e2e/package.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260323_roads_nodb_inslope_e2e/tracker.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260323_roads_nodb_inslope_e2e/prompts/active/roads_nodb_inslope_e2e_execplan.md` (pass)
- `wctl exec weppcloud python - <<'PY' ... Roads.prepare_segments() ...` on `clogging-starch` (pass; `eligible=70`, `mapped=23`)
- `wctl exec weppcloud python - <<'PY' ... Roads.run_roads_wepp() ...` on `clogging-starch` (fails with expected external `forrtl: severe (64)` blocker; `query_summary.last_run_summary` now persists `status=failed`, `failed_stage=watershed_rerun`, and segment counts)

### 2026-03-24: Runtime blocker resolution (pass writer + symlink-safe staging)
**Agent/Contributor**: Codex

**Work completed**:
- Made `roads.log` append-only and added lifecycle/config/upload/query/run action logging so controller activity is fully observable.
- Updated Roads pass staging to unlink targeted staged outputs before combine, preventing symlink-following writes into baseline `wepp/output/H*.pass.dat`.
- Updated `wepppyo3` pass combiner writer to WEPP-compatible Fortran fixed-format grouped output (`E11.5` with explicit sign + exponent padding and EVENT continuation line behavior), rebuilt `wepp_interchange_rust.so`, and revalidated Rust tests.
- Re-ran fixture prepare+run for `clogging-starch`; Roads watershed rerun now completes successfully.

**Blockers encountered**:
- None. Previous `forrtl: severe (64)` blocker is resolved in this package.

**Test/validation results**:
- `/workdir/wepppyo3`: `cargo test -p wepp_interchange_rust -- --nocapture` (pass)
- `/workdir/wepppyo3`: `cargo build -p wepp_interchange_rust --release` + copy to `release/linux/py312/wepppyo3/wepp_interchange/wepp_interchange_rust.so` (pass)
- `wctl run-pytest tests/nodb/mods/test_roads_monotonic_segments.py --maxfail=1` (pass)
- `wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1` (pass)
- `wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1` (pass)
- `wctl run-pytest tests/microservices/test_rq_engine_roads_routes.py --maxfail=1` (pass)
- `wctl run-pytest tests/rq/test_roads_rq.py --maxfail=1` (pass)
- `wctl check-rq-graph` (pass)
- `python tools/check_endpoint_inventory.py` (pass)
- `python tools/check_route_contract_checklist.py` (pass)
- `wctl run-npm lint` (pass)
- `wctl run-npm test` (pass; 70 suites / 430 tests)
- `wctl run-preflight-tests ./internal/checklist` (pass)
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` (pass)
- `wctl run-pytest tests --maxfail=1` (pass; `2491 passed, 34 skipped`)
- `wctl exec weppcloud python - <<'PY' ... Roads.prepare_segments(); Roads.run_roads_wepp() ...` on `clogging-starch` (pass; `status=completed`, `executed_segment_count=23`, `targeted_hillslope_count=14`)

## Communication Log

### 2026-03-23: User request to author Roads end-to-end planning package only
**Participants**: User, Codex
**Question/Topic**: Create a complete Roads implementation work package and active ExecPlan without production feature edits.
**Outcome**: Package scaffold and active ExecPlan authored with fixture-default validation strategy and tracker/pointer updates.

### 2026-03-23: User request to reassess Roads artifact layout
**Participants**: User, Codex
**Question/Topic**: Evaluate replacing `_pups/roads` with `wepp/roads` and update plan/spec docs if better.
**Outcome**: Change accepted; package and specification now use `wepp/roads/{segments,runs,output}` with unified pass references from `wepp/roads/output`.

### 2026-03-23: User request to execute active ExecPlan end-to-end
**Participants**: User, Codex
**Question/Topic**: Implement Milestones 1-5 without pause, keep ExecPlan/tracker synchronized, enforce governance checks, and run listed validation gates.
**Outcome**: Milestones 1-5 executed to completion; governance artifacts synchronized; fixture e2e command path validated; full required gates passed.
