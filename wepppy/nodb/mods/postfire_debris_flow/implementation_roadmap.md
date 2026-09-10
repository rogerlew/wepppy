# Postfire Debris Flow Implementation Roadmap

Status: planning baseline after dNBR backend commit `9b99d535c`.
Production model execution, NoDb, browser upload, RQ, and dashboard integration
are not implemented. The watershed/engine package completes stages 1–2 with an independently
reviewed and validated offline numerical API.

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

## Next Scoped Increment

[Local M1 predictor integration](../../../../docs/work-packages/20260909_staley_m1_predictors/package.md)
is implemented and validated locally with complete authentic Wallow evidence. It
composes the completed slope/SBS and dNBR
backends with RUSLE Nomograph K; see [accepted contract](docs/m1_predictors.md).
K policy is accepted in ADR-0059. Complete synthetic and authentic T/F/S outputs
and missing-input cases exist. Climate composition and production publication
remain successor work. Completed backend contracts are not reopened.

## Next Rainfall/Results Increment

The [rainfall/results package](../../../../docs/work-packages/20260909_staley_rainfall_results/package.md)
is scaffolded, not executing, for local M1 stage 4. Its
[proposed contract](docs/rainfall_results.md) covers events, design comparisons,
inverse thresholds and bounded local queries. L08/L09 remain pending until
source/sample policies and schemas are accepted. No production UI/RQ scope.

## Delivery Sequence

Build shared scientific components, deliver a usable M1 workflow, integrate M3,
then complete the interactive dashboard. M3 soil-policy work can proceed during
M1 development; M1 does not need to wait for that policy. Both models remain in
scope. SI/English presentation belongs in the first user-facing increment.

Stages 1–2 are **complete**, in the
[project watershed and numerical engine package](../../../../docs/work-packages/20260908_staley_watershed_engine/package.md).
Stage 3 slope/SBS local backend is **implemented and validated**, in the
[WBT slope/SBS package](../../../../docs/work-packages/20260908_staley_slope_sbs/package.md).
Local stage 3 composition is **complete**, including authentic complete-source
evidence. Later stages are **not started**. Stage completion requires its exit evidence,
not only source files. Accepted scope is the existing project watershed/outlet;
nested/channel assessments are excluded from initial delivery (ADR-0055).

| Stage | Scope and dependencies | Exit evidence |
| --- | --- | --- |
| 1. Assessment contract | Reuse the existing project watershed and resolved outlet; document authoritative mask/grid/outlet identity and full contributing-area support. Track slope/SBS/NoData decisions for stage 3. | Accepted single-watershed scope (done); canonical artifact mapping and independently checked mask/outlet evidence (done). |
| 2. Numerical engine | Implement `staley2017.py` for both M1 and M3. Can begin after its numerical contract is resolved, independently of spatial implementation. | Complete: checked coefficients, ADR-0056, 145 focused tests, six-row generated examples, independent review and full-suite validation. |
| 3. M1 predictors | Depends on stage 1 and accepted slope/SBS/NoData rules. Aggregate slope/SBS intersection, normalized dNBR, and RUSLE Nomograph K over the project watershed; emit coverage, reasons, and input identity. | Reproducible real-project predictor artifacts; correct intersection and full-domain denominators; partial and unavailable watershed checks. |
| 4. Rainfall and results | Compose stages 2–3 with Climate-owned event parquet and frequency artifacts. Define event identity, schemas, canonical units, and querying. | Event probabilities, ratified design scenarios and inverse thresholds; missing-scenario handling, source provenance, representative catalog benchmark, and inspectable generated outputs. |
| 5. Production M1 | Integrate stages 1–4 through NoDb, safe dNBR upload/publication, prerequisite checks, RQ, and a basic Pure UI control/report. | Contract checkpoint followed by upload → build → results → reload under production-equivalent identities/mounts; stale inputs, failed replacement, authorization, and SI/English equivalence verified. |
| 6. Production M3 | Resolve soil policy; compose SSURGO/fallback thickness and owned WBT relief with the shared engine and production workflow. Soil-policy preparation may precede stage 5. | Explicit source contribution/coverage, unusable-both-sources cases, terrain fidelity gate, and real-project M3 results through the same publication/report path. |
| 7. Interactive dashboard | Use established result/query contracts for project watershed events, detail, design comparisons, and thresholds; maps may show the existing basin and input coverage. | Event selections remain consistent; no nested catchment selector; partial/unavailable results, simulation dates, unitization, accessibility, and realistic catalog performance verified. |

