# Correct Peridot centroid projection and vendor releases

## Purpose / Big Picture

Make exported geographic centroids describe the actual raster pixel centroid so MOFE bedrock maps sample the intended location. This is a living ExecPlan governed by docs/prompt_templates/codex_exec_plans.md.

## Progress

- [x] (2026-09-09 UTC) Reproduced the approximation for all 505 seductive-sabra hillslopes and inspected shared exporters.
- [x] (2026-09-09 UTC) Contract checkpoint and ADR committed: Peridot 98e8a43, WEPPpy dd15f6191.
- [x] (2026-09-09 UTC) Implementation and 51 Rust tests passed; Peridot 3cef07b pushed to main.
- [x] (2026-09-09 UTC) Three binaries built/vendored; container CLI and eight-hillslope soil propagation passed.
- [x] (2026-09-09 23:00 UTC) Review and documentation complete; Peridot pushed, WEPPpy publication accompanies closeout.

## Surprises & Discoveries

PROJ is already linked. Metadata uses a four-number approximation instead. Export tasks execute in parallel, so construct and reuse a transformer inside each writer. Repeated unchanged TOPAZ baseline runs also change geometry, so exact whole-run TOPAZ parity is not a valid gate. WBT/sub-field non-coordinate and slope parity passes. The old vendored sub-field binary predates the source CSV schema; the release manifest identifies current source. Both repositories have preexisting changes; stage only package-owned files/hunks. Peridot has preexisting dirty tracked binaries; preserve copies before authorized rebuild.

## Decision Log

2026-09-09 UTC, user/Codex: replace the approximation with pointwise PROJ conversion using the raster affine transform. Preserve existing integer pixel/corner convention and all schemas. Reusing PROJ avoids a dependency evaluation or native-stack change. Raster sampler rounding and live data repair remain separate scope.

## Context and Orientation

Peridot is /home/workdir/peridot (main). WEPPpy is /home/workdir/wepppy (master). Peridot src/rasters/raster.rs builds wgs_transform from two corners. src/watershed_abstraction/flowpath_collection.rs uses it in eight metadata writers. TOPAZ and WBT abstraction plus sub-fields call those writers. WEPPpy vendors binaries in wepppy/topo/peridot/bin. Source run inputs are /wc1/runs/se/seductive-sabra/dem/topaz; never run abstraction against the original because it deletes watershed outputs.

## Milestones and Plan of Work

First amend Peridot docs/contracts/watershed-output-contract.md and add a WEPPpy ADR defining pointwise projection, error behavior, and migration expectations; commit this ancestor checkpoint before code. Record the compatibility plan in package.md.

Second provide a raster-derived reusable PROJ transformer and pass raster context to metadata writers. Initialize inside each writer, propagate initialization/conversion failures as io errors, and reject nonfinite coordinates. Update all callers, including CSV sub-fields. Add known-coordinate and export regression tests including noncentral UTM locations, southern hemisphere, rotation, and missing/invalid CRS.

Third run cargo tests and build the three changed CLI binaries with cargo build --release. Preserve preexisting binaries in /tmp before rebuilding. Copy release outputs into WEPPpy using the canonical Peridot operations runbook. Execute rebuilt/vendored TOPAZ on isolated copied input rasters and validate coordinates against pyproj; exercise WBT/sub-fields via available fixtures. Demonstrate sampled values reach isolated prepared soil files and preserve unrelated artifacts.

Finally run WEPPpy targeted Peridot tests and wctl run-pytest tests --maxfail=1, doc lint, and a correctness review. Record all failures and limitations accurately. Update tracker and package, archive this plan to prompts/completed, commit only owned changes, and push Peridot main and WEPPpy master without force.

## Validation and Acceptance

Use cargo test in Peridot; expect regression cases to pass and demonstrate the old approximation fails the known-coordinate case. Use rebuilt generated Parquet/CSV coordinates with pyproj tolerance 1e-8 degrees. Preserve non-coordinate fields and slope outputs in deterministic WBT/sub-field comparisons. For TOPAZ, require exact projected coordinate agreement and unchanged schemas/pixel IDs; record baseline-repeat geometry nondeterminism rather than claiming byte parity. Confirm vendored SHA256 matches release source. Run wctl run-pytest tests/topo --maxfail=1 and broad sanity; record environmental blockers distinctly. Correctness artifact must close medium/high findings.

## Idempotence and Recovery

Use only temporary copied runs for generation; never edit seductive-sabra. Release build is repeatable; restore backed-up binaries only if abandoning the change. Do not reset unrelated repository changes. Push normally; inspect and resolve remote divergence without force if needed.

## Interfaces and Dependencies

Reuse proj 0.27.2 and existing GDAL geotransform metadata. Pixel-to-CRS uses all six affine coefficients. PROJ output is longitude, latitude in degrees. Missing CRS or failed/nonfinite projection is an explicit error, never a two-corner fallback.

## Outcomes & Retrospective

Completed: pointwise PROJ conversion is wired through all eight metadata writers and the three rebuilt/vendored binaries. 51 Rust tests, 158 targeted Python tests, and 8146 broad Python tests passed (72 broad skips). Final container-generated outputs match pyproj; real MOFE prep writes 0.0001 for all OFEs on eight inspected hillslopes. Peridot main is pushed at 3cef07b; WEPPpy publication accompanies this closeout. TOPAZ baseline nondeterminism and stale prior binary schema were documented rather than hidden by relaxed blanket parity claims. No live repair/deployment was performed.

Revision: 2026-09-09 UTC, initial plan before implementation.

Revision: 2026-09-09 UTC, recorded implementation evidence and revised TOPAZ parity gate after unchanged-binary repeat demonstrated preexisting nondeterminism.

Revision: 2026-09-09 23:00 UTC, recorded successful full validation and closure; archived after completion.
