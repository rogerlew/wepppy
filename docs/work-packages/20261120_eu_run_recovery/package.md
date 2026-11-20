# European climate, soils, and WEPP run recovery

**Status**: Forest replay verified the original workflow, E-OBS with gridded ESDAC soils, and staged land-use upload recovery. Failed generated climate replacement and European management reconciliation remain open.
**Opened**: 2026-11-20 UTC
**Target**: Complete local deployment and end-to-end replay on `forest`

## Purpose

Make the original `autosomal-vetch` workflow usable through the WEPPcloud browser, from European watershed setup through climate, soils, and fresh WEPP results. The run must explain the current operation and any failure in terms the user can act on.

## Confirmed incident evidence

- A successful single-storm `FLOOD4.cli` upload set mode 15. Later, the successful upload of 30-year `ESFANGAR.cli` replaced the active file and left mode 15 in place. WEPP stopped at its application-level guard before starting the executable. [Upload job](https://wepp.cloud/rq-engine/api/jobinfo/3403e578-8029-4acb-a3af-dda7ae851d02) · [WEPP job](https://wepp.cloud/rq-engine/api/jobinfo/cd509426-5abf-4ebd-9e24-99309429b6d3)
- The Climate panel restored the latest build job even though a newer upload had succeeded. Three E-OBS builds failed. Coastal interpolation used scaled NoData values as rainfall and temperature observations. CLIGEN received about 67–75 inches per month in the failed build and returned invalid precipitation headers. [Latest failed build](https://wepp.cloud/rq-engine/api/jobinfo/64a1ea11-db3c-4b44-8cc5-86cda09e0c66) · [Raster readback](artifacts/20261120_incident_readback.md#e-obs-coastal-interpolation)
- European gridded soils use ESDAC. The batch report accepted 21 of 58 locations and rejected 37 with missing subsoil material. A later database single-soil build succeeded. The candidate gridded build accepted 58 of 58, using the approved editable defaults for the 37 source gaps. [ESDAC source contract](../../schemas/esdac-soil-source-contract.md) · [Candidate evidence](artifacts/20261120_esdac_soil_validation.md)

- A second current-schema `eu-disturbed` project, `studded-stranglehold`, retained the `esdac` management mapping when it returned to gridded CORINE 2018. The CORINE mapping defines class 25 as Mixed forest. The selected ESDAC mapping has no key 25 and lacks `DisturbedClass` metadata, which also caused earlier upload attempts to fail. The last build wrote dominant classes to NoDb and stopped before publishing land-use Parquet. Production dry-run migration reported version 1000 current and flagged `landuse_parquet` because the partial assignment data looked like a completed build. [Land-use job](https://wepp.cloud/rq-engine/api/jobinfo/fe02d15d-b285-4d75-8cfc-8a1284fa277f)

## Scope and acceptance

1. Each successful climate upload derives saved mode from the active file. Cover both replacement directions, legacy mode/file disagreement, failed replacement, retry, reload, and WEPP consuming the intended file.
2. Ratify the warning-only deprecation transition requested for genuine single-storm runs. Define supported execution paths and reports and verify the promised subset. Align admission, execution, and copy.
3. Restore the latest applicable climate operation across builds and uploads after reload, with correlated status, details, and summary. Preserve prior attempts in job history.
4. Trace E-OBS from the installed raster through the provider and localization into the generated and consumed CLIGEN files. Verify the scientific units and daily output. Provide an actionable failure when inputs or results are unusable.
5. Reproduce ESDAC gridded soils for the original hillslopes. If source-backed subsoil recovery cannot be established, add editable subsoil defaults under Soil Options → Advanced options for the ESDAC gridded path. Establish which profiles the authoritative data can support and any defensible recovery, preserve physical validation, and make rejected hillslopes and supported next actions visible in Soil Options. Validate generated soils through Disturbed processing and WEPP input preparation. The current 7778 validator expects metadata fields absent from 7778 readback. Repair that format-specific gate and verify the numeric and provenance checks under the configured format.
6. Complete a full candidate deployment on `forest` before rebuilding a fresh `eu-disturbed` replay of `autosomal-vetch` through its original workflow. Read back the exact model inputs, fresh outputs, browser state and reports. Closeout requires this replay evidence. A database single-soil override is a comparison and cannot satisfy gridded ESDAC acceptance.

7. Verify land-use source and mapping compatibility for gridded CORINE and uploaded land cover, including Disturbed metadata. Surface incompatible combinations in Landuse Options and define how the last usable build is preserved on failure. Keep incomplete current-schema builds out of the legacy migration gate while retaining migration for genuinely completed legacy data. Replay this incident on forest after the full deployment.

8. Audit and reconcile every ESDAC base class, disturbance and treatment entry, and referenced management template. Establish authoritative source legends, named catalog ownership and compatibility rules for built-in and uploaded rasters. Record a disposition and evidence for every row and every consumer of the affected lookups. [Initial inventory](artifacts/20261120_esdac_management_baseline.md)

The [ExecPlan](prompts/active/implementation_execplan.md) defines the deployment and replay. The production project and its job history are the read-only baseline. Production rollout and in-place production recovery are outside this package.

## Complexity budget and compatibility

Reuse the current climate catalog and upload/build operations, run metadata, ESDAC provider and quality report, native model binaries, and forest development stack. Preserve unrelated defaults, queue behavior, access boundaries, and report behavior. Keep existing public keys and the soil quality report schema. Handle persisted pre-fix runs and absent, empty, failed, and superseded states explicitly. Any change to unit conversion, formulas, thresholds or soil fallback requires a parameterization ADR and representative readback evidence. Diagnose shared assumptions and repair confirmed peer consumers under the [hardening lifecycle standard](../../standards/hardening-lifecycle-standard.md).

## Review and evidence

Security impact is provisionally low. Existing upload handling and job-status boundaries are in scope. Preserve run-scoped authorization, CSRF, upload limits, and trace sanitization. Reassess at the contract checkpoint. A dedicated security review artifact is required if the ratified scope is high impact. Independent contract and final correctness reviews follow the [contract-first standard](../../standards/contract-first-change-standard.md). Close medium and high correctness findings before final acceptance.

Retain the candidate revision, baseline and forest replay identifiers, dataset and native binary identities, job timeline, browser reload evidence, and parsed climate, base and disturbed soils, prepared WEPP inputs, and model outputs. A job status alone cannot establish success. Watch for incorrect climate totals, false deprecation banners, stale job details, invalid or silently substituted soils, and missing fresh WEPP output through the replay and a repeat attempt. [Generated artifact validation](../../standards/generated-artifact-validation-standard.md)
