# Roads Step-4: Outslope Unrutted MOFE Hillslope Replacement

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package, `outslope_unrutted` is modeled as a sheet-flow MOFE replacement path, not additive comparison. For targeted hillslopes, Roads will synthesize replacement contributors with ordering `hill -> road -> fill -> hill`, enforce area conservation, stage replacement pass files, and rerun watershed routing with unchanged topology.

## Progress

- [x] (2026-03-27 00:00Z) Authored package/tracker/ExecPlan scaffold for step-4 scope.
- [x] Milestone 1: Implement decomposition contract for targeted hillslopes (`affected strips` + `unaffected remainder`).
- [ ] Milestone 2: Build MOFE contributors with fixed ordering `hill -> road -> fill -> hill`.
- [ ] Milestone 3: Aggregate contributors into one replacement pass per targeted hillslope.
- [x] Milestone 4: Stage replacement pass files with strict replacement (no additive double counting).
- [ ] Milestone 5: Add area-conservation/topology validation and diagnostics.
- [ ] Milestone 6: Extend regression coverage to full MOFE contributor assembly and area-closure invariants.
- [ ] Milestone 7: Complete code-review artifact and resolve medium/high findings.
- [ ] Milestone 8: Complete QA-review artifact and resolve medium/high findings.
- [ ] Milestone 9: Run final gates and update handoff docs.
- [x] (2026-04-08 00:00Z) Locked step-4 decomposition contract details: physical-length thresholds, 4% geometry parity, raster-burn hillslope segmentation, and multi-road (`N`) contributor support.
- [x] (2026-04-08 08:30Z) Implemented eligibility normalization, vector-overlap inclusion/cap selection, replacement-first pass staging, and summary diagnostics propagation in `roads.py`; added targeted regression tests.
- [x] (2026-04-08 23:40Z) Fixed routed three-OFE slope serialization for outslope-unrutted replacement (point-count token mismatch), added regression coverage, and revalidated end-to-end on `/wc1/runs/cl/clogging-starch-outslope-unrutted-e2e-20260407-232343` with 5 successful replacement segments.

## Surprises & Discoveries

- Observation: Current Roads pass merge is additive and inslope-focused in phase 1.
  Evidence: existing run merge flow in `wepppy/nodb/mods/roads/roads.py`.

- Observation: User requires replacement semantics explicitly, not baseline-vs-road delta behavior.
  Evidence: user direction captured in Roads specification concept section and discussion.

- Observation: Buffer-effect fidelity at lower hillslope reaches is a key user requirement for `outslope_unrutted`.
  Evidence: user rejected simplified delta approach due to poor buffer representation.

- Observation: Cell-size-dependent inclusion/minimum-length thresholds are not acceptable for this package.
  Evidence: user direction requires physical-length thresholds because raster cell sizes can vary materially.

- Observation: `outslope_unrutted` should use its own hillslope decomposition path built from a burned roads raster, not monotonic strip assumptions.
  Evidence: user direction to burn roads into raster and evaluate inclusion hillslope-by-hillslope.

- Observation: Pass aggregation substrate currently only exposes `combine_hillslope_pass_files(..., strategy="phase1")`; there is no phase-4 replacement strategy in `wepppyo3` yet.
  Evidence: `/workdir/wepppyo3/wepp_interchange/src/hill_pass_combine.rs` rejects non-`phase1` strategies.

- Observation: WEPP slope files interpret the leading per-OFE integer as the number of profile coordinate pairs, not an OFE identifier; `outslope_unrutted` three-OFE writer emitted `4` while writing 3 pairs for the buffer OFE, triggering `forrtl: severe (24)` EOF failures.
  Evidence: failed runs in `/wc1/runs/cl/clogging-starch-outslope-unrutted-e2e-20260407-232343/wepp/roads/runs/p90000x.err` and generated `p900001.slp`.

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

- Decision: Inclusion gate for `outslope_unrutted` uses physical overlap thresholds (`L_overlap_h / W_h >= 0.60` and `L_overlap_h >= 10 m`).
  Rationale: keeps eligibility physically meaningful and independent of raster cell size variability.
  Date/Author: 2026-04-08 / User + Codex.

- Decision: Minimum landuse OFE length is physical and fixed (`L_landuse_min = 10 m`).
  Rationale: avoid cell-count-based behavior drift across rasters with different resolution.
  Date/Author: 2026-04-08 / User + Codex.

- Decision: `outslope_unrutted` road geometry parity uses fixed 4% outslope and legacy area-preserving transform behavior.
  Rationale: maintain legacy WEPP:Road compatibility for the road prism representation.
  Date/Author: 2026-04-08 / User + Codex.

- Decision: `outslope_unrutted` decomposition is raster-burn and hillslope-local, with support for `N` road crossings per hillslope via contributor aggregation.
  Rationale: supports non-monotonic crossings and avoids single-profile OFE explosion while preserving replacement semantics.
  Date/Author: 2026-04-08 / User + Codex.

- Decision: `L_overlap_h` for inclusion is measured via vector road-length intersection against hillslope geometry (Option B), not raster-cell-length approximation.
  Rationale: simplest physically meaningful implementation and avoids cell-size dependence.
  Date/Author: 2026-04-08 / User + Codex.

