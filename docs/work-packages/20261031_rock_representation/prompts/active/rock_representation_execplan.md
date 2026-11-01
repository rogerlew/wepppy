# Investigate and develop volumetric and surface rock support

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Keep Progress, Surprises & Discoveries, Decision Log and Outcomes & Retrospective current.

## Purpose / Big Picture

Users need rock inputs to retain their physical meaning through soil data, model preparation and erosion/hydrology consumers. The previous Roads audit found a RUSLE unit error, missing preferred surface proxy production and distinct native profile/surface pathways. This package delivers verified dimensional corrections and a reusable evidence basis for later scientifically justified model development, without conflating lower sediment with correctness.

## Progress

- [x] (2026-11-01 03:45 UTC) Read prior audit and subsystem/validation instructions; create package on existing branch.
- [x] M1: independent scientific and implementation review of canonical quantity/basis contract.
- [ ] M2: literature/data-source and source-consumer evidence matrix; quantitative diagnostics.
- [ ] M3: reproduce and repair RUSLE SoilGrids unit error with real raster/manifest tests.
- [ ] M4: verify SoilGrids-to-WEPP mass basis, develop any demonstrated correction and read generated soils.
- [ ] M5: investigate native capacity and permanent surface-cover feasibility; retain counterexamples and bounded next experiments.
- [ ] M6: focused/broad validation, independent correctness/science review, immutable evidence, checkpoint.

## Context and Orientation

`wepppy/nodb/mods/rusle/c_integration.py` reads optional surface columns or SoilGrids cfvo; K integration already treats recognized SoilGrids cfvo as per-mille. `wepppy/locales/earth/soils/isric/__init__.py` normalizes SoilGrids values then constructs ISRICHorizon. `wepppy/soils/ssurgo/ssurgo.py` derives mass fragments and retention data. Native WEPP INPUT/SCON consume mass fractions, cap rock and derive effective volume; crop surface cover is residue-dependent while range has explicit rock inputs.

Prior immutable source-free evidence is under `docs/work-packages/20261029_roads_parameterization_program/artifacts/{rock-cover-audit-r4,buffer-capacity-physical-review-r4,buffer-storage-ownership-r4}`. Native exact-build sources remain private in retained response roots; no source or binary change is necessary for a preprocessing repair. New derived evidence uses fresh directories under `out/rock-representation-20261031/`. Do not consume the six withheld Roads materials.

## M1: contract and design checkpoint

Create `docs/schemas/rock-fragment-representation-contract.md` with explicit units, denominator, density basis, spatial/depth/time support, conversion assumptions, null/zero distinction and model limits. Record parameterization decisions in ADR-0125. Classify RUSLE repair against its existing /10 contract; independently review any newly specified generated-soil conversion before implementation. Commit contracts and two read-only reviews as an ancestor. Operator instruction authorizes investigation/development and demonstrated dimensional corrections, not unvalidated parameter promotion.

## M2: evidence and quantitative investigation

Read primary USDA/ISRIC model/data documents and original studies on fragment water retention. Inventory consumers including coarse fragments, cover, roughness, consolidation, infiltration, storage and erosion. Quantify mass-volume round trips over bounded density/fragment grids, surface-overlap bounds and available retained-profile capacity margins. Distinguish observed, reconstructed, source-supported and unknown evidence. Preserve counterexamples instead of clipping them away.

## M3: RUSLE repair

Write failing regression using real GeoTIFF input and actual C output/manifest for RAP and SBS, both supported cfvo paths, low/100/high stored values, valid mask/nodata, absent source and explicit override. Correct only unit conversion for the recognized SoilGrids raw/aligned paths, preserving source priority, proxy interpretation and fallback. Reuse existing stack; no new raster framework. Retain fresh output evidence.

## M4: generated profile basis

Trace ISRICHorizon through HorizonMixin serialization and native input interpretation. If cfvo volume is emitted directly as native mass, reproduce it, implement the density-explicit conversion in the smallest owned location and test zero, normal, extreme and invalid inputs. Native assumes mineral fragment density 2.65 g/cm3; make that assumption explicit and do not silently infer surface area. Preserve format and 200 mm boundary. Validate actual builder output and native interpretation before claiming correct downstream propagation; retain native caps as limits, not a new default. If source density support is unavailable, reject conversion rather than invent density.

## M5: native development feasibility

Use retained 586 initialization layers to test capacity ordering and coordinate invariance under the proposed static whole-soil basis. Examine freeze/thaw and all consumers before any native behavior trial. Derive surface-overlap bounds and a field sampling/data acquisition specification including fragment size, lithology, role, exposed versus total cover and uncertainty. Assess permanent crop rock protection versus residue evolution; do not emulate rock with biomass or switch landuse. Deliver explicit experiment specifications and unresolved scientific prerequisites, not a speculative production engine change.

## M6: validation and handoff

Use `wctl run-pytest` focused modules then `wctl run-pytest tests --maxfail=1`, test-stub checks and scoped doc lint. Read generated raster pixels, metadata and serialized soil tokens; tests that mock the failed boundary are insufficient. Obtain independent correctness and scientific reviews, resolve medium/high findings, retain evidence hashes and archive without active writers. Update tracker, current program links and all living plan sections. Commit reviewable changes; do not deploy.

## Surprises & Discoveries

Initial inspection identifies `ISRICHorizon.rfg = horizon_d['cfvo']` despite cfvo being normalized volume percent. This is a candidate cross-consumer basis defect requiring serializer/native confirmation. SSURGO field/wilting retention uses a separate mass-fragment heuristic; audit its source basis before any change.

## Decision Log

2026-11-01: use one cross-cutting package, with separate observational/scientific and production-conformance claims. Rationale: the same word rock currently spans incompatible quantities; repairing one consumer must not imply validation of every heuristic. No new dependencies or infrastructure.

## Outcomes & Retrospective

Execution active. Completion will report implemented and validated corrections separately from model research requiring field evidence, native scalar gates or full-period physical validation. No overall WEPP rock-physics or Roads acceptance claim is authorized by this package.

## Recovery and reproducibility

Refuse existing experimental output directories. Never mutate frozen studies or original projects during verification. Keep source and generated-output hashes. Rebuild only disposable fixtures; rollback production corrections by reverting their commit, not rewriting previous evidence.
