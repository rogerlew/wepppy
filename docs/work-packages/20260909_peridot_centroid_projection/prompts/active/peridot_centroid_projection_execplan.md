# Correct Peridot centroid projection and vendor releases

## Purpose / Big Picture

Make exported geographic centroids describe the actual raster pixel centroid so MOFE bedrock maps sample the intended location. This is a living ExecPlan governed by docs/prompt_templates/codex_exec_plans.md.

## Progress

- [x] (2026-09-09 UTC) Reproduced the approximation for all 505 seductive-sabra hillslopes and inspected shared exporters.
- [ ] Contract checkpoint and ADR committed.
- [ ] Implementation and regression tests complete.
- [ ] Release binaries built, vendored, and exercised on isolated inputs.
- [ ] Review, documentation, commits and pushes complete.

## Surprises & Discoveries

PROJ is already linked. Metadata uses a four-number approximation instead. Export tasks execute in parallel, so construct and reuse a transformer inside each writer. Both repositories have pre-existing changes; stage only package-owned files/hunks. Peridot has pre-existing dirty tracked binaries; preserve copies before authorized rebuild.

## Decision Log

2026-09-09 UTC, user/Codex: replace the approximation with pointwise PROJ conversion using the raster affine transform. Preserve existing integer pixel/corner convention and all schemas. Reusing PROJ avoids a dependency evaluation or native-stack change. Raster sampler rounding and live data repair remain separate scope.

## Context and Orientation

Peridot is /home/workdir/peridot (main). WEPPpy is /home/workdir/wepppy (master). Peridot src/rasters/raster.rs builds wgs_transform from two corners. src/watershed_abstraction/flowpath_collection.rs uses it in eight metadata writers. TOPAZ and WBT abstraction plus sub-fields call those writers. WEPPpy vendors binaries in wepppy/topo/peridot/bin. Source run inputs are /wc1/runs/se/seductive-sabra/dem/topaz; never run abstraction against the original because it deletes watershed outputs.

## Milestones and Plan of Work

First amend Peridot docs/contracts/watershed-output-contract.md and add a WEPPpy ADR defining pointwise projection, error behavior, and migration expectations; commit this ancestor checkpoint before code. Record the compatibility plan in package.md.

Second provide a raster-derived reusable PROJ transformer and pass raster context to metadata writers. Initialize inside each writer, propagate initialization/conversion failures as io errors, and reject nonfinite coordinates. Update all callers, including CSV sub-fields. Add known-coordinate and export regression tests including noncentral UTM locations, southern hemisphere, rotation, and missing/invalid CRS.

Third run cargo tests and build the three changed CLI binaries with cargo build --release. Preserve pre-existing binaries in /tmp before rebuilding. Copy release outputs into WEPPpy using the canonical Peridot operations runbook. Execute rebuilt/vendored TOPAZ on isolated copied input rasters and validate coordinates against pyproj; exercise WBT/sub-fields via available fixtures. Demonstrate sampled values reach isolated prepared soil files and preserve unrelated artifacts.

Finally run WEPPpy targeted Peridot tests and wctl run-pytest tests --maxfail=1, doc lint, and a correctness review. Record all failures and limitations accurately. Update tracker and package, archive this plan to prompts/completed, commit only owned changes, and push Peridot main and WEPPpy master without force.

## Validation and Acceptance

Use cargo test in Peridot; expect regression cases to pass and demonstrate the old approximation fails the known-coordinate case. Use rebuilt generated Parquet/CSV coordinates with pyproj tolerance 1e-8 degrees. Preserve non-coordinate fields and slope outputs. Confirm vendored SHA256 matches release source. Run wctl run-pytest tests/topo --maxfail=1 and broad sanity; record environmental blockers distinctly. Correctness artifact must close medium/high findings.

## Idempotence and Recovery

Use only temporary copied runs for generation; never edit seductive-sabra. Release build is repeatable; restore backed-up binaries only if abandoning the change. Do not reset unrelated repository changes. Push normally; inspect and resolve remote divergence without force if needed.

## Interfaces and Dependencies

Reuse proj 0.27.2 and existing GDAL geotransform metadata. Pixel-to-CRS uses all six affine coefficients. PROJ output is longitude, latitude in degrees. Missing CRS or failed/nonfinite projection is an explicit error, never a two-corner fallback.

## Outcomes & Retrospective

Pending implementation and generated-output evidence.

Revision: 2026-09-09 UTC, initial plan before implementation.
