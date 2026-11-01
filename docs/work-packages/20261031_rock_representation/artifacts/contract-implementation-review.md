# Independent implementation contract review

Reviewer: `/root/rock_contract_impl`. Date: 2026-11-01 UTC.
Starting implementation: `7d7d8c72e`. Status: **PASS for bounded development checkpoint**. This is pre-implementation approval, not implementation or deployment acceptance.

## Source-to-consumer confirmation

- `c_integration.py:312-315` selects /10 only when the footprint maximum exceeds100. Both recognized raw/aligned paths carry SoilGrids stored units; K's recognized paths use fixed /10. The proposed C repair restores the existing dimensional contract without changing proxy precedence, normalization or explicit override.
- ISRIC `extract_soil_data` divides cfvo by10 and bdod by100. `ISRICHorizon.__init__:339` assigns this volume percentage directly to rfg. `HorizonMixin.__str__:258` serializes rfg as the eleventh token of7778 horizons; ISRIC `build_soil` writes that string. Exact retained native INPUT548-551 reads that token into RFG, caps it at85 and divides by100; SCON233-234 converts mass to volume. The volume-to-mass correction therefore addresses an actual basis mismatch.
- Native INPUT also bounds supplied density to0.8-2g/cm3; HorizonMixin prints density with one decimal and RFG with one decimal. Generated-artifact/native interpretation checks must quantify these existing rounding/clamping limits rather than claim exact arbitrary-volume round trips. The canonical contract already requires reporting native cap/recomputed-density limits; these are additional concrete instances.

## Scope and valid states

The operator's general investigation/development instruction supports these demonstrated dimensional repairs. No new surface law, native capacity change, global parameter tuning, deployment or automatic old-project rewrite is included. Proposed arithmetic validation is appropriate: optional absent/all-nodata C ancillary retains fallback, populated recognized data is converted, explicit user controls remain unchanged, and invalid mandatory profile conversion values fail before soil publication. No new security or IO boundary is introduced.

The plan correctly separates real raster/manifest tests from mocked arithmetic and requires real builder serialization/native interpretation. New units metadata is additive; no public columns, native formats or saved keys are removed. Same-branch operation and unrelated dirty work are preserved. Two independent contract reviews and the standalone ancestor checkpoint must exist before implementation.

## Bounded failure-class peer assessment

Searches of Python consumers for cfvo/fragvol and rfg/smr find no second direct SoilGrids volume-to-mass assignment outside ISRICHorizon. RUSLE K already fixes recognized SoilGrids scale; C's RAP and SBS modes share the faulty loader and must both be covered. SSURGO computes its RFG from mass-based sieve fields; fetched fragvol metadata is not substituted into this path.

SIFT is an unresolved peer: `wepppy/locales/canada/bc/soils/sift/sift.py:449` returns COFRAG directly and serializes it into RFG. The inspected local code does not establish COFRAG's mass/volume basis. Obtain primary BC metadata before declaring it correct or changing it. This does not block the confirmed SoilGrids repairs but must remain in the investigation matrix and prevents class-wide closure.

## Findings and disposition

No high/medium contract blockers. Retain SIFT source-unit uncertainty and native density formatting/clamp limits in the research evidence and final review. Production acceptance remains contingent on failing-before/passing-after real artifact tests, full required gates and independent final correctness/scientific review. This review does not certify field rock density or surface-cover priors.

## Reviewed document identities

- `docs/schemas/rock-fragment-representation-contract.md`: `041b2ddca2b51799557cd6168ee7f794dca1aac7fe57ff63b717450b2d2bcd4c`
- `docs/adrs/ADR-0125-rock-fragment-unit-and-basis-repairs.md`: `9bce86d29dec7018d72ec1b62e2ce814ef938143011a45293167d5f827218a82`
- `docs/work-packages/20261031_rock_representation/artifacts/contract-decision.md`: `0fbbaf8284fb6f7e12c1d45e219901f1fd6f8466a4010630288050c7b86e5e48`