- Decision: Cross-hillslope handling splits `outslope_unrutted` into distinct hillslope-specific segment IDs and applies the `60%` inclusion gate independently per hillslope.
  Rationale: preserves per-hillslope replacement contracts while allowing independent inclusion outcomes across crossed hillslopes.
  Date/Author: 2026-04-08 / User + Codex.

- Decision: Per-hillslope area conservation remains mandatory; aggregate road-area conservation across all crossed hillslopes is not required.
  Rationale: protect watershed hillslope response integrity without overconstraining cross-hillslope road accounting.
  Date/Author: 2026-04-08 / User + Codex.

- Decision: `outslope_unrutted` replacement does not require additional downslope/channel trace logic.
  Rationale: replacement pass routing is handled by existing watershed routing once hillslope pass replacement is staged.
  Date/Author: 2026-04-08 / User + Codex.

- Decision: Phase-4 parameter defaults/constraints follow `/workdir/fswepp2/api/wepproad.py`, with `.geojson` attributes as primary parameter source.
  Rationale: align with legacy WEPP:Road behavior while preserving segment-level explicitness from uploaded data.
  Date/Author: 2026-04-08 / User + Codex.

- Decision: Accept Gate-3 and Gate-6 recommendations: use a phase-4 replacement combiner and alias normalization for `outslope_unrutted` activation.
  Rationale: required for replacement fidelity and safe rollout from current point-source-only eligibility.
  Date/Author: 2026-04-08 / User + Codex.

- Decision: Area conservation uses absolute closure with top-OFE compensation.
  Rationale: user requested absolute handling and explicit compensation at the top landuse OFE.
  Date/Author: 2026-04-08 / User + Codex.

- Decision: No feature-flag retirement workflow is required for outslope-unrutted activation.
  Rationale: this path has not shipped; keep activation simple by unconditional alias normalization.
  Date/Author: 2026-04-08 / User + Codex.

- Decision: Cap qualifying outslope-unrutted road crossings at 3 per hillslope.
  Rationale: explicit complexity/performance bound from user direction.
  Date/Author: 2026-04-08 / User + Codex.

- Decision: Adopt the minimum diagnostics schema for `outslope_unrutted` replacement summaries.
  Rationale: close the final phase-4 decision gate with the smallest stable payload needed for gating, troubleshooting, and deterministic audits.
  Date/Author: 2026-04-08 / User + Codex.

## Outcomes & Retrospective

Partially complete.

Delivered in this pass:
- eligibility normalization for `outslope_unrutted` aliases in Roads run/prepare flow,
- vector-overlap hillslope selection with settled thresholds and cap-at-3 behavior,
- replacement-first pass staging precedence and additive suppression for replacement-targeted hillslopes,
- minimum diagnostics schema propagation into run summaries,
- focused regression tests covering alias eligibility, selection/cap behavior, and replacement staging,
- routed three-OFE slope writer correction to maintain per-OFE point-count consistency for WEPP parsing,
- fixture-backed end-to-end rerun on `/wc1/runs/cl/clogging-starch-outslope-unrutted-e2e-20260407-232343` proving 5/5 selected outslope-unrutted replacement segments executed successfully.

Still required for final closure:
- full MOFE contributor assembly (`hill -> road -> fill -> hill`) with area-closure compensation at top OFE,
- replacement aggregation semantics beyond phase-1 combiner assumptions,
- remaining broad validation/review milestones (6-9).

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
- Inclusion gating uses physical thresholds (`L_overlap_h / W_h >= 0.60` and `L_overlap_h >= 10 m`).
- Multiple road crossings per hillslope (`N`) are supported via contributor aggregation with no double counting.
- Inclusion overlap metric uses vector road-length intersection against hillslope geometry (not raster-cell-length approximation).
- Cross-hillslope crossings are segmented into distinct hillslope-specific IDs with independent inclusion evaluation.
- `outslope_unrutted` replacement path runs without additional phase-4 trace-to-channel requirements.

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

Revision note (2026-04-08 00:00Z): Added physical-length inclusion/minimum thresholds, fixed 4% geometry parity, raster-burn decomposition contract, and multi-road (`N`) support decisions.
Revision note (2026-04-08 00:30Z): Adopted gate selections: vector-overlap metric (Gate 1), independent hillslope segmentation (Gate 2), no extra tracing (Gate 4), fswepp2+geojson parameter contract (Gate 5), and accepted Gate 3/6 recommendations.
Revision note (2026-04-08 00:45Z): Finalized area-closure/top-OFE rule, removed feature-flag retirement gate, and set crossing cap to 3 per hillslope; diagnostics schema remains the only open decision gate.
Revision note (2026-04-08 01:00Z): Adopted minimum diagnostics schema contract and closed remaining phase-4 decision gates for outslope-unrutted replacement docs.

Revision note (2026-04-08 08:30Z): Implemented initial step-4 code path (alias normalization, vector-overlap gating/cap, replacement staging precedence, and targeted tests); full MOFE contributor assembly remains open.
