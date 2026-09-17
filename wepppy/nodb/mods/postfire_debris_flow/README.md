# Postfire Debris Flow

> WBT-based postfire debris-flow likelihood and rainfall-threshold
> assessment using Staley et al. (2017), with NRCS-derived STATSGO fine-earth Kf for M1.

## Status

The production M1 control, NoDb state, dNBR upload and RQ execution are implemented.
Development validation is recorded in the [production work package](../../../../docs/work-packages/20260910_staley_m1_production/package.md).
M3 soil/terrain composition, bounded source preparation and shared valid-support
results are implemented under the [runtime contract](docs/production_m3_runtime.md).
Live acceptance is tracked in the [M3 package](../../../../docs/work-packages/20260914_staley_m3_integration/package.md).
The saved likelihood report is implemented under its
[reviewed contract](../../../../docs/ui-docs/contracts/postfire-debris-flow-report-contract.md);
see [implementation progress](../../../../docs/work-packages/20260915_postfire_debris_flow_report_implementation/tracker.md).
Maps and advanced scenario exploration remain deferred. Existing
`debris_flow` behavior is unchanged. See the [specification](specification.md)
and [roadmap](implementation_roadmap.md) for scientific scope and remaining work.

## Run M1

1. Delineate the burned watershed of interest in a continental-US WBT project.
   The empirical model is intended for recently burned Western US basins.
2. Enable **Post-fire debris flow** in Mods. Build project climate and set soil
   burn severity. Run M1 automatically prepares [STATSGO fine-earth Kf](docs/kf_source.md);
   POLARIS and RUSLE are not required. The control shows missing prerequisites.
3. Upload a single-band GeoTIFF
   (preferred), self-contained IMG, or supported VRT with its referenced raster.
   **Auto** estimates the dNBR scale from values. If it cannot resolve the scale,
   choose a scale and retry the retained map without uploading again.
4. Check the accepted filename, scale and watershed coverage in the upload table.
   Select Project climate or available NOAA design rainfall and run the model.
   Download completed event, design-storm and threshold files.

Partial dNBR coverage is supported; missing observations are not zero. Failed
replacements preserve the accepted map. Changed prerequisites require preparation
or a rerun. Display units follow project preferences; model files use canonical SI
units. The model estimates occurrence likelihood, not volume or inundation extent.

## Select M3

Select M3 beside M1 in the existing control. The dNBR upload and K prerequisite
are hidden; Soils is shown instead. Initial M3 eligibility requires the project's
10 m cell size and NED13/2022 DEM source. M3 does not require Kf, POLARIS or RUSLE. Prepare project soils, SBS and
climate before submitting. The task derives soil thickness from verified SSURGO
records with original STATSGO THICK fallback, and ruggedness from the full basin.
The summary reports exact Valid coverage and links its downloadable mask.
Missing cells are excluded, not filled with zero; zero support yields explicit
unavailable probabilities. The job ID and results remain visible after reload.

Changing selection preserves prior model outputs and their model labels. The
🌋 marker represents the latest accepted result on its own inputs, independently
of the radio selection. A failed M3 task does not erase a current M1 result.

## Read the likelihood report

The report adds **View likelihood report** to the existing control. It reads the
last accepted assessment, not the currently selected model. Opening it does not
run a model, acquire data or repair missing inputs. Before a first assessment,
the page explains that no completed assessment is available.

Choose a **Rainfall window** (15, 30 or 60 minutes) to compare the four saved
rainfall scenarios and browse storm events. The three-row 50% table always shows
all windows. Filter events by minimum likelihood or original year label, then
select an event to see its three window estimates immediately below its row.
Reset filters returns to the complete event catalog; unavailable probabilities
remain visible unless a numeric likelihood filter excludes them.

Likelihood is conditional on the shown rainfall and the accepted post-fire
inputs. It is **not an annual debris-flow probability**, a warning threshold or
a prediction of runout, volume or inundation. Rainfall recurrence intervals refer
to rainfall, not debris flows. The 50% rainfall is an equation-derived equality,
not a safe/unsafe boundary. Different windows are separate estimates; do not add
or average their probabilities. All events use the same fixed post-fire inputs,
not a simulation of landscape recovery. Simulation year labels are not observed
calendar years. Spatial coverage measures usable input cells, not confidence.

Input changes leave previous results available with a warning. If the report
cannot check whether inputs are current, it says so without discarding saved
values. If another model run replaces the assessment while you are viewing it,
reload before continuing. Missing or inconsistent accepted files are explicitly
unavailable; the report never fills missing probabilities with zero.

**Download displayed rows (CSV)** exports the current page in displayed units
with full numeric precision and assessment/filter context. Full saved parquet
downloads use canonical units. Changing SI/English display units does not change
probabilities or model inputs. Methods contains assessment identity and detailed
limitations; the ordinary project browser retains source, failed and intermediate
artifacts as well as completed outputs.

## Scientific integration workflow

1. Use a continental US (CONUS) project, delineate with WBT, complete the WEPP
   Soils build, and provide a soil burn severity (SBS) map.
   Manually isolate a burned basin you suspect may be at risk when setting up
   the project. Assessment reuses that watershed and its existing outlet;
   additional or nested catchment delineation is not required.
2. For M1, supply continuous pre/post-fire dNBR. Run M1 acquires bounded source
   windows of the approved KFFACT raster and prepares Kf on the existing grid.
