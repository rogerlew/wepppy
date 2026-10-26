# Repair Roads WBT flow directions

## Purpose

A user running Roads on WBT project clogging-starch must get modeled output for
five connected segments currently skipped by a direction-code mismatch. Whitebox
D8 stores eight directions as powers of two; Peridot's tracer uses TOPAZ keypad
codes. Correct the representation boundary without changing the tracing science.
This plan is an end-to-end repair, not a surrogate or disconnected scaffold.

## Progress

- [x] Diagnose source and native boundary; confirm five converted traces succeed.
- [ ] Commit accepted contract checkpoint after two independent reviews.
- [ ] Add native and caller regressions; implement and rebuild paired artifact.
- [ ] Validate all directions, legacy/error behavior and isolated full project.
- [ ] Run required checks, independent correctness review and close package.

## Context

WEPPpy /home/workdir/wepppy starts at 69ddcafe9. Roads already requires WBT;
wepppy/nodb/mods/roads/roads.py calls wepppyo3.roads_flowpath without conversion.
/workdir/wepppyo3 starts at 47e51b8; roads_flowpath/src/lib.rs loads a Raster<u8>
and calls /workdir/peridot/src/roads_trace/trace_downslope.rs. Peridot starts at
3cef07b and has an existing remap_whitebox_d8_to_topaz_in_place helper. Preserve
unrelated dirty WEPPpy query-catalog docs and native interchange/calendar files.
Do not switch branches. Read each repository's instructions before edits.

## Milestones

First commit this package, docs/schemas/roads-flow-direction-contract.md and two
independent review dispositions. User explicitly requested scaffold and execution
of this bounded fix after confirming Roads is WBT-only. Record compatibility:
existing native callers default to TOPAZ; Roads explicitly sets keyword wbt=True.

Next add an optional keyword-only wbt=False to the existing PyO3 function and
convert its loaded flow raster in Rust when true. Reuse Peridot's conversion,
not Python raster processing. Test all eight neighbors using actual GeoTIFFs,
existing TOPAZ behavior, invalid directions, loops, edge/step limit and bad seeds
or shapes. Add the keyword to Roads and assert its propagation in controller
regressions. Document the API and implementation rationale.

Build only roads_flowpath_rust with PYO3_PYTHON=/usr/bin/python3.12 and cargo
build --release -p roads_flowpath_rust. Record toolchain, source and shared-object
hashes. Stage the new .so beside release/linux/py312/wepppyo3/roads_flowpath/
roads_flowpath_rust.so and atomically rename it; never overwrite a mapped file.
Fresh Python processes must import that exact artifact. No production services
are restarted or deployed.

Copy the current wepp1 project /geodata/wc1/runs/cl/clogging-starch to an isolated
/wc1/ablation/20261026_roads_wbt_flow_direction tree. Before NoDb hydration rebase
serialized absolute paths to the isolated root; hashing/loading must never write
original data. Use actual controller prepare/run and existing report readers.
Retain copied WBT rasters and input hashes, traces, prepared slope/management,
PASS and report readback. Expect 35 completed and four NoData skips; verify five
recovered segment IDs reach channels 204/154, fresh segment report rows and full
calendar/finite water/accounting outputs. Exact baseline input/output hashes must
remain unchanged. Source-site snapshot hashes are read-only evidence.

Use wctl run-pytest for WEPPpy regression and broad tests; use native cargo and
Python tests for the new extension. Run wctl run-pytest tests --maxfail=1, retain
failures and resolve within scope; segmented coverage is acceptable if every
collected node is accounted and intermediate failures remain visible. No test
exclusions or numeric tolerance widening. Update docs and source provenance.
Independent correctness review must close medium/high findings. Move this plan
to prompts/completed, close package/tracker and update PROJECT_TRACKER.md.

## Validation and recovery

Unit tests alone do not prove the original workflow. Require unmocked production
raster consumption and a fresh whole Roads run with generated report readback.
Compare old and new direct trace outputs in isolated copies; native API default
must remain compatible. Rollback is reverting the paired caller/native artifact,
then regenerating Roads outputs; never mix a new caller with an old extension.
Original production run and rollout remain outside this package.

## Surprises & Discoveries

2026-10-26 UTC: all three invalid starting directions are valid WBT code 16.
Overlapping valid codes can produce loops rather than explicit errors. Four
unrelated low points are subcatchment NoData. Existing native tests use TOPAZ
fixtures only, so they could not expose the production WBT mismatch.

## Decision Log

2026-10-26 UTC: retain native TOPAZ default and add explicit WBT normalization at
the PyO3 boundary; Roads always opts in. Reuse the owned Peridot conversion.
No backend autodetection or UI choice; no new native-core routing algorithm.

## Outcomes & Retrospective

Pending implementation and evidence. Final claim must distinguish validated local
paired release from production deployment and original-project recovery.

Publication dependency: tests/roads fingerprints roads.py. Preserve the historical
516-profile dataset and execution source hashes. Mark full-project evidence stale
with a visible report notice and exact reviewed source-delta receipt; regression
must reject any unacknowledged drift. This uses the existing validation-suite
contract's explicit stale-marking allowance, not a claim of rerun results.
