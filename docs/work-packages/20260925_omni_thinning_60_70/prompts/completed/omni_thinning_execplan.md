# Add Omni thinning 60% and 70%

This ExecPlan follows docs/prompt_templates/codex_exec_plans.md.

Completed 2026-09-25 UTC: code and local generated-input validation delivered.
Broad suite has one confirmed preexisting failure; no deployment claimed.

## Purpose / Big Picture

Provide six remaining-canopy choices 30/40/50/60/65/70 while retaining saved
65% scenarios. New 60/70 variants support all four existing ground covers.

## Progress

- [x] 2026-09-25 UTC: recipe inspected; scope, contract and ADR drafted.
- [x] Independent contract reviews; ancestor `9ed739875`.
- [x] Tests first, static assets/catalogs/selector and documentation.
- [x] Focused generated-input/archive 308 tests and frontend 913 tests pass.
- [x] Required broad run: 5,326 passed, 54 skipped; one preexisting timeout assertion failed.
  Later tests were not executed.
- [x] Independent correctness/QA pass; package and plan closed.

## Surprises & Discoveries

The shared thinning soil-prefix fix already covers the new choices. Extend its
artifact matrix rather than changing soil parameterization. The broad suite reproduced the unrelated 60-versus120 timeout expectation;
runner/test/ADR blobs match the starting revision. Retain truthful gate status.

## Decision Log

2026-09-25 operator/Codex: preserve 65% and all old files/IDs for compatibility;
add eight static variants from corresponding 40% files. Keep 40% default. Avoid
canopy override APIs that also scale LAI; only static cancov changes.

## Outcomes & Retrospective

Implementation `2d0891398` delivers all eight variants and preserves 65%/default 40%.
308 focused tests, 12 subtests, 913 frontend tests and 230 real soil tests pass.
Broad suite stopped on unchanged timeout debt; no full-suite pass is claimed.
Locally validated code delivery is complete; production/live acceptance and fresh
model results remain separate.

## Context and Orientation

wepppy/wepp/management/data/UnDisturbed holds thinning assets. Five catalogs are
disturbed, c3s-disturbed, au-disturbed, eu-corine-disturbed, revegetation. CSV mirror
is management/scripts/disturbed_weppcloud_managements.csv. Omni selector lives in
wepppy/weppcloud/controllers_js/omni.js. Existing test_thinning_variants.py and
nodb/test_mofe_scenario_artifacts.py read generated managements; disturbed
soil artifact tests protect the recently corrected soil selection boundary.

## Plan of Work

Commit reviewed canonical amendment/checkpoint first. Expand current regression
parameters and capture a missing-variant failure. Add eight management files by
copying 40% counterparts, changing only initial canopy. Allocate 151–158/451–458
without changing old IDs. Extend selector options and preserve 40% default. Update
user/operator/developer docs and regenerate CSV through the existing exporter,
retaining only added rows to avoid unrelated historical drift.

## Concrete Steps

From /home/workdir/wepppy use wctl run-pytest on management variants, MOFE artifact,
archive, management catalog snapshot and new soil cases. Run wctl run-npm lint,
wctl run-npm test and canonical container controller build. Then run
wctl run-pytest tests --maxfail=1. Record every result and disposition unrelated
failures without inflating coverage. Run wctl doc-lint, spelling previews,
broad-exception enforcement and observe-only quality report to temporary paths.

## Validation and Acceptance

All eight new variants parse as canopy 0.60/0.70 and both ground fractions equal
filename ground percentage. Every other numerical parameter equals 40% source.
All five catalogs resolve each variant. Actual single/MOFE/prepared inputs and
canonical restored archives preserve these values. Old files and entries compare
unchanged. UI defaults40/93 and hydrates 65% and new 60/70 correctly. Extend existing
thinning soil artifact coverage to new prefixes; numerical row stays unchanged.

## Idempotence and Recovery

Tests use temporary directories. No real project mutations. Before any 60/70
selections are saved, selector availability can be rolled back. Afterwards retain
saved 60/70 hydration/serialization and referenced files/IDs during rollback.
Simply removing selector options would lose saved-value hydration.
Do not remove 65%. Preserve unrelated working-tree changes and current branch.

## Artifacts and Notes

Retain command results, compatibility comparison and independent review artifacts
under artifacts/. Update tracker and PROJECT_TRACKER at each milestone.

## Interfaces and Dependencies

No new interfaces or dependencies. Reuse management parser/writer, existing
MOFE synthesis, WEPP preparation, archive/restore and frontend helpers.

Revision note: initial plan records requested additive options and compatibility.

Revision note: final outcome records implemented options, retained compatibility,
passing direct artifact gates and the unrelated failed broad-suite gate.