3. Select M1 (default) or M3 explicitly. M3 requires soil thickness instead of K
   and does not require dNBR. Raw project SSURGO horizons are a feasible source;
   SSURGO is the approved primary source with original STATSGO THICK as fallback.
   Production uses recorded-depth policy and common valid cells; shared WEPP
   soil builders, substitutions and caches are not changed.
4. Use the project's climate event intensities to assess storm-event
   probabilities. Browse saved events in the likelihood report and select an
   event to inspect the project watershed result, rainfall, and input provenance.
   Return-interval comparisons and rainfall thresholds are complementary views.

Map-based and advanced interactive scenarios remain deferred. M1 and M3 predict
occurrence, not debris-flow volume or inundation extent.

## Organization

Follow the [RUSLE module](../rusle/README.md): module-level overview and science
specification, a reference bundle under [docs](docs/README.md), a thin NoDb
facade, numerical helpers, and integration/provenance collaborators.
The specification and detailed contracts map the implemented source and UI paths.

## Developer and Operator Notes

- The report reads accepted attempt directories through `open_results`; it does
  not reopen unchecked public parquet copies. Its GET page/query/detail and
  fixed attachments enforce run access and no-store. Browser CSV is page-scoped.
- Freshness uses existing production checks without job reconciliation. Missing
  currentness prerequisites yield unknown freshness; do not initialize optional
  project state to satisfy a read. Existing Redis/session caches retain their
  normal behavior. A source-code identity change may legitimately mark earlier
  results stale without changing their scientific values.
- New source snapshots record file-content hashes. WEPP's unchanged climate
  hard links preserve accepted currentness. Active M1/M3 jobs also tolerate
  settled CLI ctime changes from WEPP link creation/removal after a fresh hash
  matches the admitted bytes, with the same path, size and modification time.
  Other source and publication guards remain strict. Changed bytes invalidate it,
  including equal-size rewrites with restored modification time. Older snapshots
  without hashes retain strict metadata checks and may need an explicit rerun.
  Do not rewrite historical hashes or rerun projects automatically. Soil/SQLite
  provenance and CLI/parquet readiness remain separate checks. New execution
  requires a Parquet export with matching CLI producer lineage; rebuild older
  proofless climate exports through normal **Build climate**. Reports retain
  their supported legacy reads. See the
  [freshness contract](../../../../docs/schemas/file-dependency-freshness-contract.md)
  for compatibility and active-worker verification requirements.
- Known M3 limitation: metadata changes in soil inputs, prepared source evidence
  and SQLite main/WAL/SHM files can still mark an assessment stale when their
  scientific content is unchanged. Byte-identical replacement, archive restore,
  VACUUM/checkpoint or edits to unrelated tables can trigger this behavior.
  A restored project's saved artifacts can remain intact while M3 shows stale.
  Use an explicit **Run M3** after restore to establish fresh acceptance, then
  wait for its current result before treating it as current. State polling does
  not create SQLite snapshots or rewrite saved provenance; rebuilding soils or
  editing saved hashes is not the recovery. Strict execution guards remain active.
- Troubleshoot unavailable reports by checking retained acceptance and artifact
  evidence in the ordinary project browser. Do not rebuild soils, republish or
  run a model as an automatic report recovery action. Report technical errors
  are logged server-side; browser messages omit host paths and credentials.

- WBT is the supported terrain backend for this new module.
- M3 requires built project Soils; M1 prepares its own fine-earth Kf. Availability is restricted to
  CONUS; the empirical model is intended for recently burned watersheds in the
  Western United States. Availability elsewhere in CONUS is not local validation.
- UI and reports must follow project SI/English unit preferences without
  changing calibrated model inputs or results.
- dNBR uploads follow SBS file-format conventions and are normalized onto the
  project grid. Partial watershed coverage is supported with explicit coverage
  reporting; missing pixels are not zero. See the [upload design](docs/dnbr_upload.md).
- New M1 attempts own `kf/` source receipts, native/aligned rasters and metadata;
  predictor schema 3 binds their identity. Source failures retain diagnostics and
  leave the previous acceptance intact. Retry through Run M1; never fill missing Kf.
- Legacy schema 1/2 M1 keeps its recorded POLARIS/RUSLE provenance and freshness.
  Removing RUSLE does not remove the post-fire control or invalidate new Kf results.
- Reports evaluate the accepted model on a bounded intensity grid for 15/30/60
  minutes, with P50, saved design markers, numeric values and CSV. Unit changes
  affect display only. NOAA scenarios are statistical design rainfall; recorded
  GridMetPRISM/CLIGEN event peaks are modeled/disaggregated, even with calendar dates.
- M3 offline thickness uses raw validated intervals and explicit fractional
  component support. Original units are inches; S is mean cm / 254.
  Production uses the separate accepted recorded-depth/common-valid policy;
  the strict offline study remains reproducible.
- Source preparation derives keys and extent from each basin. Operators use
  `source_acquisition.acquire_sources` only with bounded network authority,
  then `production_soils.activate_sources` with the returned receipt SHA-256.
  The accepted [Run-preparation amendment](docs/production_m3_runtime.md#2026-09-15-run-preparation-amendment)
  also makes explicit Run M3 prepare an absent source
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

## Production workflow

The [production M1 package](../../../../docs/work-packages/20260910_staley_m1_production/package.md)
delivered project readiness, dNBR upload and running the model through
a minimal control. The [control contract](../../../../docs/ui-docs/contracts/postfire-debris-flow-control-contract.md)
now also links the saved likelihood report described above. Dashboard work
remains separately scoped.

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
