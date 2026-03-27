# Roads Point-Source Outslope Rutted with Fill OFE

**Status**: Open (2026-03-27)

## Overview
This package implements step 3 of Roads modeling: `outslope_rutted` as a point-source design with explicit fill slope dynamics. It covers both channel-associated and non-channel low points and models routed contributors as `road OFE + fill OFE + flowpath buffer OFE`.

## Objectives
- Enable `outslope_rutted` design eligibility in prepare/run workflows.
- Model point-source contributors for `outslope_rutted` as `road -> fill -> buffer`.
- Support both channel-associated and non-channel low points through the step-1 trace framework.
- Introduce fill-geometry contract fields with defaults because DEM resolution cannot reliably capture fill geometry.
- Preserve existing inslope behavior and summaries.
- Complete independent code review and QA review with medium/high finding closure.

## Scope
This package implements only `outslope_rutted` point-source behavior.

### Included
- Prepare-stage design eligibility updates for `outslope_rutted`.
- Run-stage contributor assembly with explicit fill OFE.
- Fill parameter sourcing from roads-vector properties plus defaults.
- Channel-associated and non-channel routing logic for `outslope_rutted`.
- Regression tests and fixture validation updates.
- Code and QA review artifacts.

### Explicitly Out of Scope
- `outslope_unrutted` hillslope replacement behavior (step 4 package).
- Inslope behavior redesign.
- Large UI redesign; only minimal controls/diagnostics needed for new fill parameters.

## Stakeholders
- **Primary**: Roads model maintainers and users requiring rutted outslope representation.
- **Reviewers**: Roads NoDb maintainers, WEPP process maintainers, QA maintainers.
- **Informed**: WEPPcloud route/report maintainers and operations.

## Success Criteria
- [ ] `outslope_rutted` segments are eligible in prepare and run flows.
- [ ] Run path builds `road -> fill -> buffer` contributors for `outslope_rutted`.
- [ ] Fill OFE parameters are sourced from segment attributes with documented defaults (`fill_length_m` and `fill_slope_pct`).
- [ ] Channel-associated and non-channel cases are both handled with explicit diagnostics.
- [ ] Inslope and other existing designs remain regression-stable.
- [ ] `last_run_summary` includes outslope-rutted routed counts and fill-default usage counts.
- [ ] Targeted and full regression suites pass.
- [ ] Code review artifact has no unresolved medium/high findings.
- [ ] QA review artifact has no unresolved medium/high findings.

## Dependencies

### Prerequisites
- Step-1 trace substrate package:
  - `docs/work-packages/20260327_roads_peridot_trace_core/`
- Step-2 inslope non-channel package:
  - `docs/work-packages/20260327_roads_point_source_inslope_non_channel/`
- Roads modeling contract baseline:
  - `wepppy/nodb/mods/roads/specification.md`

### Blocks
- Step-4 `outslope_unrutted` replacement package needs settled `outslope_rutted` fill parameter contracts and routing diagnostics.

## Related Packages
- **Depends on**: [20260327_roads_peridot_trace_core](../20260327_roads_peridot_trace_core/package.md)
- **Depends on**: [20260327_roads_point_source_inslope_non_channel](../20260327_roads_point_source_inslope_non_channel/package.md)
- **Follow-up**: [20260327_roads_outslope_unrutted_mofe_replacement](../20260327_roads_outslope_unrutted_mofe_replacement/package.md)

## Timeline Estimate
- **Expected duration**: 3-6 focused sessions.
- **Complexity**: High.
- **Risk level**: High.

## References
- `wepppy/nodb/mods/roads/roads.py` - run assembly and segment input resolution.
- `wepppy/nodb/mods/roads/monotonic_segments.py` - design eligibility and low-point classification.
- `wepppy/nodb/mods/roads/specification.md` - point-source semantics and fill assumptions.
- Legacy WEPP:Road behavior evidence (for geometry intent) summarized in Roads spec.

## Deliverables
- Package scaffold (`package.md`, `tracker.md`, active ExecPlan).
- Active ExecPlan: `prompts/active/roads_point_source_outslope_rutted_execplan.md`.
- Implemented `outslope_rutted` point-source modeling path with fill OFE.
- Updated Roads specification for fill parameter contract and defaults.
- Review artifacts:
  - `artifacts/20260327_code_review.md`
  - `artifacts/20260327_qa_review.md`

## Follow-up Work
- Evaluate sensitivity of fill default parameters against domain-calibration runs.
- Add optional vector schema helpers for fill attribute discovery/mapping if user input heterogeneity is high.
