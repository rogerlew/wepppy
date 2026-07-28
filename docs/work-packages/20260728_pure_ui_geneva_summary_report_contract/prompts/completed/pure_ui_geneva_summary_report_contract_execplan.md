# Verify the Geneva interactive summary report

This ExecPlan is maintained under `docs/prompt_templates/codex_exec_plans.md`.
Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes &
Retrospective` current.

## Purpose / Big Picture

An authorized user opening the Geneva summary sees initialized filters, storm
parameters, chart/table selection, and HRU map behavior using the run's
validated payload. Unit preferences update visible data, unavailable data is
explained safely, and query/report responses remain run-scoped and no-store.

## Progress

- [x] (2026-07-28 UTC) Scaffolded SURF-11 and ratified concise intent.
- [x] (2026-07-28 UTC) Traced canonical Geneva spec, routes, template, client,
  Unitizer dependency, query collaborators, and existing tests.
- [x] (2026-07-28 UTC) Added actual-render and single-owner production-init
  regressions.
- [x] (2026-07-28 UTC) Ran/extended client, route, and applicable
  query/service evidence.
- [x] (2026-07-28 UTC) Confirmed conformance without a production repair.
- [x] (2026-07-28 UTC) Completed broad validation, independent security
  review, records, and commit preparation.

## Surprises & Discoveries

- Observation: Initial search incorrectly treated test calls as the only
  initialization path; the controller itself already registers a
  `DOMContentLoaded` initializer near its export.
  Evidence: Independent review traced the source and generated bundle and
  showed that a proposed template initializer would create two lifecycle
  owners and duplicate request listeners.

- Observation: Counting an inline initialization string in rendered HTML
  cannot prove lifecycle ownership across a deferred bundle.
  Evidence: The corrected Jest regression spies on listener registration,
  asserts one controller-owned initializer, invokes it, and observes the
  rendered parameter rows.

## Decision Log

- Decision: Preserve the canonical Geneva Section 13/14 response and UI
  contracts without schema or hydrologic changes.
  Rationale: SURF-11 verifies the registered report surface; DOM-27 owns domain
  execution and artifacts.
  Date/Author: 2026-07-28 / Codex with operator authority.

- Decision: Preserve the controller as the sole production initialization
  owner and test that lifecycle directly.
  Rationale: `init()` is not idempotent, and adding a second template-owned
  listener would duplicate filter/map request handlers.
  Date/Author: 2026-07-28 / Codex.

## Outcomes & Retrospective

SURF-11 closed without a production repair. Direct rendering verifies the
report payload, exact selected filters, run-scoped query/map URLs, map actions,
empty/error states, and accessibility targets. The focused route/render set
passed 133 tests; Geneva event-measure/map services passed 11; focused Jest
passed 7. Frontend lint and the full 89-suite/671-test frontend sweep passed.

The first independent review blocked a proposed duplicate template bootstrap.
Removing it and adding runtime lifecycle ownership evidence preserved the
already-conforming production path. Final security review passed with no
unresolved findings. The repository-wide Python sweep reached 2,452 passes and
40 skips before stopping on the known unrelated GridMET `_FakeUnits.degC`
fixture failure.

## Context and Orientation

`wepppy/nodb/mods/geneva/specification.md` sections 13 and 14 define the
canonical routes and interactive summary. `geneva_bp.py` owns four report/query
producers. `summary.htm` embeds the payload and run URLs.
`geneva_summary_report.js` renders filters, chart/table selection, Unitizer
updates, and the deck.gl HRU map. DOM-27 already verified Geneva execution.

## Plan of Work

Render the production template with representative persisted filters,
availability, events, and shell context. Assert exact risk-bearing fields,
selected state, payload, URLs, targets, and initialization. Retain route tests
for validation/no-store/context and Jest tests for selection, filters,
Unitizer, map requests/layers, availability, and errors after inspecting them.
Run focused Geneva schema/collaborator tests only where they prove payload
seams. If initialization or another behavior contradicts the concise contract,
retain the failing regression, patch minimally, rebuild, and obtain independent
security/correctness review.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py tests/weppcloud/routes/test_geneva_bp.py --maxfail=1
    wctl run-npm test -- geneva_summary_report
    wctl run-pytest tests/nodb/mods/geneva/test_geneva_query_schema.py tests/nodb/mods/geneva/test_geneva_hru_event_measure_service.py --maxfail=1
    python wepppy/weppcloud/controllers_js/build_controllers_js.py
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260728_pure_ui_geneva_summary_report_contract
    wctl doc-lint --path docs/work-packages/20260716_pure_ui_contract_standardization_c
    git diff --check

Build only after controller source changes. No RQ graph/stub gate applies
without corresponding implementation changes.

## Validation and Acceptance

Acceptance requires direct actual-render evidence, exactly one production
initialization path, existing client interaction/map/Unitizer evidence, and
route/query validation/no-store/run-scoping evidence. All focused, frontend,
documentation, and applicable broad gates pass or record a proven unrelated
pre-existing failure.

## Idempotence and Recovery

All render/Jest/pytest/lint/build commands are safe to rerun. Rebuild generated
assets only from controller sources. Preserve unrelated work and stop before
any intended schema, parameterization, authorization, or terrain-provider
change.

## Interfaces and Dependencies

Preserve the four registered route paths, schema version, top-level payloads,
`data-geneva-summary-*` hooks, `GenevaSummaryReport.getInstance()`, Unitizer
event name, and no-store headers. Add no dependency, queue edge, Flask query
wrapper, or fallback persistence.

## Revision Notes

2026-07-28: Created from explicit operator direction after SHR-05 closed.
2026-07-28: Closed after correcting initialization evidence; no production
repair was retained.
