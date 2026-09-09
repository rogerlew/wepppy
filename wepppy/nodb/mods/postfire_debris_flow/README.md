# Postfire Debris Flow

> Planned WBT-based postfire debris-flow likelihood and rainfall-threshold
> assessment using Staley et al. (2017), with RUSLE supplying M1 soil erodibility.

## Status

Offline soil-thickness derivation and a reproducible source-comparison harness
are implemented. No postfire controller, UI, API or production model wiring is
implemented here. Existing `debris_flow` behavior is unchanged.
The [specification](specification.md) distinguishes accepted direction from
open scientific and integration decisions.

## Intended Workflow

1. Use a continental US (CONUS) project, delineate with WBT, complete the WEPP
   Soils build, and provide a soil burn severity (SBS) map.
2. For M1, acquire POLARIS inputs and build the Nomograph K raster through RUSLE;
   also supply continuous pre/post-fire dNBR.
3. Select M1 (default) or M3 explicitly. M3 requires soil thickness instead of K
   and does not require dNBR. Raw project SSURGO horizons are a feasible source;
   offline aggregation and coverage are explicit, but source substitution is not
   approved.
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
- M3 offline thickness uses raw validated intervals and explicit fractional
  component support. Original units are inches; S is mean cm / 254.
  Production source approval, assessment scope and rainfall sourcing remain open.
- See [local agent guidance](AGENTS.md) for implementation sequencing.
- See [SSURGO feasibility](docs/ssurgo_m3_feasibility.md) for reusable raw fields
  and why generated WEPP soil depth and the current `SolThk` are unsuitable.

## Offline soil study

`soil_thickness.py` provides pure interval/map-unit calculations, a read-only
SQLite adapter, and `build_artifacts` for prepared GeoTIFFs and upstream masks.
It writes component/map-unit audits, thickness/support rasters, catchment S
and input hashes into a new directory. It never builds live soils or acquires
missing sources. Partial means are diagnostics; full-support outputs are absent
when component or spatial support is incomplete.

See the [canonical soil contract](docs/m3_soil_thickness.md) for signatures,
required columns, reason codes and the strict-soil/all-layer distinction.
The [study harness and validation](../../../../docs/work-packages/20260908_staley_m3_soils/artifacts/validation.md)
reproduce the frozen three-site comparison with owned WBT routing and Rust
intersection counts. The helper can be loaded directly by that harness without
NoDb's package-level Redis initialization.

The study recommends retaining the original STATSGO predictor pending a
scientific source decision. SSURGO's finer mapping does not establish calibrated
parity, and the sampled catchments all have incomplete component support.

## References and Licensing

The scientific source is [Staley et al. (2017)](https://doi.org/10.1016/j.geomorph.2016.10.019).
The planned implementation is independently derived from the publication.
The GPL-3.0-only pfdf package is a comparison reference, not a runtime dependency.
See the [PDF storage decision](docs/pdfs/README.md) for reference redistribution.
