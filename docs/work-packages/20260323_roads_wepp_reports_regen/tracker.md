# Tracker - Roads WEPP Report Regeneration and Run Results Summary

> Living document tracking progress, decisions, risks, and verification for Roads report-resource parity work.

## Quick Status

**Started**: 2026-03-23  
**Current phase**: Completed (Milestones 1-10 closed)  
**Last updated**: 2026-03-24  
**Active ExecPlan**: `prompts/active/roads_wepp_reports_regen_execplan.md`  
**Next milestone**: None (package ready for handoff/merge)

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Created package scaffold and active ExecPlan for Roads report-resource parity scope (2026-03-23).
- [x] Updated root `AGENTS.md` active ExecPlan pointer to this package (2026-03-23).
- [x] Added package entry to `PROJECT_TRACKER.md` and updated active package counts (2026-03-23).
- [x] Authored end-to-end execution prompt for this package in `prompts/active/roads_wepp_reports_regen_e2e_prompt.md` (2026-03-23).
- [x] Added minimal-regression componentized rollout strategy and dedicated per-rollover regression review requirement (2026-03-23).
- [x] Finalized the active e2e prompt with mandatory startup reads, strict rollout/review gates, and explicit validation/handoff format (2026-03-23).
- [x] Milestone 1 completed: strict `output_scope` contract and scoped path resolver with baseline-default regression tests (2026-03-24).
- [x] Milestone 2 completed: `return_periods` rolled to scoped outputs with dedicated regression artifact and medium/high closure (2026-03-24).
- [x] Milestone 3 completed: `streamflow + water balance` rolled to scoped outputs with dedicated regression artifact and medium/high closure (2026-03-24).
- [x] Milestone 4 completed: `gl-dashboard` rolled to backend-owned scoped path maps with dedicated regression artifact and medium/high closure (2026-03-24).
- [x] Milestone 5 completed: `storm event analyzer` rolled to backend-owned scoped path maps with dedicated regression artifact and medium/high closure (2026-03-24).
- [x] Milestone 6 completed: Roads post-run report-resource regeneration + Roads Run Results summary route/template/control links delivered (2026-03-24).
- [x] Milestone 7 completed: expanded regression coverage + `clogging-starch` fixture e2e verification completed (2026-03-24).
- [x] Milestone 8 completed: cross-cutting code review artifact authored and medium/high findings resolved (2026-03-24).
- [x] Milestone 9 completed: cross-cutting QA review artifact authored and medium/high findings resolved (2026-03-24).
- [x] Milestone 10 completed: final governance/doc sync + full validation gates passed (2026-03-24).
- [x] Follow-up adjustment completed: Roads segment-loss export is parquet-only and CSV is delivered via browse/download conversion (`?as_csv=1`) with no on-disk CSV artifact (2026-03-24).
- [x] Follow-up subagent review remediation completed: fixed roads-scope WEPP loss summary routing, corrected segment-loss join precedence, split GL channel path semantics, and expanded regression coverage for full `wepp_paths` contracts + roads-scope route behaviors (2026-03-24).

## Timeline

- **2026-03-23** - Package created, tracker + ExecPlan + e2e prompt authored.
- **2026-03-23** - Root tracker and AGENTS active-plan pointer updated.
- **2026-03-23** - Added componentized rollover sequence (`return_periods` -> `streamflow/watbal` -> `gl-dashboard` -> `storm event analyzer`) with dedicated regression review gates.
- **2026-03-23** - Finalized active e2e prompt structure (startup checklist, rollover/review closure rules, validation/handoff contract).
- **2026-03-24** - Completed Milestone 1 (`output_scope` guardrails) and Milestone 2 (`return_periods` scope rollover) with dedicated Milestone 2 regression artifact.
- **2026-03-24** - Completed Milestone 3 (`streamflow + water balance` scope rollover) with dedicated Milestone 3 regression artifact.
- **2026-03-24** - Completed Milestone 4 (`gl-dashboard` scope rollover) with dedicated Milestone 4 regression artifact.
- **2026-03-24** - Completed Milestone 5 (`storm event analyzer` scope rollover) with dedicated Milestone 5 regression artifact.
- **2026-03-24** - Completed Milestone 6 (Roads post-run report-resource regeneration + Roads Run Results summary links).
- **2026-03-24** - Completed Milestones 7-10 (regression expansion, fixture e2e, cross-cutting reviews, and full final gates).
- **2026-03-24** - Applied follow-up Roads reports adjustment: generated `roads_segment_loss_summary.parquet` and switched panel CSV access to on-demand browse/download conversion.
- **2026-03-24** - Remediated follow-up subagent code/QA findings with route/report scope fixes, segment-summary join correction, GL channel-path split, and added regression tests.

