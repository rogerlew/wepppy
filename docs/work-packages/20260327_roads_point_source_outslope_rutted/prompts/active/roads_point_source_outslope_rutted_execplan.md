# Roads Step-3: Outslope Rutted Point Source with Fill OFE

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package, `outslope_rutted` is modeled as a point-source Roads design with explicit fill dynamics. Contributors will use `road OFE + fill OFE + buffer OFE`, where fill geometry comes from vector attributes and defaults rather than DEM-only inference. Both channel-associated and non-channel low points are supported with explicit branch diagnostics.

## Progress

- [x] (2026-03-27 00:00Z) Authored package/tracker/ExecPlan scaffold for step-3 scope.
- [x] (2026-03-27 23:40Z) Step-1 and step-2 dependencies confirmed complete; package activated as current Roads ExecPlan.
- [ ] Milestone 1: Implement design eligibility and fill-parameter contract.
- [ ] Milestone 2: Integrate run-stage `outslope_rutted` contributor builder (`road -> fill -> buffer`).
- [ ] Milestone 3: Implement channel-associated and non-channel branch behavior with diagnostics.
- [ ] Milestone 4: Add tests and fixture-backed validation.
- [ ] Milestone 5: Complete code-review artifact and resolve medium/high findings.
- [ ] Milestone 6: Complete QA-review artifact and resolve medium/high findings.
- [ ] Milestone 7: Run final gates and update handoff docs.

## Surprises & Discoveries

- Observation: Current phase-1 design eligibility intentionally restricts to inslope designs.
  Evidence: `Roads._is_eligible_design` and prepare-stage design checks.

- Observation: Roads phase-1 run assembly is built around single-OFE segment templates.
  Evidence: segment soil/slope/man assembly paths in `wepppy/nodb/mods/roads/roads.py`.

- Observation: DEM resolution is insufficient to infer real fill geometry reliably at road scale.
  Evidence: user direction captured in Roads specification future-architecture section.

## Decision Log

- Decision: `outslope_rutted` contributor ordering is `road -> fill -> buffer`.
  Rationale: user-required representation of concentrated outslope flow and fill-slope erosion potential.
  Date/Author: 2026-03-27 / User + Codex.

- Decision: Fill geometry is sourced from vector attributes with defaults (`fill_length_m`, `fill_slope_pct`).
  Rationale: avoids unstable DEM-derived fill inference.
  Date/Author: 2026-03-27 / User + Codex.

- Decision: Channel-associated and non-channel branches both remain explicit, with separate counters in run summary.
  Rationale: keeps diagnostics and QA behavior transparent.
  Date/Author: 2026-03-27 / Codex.

## Outcomes & Retrospective

Not complete yet. Fill during milestone closure and final handoff.

## Context and Orientation

This package runs primarily in `/workdir/wepppy`.

Key files:
- `wepppy/nodb/mods/roads/roads.py` (design eligibility, segment run assembly, summaries).
- `wepppy/nodb/mods/roads/monotonic_segments.py` (prepare-stage routing/design metadata).
- `wepppy/nodb/mods/roads/specification.md` (modeling contract updates).
- `tests/nodb/mods/test_roads_controller.py` and `test_roads_monotonic_segments.py`.

Dependencies:
- Step-1 trace API must be available.
- Step-2 non-channel inslope routing should be complete so branch integration patterns are stable.

Working-tree rule:
- `/workdir/wepppy` may contain unrelated dirty files; do not revert or modify unrelated changes.
- Restrict edits to Roads step-3 implementation/test/docs files.

## Plan of Work

Milestone 1 - Eligibility and parameter contracts:

- Extend design eligibility to include `outslope_rutted`.
- Add fill parameter inputs:
  - vector attribute keys (documented canonical names and accepted aliases),
  - defaults in Roads params:
    - `fill_length_default_m = 30.0`
    - `fill_slope_default_pct = 10.0`
- Add validation bounds and explicit error/warning behavior.

