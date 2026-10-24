# Implement Roads detachment and dashboard output scope

This living ExecPlan follows docs/prompt_templates/codex_exec_plans.md. The user authorized implementation after independent contract review. The standalone reviewed ancestor is `2399f835c`. Execute this plan, not the completed review plan.

## Purpose / Big Picture

Users can display mean annual Roads detachment on prepared road centerlines and switch between Baseline and Roads WEPP results inside GL Dashboard. The reported clogging-starch project has 39 lines and 34 profiles but the existing dashboard has no renderer. Implement the accepted canonical docs/schemas/roads-gl-dashboard-contract.md and ADR-0105. No model rerun or deployment is included.

## Progress

- [x] Reviewed contract committed as standalone ancestor `2399f835c` before runtime edits.
- [x] Implement coherent authorized detachment response and regression tests.
- [x] Implement Roads overlay, accessible details, legends and scope transitions.
- [ ] Validate real artifacts, HTTP/browser behavior and regression gates.
- [x] Obtain independent correctness/security/UX implementation reviews; twelve findings fixed and independently closed.
- [ ] Update user/developer documentation and record final evidence.

## Surprises & Discoveries

The broad gate caught scientific publication source discovery including the new
HTTP-only reader placed under NoDb Roads. Move that reader beside its route;
retain the strict scientific source inventory and published identities unchanged.
All 516 model cases passed before this provenance failure.

Scope restoration needs both early preference hydration and actual dynamic-layer activation after discovery. A selected radio alone does not reload yearly data. Nullable defaults also require explicit type validation. Regression tests now cover these discovered failures.

The prior successful rerun is valid artifact evidence, but cannot supply a missing renderer. Independent browser artifact requests can mix preparations with reused IDs; the server must materialize one response under the existing shared Roads guard.

## Decision Log

Use the reviewed additive `resources/roads.json?view=detachment` response. Preserve the ordinary map response. Reuse shared Roads admission, existing CRS transformations, jet2 palette and dashboard modules. Scope changes use the established URL parameter. Optional Roads failures must not poison baseline query state. These choices were accepted in the reviewed ancestor; implementation cannot relax them.

## Outcomes & Retrospective

Implementation and focused runtime/browser validation pass. Independent reviews pass. Broad Python regression and existing dashboard smoke checks remain in progress; no deployment claimed.

## Context and Orientation

The Roads controller is wepppy/nodb/mods/roads/roads.py. Shared read admission is wepppy/wepp/interchange/_roads_lifecycle.py. The authorized map route lives in wepppy/weppcloud/routes/nodb_api/roads_bp.py. Dashboard page context comes from routes/gl_dashboard.py and templates/gl_dashboard.htm. Browser wiring is static/js/gl-dashboard.js; supporting modules live in static/js/gl-dashboard/. Tests are under tests/nodb/mods, tests/weppcloud/routes and wepppy/weppcloud/static-src/tests.

Canonical authority also includes output-scope, Roads preparation lifecycle, segment summary, NoDb persistence and shared UI controller contracts. The reviewed package decision artifact names these boundaries. Prepared geometry, effective input_crs, manifest and summary must be read coherently. Full-profile rate is 10 times summed annual soil_loss_kg divided by summed modeled_area_m2. Distinct completed profiles only; replacement remainders are counted separately. Signed negative values remain distinct. Partial lines expose diagnostics without aggregate color. No fill, buffer or land-use footprints are drawn.

## Plan of Work

First add a bounded read materializer using the existing shared admission guard. Validate IDs, metrics, duration and effective CRS; transform to longitude/latitude. Preserve source properties but reserve computed roads_detachment metadata. Add the opt-in route after existing authorization and preserve lifecycle error codes/no-store. Tests exercise actual temporary artifacts and guards, including contention; mocks cannot establish filesystem safety.