## Decisions

### 2026-03-23: Keep Roads report resources isolated under `wepp/roads/output`
**Context**: Roads needs canonical report parity without mutating baseline WEPP outputs.

**Options considered**:
1. Reuse/overwrite baseline `wepp/output/interchange` datasets.
2. Generate and consume Roads-scoped resources under `wepp/roads/output/interchange`.

**Decision**: Use option 2.

**Impact**: Baseline WEPP reports remain stable; Roads report parity is explicit and auditable per run.

---

### 2026-03-23: Require independent code and QA reviews in-package before closure
**Context**: Report-scope plumbing crosses NoDb, report adapters, and UI routes, increasing regression risk.

**Options considered**:
1. Close package after implementation tests only.
2. Add independent code review and QA review milestones with mandatory medium/high closure.

**Decision**: Use option 2.

**Impact**: Lowers risk of hidden regressions in canonical report pathways and improves release confidence.

---

### 2026-03-23: Enforce minimal-regression sequencing with dedicated rollover reviews
**Context**: Cross-cutting consumers (return periods, water balance, GL dashboard, storm event analyzer) have differing coupling to baseline `wepp/output` artifacts and caches.

**Options considered**:
1. Do one broad path-swap PR covering all report consumers.
2. Roll over one component at a time with strict scope contract + mandatory dedicated regression review before the next component.

**Decision**: Use option 2.

**Impact**: Limits blast radius, keeps rollback bounded by component, and surfaces scope/caching regressions early.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Canonical report adapters are hard-coded to `wepp/output/interchange` and break Roads scope | High | High | Add explicit output-scope plumbing with baseline default + roads-specific tests | Mitigated (Milestones 1-5 complete) |
| Roads post-run interchange generation may fail on missing optional files for single-storm behavior | Medium | Medium | Gate optional conversions by climate mode and fail explicitly for required Roads report resources | Mitigated (Milestone 6-7 complete) |
| UI links drift from backend route contracts | Medium | Medium | Add route/template tests and run pure-control render tests | Mitigated (Milestones 6-7 complete) |
| Query-engine catalog visibility for Roads datasets may lag after rerun | Medium | Medium | Run explicit catalog refresh and fixture verification on generated Roads datasets | Mitigated (Milestones 6-7 complete) |
| Return-period staging/cache outputs may cross-contaminate baseline and Roads scopes | High | Medium | Use scoped staging/cache roots keyed by `output_scope`; add rollover-specific regression tests | Mitigated (Milestone 2 complete) |
| GL dashboard payloads still embed literal baseline interchange paths | High | Medium | Route all active payload pathing through backend-owned scope maps and add adapter tests | Mitigated (Milestone 4 complete) |
| Storm event analyzer endpoints may preserve legacy baseline path assumptions in transitive loaders | High | Medium | Introduce scoped resolver in each load path and verify end-to-end with fixture-backed route tests | Mitigated (Milestone 5 complete) |
| Silent fallback from Roads scope to baseline outputs hides real data gaps | High | Low | Reject invalid/missing requested scope dependencies with explicit failures (no silent fallback) | Mitigated (scope contract enforced) |

## Verification Checklist

### Code Quality
- [x] `wctl run-pytest tests/wepp/reports -k output_scope --maxfail=1`
- [x] `wctl run-pytest tests/wepp/reports -k return_period --maxfail=1`
- [x] `wctl run-pytest tests/wepp/reports -k "streamflow or watbal" --maxfail=1`
- [x] `wctl run-pytest tests/weppcloud -k gl_dashboard --maxfail=1`
- [x] `wctl run-pytest tests/weppcloud -k "storm_event or analyzer" --maxfail=1`
- [x] `wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1`
- [x] `wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1`
- [x] `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`
- [x] `wctl run-pytest tests/wepp/reports --maxfail=1`
- [x] `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`

### Documentation
- [x] ExecPlan + tracker living sections updated continuously.
- [x] `wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/package.md`
- [x] `wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/tracker.md`
- [x] `wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/prompts/active/roads_wepp_reports_regen_execplan.md`
- [x] `wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/prompts/active/roads_wepp_reports_regen_e2e_prompt.md`

### Testing
- [x] `wctl run-npm lint`
- [x] `wctl run-npm test`
- [x] `wctl run-pytest tests --maxfail=1`
- [x] Fixture verification on `clogging-starch` confirms Roads-scoped report resources and report links.

