# Roads Step-4: Outslope Unrutted MOFE Hillslope Replacement

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package, `outslope_unrutted` is modeled as a sheet-flow MOFE replacement path, not additive comparison. For targeted hillslopes, Roads will synthesize replacement contributors with ordering `hill -> road -> fill -> hill`, enforce area conservation, stage replacement pass files, and rerun watershed routing with unchanged topology.

## Progress

- [x] (2026-03-27 00:00Z) Authored package/tracker/ExecPlan scaffold for step-4 scope.
- [ ] Milestone 1: Implement decomposition contract for targeted hillslopes (`affected strips` + `unaffected remainder`).
- [ ] Milestone 2: Build MOFE contributors with fixed ordering `hill -> road -> fill -> hill`.
- [ ] Milestone 3: Aggregate contributors into one replacement pass per targeted hillslope.
- [ ] Milestone 4: Stage replacement pass files with strict replacement (no additive double counting).
- [ ] Milestone 5: Add area-conservation/topology validation and diagnostics.
- [ ] Milestone 6: Add regression tests and fixture-backed validation.
- [ ] Milestone 7: Complete code-review artifact and resolve medium/high findings.
- [ ] Milestone 8: Complete QA-review artifact and resolve medium/high findings.
- [ ] Milestone 9: Run final gates and update handoff docs.

## Surprises & Discoveries

- Observation: Current Roads pass merge is additive and inslope-focused in phase 1.
  Evidence: existing run merge flow in `wepppy/nodb/mods/roads/roads.py`.

- Observation: User requires replacement semantics explicitly, not baseline-vs-road delta behavior.
  Evidence: user direction captured in Roads specification concept section and discussion.

- Observation: Buffer-effect fidelity at lower hillslope reaches is a key user requirement for `outslope_unrutted`.
  Evidence: user rejected simplified delta approach due to poor buffer representation.

## Decision Log

- Decision: Replacement semantics are mandatory for `outslope_unrutted`.
  Rationale: avoids double counting and matches user’s “enhanced model” intent.
  Date/Author: 2026-03-27 / User + Codex.

- Decision: Contributor ordering is fixed to `hill -> road -> fill -> hill`.
  Rationale: captures sheet-flow representation and explicit buffering.
  Date/Author: 2026-03-27 / User + Codex.

- Decision: Area conservation is a hard acceptance gate, not advisory telemetry.
  Rationale: replacement model correctness depends on matching original hillslope area.
  Date/Author: 2026-03-27 / Codex.

## Outcomes & Retrospective

Not complete yet. Fill during implementation milestones and final closure.

## Context and Orientation

This package runs primarily in `/workdir/wepppy`.

Key files:
- `wepppy/nodb/mods/roads/roads.py` (pass construction, merge/staging, run summaries).
- `wepppy/nodb/mods/roads/monotonic_segments.py` (segment/low-point metadata and receiving hillslope linkage).
- `wepppy/nodb/mods/roads/specification.md` (replacement invariants and deferred-detail sections).
- `wepppyo3` pass-combine interfaces used by Roads for hillslope pass assembly.

Dependencies:
- Step-1/2/3 packages must be completed for trace and point-source infrastructure.

Working-tree rule:
- `/workdir/wepppy` may contain unrelated dirty files; do not revert or modify unrelated changes.
- Restrict edits to Roads step-4 implementation/test/docs files.

## Plan of Work

Milestone 1 - Targeted-hillslope decomposition:

- Define data structures representing:
  - road-affected strips mapped to receiving hillslopes,
  - unaffected remainder per targeted hillslope.
- Implement decomposition with deterministic IDs and summary diagnostics.

Milestone 2 - MOFE contributor assembly:

- Build per-strip roads-aware contributors with OFE ordering:
  - upslope hill segment,
  - road segment,
  - fill segment,
  - downslope buffer segment.
- Parameterize `road` and `fill` from roads attributes/defaults; parameterize hill/buffer using receiving hillslope context.

Milestone 3 - Replacement pass aggregation:

