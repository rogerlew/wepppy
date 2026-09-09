# ADR-0059: Local M1 prepared predictor composition

Status: accepted, 2026-09-09.

## Context and decision

Compose existing local engines without upstream mutation. Use named POLARIS
Nomograph K with multiplier 1 on the customary USLE scale. Point S requires
full basin coverage of finite K in [0,1], matching the producer's range; zero
remains valid. Preserve partial mean/coverage as diagnostics; no extra filling.
Require K provenance independently of R/LS/C success. Completed WEPP Soils
remains a production prerequisite; this local file adapter cannot establish it.
Missing legacy provenance leaves the corresponding predictor unavailable.
Retain upstream depth, gap-fill and fragment choices, without claiming measured
STATSGO equivalence or freshness from a newly computed digest.

## Rationale and alternatives

The [unit audit](../work-packages/20260909_staley_m1_predictors/artifacts/k_unit_audit.md)
supports identity conversion. SI conversion or another division by 100 changes
the calibration scale. Partial K extrapolation is not justified by dNBR's
separate partial-support rule. Unrelated RUSLE factors add no K evidence.
EPIC, STATSGO and WEPP erodibilities are not implicit substitutions.

## Decision provenance

- Venue: repository task conversation, 2026-09-09, America/Los_Angeles.
- Participants: requesting repository owner and Codex.
- Owner: requesting owner, replying "proceed as recommended" to P02/P03.
- Implementer: Codex.
- Change: previously unimplemented composition gains these rules; upstream
  parameterizations and production workflows remain unchanged.

## Evidence, risk and rollback

See the [package](../work-packages/20260909_staley_m1_predictors/package.md).
POLARIS estimates are not empirically proven equivalent to calibration STATSGO.
Full numeric support is not full measured support. Retire the local adapter or
revise this ADR if source/unit evidence changes; no persisted migration occurs.
