# Postfire Debris Flow Implementation Roadmap

Status: planning baseline after dNBR backend commit `9b99d535c`.
Production model execution, NoDb, browser upload, RQ, and dashboard integration
are not implemented. No implementation package is activated by this roadmap.

## Maintenance Contract

This is the living delivery tracker. [specification.md](specification.md) and
its named contracts remain the authority for scientific and runtime behavior.
Recommendations below are proposals until recorded as accepted decisions there.

For each implementation increment:

1. Resolve its blocking decisions in the specification and affected detailed
   contracts, including rationale and any required parameterization ADR.
2. Create an active ExecPlan for substantial work. Complete the repository's
   [contract-first checkpoint](../../../../docs/standards/contract-first-change-standard.md)
   before covered UI/NoDb/RQ implementation: operator approval, independent
   reviews, and a standalone contract ancestor commit.
3. Update this roadmap and the specification in the same change set as code.
   Distinguish accepted intent, implemented behavior, validated behavior, and
   deployment; completing one does not establish the others.
4. Record the package, implementation revision, validation evidence, remaining
   limitations, and disposition of each affected loose end here. Update the
   active package's plan and tracker before handoff.
5. Promote durable decisions into current contracts before package closure.
   Keep closed packages immutable; link them only as historical evidence.

## Completed Foundations

| Foundation | Delivered | Remaining integration |
| --- | --- | --- |
| M3 terrain | Owned WBT `D8UpstreamRelief`, bindings, analytical checks, and matched 10 m/30 m evaluation. [Contract and evidence](docs/m3_terrain.md). | Runtime invocation, binary availability, catchment sampling, and adoption/enforcement of the genuine 10 m recommendation. |
| M3 soils | Offline raw SSURGO interval/map-unit derivation and comparison with original STATSGO THICK. [Contract and evidence](docs/m3_soil_thickness.md). | SSURGO-primary/STATSGO-fallback runtime policy, acquisition/readiness, and production coverage handling. |
| dNBR | Local normalization/summary API, explicit encoding, project-grid alignment, partial coverage, provenance, and two public Arizona fixtures; `9b99d535c`. [Contract](docs/dnbr_upload.md), [validation](../../../../docs/work-packages/20260908_staley_dnbr/artifacts/validation.md). | Browser transport, authorized run paths, active-artifact publication, and freshness. |

The offline soil study's complete-only outputs are not a production coverage
gate. SSURGO primary and original STATSGO fallback are accepted source priority.
The dNBR backend is not a completed browser upload workflow.

## Delivery Sequence

Build shared scientific components, deliver a usable M1 workflow, integrate M3,
then complete the interactive dashboard. M3 soil-policy work can proceed during
M1 development; M1 does not need to wait for that policy. Both models remain in
scope. SI/English presentation belongs in the first user-facing increment.

All stages below are **not started**. Attach execution packages and evidence as
work begins; stage completion requires its exit evidence, not only source files.

| Stage | Scope and dependencies | Exit evidence |
| --- | --- | --- |
| 1. Assessment contract | Define assessment outlets, stable catchment IDs, nested upstream domains, grid/slope/SBS rules, and aggregation denominators. Proposed scope: each channel's full upstream catchment plus the watershed outlet, deduplicating identical outlets. | Accepted scope and missing-data rules; independently checked masks/counts and a reproducible fixture plan. |
| 2. Numerical engine | Implement `staley2017.py` for both M1 and M3. Can begin after its numerical contract is resolved, independently of spatial implementation. | Independently checked published coefficients, ADR, analytical cases, stable forward/inverse behavior, invalid-input and unreachable-threshold tests. |
| 3. M1 predictors | Depends on stage 1. Aggregate slope/SBS intersection, normalized dNBR, and RUSLE Nomograph K; emit coverage, reasons, and input identity. | Reproducible real-project predictor artifacts; correct intersection and full-domain denominators; partial and unavailable catchment checks. |
| 4. Rainfall and results | Compose stages 2–3 with Climate-owned event parquet and frequency artifacts. Define event identity, schemas, canonical units, and querying. | Event probabilities, ratified design scenarios and inverse thresholds; missing-scenario handling, source provenance, representative catalog benchmark, and inspectable generated outputs. |
| 5. Production M1 | Integrate stages 1–4 through NoDb, safe dNBR upload/publication, prerequisite checks, RQ, and a basic Pure UI control/report. | Contract checkpoint followed by upload → build → results → reload under production-equivalent identities/mounts; stale inputs, failed replacement, authorization, and SI/English equivalence verified. |
| 6. Production M3 | Resolve soil policy; compose SSURGO/fallback thickness and owned WBT relief with the shared engine and production workflow. Soil-policy preparation may precede stage 5. | Explicit source contribution/coverage, unusable-both-sources cases, terrain fidelity gate, and real-project M3 results through the same publication/report path. |
| 7. Interactive dashboard | Use established result/query contracts for linked events, catchment map, detail, design comparisons, and thresholds. | Event/catchment selections remain consistent; partial/unavailable results, simulation dates, unitization, accessibility, and realistic catalog performance verified. |

