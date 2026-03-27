# Roads Point-Source Flowpath Trace Core (Peridot + PyO3)

**Status**: Open (2026-03-27)

## Overview
Roads phase 1 can only inject point-source road contributors when the low point is on or adjacent to a channel pixel. The next Roads phase needs deterministic routing from non-channel low points to a channel path, but that routing must stay in Rust (`peridot`/`wepppyo3`) rather than adding a pure-Python hydrology path. This package delivers step 1 only: implement the shared Rust downslope tracer core and expose it through `wepppyo3` for Roads pipelines.

## Objectives
- Implement a reusable Rust `trace_downslope_flowpath` core in `peridot` that traces one seed point downslope to channel/termination.
- Define and stabilize a machine-usable result contract (distance/elevation profile, geometry, termination reason, channel reach flag).
- Expose the same core through a `wepppyo3` `pyo3` module with no algorithm fork.
- Add a CLI interface in `peridot` for ops/debug parity and batch seed debugging.
- Add regression tests in `peridot` and `wepppyo3`, plus a thin WEPPpy-side smoke path for future Roads integration.
- Complete independent code review and QA review with medium/high finding closure before package close.

## Scope
This package implements the point-source routing substrate only.

### Included
- New `peridot` library module(s) for point-seed downslope tracing.
- New `peridot` CLI entrypoint for trace runs and JSON output.
- New `wepppyo3` binding(s) that call the same `peridot` core.
- Result-contract documentation updates in Roads specification and package artifacts.
- Focused regression tests across Rust core and `pyo3` wrapper.
- Review artifacts: code review + QA review.

### Explicitly Out of Scope
- Roads run-path behavior changes for `inslope_bd`, `inslope_rd`, `outslope_rutted`, or `outslope_unrutted`.
- MOFE assembly changes for Roads contributors.
- New UI controls or route contracts in WEPPcloud Roads pages.
- Pure-Python reimplementation of trace logic.

## Stakeholders
- **Primary**: Roads/NoDb maintainers implementing non-channel low-point routing.
- **Reviewers**: Peridot maintainers, `wepppyo3` maintainers, Roads NoDb maintainers.
- **Informed**: WEPPcloud operations and QA maintainers.

## Success Criteria
- [ ] `peridot` exposes a reusable Rust trace function for one seed point with explicit termination semantics.
- [ ] Trace contract includes channel reach status, termination reason, per-step geometry, and distance/elevation profile.
- [ ] `peridot` CLI can run the tracer and emit deterministic JSON output for a seed point.
- [ ] `wepppyo3` exposes a Python-callable binding that uses `peridot` core (no duplicated algorithm).
- [ ] Regression tests cover channel hit, invalid flow direction, loop prevention, raster-edge termination, and deterministic profiles.
- [ ] Roads-spec future architecture section is synchronized with implemented contract details.
- [ ] Code review artifact completed with no unresolved medium/high findings.
- [ ] QA review artifact completed with no unresolved medium/high findings.

## Dependencies

### Prerequisites
- Roads architecture concept updates in `wepppy/nodb/mods/roads/specification.md`.
- Existing `peridot` watershed rasters and flowpath primitives.
- Existing `wepppyo3` workspace and release packaging flow.

### Blocks
- Step 2 package work: non-channel point-source implementation for `inslope_bd`/`inslope_rd`.
- Step 3 package work: `outslope_rutted` point-source with fill OFE.
- Step 4 package work: `outslope_unrutted` MOFE hillslope replacement.

## Related Packages
- **Depends on**: [20260323_roads_nodb_inslope_e2e](../20260323_roads_nodb_inslope_e2e/package.md)
- **Related**: [20260323_roads_wepp_reports_regen](../20260323_roads_wepp_reports_regen/package.md)
- **Follow-up**: Roads point-source integration package(s) for steps 2-4.

## Timeline Estimate
- **Expected duration**: 3-6 focused sessions.
- **Complexity**: High.
- **Risk level**: Medium-High.

## References
- `wepppy/nodb/mods/roads/specification.md` - Roads source-of-truth and future architecture draft.
- `/workdir/peridot/src/watershed_abstraction/watershed_abstraction.rs` - existing flowpath walk primitives.
- `/workdir/peridot/src/watershed_abstraction/flowpath.rs` - flowpath data model/profile handling.
- `/workdir/peridot/src/bin/abstract_watershed.rs` - CLI pattern for peridot tools.
- `/workdir/wepppyo3/Cargo.toml` - workspace members and crate layout.
- `/workdir/wepppyo3/wepp_interchange/src/lib.rs` - current `pyo3` export conventions.
- `wepppy/topo/peridot/peridot_runner.py` - current binary-bridge pattern in WEPPpy.
- `wepppy/nodb/mods/roads/monotonic_segments.py` - current low-point channel mapping boundary.

## Deliverables
- Package scaffold (`package.md`, `tracker.md`, active ExecPlan).
- Active ExecPlan: `prompts/active/roads_peridot_trace_core_execplan.md`.
- Implemented `peridot` core + CLI trace capability.
- Implemented `wepppyo3` binding over the shared core.
- Updated Roads specification contract text for implemented trace fields.
- Review artifacts:
  - `artifacts/20260327_code_review.md`
  - `artifacts/20260327_qa_review.md`

## Follow-up Work
- Integrate trace results into Roads step-2 non-channel point-source MOFE assembly.
- Add vectorized/batch seed tracing API if one-point-at-a-time throughput is insufficient.
- Expand trace contract to include flowpath-hillslope overlap segmentation if needed by step 3/4 modeling.
