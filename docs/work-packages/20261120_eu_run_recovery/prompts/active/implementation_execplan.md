# Restore the original autosomal-vetch workflow on forest

## Purpose

A user following the original European project workflow can produce usable climate and soil inputs, execute the supported WEPP paths, and understand which operation succeeded or failed after reloading the run page. Acceptance requires a fresh rebuild of `autosomal-vetch` after a complete candidate deployment on `forest`.

## Progress

- [x] 2026-11-20 UTC: Created the package, tracker and draft contract decision.
- [x] Preserve available production inputs and complete initial raster and management readbacks.
- [ ] Verify exact original workflow settings and recover the original land-cover upload or record the fidelity gap.
- [x] Ratify and commit the bounded ESDAC soil contract checkpoint (1b388d50b).
- [x] Implement the bounded soil slice (194978f04) and retain focused and generated-artifact evidence.
- [x] Ratify the standalone E-OBS sampling rule in the [sampling checkpoint](../../artifacts/20261120_eobs_sampling_checkpoint.md).
- [x] Implement and verify the E-OBS sampling rule against the [candidate HTTP provider and generated CLIGEN artifact](../../artifacts/20261120_eobs_sampling_validation.md).
- [x] Repair land-use backfill eligibility for partial builds and verify the retry route and generated legacy Parquet. [Migration checkpoint and validation](../../artifacts/20261120_landuse_migration_checkpoint.md)
- [x] Restore the latest verified climate job and preserve displayed artifacts during replacement. [Climate status checkpoint and validation](../../artifacts/20261120_climate_status_checkpoint.md)
- [x] Restore warning-only individual event execution and the legacy deck prompt. [Single-storm checkpoint and validation](../../artifacts/20261120_single_storm_execution_checkpoint.md)
- [x] Reconcile uploaded climate classification and verify the archived continuous CLI. [Upload mode checkpoint and validation](../../artifacts/20261120_uploaded_climate_mode_checkpoint.md)
- [x] Isolate and verify climate upload admission and follow-up worker validation. [Upload admission checkpoint](../../artifacts/20261120_climate_upload_admission_checkpoint.md)
- [x] Rebuild the E-OBS v19.0e monthly data privately and run the original station against the rebuilt provider.
- [x] Resolve the gridded CORINE source and regenerate archived assignment summaries. [CORINE provider checkpoint](../../artifacts/20261120_landuse_source_checkpoint.md)
- [x] Repair byte-identical renamed management file references. [Historical thinning checkpoint](../../artifacts/20261120_management_reference_checkpoint.md)
- [ ] Ratify remaining climate and land-use checkpoints.
- [ ] Implement and verify each confirmed failure class and its peer consumers.
- [ ] Complete the forest deployment and record the runtime revision.
- [ ] Replay the original run and complete generated-artifact and correctness review.

## Surprises & Discoveries

One successful upload can coexist with a stale deprecated mode and an older failed climate build displayed in the UI. The E-OBS CLIGEN failure and the ESDAC gridded-soil rejection occurred independently. The [incident readback](../../artifacts/20261120_incident_readback.md) traces the inflated E-OBS values to scaled coastal NoData in the cubic sampling window. A diagnostic CLIGEN comparison produced a finite 30-year climate with bilinear samples. Paired soil-grid sampling also revealed a pixel-selection difference and source gaps that persist under either choice.

A bounded E-OBS probe preserved cubic at an inland control, rejected an offshore control and generated all 10,957 original daily records with masked coastal sampling. The operator selected that rule. Independent review also found partially contaminated legacy cells from source masks lost during aggregation. Reconstructing affected historical grids requires validated regeneration from the raw daily files.

For `studded-stranglehold`, a failed gridded CORINE build persisted dominant land-cover codes under an incompatible ESDAC management mapping. Migration discovery treated that partial output as eligible for land-use Parquet backfill and caused a run-page redirect even though the schema is current.

## Decision Log

2026-11-20 UTC. Require the real browser and RQ workflow after a complete local deployment to forest. Preserve the original production run as evidence. The replay must attempt the original gridded ESDAC path and retain its disposition, even if it also exercises the original database-soil override.

## Outcomes & Retrospective

The soil slice is implemented and locally validated, including the preset warning and 7778 controls. The E-OBS sampler and future preprocessing correction are implemented, with actual local HTTP and CLIGEN artifact readback. The broader legacy raster rebuild, remaining contract decisions and implementation, deployment and browser replay are open.

## Milestones

### 1. Capture the baseline and ratify contracts

Read the [package](../../package.md), [tracker](../../tracker.md) and [draft decision](../../artifacts/20261120_contract_decision.md). Derive the replay manifest from the original `autosomal-vetch/eu-disturbed` config, persisted settings, available event records, job history, logs and user inputs. Capture the original watershed location, DEM and delineation settings, outlet and channels, land cover and Disturbed settings including any supplied burn map, soils settings and overrides, climate station and settings, and both uploaded climate files. Securely retain inputs outside Git where appropriate. Record artifact hashes and distinguish established facts from gaps. Preserve the original operation ordering, including the early gridded soil attempt, the override, `FLOOD4.cli`, E-OBS build attempts, and the later `ESFANGAR.cli` upload and WEPP attempts.