### Reviews
- [x] `return_periods` dedicated regression review completed; medium/high findings resolved.
- [x] `streamflow + water balance` dedicated regression review completed; medium/high findings resolved.
- [x] `gl-dashboard` dedicated regression review completed; medium/high findings resolved.
- [x] `storm event analyzer` dedicated regression review completed; medium/high findings resolved.
- [x] Code review completed; medium/high findings resolved.
- [x] QA review completed; medium/high findings resolved.

## Progress Notes

### 2026-03-23: Package authoring and activation
**Agent/Contributor**: Codex

**Work completed**:
- Created package scaffold and authored package brief, tracker, active ExecPlan, and execution prompt.
- Updated root `AGENTS.md` active ExecPlan pointer to this package.
- Added package entry to `PROJECT_TRACKER.md` with active package count update.
- Augmented package strategy to require minimal-regression component rollovers and dedicated regression-focused subagent reviews per rollover.

**Blockers encountered**:
- None.

**Next steps**:
- Execute Milestone 1 foundation guardrails, then complete component rollovers in sequence with dedicated regression review gates between milestones.

**Test results**:
- `wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/package.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/tracker.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/prompts/active/roads_wepp_reports_regen_execplan.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/prompts/active/roads_wepp_reports_regen_e2e_prompt.md` (pass)
- `tools/check_agents_size.sh AGENTS.md` (pass; 140 lines)

### 2026-03-23: Active e2e prompt completion
**Agent/Contributor**: Codex

**Work completed**:
- Rewrote `prompts/active/roads_wepp_reports_regen_e2e_prompt.md` into a complete execution prompt with mandatory startup reads, explicit scope guardrails, exact rollout order, and review-closure requirements.
- Added synchronized ExecPlan progress note for the prompt completion so plan/tracker state remains aligned.
- Kept validation expectations explicit in the e2e prompt, including docs lint coverage for package docs and active prompts.

**Blockers encountered**:
- None.

**Next steps**:
- Execute Milestone 1 guardrails from the active ExecPlan and begin rollover sequence with dedicated regression-review artifacts.

**Test results**:
- `wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/prompts/active/roads_wepp_reports_regen_e2e_prompt.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/prompts/active/roads_wepp_reports_regen_execplan.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/tracker.md` (pass)

### 2026-03-24: Milestones 1-2 execution and closure
**Agent/Contributor**: Codex

**Work completed**:
- Added `wepppy/wepp/reports/output_scope.py` with strict `baseline|roads` normalization and scoped path mapping.
- Integrated return-period staging/cache/report route/template flow with explicit `output_scope` plumbing.
- Added/updated regression tests for output-scope contract and return-period roads-scope behavior.
- Authored dedicated Milestone 2 regression artifact: `artifacts/return_periods_regression_review.md`.

**Blockers encountered**:
- Initial ordering bug in `ReturnPeriodDataset` validated scope after context resolution; caused `FileNotFoundError` instead of contract `ValueError` for invalid scopes.
- Resolved by validating `output_scope` before resolving run context.

**Next steps**:
- Execute Milestone 3 (`streamflow + water balance`) rollover, run component tests, complete dedicated regression review artifact, and close all medium/high findings before Milestone 4.

**Test results**:
- `wctl run-pytest tests/wepp/reports -k output_scope --maxfail=1` (pass)
- `wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1` (pass)
- `wctl run-pytest tests/wepp/reports -k return_period --maxfail=1` (pass)

### 2026-03-24: Milestone 3 execution and closure
**Agent/Contributor**: Codex

**Work completed**:
- Added scoped dataset-path support to `HillslopeWatbalReport`, `ChannelWatbalReport`, and `TotalWatbalReport`.
- Added scope-isolated caching for roads hillslope water-balance summaries.
- Rolled over streamflow and water-balance routes/templates to preserve and enforce `output_scope`.
- Added report regression coverage for roads-scoped watbal/streamflow datasets and invalid-scope route assertions.
- Authored dedicated Milestone 3 regression artifact: `artifacts/streamflow_watbal_regression_review.md`.

**Blockers encountered**:
- None.

**Next steps**:
- Execute Milestone 4 (`gl-dashboard`) rollover and close dedicated regression review findings before Milestone 5.

**Test results**:
- `wctl run-pytest tests/wepp/reports -k "streamflow or watbal" --maxfail=1` (pass)
- `wctl run-pytest tests/weppcloud/routes/test_wepp_bp.py -k output_scope --maxfail=1` (pass)

### 2026-03-24: Milestone 4 execution and closure
**Agent/Contributor**: Codex

