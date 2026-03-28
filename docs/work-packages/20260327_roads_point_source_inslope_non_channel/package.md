# Roads Point-Source Inslope Non-Channel Routing

**Status**: Implemented + post-handoff hotfix validated (2026-03-27)

## Overview
Roads phase 1 supports point-source injections only when segment low points are channel-associated (on or adjacent to channel pixels). This package implements non-channel routing for `inslope_bd` and `inslope_rd` by tracing low-point flowpaths to channel and modeling contributors as `road OFE + flowpath buffer OFE` before pass-file merge.

Post-handoff hotfix note: routed two-OFE management generation now remaps yearly FOREST `itype` from `3` to `2` after fill scenario removal to keep WEPP management cardinality parse-safe.

## Objectives
- Enable non-channel low-point eligibility for `inslope_bd` and `inslope_rd` when low point lies on a hillslope pixel (`subwta` suffix `1|2|3`).
- Route eligible low points to channel via the Rust trace contract delivered by step 1 package.
- Build point-source MOFE contributor geometry for inslope non-channel cases as `road -> buffer`.
- Merge routed point-source contributors into receiving hillslope pass files using existing Roads pass-combine flow.
- Preserve current channel-associated inslope behavior and avoid regressions.
- Complete independent code review and QA review with medium/high finding closure.

## Scope
This package implements inslope non-channel point-source behavior only.

### Included
- Prepare-stage low-point classification updates for routable non-channel inslope points.
- Run-stage integration of per-point trace results for `inslope_bd` and `inslope_rd`.
- MOFE construction for inslope routed contributors (`road OFE + buffer OFE`).
- Summary/reporting updates for routed non-channel segments.
- Regression tests and fixture validations.
- Code and QA review artifacts.

### Explicitly Out of Scope
- `outslope_rutted` point-source behavior (step 3 package).
- `outslope_unrutted` hillslope replacement behavior (step 4 package).
- Fill OFE modeling for inslope (inslope assumes culvert bypass of fill dynamics).
- New UI redesign beyond exposing useful status diagnostics.

## Stakeholders
- **Primary**: Roads NoDb maintainers and Roads model users needing non-channel inslope routing.
- **Reviewers**: Roads NoDb maintainers, `wepppyo3` integration maintainers, QA maintainers.
- **Informed**: WEPPcloud route/report maintainers and operations.

## Success Criteria
- [x] Inslope non-channel low points are identified as routable when low-point `subwta` ends in `1|2|3`.
- [x] Segment run path traces routable low points to channel through step-1 Rust API.
- [x] Routed inslope contributors use MOFE ordering `road -> buffer` and produce WEPP pass files.
- [x] Routed contributor passes merge into receiving hillslope pass outputs without double-run failures.
- [x] Existing channel-associated inslope behavior remains unchanged.
- [x] `last_prepare_summary` and `last_run_summary` include explicit routed/non-routed diagnostics.
- [x] Routed two-OFE management files remain WEPP-parseable (`itype` cardinality aligned to two-scenario output).
- [ ] Targeted and full regression suites pass. (targeted pass; full-suite has unrelated baseline failure outside Roads scope)
- [x] Code review artifact has no unresolved medium/high findings.
- [x] QA review artifact has no unresolved medium/high findings.

## Dependencies

### Prerequisites
- Step-1 trace substrate package completed:
  - `docs/work-packages/20260327_roads_peridot_trace_core/`
- Roads source contracts:
  - `wepppy/nodb/mods/roads/specification.md`

### Blocks
- Step-3 `outslope_rutted` package depends on this non-channel routing path pattern.

## Related Packages
- **Depends on**: [20260327_roads_peridot_trace_core](../20260327_roads_peridot_trace_core/package.md)
- **Related**: [20260323_roads_nodb_inslope_e2e](../20260323_roads_nodb_inslope_e2e/package.md)
- **Follow-up**: [20260327_roads_point_source_outslope_rutted](../20260327_roads_point_source_outslope_rutted/package.md)

## Timeline Estimate
- **Expected duration**: 3-5 focused sessions.
- **Complexity**: High.
- **Risk level**: Medium-High.

## References
- `wepppy/nodb/mods/roads/monotonic_segments.py` - low-point decisions and channel/hillslope attribution.
- `wepppy/nodb/mods/roads/roads.py` - prepare/run orchestration and pass merge.
- `wepppy/nodb/mods/roads/specification.md` - sheet-flow vs point-source model contract.
- `wepppy/wepp/hillslope.py` and Roads run assembly helpers - OFE slope/soil/man inputs.
- Step-1 trace API docs/artifacts in `20260327_roads_peridot_trace_core`.

## Deliverables
- Package scaffold (`package.md`, `tracker.md`, active ExecPlan).
- Active ExecPlan: `prompts/active/roads_point_source_inslope_non_channel_execplan.md`.
- Implemented Roads non-channel inslope routing and MOFE contributor path.
- Updated Roads specification for inslope non-channel routing details and constraints.
- Review artifacts:
  - `artifacts/20260327_code_review.md`
  - `artifacts/20260327_qa_review.md`

## Follow-up Work
- Extend the same routing framework to `outslope_rutted` with explicit fill OFE.
- Evaluate optional batch tracing for high-segment-count runs after correctness is proven.
