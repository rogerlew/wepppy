# AgFields Flowpath-to-Channel Connectivity Inventory

**Status**: Closed (2026-07-13)
**Timezone**: UTC

## Overview

This package adds a reusable Peridot command-line investigation for counting
AgFields sub-fields that have one or more generated per-cell flowpaths whose first
cell outside the sub-field is a channel. The first application is
`/wc1/runs/sa/sacral-self-discipline`. Discovery reduced the final contract to
three required rasters, each supplied explicitly, so the same inventory can be run
on other projects.

This is a non-blocking companion to Concept 2 watershed integration. It provides
simple topology evidence that may help Mariana's later scientific evaluation; it
does not gate Concept 2 engineering delivery or change how WEPP routes water or
sediment.

## Objectives

- Add a Peridot CLI that accepts the required sub-field ID, SUBWTA, D8 flow, and
  optional channel-mask rasters without assuming a WEPPcloud run-directory layout.
- Define a small, deterministic JSON summary centered on the count of sub-fields
  with one or more channel-draining flowpaths.
- Cover grid validation, grouping, and direct-channel/non-channel boundary cases
  with focused Rust tests.
- Run the command against `sacral-self-discipline` and record the exact invocation
  and observed counts for reproducibility.

## Scope

### Included

- A Peridot binary with read-only raster inputs and reusable library logic.
- Explicit local input paths and JSON written to standard output or an optional
  caller-selected output path.
- Simple totals for retained sub-fields and direct channel outlet cells.
- Focused debug-build tests and one generated-data smoke run.
- Peridot CLI documentation and this WEPPpy work-package record.

### Explicitly Out of Scope

- Changing AgFields, WEPP, RQ, API, UI, or Concept 2 execution behavior.
- Estimating delivery ratios, buffer trapping, travel time, contributing area, or
  sediment/water mass.
- Treating a direct path-boundary result as scientific validation of buffer effects.
- Writing derived artifacts into the designated dev-project directory.
- Concept 1 planning or implementation.

## Stakeholders

- **Primary**: WEPPpy and Peridot maintainers.
- **Decision owner**: Roger Lew.
- **Scientific evaluator**: Mariana Dobre.
- **Reviewers**: AgFields/Peridot maintainer.
- **Security Reviewer**: Not required; the tool is a local, read-only CLI.
- **Informed**: Concept 2 implementers and scientific reviewers.

## Success Criteria

- [x] The Peridot binary requires caller-specified resources and has no hidden
  dependency on `/wc1/runs` or the WEPPcloud project layout.
- [x] Output is deterministic JSON containing the number of distinct sub-fields
  with at least one channel-draining flowpath and the minimal supporting totals.
- [x] Dimension, affine-geotransform, and projection mismatches fail explicitly
  instead of allowing elementwise comparison of unaligned rasters.
- [x] Focused Rust tests and formatting/check gates pass without a release build.
- [x] The exact `sacral-self-discipline` command and result are recorded in the
  package tracker.
- [x] Existing files in the dev project and preexisting Peridot release artifacts
  remain unchanged.

## Parameterization ADR Gate

- **Parameterization change present**: `no`
- **ADR required**: `no`
- **ADR link(s)**: N/A
- **Decision provenance captured**: `yes`

The command inventories existing D8/channel topology and does not alter model
formulas, defaults, thresholds, units, or fallback behavior.

## Dependencies

### Prerequisites

- Peridot's existing raster readers and D8 channel-trace semantics.
- AgFields sub-field and flowpath metadata produced by
  `sub_fields_abstraction`.
- The designated dev project's aligned watershed rasters.

### Blocks

None. The result is informative evidence for scientific evaluation and does not
block Concept 2 implementation.

## Related Packages

- **Related, non-blocking**: [AgFields Concept 2 Watershed Integration](../20260713_ag_fields_concept2_watershed_integration/package.md)
- **Builds on**: [AgFields Backend Readiness](../20260709_ag_fields_backend_readiness/package.md)

## Timeline Estimate

- **Expected duration**: One focused implementation and validation session.
- **Complexity**: Low to medium.
- **Risk level**: Low; the principal risk is mislabeling the path-boundary
  metric as full routing fidelity.

## Security Impact and Review Gate

- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: Adds a local read-only CLI. It introduces no route, queue,
  authentication, secret, subprocess, deployment, or network surface.
- **Security review artifact**: N/A

## References

- `/workdir/peridot/src/roads_trace/trace_downslope.rs` - existing D8 tracing and
  channel-cell semantics.
- `/workdir/peridot/src/wbt/wbt_sub_fields_abstraction.rs` - producer of AgFields
  sub-field and flowpath resources.
- `/wc1/runs/sa/sacral-self-discipline/ag_fields/sub_fields/` - designated input
  fixture; treated as immutable.
- `docs/work-packages/20260713_ag_fields_flowpath_channel_connectivity/prompts/completed/ag_fields_flowpath_channel_connectivity_execplan.md`
  - completed implementation and validation plan.

## Deliverables

- Peridot commit `8343b8f` adds the documented
  `subfield_channel_connectivity` library module and CLI.
- Six focused connectivity/grid-validation tests plus the full Peridot test suite
  pass in debug mode.
- The dev-project inventory found 3,269 of 6,626 retained sub-fields with direct
  channel drainage and 12,365 direct channel outlet cells.
- The default SUBWTA channel rule and an explicit `netful.tif` mask produced the
  same metrics.

## Follow-up Work

Any richer connectivity, buffer, delivery, or mass-routing metric requires a
separate science-led scope after Mariana reviews the simple inventory.

## Closure Notes

**Closed**: 2026-07-13

**Summary**: The resource-oriented Peridot CLI is implemented, tested, documented,
run against the designated project, and pushed. Raster analysis replaced the
initial Parquet-centroid trace sketch because `sub_fields_abstraction` already
starts one path at every retained cell and stops immediately after the first cell
outside its sub-field. Testing that outside cell directly is both simpler and
faithful to the generated sub-field path boundary.

**Lessons Learned**: The retained sub-field raster is the authoritative source for
this existence count. Parquet remains useful as a cross-check of the 6,626
sub-field universe and 126,416 generated flowpath rows, but is not a required CLI
resource.

**Archive Status**: The completed ExecPlan and full validation transcript remain in
this package. Scientific interpretation is intentionally deferred to Mariana.
