# Postfire Debris Flow

> Planned WBT-based postfire debris-flow likelihood and rainfall-threshold
> assessment using Staley et al. (2017), with RUSLE supplying M1 soil erodibility.

## Status

Documentation scaffold, started 2026-09-08. No controller, UI, API, or executable
model is implemented here. Existing `debris_flow` behavior is unchanged.
The [specification](specification.md) distinguishes accepted direction from
open scientific and integration decisions.

## Intended Workflow

1. Use a continental US (CONUS) project, delineate with WBT, complete the WEPP
   Soils build, and provide a soil burn severity (SBS) map.
2. For M1, acquire POLARIS inputs and build the Nomograph K raster through RUSLE;
   also supply continuous pre/post-fire dNBR.
3. Select M1 (default) or M3 explicitly. M3 requires soil thickness instead of K
   and does not require dNBR. Raw project SSURGO horizons are a feasible source;
   their aggregation and missing-data rules still need validation.
4. Use the project's climate event intensities to assess storm-event
   probabilities. Browse events in an interactive dashboard and select an
   event to inspect catchment results, rainfall, and input provenance.
   Return-interval comparisons and rainfall thresholds are complementary views.

These are planned steps, not currently available commands. M1 and M3 predict
occurrence, not debris-flow volume or inundation extent.

## Organization

Follow the [RUSLE module](../rusle/README.md): module-level overview and science
specification, a reference bundle under [docs](docs/README.md), a thin NoDb
facade, numerical helpers, and integration/provenance collaborators.
The specification records planned source and UI paths; empty executable
placeholders are intentionally deferred until the contracts are ready.

## Developer and Operator Notes

- WBT is the supported terrain backend for this new module.
- Both models require built project Soils data. Availability is restricted to
  CONUS; the empirical model is intended for recently burned watersheds in the
  Western United States. Availability elsewhere in CONUS is not local validation.
- UI and reports must follow project SI/English unit preferences without
  changing calibrated model inputs or results.
- dNBR uploads follow SBS file-format conventions and are normalized onto the
  project grid. Partial watershed coverage is supported with explicit coverage
  reporting; missing pixels are not zero. See the [upload design](docs/dnbr_upload.md).
- RUSLE owns M1 K preparation and its UI; do not duplicate the K estimator.
- The standard RUSLE build produces named K artifacts, not `rusle/k.tif`.
- M3 ruggedness, thickness aggregation, assessment scope, and rainfall sourcing
  need resolution before implementation. Original thickness units are inches:
  M3 uses mean thickness in inches divided by 100.
- See [local agent guidance](AGENTS.md) for implementation sequencing.
- See [SSURGO feasibility](docs/ssurgo_m3_feasibility.md) for reusable raw fields
  and why generated WEPP soil depth and the current `SolThk` are unsuitable.

## References and Licensing

The scientific source is [Staley et al. (2017)](https://doi.org/10.1016/j.geomorph.2016.10.019).
The planned implementation is independently derived from the publication.
The GPL-3.0-only pfdf package is a comparison reference, not a runtime dependency.
See the [PDF storage decision](docs/pdfs/README.md) for reference redistribution.