- Run WEPP for each contributor as needed.
- Aggregate contributor pass outputs to produce one synthetic replacement `H<wepp_id>.pass.dat` per targeted hillslope.
- Keep untouched hillslope pass files baseline.

Milestone 4 - Replacement staging contract:

- Stage replacement pass files for targeted hillslopes in watershed rerun input set.
- Ensure targeted hillslopes are replaced exactly once and never additionally include baseline pass in the same run set.

Milestone 5 - Invariants and diagnostics:

- Add strict invariant checks:
  - replacement-only semantics for targeted hillslopes,
  - area conservation per targeted hillslope,
  - topology preservation (`left/right/top` linkage unchanged).
- Persist invariant results and contributor inventory in run summary.

Milestone 6 - Tests and fixtures:

- Add deterministic tests for:
  - area conservation,
  - replacement staging,
  - contributor ordering.
- Run fixture-backed validation proving watershed rerun success and replacement inventory correctness.

Milestones 7 and 8 - Mandatory reviews:

- Milestone 7: independent code review artifact at `artifacts/20260327_code_review.md`; resolve all medium/high findings.
- Milestone 8: independent QA review artifact at `artifacts/20260327_qa_review.md`; resolve all medium/high findings.

Milestone 9 - Final gates and docs synchronization.

## Concrete Steps

Run from `/workdir/wepppy`.

1. Implement Milestones 1-3 and run focused tests:

    wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1
    wctl run-pytest tests/nodb/mods/test_roads_monotonic_segments.py --maxfail=1

2. Implement Milestones 4-5 and run integration checks:

    wctl run-pytest tests/wepp/reports --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1

3. Milestone 6 broader validation:

    wctl run-npm test -- roads
    wctl run-npm lint
    wctl run-pytest tests --maxfail=1

4. Docs and review artifacts:

    wctl doc-lint --path wepppy/nodb/mods/roads/specification.md
    wctl doc-lint --path docs/work-packages/20260327_roads_outslope_unrutted_mofe_replacement/package.md
    wctl doc-lint --path docs/work-packages/20260327_roads_outslope_unrutted_mofe_replacement/tracker.md
    wctl doc-lint --path docs/work-packages/20260327_roads_outslope_unrutted_mofe_replacement/prompts/active/roads_outslope_unrutted_mofe_replacement_execplan.md

## Validation and Acceptance

Acceptance requires:

- `outslope_unrutted` uses replacement, not additive semantics, for targeted hillslopes.
- Contributor ordering is `hill -> road -> fill -> hill`.
- Area conservation checks pass per targeted hillslope.
- Untouched hillslopes remain baseline.
- Watershed rerun succeeds with mixed replacement + baseline pass files.
- Required suites pass.
- Code and QA review artifacts exist with no unresolved medium/high findings.

## Idempotence and Recovery

- Re-running replacement workflow should regenerate targeted replacement passes deterministically.
- Invariant check failures must fail fast and identify targeted hillslope IDs.
- No fallback to additive staging is permitted.

## Artifacts and Notes

Required artifacts:
- `docs/work-packages/20260327_roads_outslope_unrutted_mofe_replacement/artifacts/20260327_code_review.md`
- `docs/work-packages/20260327_roads_outslope_unrutted_mofe_replacement/artifacts/20260327_qa_review.md`

Recommended evidence:
- per-hillslope area-conservation report,
- replacement inventory table (targeted hillslope IDs and contributor counts).

## Interfaces and Dependencies

End-state requirements:

- Roads run summaries expose replacement diagnostics and conservation checks.
- Replacement pass staging explicitly overrides targeted baseline hillslopes.
- `outslope_unrutted` implementation remains compatible with previously delivered point-source infrastructure.

Dependency requirement:
- Consume step-1 trace and step-2/3 contributor contracts; do not introduce duplicate tracing/aggregation frameworks.

---

Revision note (2026-03-27 00:00Z): Initial step-4 ExecPlan authored with replacement semantics, area-conservation gates, and mandatory code/QA review milestones.
