# Postfire Debris Flow

> WBT-based postfire debris-flow likelihood and rainfall-threshold
> assessment using Staley et al. (2017), with RUSLE supplying M1 soil erodibility.

## Status

The production M1 control, NoDb state, dNBR upload and RQ execution are implemented.
Development validation is recorded in the [production work package](../../../../docs/work-packages/20260910_staley_m1_production/package.md).
M3 soil/terrain composition, bounded source preparation and shared valid-support
results are implemented under the [runtime contract](docs/production_m3_runtime.md).
Live acceptance is tracked in the [M3 package](../../../../docs/work-packages/20260914_staley_m3_integration/package.md).
Reports and the event dashboard remain deferred. Existing
`debris_flow` behavior is unchanged. See the [specification](specification.md)
and [roadmap](implementation_roadmap.md) for scientific scope and remaining work.

## Run M1

1. Delineate the burned watershed of interest in a continental-US WBT project.
   The empirical model is intended for recently burned Western US basins.
2. Enable **Post-fire debris flow** in Mods (also enables POLARIS and RUSLE).
   Build project climate, set soil burn severity, and prepare POLARIS
   Nomograph K through RUSLE. The control shows which prerequisites need work;
   completion of the entire RUSLE model is not required.
3. Upload a single-band GeoTIFF
   (preferred), self-contained IMG, or supported VRT with its referenced raster.
   **Auto** estimates the dNBR scale from values. If it cannot resolve the scale,
   choose a scale and retry the retained map without uploading again.
4. Check the accepted filename, scale and watershed coverage in the upload table.
   Select Project climate or available NOAA design rainfall and run the model.
   Download completed event, design-storm and threshold files. Reports are deferred.

Partial dNBR coverage is supported; missing observations are not zero. Failed
replacements preserve the accepted map. Changed prerequisites require preparation
or a rerun. Display units follow project preferences; model files use canonical SI
units. The model estimates occurrence likelihood, not volume or inundation extent.

## Select M3

Select M3 beside M1 in the existing control. The dNBR upload and K prerequisite
are hidden; Soils is shown instead. Initial M3 eligibility requires the project's
10 m cell size and NED13/2022 DEM source. Automatic POLARIS/RUSLE enablement stays
in place, but M3 does not require their outputs. Prepare project soils, SBS and
climate before submitting. The task derives soil thickness from verified SSURGO
records with original STATSGO THICK fallback, and ruggedness from the full basin.
The summary reports exact Valid coverage and links its downloadable mask.
Missing cells are excluded, not filled with zero; zero support yields explicit
unavailable probabilities. The job ID and results remain visible after reload.

Changing selection preserves prior model outputs and their model labels. The
🌋 marker represents the latest accepted result on its own inputs, independently
of the radio selection. A failed M3 task does not erase a current M1 result.

## Scientific integration and planned dashboard workflow

1. Use a continental US (CONUS) project, delineate with WBT, complete the WEPP
   Soils build, and provide a soil burn severity (SBS) map.
   Manually isolate a burned basin you suspect may be at risk when setting up
   the project. Assessment reuses that watershed and its existing outlet;
   additional or nested catchment delineation is not required.
2. For M1, acquire POLARIS inputs and build the Nomograph K raster through RUSLE;
   also supply continuous pre/post-fire dNBR.
3. Select M1 (default) or M3 explicitly. M3 requires soil thickness instead of K
   and does not require dNBR. Raw project SSURGO horizons are a feasible source;
   SSURGO is the approved primary source with original STATSGO THICK as fallback.
   Production uses recorded-depth policy and common valid cells; shared WEPP
   soil builders, substitutions and caches are not changed.
4. Use the project's climate event intensities to assess storm-event
   probabilities. Browse events in an interactive dashboard and select an
   event to inspect the project watershed result, rainfall, and input provenance.
   Return-interval comparisons and rainfall thresholds are complementary views.

The interactive dashboard remains planned. M1 and M3 predict
occurrence, not debris-flow volume or inundation extent.

## Organization

Follow the [RUSLE module](../rusle/README.md): module-level overview and science
specification, a reference bundle under [docs](docs/README.md), a thin NoDb
facade, numerical helpers, and integration/provenance collaborators.
The specification and detailed contracts map the implemented source and UI paths.

## Developer and Operator Notes

- WBT is the supported terrain backend for this new module.
- M3 requires built project Soils; M1 requires current RUSLE K instead. Availability is restricted to
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
  Production uses the separate accepted recorded-depth/common-valid policy;
  the strict offline study remains reproducible.