Milestone 2 - Contributor assembly (`road -> fill -> buffer`):

- Add run-stage contributor builder for `outslope_rutted` using:
  - road OFE from road geometry/design properties,
  - fill OFE from vector/default fill parameters,
  - buffer OFE from trace path.
- Ensure channel-associated branch still builds valid contributor inputs (with explicit minimum buffer handling if required by WEPP file format constraints).

Milestone 3 - Branch routing and diagnostics:

- Non-channel branch:
  - trace low point to channel,
  - if reached, build full `road -> fill -> buffer` contributor.
- Channel-associated branch:
  - use near-channel branch logic with explicit diagnostics and contributor generation path.
- Persist branch counts and fill-default usage statistics in `last_run_summary` and logs.

Milestone 4 - Tests and fixtures:

- Add regression tests for:
  - design eligibility,
  - fill parameter parsing/defaults,
  - channel vs non-channel branch behavior,
  - generated contributor structure.
- Run fixture-backed Roads validation with mixed low-point scenarios.

Milestones 5 and 6 - Mandatory reviews:

- Milestone 5: independent code review artifact at `artifacts/20260327_code_review.md`; resolve all medium/high findings.
- Milestone 6: independent QA review artifact at `artifacts/20260327_qa_review.md`; resolve all medium/high findings.

Milestone 7 - Final gates and docs synchronization.

## Concrete Steps

Run from `/workdir/wepppy`.

1. Implement Milestones 1-2 and run focused tests:

    wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1
    wctl run-pytest tests/nodb/mods/test_roads_monotonic_segments.py --maxfail=1

2. Implement Milestone 3 and run route/UI checks:

    wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1
    wctl run-npm test -- roads

3. Milestone 4 broader validation:

    wctl run-npm lint
    wctl run-pytest tests --maxfail=1

4. Docs and review artifacts:

    wctl doc-lint --path wepppy/nodb/mods/roads/specification.md
    wctl doc-lint --path docs/work-packages/20260327_roads_point_source_outslope_rutted/package.md
    wctl doc-lint --path docs/work-packages/20260327_roads_point_source_outslope_rutted/tracker.md
    wctl doc-lint --path docs/work-packages/20260327_roads_point_source_outslope_rutted/prompts/active/roads_point_source_outslope_rutted_execplan.md

## Validation and Acceptance

Acceptance requires:

- `outslope_rutted` is eligible and runnable.
- Contributors are generated as `road -> fill -> buffer`.
- Fill parameter sourcing/default behavior is explicit and test-covered.
- Channel-associated and non-channel branches are both functional and diagnostics-rich.
- Required suites pass.
- Code and QA review artifacts exist with no unresolved medium/high findings.

## Idempotence and Recovery

- Re-running Roads prepare/run should deterministically regenerate Roads-scoped artifacts.
- Fill-default usage and missing-attribute paths must be explicit in summaries/logs.
- No silent fallback to inslope semantics for `outslope_rutted`.

## Artifacts and Notes

Required artifacts:
- `docs/work-packages/20260327_roads_point_source_outslope_rutted/artifacts/20260327_code_review.md`
- `docs/work-packages/20260327_roads_point_source_outslope_rutted/artifacts/20260327_qa_review.md`

Recommended evidence:
- default-fill usage table from fixture run,
- branch routing outcome counts (channel-associated vs non-channel).

## Interfaces and Dependencies

End-state requirements:

- Roads params include fill defaults with explicit units.
- Segment run assembly can emit multi-OFE `outslope_rutted` contributor inputs.
- Run summaries report fill/default and branch-routing diagnostics.

Dependency requirement:
- Step-1 trace API and step-2 routing integration pattern must be consumed as contracts; do not duplicate tracing in Python.

---

Revision notes:

- 2026-03-27 00:00Z: Initial step-3 ExecPlan authored with explicit fill OFE contract and mandatory code/QA review gates.
- 2026-03-27 23:40Z: Activated as current Roads ExecPlan after step-1/step-2 completion handoff.