Recommended architecture: separate predictor preparation from rainfall
evaluation so climate changes do not require terrain/soil/dNBR recomputation.
Define exact invalidation edges in stage 5's contract. Benchmark stored results
against evaluation on demand before committing to an event × catchment ×
duration materialization strategy in stage 4.

## Loose Ends and Decision Gates

IDs are stable tracking labels, not payload fields. Close a row by linking its
accepted specification/ADR section and implementation evidence; retain any
scientific limitation that implementation cannot resolve.

| ID | Decision or remaining work | Resolve before | Current authority / status |
| --- | --- | --- | --- |
| L01 | Whole watershed versus channel upstream catchments; outlet placement, duplicate/nested domains, IDs, and map geometry. | Stage 1 completion | [Terrain and scope](specification.md#terrain-sbs-and-assessment-scope); per-channel plus outlet remains proposed. |
| L02 | Slope algorithm, SBS class mapping, unknown pixels, soil/K coverage, and independent predictor denominators. | Stage 3 implementation | [Predictors](specification.md#predictors), [dNBR](specification.md#dnbr-upload-and-processing-contract). Do not extend accepted dNBR partial-coverage policy to other predictors implicitly. |
| L03 | Coefficient verification, stable sigmoid/logit, permitted rainfall/probability inputs, zero/negative denominators, negative or unreachable thresholds. | Stage 2 implementation | [Scientific model](specification.md#scientific-model); numerical contract and ADR pending. |
| L04 | K calibration units, artifact provenance/freshness, full RUSLE versus K-only readiness, and M3's RUSLE prerequisite. | Stages 3 and 5 | [RUSLE dependency](specification.md#rusle-and-polaris-dependency). Recommend K-artifact readiness for M1 and no RUSLE prerequisite for M3; not yet ratified. |
| L05 | Soil material inclusion, horizon validity, incomplete components, fallback granularity/triggers, and residual missing coverage. | Stage 6 implementation | [M3 soil direction](specification.md#m3-soil-thickness-ssurgo-feasibility); source priority accepted, production rules pending. |
| L06 | Prepared SSURGO inventory, substituted/custom/legacy soils, STATSGO source delivery and freshness; neither source usable. | Stage 6 integration | [Soils readiness](specification.md#availability-and-soils-readiness), [soil contract](docs/m3_soil_thickness.md). No implicit soil rebuild or acquisition authority. |
| L07 | Adopt genuine 10 m M3 requirement; detect source fidelity, validate installed WBT tool/bindings, and sample accepted relief/area at assessment outlets. | Stage 6 integration | [Terrain contract](docs/m3_terrain.md). Calibration-preprocessing equivalence remains unproven; upsampling does not establish fidelity. |
| L08 | Ratify 1/2/5/10-year × 15/30/60-minute matrix, CLIGEN/NOAA selector/default, sample guidance, precision, and inverse target probabilities. | Stage 4 implementation | [Rainfall](specification.md#rainfall-sources-and-scenario-outputs). No silent source switch; NOAA is not an event catalog. |
| L09 | Stable event IDs, source/date semantics, result/export schemas, query strategy, catalog limits, and filter defaults. | Stage 4 completion | [Dashboard](specification.md#interactive-event-dashboard). Current predictor state applies to all rainfall scenarios; no recovery simulation. |
| L10 | Upload packaging, path authorization, CSRF, resource limits, replacement, concurrent builds, atomic publication, and failed-build preservation. | Stage 5 implementation | [dNBR backend contract](docs/dnbr_upload.md) plus shared transport/NoDb contracts; local backend trust assumptions do not define browser safety. |
| L11 | Exact dependency fingerprints and invalidation for DEM/routing, Soils, SBS, K, dNBR, climate, parameters, and results. | Stage 5 implementation | [Compatibility plan](specification.md#compatibility-and-validation-plan). Preserve old `debris_flow.nodb`; define additive schemas and stale-result presentation. |
| L12 | Effective CONUS locale mapping, legacy `us`, cross-boundary footprints, and server/UI prerequisite parity. | Stage 5 implementation | [Availability](specification.md#availability-and-soils-readiness). WBT/CONUS/built Soils accepted; Western US guidance is not a second regional gate. |
| L13 | Exact Unitizer categories, API normalization, export units, and age/area evidence-domain presentation. | Stage 5 implementation | [Unitization](specification.md#unitization-contract), [scientific context](specification.md#scientific-model). No new age/area rejection thresholds approved. |
| L14 | Control/feature registration, payloads, job graph, dashboard host, accessibility, and empty/partial/legacy/hostile states. | Relevant stages 5–7 implementation | [Planned organization](specification.md#planned-file-organization) and shared UI/RQ contracts; detailed runtime contracts pending. |

## Progress Log

- Baseline: terrain and soil evaluations and local dNBR backend are complete;
  remaining stages and loose ends recorded. Next work: assessment contract and
  numerical engine. No production implementation or deployment is claimed.