**Work completed**:
- Added strict `output_scope` handling and backend-owned WEPP path map generation for run-scoped GL Dashboard.
- Added scoped WEPP path map context for batch GL Dashboard mode.
- Removed frontend baseline path literals from active gl-dashboard query payload builders (data/graph/layer modules) by consuming backend path maps.
- Added gl-dashboard route regressions for roads scope and invalid-scope 400 behavior.
- Authored dedicated Milestone 4 regression artifact: `artifacts/gl_dashboard_regression_review.md`.

**Blockers encountered**:
- None.

**Next steps**:
- Execute Milestone 5 (`storm event analyzer`) scope rollover and dedicated regression review closure before Milestone 6.

**Test results**:
- `wctl run-pytest tests/weppcloud -k gl_dashboard --maxfail=1` (pass)
- `wctl run-npm test -- gl-dashboard` (pass)

### 2026-03-24: Milestone 5 execution and closure
**Agent/Contributor**: Codex

**Work completed**:
- Added strict `output_scope` handling for storm-event-analyzer route with explicit `400` response on invalid scope.
- Injected backend-owned scoped `wepp_paths` map into storm-event-analyzer template context.
- Removed baseline path literals from analyzer event-data query payload builders by requiring scoped path input for soil/water/outlet/hill-events/tc datasets.
- Added route coverage for baseline/roads/invalid-scope behavior and JS coverage for scoped path payload wiring + required-context contract.
- Authored dedicated Milestone 5 regression artifact: `artifacts/storm_event_analyzer_regression_review.md`.

**Blockers encountered**:
- One route-test fixture failure due `RonViewModel` expectations on mocked `Ron`; resolved by patching fixture to stub `RonViewModel`.
- One JS test expectation mismatch for missing-path enforcement; resolved by making `createEventDataManager` fail explicitly when `weppPaths` are absent.

**Next steps**:
- Execute Milestone 6 (Roads post-run resource regeneration + Run Results summary), then continue to Milestone 7 fixture e2e and expanded regression coverage.

**Test results**:
- `wctl run-pytest tests/weppcloud -k "storm_event or analyzer" --maxfail=1` (pass)
- `wctl run-npm test -- storm-event-analyzer` (pass)

### 2026-03-24: Milestones 6-10 execution and closure
**Agent/Contributor**: Codex

**Work completed**:
- Implemented Roads post-run regeneration (`_regenerate_roads_report_resources`) in `Roads.run_roads_wepp()` with Roads-only output targeting, required-resource verification, run-log instrumentation, and query-engine refresh.
- Added Roads Run Results summary UX with roads-scoped canonical report links and artifact browse links.
- Expanded regression coverage for Roads controller regeneration behavior, Roads summary route payloads, and Roads controls render expectations.
- Executed fixture-backed e2e on `clogging-starch` and validated required Roads report resources.
- Authored cross-cutting review artifacts:
  - `artifacts/code_review_findings.md`
  - `artifacts/qa_review_findings.md`
- Ran full final validation gates and synchronized tracker/ExecPlan completion status.

**Blockers encountered**:
- Fixture e2e initially failed when optional interchange sources (`soil_pw0.txt`, `chan.out`, `chnwb.txt`) were absent.
- Resolved by explicit source-availability gating for optional conversions while preserving strict required-resource failure behavior.
- Broad-exception enforcement initially failed in `batch_runner_bp.py`; resolved by removing broad catch and narrowing the remaining fallback catch.

**Next steps**:
- Package is complete and ready for handoff/merge.

**Test results**:
- `wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1` (pass)
- `wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1` (pass)
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1` (pass)
- `wctl run-pytest tests/wepp/reports --maxfail=1` (pass)
- `wctl run-npm test -- roads` (pass)
- Fixture e2e command (ExecPlan step 12) (pass; `run_status=completed`, required `missing=[]`)
- `wctl run-npm lint` (pass)
- `wctl run-npm test` (pass)
- `wctl run-preflight-tests ./internal/checklist` (pass)
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` (pass)
- `wctl run-pytest tests --maxfail=1` (pass; 2522 passed, 34 skipped)
- `wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/package.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/tracker.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/prompts/active/roads_wepp_reports_regen_execplan.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/prompts/active/roads_wepp_reports_regen_e2e_prompt.md` (pass)

### 2026-03-24: Follow-up subagent review remediation
**Agent/Contributor**: Codex

