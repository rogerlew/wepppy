# Roads WEPP Report Regeneration and Run Results Summary

**Status**: Open (2026-03-23)

## Overview
This package extends the Roads phase-1 execution path so a completed Roads run produces the same downstream report resources expected by canonical WEPP report endpoints. It also adds a Roads-specific Run Results summary view with links to Roads-augmented outputs and reports rooted at `wepp/roads/output`.

## Objectives
- Regenerate Roads-scoped interchange outputs after `run_roads_wepp()` watershed rerun completes.
- Build Roads-scoped `totalwatsed3` and water-balance resources needed by canonical WEPP report workflows.
- Expose a Roads Run Results summary with links to Roads-scoped canonical WEPP reports and artifact files.
- Execute a minimal-regression rollout with strict scope controls (`baseline|roads`, default `baseline`) and no baseline fallback when Roads scope is requested.
- Complete report rollovers component-by-component (`return_periods`, `streamflow + water balance`, `gl-dashboard`, `storm event analyzer`) with dedicated regression-focused subagent reviews per component.
- Add independent code-review and QA-review passes, and resolve all medium/high findings before closure.

## Scope
This package includes the implementation and validation needed to make Roads report resources parity-complete for canonical WEPP reporting, without mutating baseline `wepp/output` artifacts.

### Included
- Roads controller post-run resource regeneration under `wepp/roads/output/interchange`.
- Roads run summary state updates that surface report-resource readiness and artifact paths.
- Report-routing/report-adapter changes needed to render canonical WEPP reports against Roads outputs.
- Centralized scope resolver and path contract for report resources (strict enum, baseline default, no arbitrary path input).
- Componentized rollover implementation order and guardrails for:
  - return periods
  - streamflow + water balance
  - GL Dashboard
  - Storm Event Analyzer
- Roads Run Results summary UI endpoint/template and control-link integration.
- Targeted and full validation gates, fixture e2e verification on `clogging-starch`, and review artifacts.
- Independent code and QA review milestones with findings triage/resolution requirements.
- Dedicated subagent regression reviews for each component rollover before proceeding to the next component.

### Explicitly Out of Scope
- Hydrologic/erosion algorithm changes to Roads segment execution or pass-combine math.
- Non-Roads module report UX redesign.
- New fallback wrappers that mask missing report dependencies.
- Non-inslope Roads designs.

## Stakeholders
- **Primary**: WEPPcloud users running Roads-augmented disturbed watershed runs.
- **Reviewers**: NoDb + WEPPcloud route/report maintainers, query/report maintainers, QA maintainers.
- **Informed**: Operations maintainers watching queue/preflight/report regression risk.

## Success Criteria
- [ ] `run_roads_wepp()` regenerates Roads report resources under `wepp/roads/output/interchange` and records readiness in `last_run_summary`.
- [ ] Roads outputs include resources needed by canonical WEPP reports (loss summaries, totalwatsed3, water-balance, and watershed interchange files).
- [ ] Roads Run Results summary route/template provides stable links for Roads-scoped report and artifact access.
- [ ] Canonical WEPP reports can be rendered against Roads outputs without overwriting baseline `wepp/output` resources.
- [ ] Output-scope contract is explicit and constrained (`baseline|roads` only), default remains `baseline`, and invalid scopes fail with explicit 400 errors.
- [ ] Return periods rollover includes scoped staging/cache isolation and no cross-scope contamination.
- [ ] Streamflow and water-balance rollover preserves baseline behavior and isolates scoped caches.
- [ ] GL Dashboard and Storm Event Analyzer consume backend-owned scope/path maps with no literal baseline-path coupling remaining in active query payloads.
- [ ] Each rollover component has dedicated regression-review artifacts, and medium/high findings are resolved before the next rollover starts.
- [ ] Code review completed and all medium/high findings resolved.
- [ ] QA review completed and all medium/high findings resolved.
- [ ] Required validation gates pass (`pytest`, `npm lint/test`, preflight tests, broad-exception check, docs lint).

## Dependencies

### Prerequisites
- Completed Roads phase-1 package: `docs/work-packages/20260323_roads_nodb_inslope_e2e/`.
- Roads specification authority: `wepppy/nodb/mods/roads/specification.md`.
- Fixture run data available at `/wc1/runs/cl/clogging-starch`.

### Blocks
- Roads report-product readiness and user-facing Roads report navigation depend on this package.

## Related Packages
- **Depends on**: [20260323_roads_nodb_inslope_e2e](../20260323_roads_nodb_inslope_e2e/package.md)
- **Related**: [20260208_rq_engine_agent_usability](../20260208_rq_engine_agent_usability/package.md)
- **Follow-up**: Roads comparative baseline-vs-roads analytics package (to be scoped after this package closes).

## Timeline Estimate
- **Expected duration**: 3-6 focused sessions.
- **Complexity**: High.
- **Risk level**: Medium-High.

## References
- `wepppy/nodb/mods/roads/specification.md` - Roads source-of-truth contract.
- `wepppy/nodb/mods/roads/roads.py` - Roads run pipeline and persisted summaries.
- `wepppy/nodb/wepp_nodb_post_utils.py` - canonical WEPP post-run regeneration helpers.
- `wepppy/wepp/interchange/*` - interchange and totalwatsed generation functions.
- `wepppy/wepp/reports/*` - canonical report adapters with current dataset-path assumptions.
- `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` - canonical WEPP report route behavior.
- `wepppy/weppcloud/routes/nodb_api/roads_bp.py` - Roads API/report surfaces.
- `docs/ui-docs/ui-style-guide.md` - UI implementation and structure constraints.
- Fixture defaults:
  - run id: `clogging-starch`
  - wd: `/wc1/runs/cl/clogging-starch`
  - config: `disturbed9002-wbt-mofe.cfg`
  - roads input: `/wc1/runs/cl/clogging-starch/roads/UM1_roads_info.geojson`
  - DEM: `/wc1/runs/cl/clogging-starch/dem/wbt/relief.tif`

## Deliverables
- Active ExecPlan: `prompts/active/roads_wepp_reports_regen_execplan.md`.
- End-to-end execution prompt: `prompts/active/roads_wepp_reports_regen_e2e_prompt.md`.
- Package tracker with review milestones and gate status: `tracker.md`.
- Implemented code/test changes enabling Roads-scoped canonical report resources and Run Results summary links.
- Review artifacts under `artifacts/` documenting code/QA findings and resolutions.
- Dedicated component regression-review artifacts:
  - `artifacts/return_periods_regression_review.md`
  - `artifacts/streamflow_watbal_regression_review.md`
  - `artifacts/gl_dashboard_regression_review.md`
  - `artifacts/storm_event_analyzer_regression_review.md`

## Follow-up Work
- Add explicit Roads-vs-baseline comparative charts and report deltas.
- Evaluate whether report output-scope support should be generalized to additional scenario outputs beyond Roads.
