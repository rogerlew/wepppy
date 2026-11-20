# European climate, soils, and WEPP run recovery tracker

## Status

Scaffolded on 2026-11-20 UTC. The [contract decision draft](artifacts/20261120_contract_decision.md) and [active ExecPlan](prompts/active/implementation_execplan.md) are open. Implementation conformance, forest deployment, and replay are pending.

## Progress

- [x] Record the production failure signatures and scope the work package.
- [x] Preserve the available production baseline inputs and run initial raster and management readbacks.
- [ ] Reconcile the original operation settings and locate the overwritten land-cover upload or document replay limits.
- [ ] Resolve climate unit and ESDAC source questions, ratify the contracts, and record the checkpoint ancestor revision.
- [ ] Implement and validate the climate, WEPP and soil changes.
- [ ] Complete the full candidate deployment on forest and record runtime identities.
- [ ] Rebuild the original workflow on forest, verify artifacts and browser behavior, and complete final correctness review.

- [ ] Replay the CORINE/upload mapping switch and false migration prompt from `studded-stranglehold`, with a genuine legacy migration control.

- [ ] Complete the [ESDAC management inventory and reconciliation](artifacts/20261120_esdac_management_baseline.md), including a reviewed row-by-row disposition and generated-output validation.

## Decisions

2026-11-20 UTC. The operator requires a complete local deployment on forest followed by a rebuild of `autosomal-vetch` through the original workflow. Use a fresh forest run derived from the original inputs and preserve the production project as the baseline. Gridded soil acceptance requires ESDAC evidence for the original hillslopes. A single-soil comparison cannot establish that result.

2026-11-20 09:12 UTC. Added `studded-stranglehold`. The latest land-use job failed at 2026-11-19 12:16:03 UTC. Its saved gridded source is CORINE 2018 with the ESDAC management mapping. The deployed Web container's migration dry run reports schema 1000 current and `landuse_parquet` as the only applicable migration. No production state was changed by the investigation.

## Open evidence

The E-OBS raster unit and conversion chain, the supported single-storm execution/report matrix, and whether authoritative data can recover the 37 ESDAC rejects need evidence before contract ratification. If required original inputs are unavailable, record the missing input and its effect on replay fidelity.

## Notes – 2026-11-20 UTC

Preserved both incident baselines on forest and retained [raster readback and fixture evidence](artifacts/20261120_incident_readback.md). The E-OBS failure is reproducible as coastal NoData contamination in cubic interpolation. A real CLIGEN comparison generated 30 years with the alternate sampling probe. Paired ESDAC pixel sampling found six potential recoveries and five potential regressions, with 31 original rejects still missing subsoil fields. Added the full catalog inventory and native template parse results.

The operator authorized a [bounded same-unit soil recovery study](artifacts/20261120_esdac_same_unit_study.md). The authorization covers evaluation. Review of scientific suitability and regressions is required before runtime use.

The operator authorized ESDAC-only subsoil defaults in Soil Options → Advanced options when source-backed recovery cannot be established. The operator subsequently chose a fixed loam preset available before the first soil build. An earlier source-derived profile remains diagnostic comparison evidence. No generic default will replace a valid source profile.

The diagnostic source-backed donor and fallback writer trials generated and parsed 31/31 and 37/37 base soils, respectively. The configured 7778 Disturbed validation rejected its metadata readback, including an unchanged source control. Added the format-specific downstream defect to acceptance.

Drafted [ADR-0151](../../adrs/ADR-0151-esdac-missing-subsoil-defaults.md) for review. It records the six seeded values, eligible missing-data signature and provenance. Application changes, candidate deployment and both incident replays remain open.

The standalone [soil contract checkpoint](artifacts/20261120_esdac_soil_checkpoint.md) is `1b388d50b`. The soil implementation is `194978f04`. Climate, land-use management reconciliation, forest deployment and the two replays remain open.

The soil slice built all 58 incident profiles through the actual batch writer, with 37 defaults and 21 unchanged native controls, and validated 35 configured 7778 Disturbed rewrites. [Local validation](artifacts/20261120_esdac_soil_validation.md) records focused gates, review, and remaining deployment evidence. Broad pytest stopped at a culvert lock conflict reproduced on the unchanged baseline.

The operator selected masked bilinear fallback for covered E-OBS cells with incomplete cubic neighborhoods. The [sampling checkpoint](artifacts/20261120_eobs_sampling_checkpoint.md) is `9671cc1c0`. The candidate HTTP provider and normal CLIGEN client reproduced a 30-year Es Fangar CLI with 10,957 daily records, retained inland cubic sampling, and rejected missing offshore data. [Candidate validation](artifacts/20261120_eobs_sampling_validation.md)

The installed legacy E-OBS grids also contain partially contaminated aggregates from source masks lost during preprocessing. Implausible rainfall cells can be screened at runtime. Plausible contaminated temperature values require a rebuild and independent readback from the raw daily NetCDF files, which are available on forest. Regional raster remediation remains open.

The [land-use migration eligibility checkpoint](artifacts/20261120_landuse_migration_checkpoint.md) is `8d20d6897`. The candidate preserved the retry route on a current-schema partial build and generated Parquet for a matching serialized legacy treatment. Land-use mapping and the forest replay remain open.

The [climate status checkpoint](artifacts/20261120_climate_status_checkpoint.md) is `ccb90d394`. The panel now follows the latest verified build or upload and displays neutral unavailable status on expiry. The deployed replay remains open.

The [single-storm execution checkpoint](artifacts/20261120_single_storm_execution_checkpoint.md) is `3b5f6bb5b`. The legacy binary completed 18 hillslopes and the companion watershed using the original storm CLI and regenerated deck. Individual storms now receive an advisory, while the separately diagnosed batch postprocessing limitation remains open.

The [uploaded climate checkpoint](artifacts/20261120_uploaded_climate_mode_checkpoint.md) is `a94869bbd`. A private copy of the archived continuous climate rendered without the storm warning and corrected saved mode 15 to mode 12 during WEPP preparation. Upload admission and publication isolation remain open.

The [climate upload admission checkpoint](artifacts/20261120_climate_upload_admission_checkpoint.md)
is `38ea8f51b`. Private HTTP and RQ verification used both archived CLIs and
preserved the applied climate across a rejected same-name submission and an
admitted malformed upload. Whole-generation publication recovery remains open.

The E-OBS v19.0e data rebuild completed off the shared dataset. The private
staging tree contains 96 WGS84 rasters and eight relocatable VRTs. Candidate
metquery and CLIGEN produced 10,957 valid rows from the rebuilt source at Es
Fangar. Forest has yet to use these data through the full deployed stack.

The [CORINE provider checkpoint](artifacts/20261120_landuse_source_checkpoint.md)
is `59c9e23d7`. The candidate generated 58 land-use Parquet rows from the
archived classes, including 16 class-25 Mixed forest hillslopes. Incompatible
upload preflight and the complete forest replay remain open.

The [historical thinning reference checkpoint](artifacts/20261120_management_reference_checkpoint.md)
is `9402cef2d`. All 16 corrected references across four tables round-tripped
through the native 98.4 reader. The Disturbed ESDAC generic thinning class
still prevents full catalog hydration for keys 115–117, 123 and 124.