- Source preparation derives keys and extent from each basin. Operators use
  `source_acquisition.acquire_sources` only with bounded network authority,
  then `production_soils.activate_sources` with the returned receipt SHA-256.
  The accepted [Run-preparation amendment](docs/production_m3_runtime.md#2026-09-15-run-preparation-amendment)
  (implementation pending) also makes explicit Run M3 prepare an absent source
  pointer automatically. Existing pointers are reused. Readers never acquire
  sources, and neither workflow rebuilds soils or changes shared caches.
- See [local agent guidance](AGENTS.md) for implementation sequencing.
- See [SSURGO feasibility](docs/ssurgo_m3_feasibility.md) for reusable raw fields
  and why generated WEPP soil depth and the current `SolThk` are unsuitable.

## Offline numerical engine

`staley2017.py` evaluates explicit scalar M1/M3 predictors for 15, 30 and 60
minutes. It does not derive project predictors or fetch rainfall. Use the
[accepted engine contract](docs/staley2017_engine.md) for input ranges, units,
and unavailable/nonunique reasons.

```python
from wepppy.nodb.mods.postfire_debris_flow.staley2017 import probability, rainfall_threshold

# Synthetic M1 inputs: T is a spatial intersection fraction, F is already
# normalized dNBR, and S is K in the calibrated convention.
p = probability("M1", 15, T=0.4, F=0.6, S=0.3, rainfall_mm=8)
# p = 0.929432205755199; 8 mm in 15 minutes is 32 mm/hour.
threshold = rainfall_threshold(
    "M1", 15, T=0.4, F=0.6, S=0.3, target_probability=0.5,
)
# threshold.status == "available"; rainfall_mm is approximately 4.677835.
```

Inverse results solve an equality. Always inspect `status`/`reason` before
using numeric values. A decreasing response from negative M1 dNBR is an
algebraic result, not a validated triggering threshold. Zero rainfall retains
the equation's small intercept probability. Caller errors and forward overflow
raise explicitly; unavailable inverse results carry `None`, not zero/infinity.
Synthetic [generated examples](../../../../docs/work-packages/20260908_staley_watershed_engine/artifacts/synthetic_examples.json)
cover both models and all durations. Reproduce them in the container:

```bash
wctl run-python docs/work-packages/20260908_staley_watershed_engine/artifacts/generate_examples.py
wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_staley2017.py --maxfail=1
```

Production preparation, Climate integration, persisted results and browser
controls compose this API separately. No live rebuild is needed to use the
offline numerical functions.

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

The subsequent owner decision selects **SSURGO primary, original STATSGO THICK
fallback**, preferring detailed soil information with broader-coverage backup.
Source selection and fallback contributions must be reported. Material policy,
partial-support handling, and fallback granularity remain implementation
decisions; the offline complete-only criterion is not a production requirement.
The study measures source sensitivity, not comparative predictive accuracy.

## dNBR Backend

The local Python interface in `dnbr.py` normalizes explicitly encoded dNBR
onto a supplied WBT project grid. It accepts partial coverage and reports
observed-support means for M1 without double scaling. Example:

```python
from wepppy.nodb.mods.postfire_debris_flow.dnbr import normalize_dnbr, summarize_dnbr

manifest = normalize_dnbr(
    source="source_dnbr.tif", dem="dem.tif", watershed_mask="catchment_mask.tif",
    output_dir="new_dnbr_artifact", scale_factor=0.001,
)
summary = summarize_dnbr("new_dnbr_artifact/dnbr.tif", "catchment_mask.tif")
```

The output directory must not exist; failed processing preserves prior artifacts.
The mask must be binary 1 inside / 0 outside on the exact DEM grid. Do not pass
an arbitrary watershed label raster without constructing the binary mask.
This is a backend interface, not a working browser upload or NoDb publication
workflow. See the [input contract](docs/dnbr_upload.md) for safe VRT restrictions,
self-contained IMG, optional dates, limits, error codes and provenance.

Two real USGS Arizona fixtures (CC0) and their original metadata are included
under `tests/nodb/mods/fixtures/postfire_debris_flow_dnbr`. They are Float32
x1000 data, so use explicit scale 0.001. The tests also cover normalized floats
and integer encoding; dtype alone cannot establish scale.

## References and Licensing

The scientific source is [Staley et al. (2017)](https://doi.org/10.1016/j.geomorph.2016.10.019).
The planned implementation is independently derived from the publication.
The GPL-3.0-only pfdf package is a comparison reference, not a runtime dependency.
See the [PDF storage decision](docs/pdfs/README.md) for reference redistribution.

## Local M1 predictors and rainfall results

The [M1 predictor package](../../../../docs/work-packages/20260909_staley_m1_predictors/package.md)
provides local T/F/S composition with accepted Nomograph K policy and complete
authentic Wallow evidence. See the [predictor contract](docs/m1_predictors.md).

`results.build_m1_results` composes pinned predictors and existing Climate
snapshots into event, explicit CLI/NOAA design and inverse tables. `open_results`,
`list_events` and `get_event` provide bounded local browsing. The approved R02
policy retains unsupported CLI ranks as unavailable rows with
`insufficient_positive_samples`; supported ranks and durations remain usable.
See the [rainfall contract](docs/rainfall_results.md) for arguments, units,
limits, provenance and query semantics, and the
[work package](../../../../docs/work-packages/20260909_staley_rainfall_results/package.md)
for genuine Wallow evidence and reproduction scripts. Production publication,
NoDb/RQ integration and dashboard work remain separately scoped.

## Production workflow planning

The [production M1 package](../../../../docs/work-packages/20260910_staley_m1_production/package.md)
is scaffolded for project readiness, dNBR upload and running the model through
a minimal control. [UI design](../../../../docs/ui-docs/contracts/postfire-debris-flow-control-contract.md)
is proposed for owner review before implementation. Reports and dashboard are
deferred; initial completion provides status and authorized model-file access.

## Production operations

The [production contract](docs/production_m1.md) defines routes, state, source
freshness, candidate retention and publication. `postfire_debris_flow.nodb` is
optional until the first accepted mutation. Inputs and outputs are immutable
under visible `postfire_debris_flow/attempts/<attempt-id>/`. Sources, intermediate
maps, diagnostics, failed work and completed files are browsable and archived.
The latest four result files also appear directly in `postfire_debris_flow/`. Unaccepted retries expire after 24 hours;
automatic artifact deletion is deferred.

Workers require the owned WBT `StaleySlopeSbs` tool. Use the existing
[WBT cutover runbook](../../../../docs/dev-notes/weppcloud-wbt-release-cutover.md)
and verify the actual worker executable before installing on another host.
Development-host verification does not establish production-host installation.
