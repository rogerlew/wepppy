# Roads Outslope Unrutted MOFE Hillslope Replacement

**Status**: Open (2026-03-27)

## Overview
This package implements step 4: `outslope_unrutted` as a sheet-flow abstraction using MOFE hillslope replacement, not additive delta injection. Targeted hillslopes are replaced by roads-aware synthetic contributors with explicit ordering `hill -> road -> fill -> hill` and strict no-double-counting invariants.

## Objectives
- Implement `outslope_unrutted` as a replacement model for affected hillslopes.
- Build roads-aware MOFE contributors with explicit `hill -> road -> fill -> hill` ordering.
- Preserve area conservation between affected-strip contributors and unaffected remainder.
- Stage replacement pass files for impacted hillslopes and keep untouched hillslopes baseline.
- Maintain watershed topology while using roads-aware replacement pass files.
- Complete independent code review and QA review with medium/high finding closure.

## Scope
This package implements only `outslope_unrutted` hillslope replacement semantics.

### Included
- Prepare/run support for `outslope_unrutted` replacement workflow.
- Affected-strip and unaffected-remainder decomposition logic per receiving hillslope.
- Contributor assembly and pass aggregation to produce one synthetic replacement pass per targeted hillslope.
- Replacement staging rules (replace, do not add) for targeted hillslopes.
- Regression tests for area conservation and replacement semantics.
- Code and QA review artifacts.

### Explicitly Out of Scope
- New comparative analytics/visualization package work.
- Broader redesign of all Roads designs; package is specific to `outslope_unrutted`.
- Major topology redesign of watershed/channel network representation.

## Stakeholders
- **Primary**: Roads model maintainers and users requiring high-fidelity `outslope_unrutted` behavior.
- **Reviewers**: Roads NoDb maintainers, WEPP process/report maintainers, QA maintainers.
- **Informed**: Operations and report-route maintainers.

## Success Criteria
- [ ] `outslope_unrutted` runs with replacement semantics (no additive double counting on targeted hillslopes).
- [ ] Contributor decomposition enforces ordering `hill -> road -> fill -> hill`.
- [ ] Area conservation checks pass for each targeted hillslope.
- [ ] Untouched hillslopes remain baseline pass files.
- [ ] Watershed rerun succeeds with mixed replacement + baseline pass staging.
- [ ] Summaries include replacement-hillslope inventory and area-conservation diagnostics.
- [ ] Targeted and full validation suites pass.
- [ ] Code review artifact has no unresolved medium/high findings.
- [ ] QA review artifact has no unresolved medium/high findings.

## Dependencies

### Prerequisites
- Step-1 trace substrate package:
  - `docs/work-packages/20260327_roads_peridot_trace_core/`
- Step-2 inslope non-channel package:
  - `docs/work-packages/20260327_roads_point_source_inslope_non_channel/`
- Step-3 outslope-rutted package:
  - `docs/work-packages/20260327_roads_point_source_outslope_rutted/`
- Roads concept contract in:
  - `wepppy/nodb/mods/roads/specification.md`

### Blocks
- Future comparative roads-vs-baseline analytics package depends on replacement-summary diagnostics from this package.

## Related Packages
- **Depends on**: [20260327_roads_peridot_trace_core](../20260327_roads_peridot_trace_core/package.md)
- **Depends on**: [20260327_roads_point_source_inslope_non_channel](../20260327_roads_point_source_inslope_non_channel/package.md)
- **Depends on**: [20260327_roads_point_source_outslope_rutted](../20260327_roads_point_source_outslope_rutted/package.md)

## Timeline Estimate
- **Expected duration**: 5-9 focused sessions.
- **Complexity**: Very High.
- **Risk level**: High.

## References
- `wepppy/nodb/mods/roads/specification.md` - replacement semantics and fidelity invariants.
- `wepppy/nodb/mods/roads/roads.py` - pass aggregation/staging and watershed rerun orchestration.
- `wepppy/wepp/hillslope.py` and pass-combine interfaces in `wepppyo3` - contributor pass assembly baseline.

## Deliverables
- Package scaffold (`package.md`, `tracker.md`, active ExecPlan).
- Active ExecPlan: `prompts/active/roads_outslope_unrutted_mofe_replacement_execplan.md`.
- Implemented `outslope_unrutted` replacement workflow with area-conservation checks.
- Updated Roads specification with finalized replacement implementation details.
- Review artifacts:
  - `artifacts/20260327_code_review.md`
  - `artifacts/20260327_qa_review.md`

## Follow-up Work
- Performance tuning for large watersheds with many replacement contributors.
- Optional UI/report enhancements showing replacement decomposition diagnostics to users.