Next add a dashboard Roads data/controller module and line rendering through existing Deck layers. Use text nodes for labels, persistent details and keyboard/table selection. Add independent visibility and scale controls, numeric legend and negative/unavailable labels. Add visible output scope navigation preserving map and compatible display choices. Disable incompatible map scenarios/comparisons in Roads scope; clear unsupported graphs with explanation, preserving supported graph rules. Initial unavailable Roads pages keep error status and provide Baseline escape. Roads results entry enables the overlay; ordinary entry does not.

Finally run focused tests, frontend gates, broad pytest and read-only browser checks on actual clogging-starch artifacts. Have the existing independent reviewers review implementation and evidence; resolve findings before acceptance. Update documentation, tracker and this plan. No production project mutation, rerun, service deployment, new dependency, queue or persisted schema change is authorized by this plan.

## Compatibility and Regression Plan

The HTTP view is additive; requests without view retain existing shape. No persisted project columns, NoDb fields, model files or artifact paths change. Verify actual existing artifact values propagate to the response and browser without regenerating model outputs. Validate absent optional Roads, typed-empty valid summary, populated single/multiple/mixed profiles, valid single-storm, stale/failed/busy lifecycle, old beta without receipt, hostile labels, malformed IDs/metrics/CRS, and authorization denial. Continuous missing summary remains scope-ineligible. Baseline remains usable for all optional-layer failures. Unsupported explicit views return 400 only after authorization.

## Concrete Steps

Work in /home/workdir/wepppy. Use wctl run-pytest for focused Python tests, wctl run-npm lint and wctl run-npm test for frontend, then wctl run-pytest tests --maxfail=1. Run targeted Playwright dashboard smoke tests with PLAYWRIGHT_BROWSERS_PATH=/workdir/wepppy/wepppy/weppcloud/static-src/.playwright-browsers. Read smoke AGENTS before authenticated checks. Use wctl doc-lint --path for changed documentation and git diff --check. Record exact commands/results in artifacts/implementation_validation.md. Do not start containers automatically if the existing stack is unavailable.

## Validation and Acceptance

On the reported dashboard, Roads detachment becomes selectable and draws only centerlines. Values must agree with source summary aggregation; no second annualization or receiving-hillslope substitution. Scope navigation works both ways and reflects corresponding datasets without stale scenario/graph values. Keyboard access reaches segment details. Malicious labels remain literal. Baseline can recover from optional Roads errors; unavailable initial Roads navigation retains HTTP lifecycle failure with a Baseline link. Existing ordinary prepared map consumers remain unchanged. Passing tests alone do not establish browser or live artifact acceptance.

## Idempotence and Recovery

All production artifact reads are read-only. Use temporary fixtures for mutation/race tests. Keep unrelated working-tree changes untouched. Changes can be reverted by scoped commits without data migration. Record failures honestly and repeat only relevant gates after fixes.

## Artifacts and Notes

Contract reviews and nine closed findings are retained in artifacts/review_disposition.md and review_manifest.json. Their original reviewed hashes remain historical evidence. Retain final implementation reviews and validation separately.

## Interfaces and Dependencies

The new view is a longitude/latitude GeoJSON FeatureCollection with top-level roads_detachment state, units, remainder count and reason. Each feature carries complete/partial/no_results state, nullable aggregates and completed raw profile diagnostics including segment_length_m. Use installed geospatial/PyArrow facilities and existing lifecycle locks. Browser data stays separate from the query-engine Roads-unavailable latch. No new infrastructure or identity protocol is permitted.

Revision: initial implementation plan records new user authorization and ancestor checkpoint before runtime work.

Revision: implementation and independent findings disposition completed; focused Python 279, frontend 1007 and live browser 3 checks pass. Broad regression remains running.

Revision: invalid-maximum edits retain active scale; scoped lifecycle failures preserve busy guidance and hide stale scene content while keeping Baseline navigation. Final frontend 1012/browser 4 checks pass; broad Python remains running.

Revision: COR-I05 isolates child/contrast graph lifecycle failures from current-run admission. Final frontend 1017/browser 5 checks pass; independent correctness/security approval retained. Broad Python remains running.