**Work completed**:
- Resolved code-review findings by enforcing `output_scope` through `report_wepp_loss` and loss report adapters (`loss_outlet_report.py`, `loss_hill_report.py`, `loss_channel_report.py`) and preserving scope in WEPP summary template links.
- Corrected Roads segment-loss summary joins to prefer `target_hillslope_wepp_id` (with explicit fallback to `segment_run_id`) and added `loss_match_key` diagnostics.
- Split GL dashboard channel dataset semantics (`lossChannel` for channel summaries/cumulative graphs vs `lossAllYearsChannel` for yearly-channel overlays/refresh).
- Expanded test coverage for:
  - full `wepp_paths` contract assertions (run + batch GL dashboard, storm-event-analyzer),
  - roads-scope positive route behavior (`report_wepp_loss`, `avg_annual_watbal`),
  - invalid-scope enforcement including `/report/wepp/summary`,
  - Roads segment-summary generation failure propagation,
  - pure render coverage for `controls/roads_reports.htm`.
- Updated cross-cutting review artifacts (`artifacts/code_review_findings.md`, `artifacts/qa_review_findings.md`) with resolved follow-up findings.

**Blockers encountered**:
- Combined pytest invocation failed due known stub contamination between `test_loss_reports.py` and other modules (temporary `pyproj` stub).  
- Resolved by executing affected suites in isolated pytest commands.

**Next steps**:
- Run/record remaining final gate commands and prepare commit/push handoff.

**Test results**:
- `wctl run-pytest tests/wepp/reports/test_loss_reports.py --maxfail=1` (pass)
- `wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1` (pass)
- `wctl run-pytest tests/weppcloud/routes/test_wepp_bp.py tests/weppcloud/routes/test_gl_dashboard_route.py tests/weppcloud/routes/test_gl_dashboard_batch_route.py tests/weppcloud/routes/test_storm_event_analyzer_route.py tests/weppcloud/routes/test_pure_controls_render.py tests/weppcloud/routes/test_roads_bp.py --maxfail=1` (pass)

### 2026-03-24: Final subagent review closure pass
**Agent/Contributor**: Codex

**Work completed**:
- Resolved final code-review findings by fixing `HillslopeWatbalReport` baseline error propagation and gating Roads Run Results report links by required resource availability (single-storm-safe behavior).
- Resolved final QA findings by adding:
  - roads-scope positive coverage for `yearly_watbal`, `streamflow`, and `return_periods` routes;
  - Roads segment-summary fallback/missing/non-list-manifest branch tests;
  - stronger ordered-call assertions in `controllers_js/__tests__/roads.test.js`;
  - gl-dashboard WEPP path wiring assertions in `gl-dashboard/__tests__/wepp-data.test.js`.
- Updated review artifacts (`artifacts/code_review_findings.md`, `artifacts/qa_review_findings.md`) and active ExecPlan living sections to reflect closure.

**Blockers encountered**:
- Combined pytest invocation triggered known `pyproj` stub contamination across mixed suites.
- Resolved by running affected suites in isolated pytest commands and recording outcomes.

**Next steps**:
- Commit and push the work-package branch.

**Test results**:
- `wctl run-pytest tests/wepp/reports/test_hillslope_watbal.py --maxfail=1` (pass)
- `wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1` (pass)
- `wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1` (pass)
- `wctl run-pytest tests/weppcloud/routes/test_wepp_bp.py --maxfail=1` (pass)
- `wctl run-npm test -- roads.test.js wepp-data.test.js` (pass)
- `wctl run-npm lint` (pass)
- `wctl run-npm test` (pass)
- `wctl run-preflight-tests ./internal/checklist` (pass)
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` (pass)
- `wctl run-pytest tests --maxfail=1` (pass; 2540 passed, 34 skipped)
- `wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/package.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/tracker.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/prompts/active/roads_wepp_reports_regen_execplan.md` (pass)
- `wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/prompts/active/roads_wepp_reports_regen_e2e_prompt.md` (pass)

## Communication Log

### 2026-03-23: User requested new Roads report-resource package and active ExecPlan handoff
**Participants**: User, Codex  
**Question/Topic**: Author a new work-package for Roads report-resource parity + Roads Run Results summary, include code/QA reviews, install as active ExecPlan in `AGENTS.md`, and provide end-to-end agent prompt.  
**Outcome**: Package authored and activated; execution prompt prepared.

### 2026-03-23: User requested completion of active Roads e2e prompt
**Participants**: User, Codex  
**Question/Topic**: Complete `docs/work-packages/20260323_roads_wepp_reports_regen/prompts/active/roads_wepp_reports_regen_e2e_prompt.md`.  
**Outcome**: Prompt rewritten into complete execution contract and synchronized with active ExecPlan/tracker living sections.