Recommended architecture: separate predictor preparation from rainfall
evaluation so climate changes do not require terrain/soil/dNBR recomputation.
Define exact invalidation edges in stage 5's contract. Benchmark stored results
against evaluation on demand for the project event × model × duration catalog
in stage 4. There is one assessment watershed per project.

## Loose Ends and Decision Gates

IDs are stable tracking labels, not payload fields. Close a row by linking its
accepted specification/ADR section and implementation evidence; retain any
scientific limitation that implementation cannot resolve.

| ID | Decision or remaining work | Resolve before | Current authority / status |
| --- | --- | --- | --- |
| L01 | Scope resolved: existing project watershed and existing outlet. Confirm canonical artifact mapping; no new outlet selection or nested enumeration. | Stage 1 completion | [Accepted scope](specification.md#project-watershed-assessment-scope), [ADR-0055](../../../../docs/adrs/ADR-0055-staley-project-watershed-scope.md); [artifact audit completed](../../../../docs/work-packages/20260908_staley_watershed_engine/artifacts/watershed_artifact_audit.md). |
| L02 | Slope algorithm, SBS class mapping, unknown pixels, soil/K coverage, and independent predictor denominators. | Stage 3 implementation | [Slope/SBS backend](docs/slope_sbs.md) and both WBT bindings validated; Horn, raw DEM, strict edges and uncertainty preservation recorded (ADR-0058). Full K coverage without additional fill is accepted in ADR-0059; partial K remains diagnostic. |
| L03 | Coefficient verification, stable sigmoid/logit, permitted rainfall/probability inputs, zero/negative denominators, negative or unreachable thresholds. | Stage 2 implementation | Resolved in [engine contract](docs/staley2017_engine.md) and [ADR-0056](../../../../docs/adrs/ADR-0056-staley-numerical-engine.md), including review fixes for adjacent targets and inverse underflow. |
| L04 | K calibration units, artifact provenance/freshness, full RUSLE versus K-only readiness, and M3's RUSLE prerequisite. | Stages 3 and 5 | [RUSLE dependency](specification.md#rusle-and-polaris-dependency). M1 K-artifact readiness and identity scale are accepted in ADR-0059; production freshness enforcement and M3 requirements remain separate. |
| L05 | Soil material inclusion, horizon validity, incomplete components, fallback granularity/triggers, and residual missing coverage. | Stage 6 implementation | [M3 soil direction](specification.md#m3-soil-thickness-ssurgo-feasibility); source priority accepted, production rules pending. |
| L06 | Prepared SSURGO inventory, substituted/custom/legacy soils, STATSGO source delivery and freshness; neither source usable. | Stage 6 integration | [Soils readiness](specification.md#availability-and-soils-readiness), [soil contract](docs/m3_soil_thickness.md). No implicit soil rebuild or acquisition authority. |
| L07 | Adopt genuine 10 m M3 requirement; detect source fidelity, validate installed WBT tool/bindings, and sample accepted relief/area at assessment outlets. | Stage 6 integration | [Terrain contract](docs/m3_terrain.md). Calibration-preprocessing equivalence remains unproven; upsampling does not establish fidelity. |
| L08 | Ratify 1/2/5/10-year × 15/30/60-minute matrix, CLIGEN/NOAA selector/default, sample guidance, precision, and inverse target probabilities. | Stage 4 implementation | [Rainfall](specification.md#rainfall-sources-and-scenario-outputs). No silent source switch; NOAA is not an event catalog. |
| L09 | Stable event IDs, source/date semantics, result/export schemas, query strategy, catalog limits, and filter defaults. | Stage 4 completion | [Dashboard](specification.md#interactive-event-dashboard). Current predictor state applies to all rainfall scenarios; no recovery simulation. |
| L10 | Upload packaging, path authorization, CSRF, resource limits, replacement, concurrent builds, atomic publication, and failed-build preservation. | Stage 5 implementation | [dNBR backend contract](docs/dnbr_upload.md) plus shared transport/NoDb contracts; local backend trust assumptions do not define browser safety. |
| L11 | Exact dependency fingerprints and invalidation for DEM/routing, Soils, SBS, K, dNBR, climate, parameters, and results. | Stage 5 implementation | [Compatibility plan](specification.md#compatibility-and-validation-plan). Preserve old `debris_flow.nodb`; define additive schemas and stale-result presentation. |
| L12 | Effective CONUS locale mapping, legacy `us`, cross-boundary footprints, and server/UI prerequisite parity. | Stage 5 implementation | [Availability](specification.md#availability-and-soils-readiness). WBT/CONUS/built Soils accepted; Western US guidance is not a second regional gate. |
| L13 | Exact Unitizer categories, API normalization, export units, and age/area evidence-domain presentation. | Stage 5 implementation | [Unitization](specification.md#unitization-contract), [scientific context](specification.md#scientific-model). Area policy accepted: warn outside inclusive 0.2–8 km²; never hard-fail solely for area. ADR-0057; warning propagation/presentation remain to implement, age policy remains open. |
| L14 | Control/feature registration, payloads, job graph, dashboard host, accessibility, and empty/partial/legacy/hostile states. | Relevant stages 5–7 implementation | [Planned organization](specification.md#planned-file-organization) and shared UI/RQ contracts; detailed runtime contracts pending. |

## Progress Log

- 2026-09-09 UTC: owner selected a nonblocking warning outside the manuscript's
  inclusive 0.2–8 km² study range, for both models. Accepted in the specification
  and ADR-0057; use full unrounded watershed area and preserve model results.
  Add warning propagation in stage 4 and user-facing presentation in stage 5.
  The completed scalar engine has no area input and remains unchanged.

- 2026-09-09 UTC, post-closeout owner decision: the supplied manuscript is
  authoritative for the study's 0.2–8 km² catchment range. Corrected the
  unsupported 0.02 km² lower bound in the specification and retired the
  source-reconciliation caveat. This updates evidence-domain guidance only;
  no engine parameter or area gate changes. See
  [Published Coefficients and study context](specification.md#published-coefficients).

- Baseline: terrain and soil evaluations and local dNBR backend are complete;
  remaining stages and loose ends recorded. Next work: assessment contract and
  numerical engine. No production implementation or deployment is claimed.

- 2026-09-09 04:18 UTC: owner selected the existing project watershed/outlet and
  manual isolation of suspected burned basins. Removed the per-channel proposal
  from initial scope; synchronized the specification and dashboard description.
  First package scaffolded for stages 1–2; numerical policies remain proposed in
  its decision register. No executable implementation started.

- 2026-09-09 04:33 UTC: verified publication coefficients and equations; audited
  existing Topanga watershed in the container (49,917 cells, outlet included,
  matching grids and unchanged hashes). Stage 1 mapping is now documented in
  the specification. Stage 2 contract is drafted in
  [staley2017_engine.md](docs/staley2017_engine.md), explicitly proposed pending
  N01–N04 owner resolution; engine implementation and final review remain.

- 2026-09-09 UTC: owner approved N01–N04; implemented pure scalar engine,
  generated synthetic examples for six model/duration rows and passed 145
  focused tests. Independent correctness review resolved adjacent-baseline
  cancellation and inverse underflow; no open findings. Full-suite validation
  and package closeout are running. L01/L03 are resolved; L02 and L04–L14 remain.

- 2026-09-09 UTC closeout: stages 1–2 complete. Full suite passed 7,959 tests
  with 72 skips; final focused suite passed 145. Container fixture and synthetic
  example reproduction, API/stub and docs gates passed; plan archived and board
  moved to Done. See [validation](../../../../docs/work-packages/20260908_staley_watershed_engine/artifacts/validation.md).
  Stage 3 starts with slope/SBS/K unit/support policy; stages 3–7 remain pending.

- 2026-09-09 05:08 UTC: scaffolded owned WBT slope/SBS package for part of
  stage 3. Initial source inspection distinguishes FVSlope, Florinsky and Horn;
  Horn/raw DEM recommendation requires evidence and policy disposition. No
  nested catchments, new M1 resolution gate or runtime wiring introduced.

- 2026-09-09 UTC: owner explicitly adopted Horn 3×3 (ADR-0058). Raw DEM,
  edge handling and incomplete-support behavior remain pending; comparisons
  now characterize the selected method rather than reselect its algorithm.

- 2026-09-09 UTC: owner accepted uncertainty preservation for slope/SBS.
  Unknown intersection cells retain T bounds and unavailable point T; no
  partial-support extrapolation. Verified the supplied pysheds link describes
  routed drop/distance, not Horn; it is not calibration-parity evidence.

- 2026-09-09 UTC: [historical USGS evidence](docs/historical_slope_evidence.md)
  confirms ArcGIS planar/Horn-style slope in the preserved 2022-named workflow.
  The modern directional helper follows a 2023 migration; its predictor
  compatibility is a suspected regression to investigate. Original 2017
  calibration method is still unconfirmed. Do not use current pfdf as M1 T oracle.

- 2026-09-09 UTC: completed the local StaleySlopeSbs Rust backend, both bindings,
  60 analytical and 24 security CLI checks, six-terrain panel and independent
  reviews. [Validation and limitations](../../../../docs/work-packages/20260908_staley_slope_sbs/artifacts/validation.md).
  Stage 3 remains partial: K integration, normalized dNBR composition and
  production predictor preparation/orchestration are successor work. No binary
  installation or deployment was performed.

- 2026-09-09 15:06 UTC: [local M1 predictor package](../../../../docs/work-packages/20260909_staley_m1_predictors/package.md)
  scaffolded for remaining local stage-3 composition. See the
  [accepted contract](docs/m1_predictors.md). Covers WBT-compatible prepared
  inputs, independent T/F/S support and provenance. K unit verification,
  coverage policy and artifact-only readiness remain decision gates. Execution
  has not started; live publication and UI/RQ remain stage 5 work.

- 2026-09-09 execution: owner accepted P02/P03, recorded in ADR-0059. Local
  adapter and 50 boundary tests implemented; actual binary generated synthetic
  complete and authentic `strained-mod` missing-dNBR bundles. Correctness findings
  closed. Full suite: 8,016 passed, 72 skipped; API/stub/docs gates passed.
  Stage 3 remains open for authentic complete
  source evidence. No production publication or climate integration claimed.

- 2026-09-09 UTC: owner rebuilt Wallow using final polygon SBS. Matching June 23
  dNBR and rebuilt Nomograph K yield full T/F/S support on 12,973 cells, zero
  unknown intersections and explicit scenario outputs. Local stage 3 acceptance
  is complete; area applicability warning retained. Production wiring remains
  stage 5 scope.

- 2026-09-10 05:15 UTC: reviewed completed M1 contract/validation and authentic
  Wallow acceptance; scaffolded local rainfall/results package. Climate CSV
  rounding, missing-column zeros and sparse-duration rank clamping are explicit
  decision gates. Review is read-only, not a new correctness/security signoff.
