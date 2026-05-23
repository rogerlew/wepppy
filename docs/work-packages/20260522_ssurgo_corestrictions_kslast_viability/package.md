# SSURGO Corestrictions `kslast` Viability Assessment

**Status**: Closed 2026-05-23  
**Timezone**: UTC

## Closeout Summary

- Delivered reproducible national + ecoregion viability artifacts under `artifacts/`.
- Recommendation outcome: `retain legacy` (no production `ssurgo.py` change in this package).
- Major execution caveat: several ecoregion restrictive-present quotas were constrained by SDA extraction/runtime limits during this run; this is an infrastructure constraint, not a claim of missing underlying SSURGO records.

## Overview

This package defines and executes a national assessment of whether SSURGO `corestrictions` fields can support a physically reasonable WEPP restrictive-layer parameterization for `kslast`, and whether that approach should replace or augment the legacy heuristic currently implemented in `wepppy/soils/ssurgo/ssurgo.py`.

The package focuses on evidence quality, cross-ecoregion representativeness, and side-by-side comparison against the current legacy behavior.

## Objectives

- Quantify availability and completeness of candidate SSURGO bedrock/restriction fields needed for parameterizing `kslast`.
- Evaluate whether observed field values are physically plausible and internally consistent for WEPP restrictive-layer semantics.
- Compare candidate `corestrictions`-driven parameterizations against the legacy `kslast` behavior in representative U.S. ecoregions.
- Produce a decision-ready recommendation (`adopt`, `adopt with guardrails`, or `retain legacy`) with explicit uncertainty and risk notes.

## Scope

### Included

- A normative assessment specification with reproducible methods ([spec.md](spec.md)).
- Coverage and quality diagnostics for:
  - `corestrictions.reskind`, `resdept_r`, `resdepb_r`, `resthk_r`, `reshard`
  - `muaggatt.brockdepmin`
  - `chorizon.ksat_r` (as conductivity anchor)
- Ecoregion-stratified sampling across diverse U.S. hydroclimate and parent-material regimes.
- Candidate parameterization formulas/rules for experimental evaluation only.
- Legacy-vs-candidate comparison metrics for WEPP inputs and hydrologic response outputs.
- A recommendation artifact and follow-up implementation guidance.

### Explicitly Out of Scope

- Changing default production `kslast` behavior in `ssurgo.py` within this package.
- Full national recalibration of WEPP hydrology beyond restrictive-layer treatment.
- UI or API contract changes.
- Replacing SSURGO as the source soil dataset.

## Stakeholders

- **Primary**: WEPPpy soil/hydrology maintainers.
- **Reviewers**: SSURGO pipeline maintainers, WEPP domain reviewers.
- **Security Reviewer**: Not required for this assessment-only package.
- **Informed**: Model operators and analysts consuming WEPP hydrograph behavior.

## Success Criteria

- [x] Ecoregion matrix finalized with at least 10 distinct U.S. ecoregions and documented sampling rationale.
- [x] Coverage/completeness report produced for all candidate fields (national + per-ecoregion sampled denominators).
- [x] Reasonableness checks executed with explicit pass/fail criteria and anomaly catalog.
- [x] At least two candidate `corestrictions` parameterization strategies evaluated against legacy.
- [x] Legacy-vs-candidate comparison completed for representative sampled cohorts across selected ecoregions (full WEPP run-fixture hydrograph reruns deferred to follow-up).
- [x] Final recommendation published with guardrails, residual risks, and implementation go/no-go conditions.

## Dependencies

### Prerequisites

- Access to NRCS SDA tabular endpoint for SSURGO queries.
- Existing WEPPpy SSURGO build path and benchmarkable run fixtures.
- Reproducible execution environment for targeted WEPP comparisons.

### Blocks

- Any production cutover package to replace legacy restrictive-layer parameterization.

## Related Packages

- **Related**: [20260421_disturbed_mofe_9002_soils](../20260421_disturbed_mofe_9002_soils/package.md)
- **Related**: [20260513_ebe_pw0_peak_runoff_regression_ablation](../20260513_ebe_pw0_peak_runoff_regression_ablation/package.md)
- **Follow-up**: TBD infrastructure + hydrologic-validation package to resolve SDA extraction constraints and execute full run-fixture hydrograph validation.

## Timeline Estimate

- **Expected duration**: 3-6 focused sessions.
- **Complexity**: Medium-High.
- **Risk level**: Medium (scientific/modeling risk, low security risk).

## Security Impact and Review Gate

- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: Assessment work touches data extraction, analysis, and documentation only; no auth/session/input-surface changes are planned.
- **Security review artifact**: `N/A`

## References

- [wepppy/soils/ssurgo/ssurgo.py](../../../wepppy/soils/ssurgo/ssurgo.py) - Current restrictive-layer and `kslast` implementation.
- [wepppy/soils/ssurgo/ssurgo.md](../../../wepppy/soils/ssurgo/ssurgo.md) - SSURGO conversion docs and `kslast` history.
- [wepppy/wepp/soils/horizon_mixin.py](../../../wepppy/wepp/soils/horizon_mixin.py) - Conductivity/anisotropy equations.
- [spec.md](spec.md) - Assessment protocol, ecoregion matrix, and decision framework.

## Deliverables

- [x] Assessment protocol and matrix ([spec.md](spec.md)).
- [x] Data extraction + QA artifacts under `artifacts/`.
- [x] Ecoregion-stratified legacy vs candidate comparison report.
- [x] Recommendation memo and implementation gating checklist.

## Follow-up Work

- Outcome is negative for production cutover in this package (`retain legacy`); keep current `ssurgo.py` behavior.
- Open a follow-up package focused on infrastructure-constrained regional extraction and fixed run-fixture hydrologic validation.
- Revisit candidate adoption only after those follow-up gates are complete.
