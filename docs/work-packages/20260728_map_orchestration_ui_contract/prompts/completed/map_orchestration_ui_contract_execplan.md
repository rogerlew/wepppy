# Execute DOM-04A Map Orchestration Contract Audit

This ExecPlan is a living document. Maintain it under
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

This package ensures a WEPPcloud user can use the rendered Map control to
navigate by coordinate, find a TOPAZ or WEPP identifier, load its drilldown,
and obtain an elevation reading. The proof is direct rendered-template and
controller/request testing, not a new UI-contract platform.

## Progress

- [x] (2026-07-28 UTC) Scoped DOM-04A, separated DOM-04B helpers, and created
  the package, tracker, and field matrix.
- [x] Added actual-render actions/targets and exact elevation request
  assertions; no mismatch was found.
- [x] Ran focused Python (121 passed), frontend lint, and focused Map Jest
  (38 passed).
- [x] Ran full frontend validation (88 suites, 662 tests passed).
- [x] Full Python suite stopped after 2,451 passes on an unrelated GridMET
  fake-units fixture failure; recorded the result and closed this package.

## Surprises & Discoveries

- Observation: Map orchestration has no persisted map-state or RQ boundary.
  Evidence: `map_gl.js` navigates the Deck view, fetches elevation, or requests
  report HTML; no mutation/queue call is in scoped actions.

## Decision Log

- Decision: Test rendered action hooks and the exact elevation request rather
  than general map-layer behavior.
  Rationale: These values cross the DOM/controller/route boundary; layers,
  scales, legends, and feature presentation are explicitly DOM-04B.
  Date/Author: 2026-07-28 / Codex

## Outcomes & Retrospective

DOM-04A closed without a production repair. Direct tests now protect the
actual Map action hooks and the exact run-scoped elevation `{lat, lng}` request.
Existing coordinate, TOPAZ/WEPP lookup, drilldown, elevation microservice, and
report-route tests conformed. No helper was extracted and no production
security boundary changed. Focused validation passed: 121 Python tests,
frontend lint, 38 Map Jest tests, and the full frontend suite (88 suites, 662
tests). The full Python suite stopped after 2,451 passes and 40 skips on
`test_gridmet_interpolation_propagates_unpublished_suffix_to_parquet_and_prn`:
its climate test fixture lacks `degC`. That failure is outside DOM-04A; its
tracker records the exact evidence for a separate climate-owner repair.

## Context and Orientation

`wepppy/weppcloud/templates/controls/map_pure_gl.htm` renders the Map form and
is included by `routes/run_0/templates/runs0_pure.htm`. The singleton in
`wepppy/weppcloud/controllers_js/map_gl.js` binds map actions. Its elevation
request uses the run-scoped `elevationquery/` microservice, while TOPAZ and
WEPP searches load report drilldowns. `map_gl_*` helper behavior belongs to
DOM-04B and is out of scope.

## Plan of Work

Add actual Jinja-render assertions for map host/action identities to
`tests/weppcloud/routes/test_pure_controls_render.py`. Add a focused Jest
assertion that hover sends numeric latitude/longitude to the run-scoped
elevation endpoint. Reuse existing coordinate/search/drilldown tests and the
elevation microservice/report route tests. If all evidence conforms, make no
production change; otherwise write the failing regression first and apply only
the smallest compatible repair.

## Concrete Steps

From `/home/workdir/wepppy`, run:

    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py tests/microservices/test_elevationquery.py tests/weppcloud/routes/test_wepp_bp.py --maxfail=1
    wctl run-npm lint
    wctl run-npm test -- map_gl
    wctl run-npm test
    wctl doc-lint --path docs/work-packages/20260728_map_orchestration_ui_contract

If controller source changes, rebuild with:

    python wepppy/weppcloud/controllers_js/build_controllers_js.py

## Validation and Acceptance

The focused Python suite must pass and prove rendered identities plus elevation
responses and report routes. Map Jest must prove coordinate/search/drilldown
behavior and exact elevation payload. The full frontend suite must pass after
Jest edits. No route or controller build is required unless production source
changes.

## Idempotence and Recovery

All tests and documentation edits are repeatable. If a mismatch is found,
retain the direct regression, narrow the patch to the mismatched seam, and
re-run the commands above. Do not edit DOM-04B helpers in this package.

## Artifacts and Notes

The concise action matrix is at
`docs/work-packages/20260728_map_orchestration_ui_contract/artifacts/field_matrix.md`.

## Interfaces and Dependencies

The controller uses `WCHttp.postJson(url_for_run("elevationquery/"), {lat,
lng})`; the microservice returns `elevation`, `units`, `latitude`, and
`longitude`, with an `error.message` when unavailable. Report drilldown URLs
remain `report/sub_summary/<topaz_id>/` and `report/chn_summary/<topaz_id>/`.