If the same-unit analysis cannot establish a defensible source-backed recovery, ratify the operator-authorized ESDAC-only subsoil defaults and their provenance. Review the proposed starting profile, normal form admission, existing successful profiles and generated artifacts before approving use.

Trace E-OBS at the incident coordinates and comparable successful locations through the actual provider, source raster, units, conversion, station parameters, and generated daily and monthly output. For ESDAC, compare accepted and rejected original hillslopes against emitted horizon requirements and authoritative physical inputs. Enumerate shared consumers of the diagnosed assumptions. Complete the contract checkpoint and required reviews before implementation.

Capture the `studded-stranglehold` land-use source/mode transitions, effective mappings, uploaded raster if retained, job timeline and dry-run migration output. Audit gridded and uploaded mapping consumers, Disturbed metadata validation, and migration eligibility for absent, partial, successfully completed and legacy artifacts. The exact original uploaded raster may no longer be retained. Confirm availability before claiming original-input parity.

### Audit and reconcile European management catalogs

Start with the [ESDAC baseline inventory](../../artifacts/20261120_esdac_management_baseline.md). Identify each supported raster or upload encoding and its authoritative legend, observed values, nodata values and version. Inventory plain ESDAC, Disturbed ESDAC, CORINE and applicable overrides, along with UI options, config aliases and existing consumers. Inspect saved and legacy runs where representative data are available. Keep source class codes separate from generated fire, treatment and management identifiers. Verify precedence and report unsupported or ambiguous codes with the source and expected encoding.

Retain a row-by-row matrix with source and code, authoritative meaning, existing and proposed mapping and template, Disturbed class, relevant severity and treatment targets, downstream soil lookup where applicable, provenance, compatibility impact and final disposition. Explicitly review alias collisions, the nine base template differences, four absent file references, blank classes and similarly labeled severity or treatment rows. Require evidence for parameterization changes and preserve valid historical assignments unless the approved contract changes them. Audit real consumers in land-use summaries, Disturbed and soil modifications, single- and multiple-OFE WEPP preparation, exports and reports. For every supported entry, verify that references resolve and templates parse. For changed assignments, inspect generated managements and representative downstream soil and WEPP input/output. Use both forest incident replays to verify the user-facing behavior under the deployed candidate.

### 2. Implement and validate the accepted changes

Exercise upload replacement, stale persisted state, true single-storm admission and reporting, status ordering after reload, and invalid climate and soils input handling. Follow the normal upload, build, and RQ job entry points. Use focused Python and frontend regressions, canonical wctl gates, and direct artifact readbacks. Test that a failed replacement or rejected batch leaves coherent state. Retain reason codes and user-visible recovery guidance. Run the RQ graph check if dependency wiring changes.

### 3. Complete the local deploy on forest

Use the installed `wctl` dev preset and the canonical full Compose deployment documented in the [development setup](../../../../../readme.md) and [forest host guide](../../../../infrastructure/homelab-tailscale.md). Verify hostname, candidate checkout, Compose preset, active jobs, and data mounts. Coordinate with shared-stack users as needed. Build and bring up the full selected development stack, including regenerated frontend assets and any required migrations. Verify the served page, RQ API and worker, status delivery, Redis, European data providers, and native tooling against the candidate. Record effective service identities, revs or image IDs, mounts, binaries and dataset versions. A targeted restart or isolated test container does not satisfy this milestone.

### 4. Rebuild autosomal-vetch through the original workflow

Create a fresh forest replay from the captured baseline inputs and record its run ID and URL. Use the normal browser controls, equivalent user authorization, and live RQ orchestration. Recreate the watershed, land cover and Disturbed configuration. Build the original gridded European soils and verify per-hillslope disposition and parsed generated soils through Disturbed and WEPP prep. Follow the captured climate operation order, checking single-storm policy and warning, E-OBS build behavior, continuous replacement, the active file actually used by WEPP, and the operation shown after reload.

Run an independent E-OBS and gridded-soil acceptance path before a later override or upload replaces its artifacts, using a companion replay if needed to preserve the original sequence. Inspect E-OBS monthly statistics and daily data, actual prepared soil and climate files, fresh hillslope and watershed output where supported, and the reports available to users. If the original gridded workflow still has an unresolved material gap, retain the rejected hillslopes and mark full acceptance open. If the replay diverges from the original inputs or workflow, record the difference and its impact on acceptance.

On the same deployed stack, replay `studded-stranglehold` with the original CORINE 2018 source and upload-to-gridded transitions. Verify that valid CORINE class 25 resolves to Mixed forest with the appropriate management, that incompatible upload mappings receive actionable feedback, and that a failed first build on a newly created project leaves its normal run page and retry controls accessible. Read back assignments, management summaries and land-use Parquet after a valid build. Verify a completed legacy fixture still receives its legitimate migration path. Keep the second replay receipt and identify any differences from the original input.

Keep a forest deployment receipt, replay manifest, job timeline, browser evidence, and parsed artifact summaries under this package. Finish with an independent correctness review and update the tracker and repository project board with only the outcomes the evidence supports.
