# ADR: SSURGO Field Capacity and Wilting Point Sanitization

Status: Accepted  
Date: 2026-07-06  
Review Date: 2026-08-06

## Context

NASA ROSES batch runs under `/wc1/batch/nasa-roses-202606-psbs/` generated WEPP soil files with invalid legacy water-content values such as `-9.9 nan` in the `fc wp` columns. WEPP hillslope jobs failed with `wepp_260606_hill` return code `-8` and a Fortran SIGFPE while reading soil input. The WEPP source uses the read values after input parsing, so this is a model-input validity issue rather than harmless parsing residue.

## Decision

WEPPcloud will treat SSURGO/WEPP field capacity and wilting point as valid only when both values are finite volumetric water-content fractions and satisfy `0 <= wp <= fc <= 1`. SSURGO horizon construction will continue to prefer SSURGO `wthirdbar_r` and `wfifteenbar_r` values adjusted for rock content, but if the resulting pair is invalid it will replace both values with Rosetta predictions and record a build note. Generic WEPP soil serialization will enforce the same rule and fail explicitly if invalid values reach it.

## Decision Provenance

Decision Venue: Codex operator session for production batch failure, 2026-07-05 22:11 PDT  
Participants Present: Roger Lew, Codex  
Decision Owner(s): Roger Lew / WEPPcloud maintainer  
Implementer(s): Codex

## Change Summary

Old behavior:
- `isfloat()` accepted strings or floats such as `nan`.
- SSURGO horizon construction could serialize invalid `field_cap`/`wilt_pt` values if source or Rosetta-derived candidates were non-finite or sentinel values.
- `WeppSoilUtil` could parse and reserialize invalid legacy `fc`/`wp` values, including during 9002 conversion.

New behavior:
- Local `fc`/`wp` validation requires finite values and `0 <= wp <= fc <= 1`.
- SSURGO generation falls back to Rosetta for the pair when SSURGO-derived values fail validation.
- `WeppSoilUtil` validates Rosetta recomputation and rejects invalid legacy values before writing 7778/900x soil rows.

## Rationale

The chosen range matches the model contract for volumetric water-content fractions and catches every observed production failure mode: `nan`, `inf`, negative sentinels such as `-9.9`, values above one, and inverted `wp > fc` pairs. Local validation avoids a broad change to `isfloat()` while giving this model-input path explicit physical semantics.

## Alternatives Considered

1. Change `wepppy.all_your_base.isfloat()` to reject `nan` and `inf` - rejected because the helper is global and may be used where "convertible to float" is the intended predicate.
2. Let WEPP fail and only document affected runs - rejected because the generated input is invalid and can be repaired deterministically before execution.
3. Drop SSURGO source water-content fields entirely and always use Rosetta - rejected because valid SSURGO water-content data remains the preferred source.

## Consequences

Valid SSURGO water-content values keep the existing parameterization. Invalid values are replaced with Rosetta estimates, which may differ from SSURGO where the source data is corrupt or sentinel-filled. If Rosetta also returns invalid values, WEPPcloud fails before writing the soil file, producing a Python error with horizon context instead of a later WEPP SIGFPE.

## Evidence

- Work package: `docs/work-packages/20260705_ssurgo_fc_wp_sanitization/package.md`
- Production failure signature: `/wc1/batch/nasa-roses-202606-psbs/` runids with `wepp_260606_hill` return code `-8` and `-9.9 nan` soil rows.
- WEPP source evidence: `/workdir/wepp-forest_260430_baseline/src/input.for` reads `thetd2`, and later water-balance paths consume derived `thetd1`/`thetfc`.
- Regression tests: `tests/soils/test_ssurgo_fc_wp_sanitization.py` and `tests/wepp/soils/utils/test_wepp_soil_util.py`.

## Risk and Rollback Notes

Risk: some unusual historical soil files with out-of-range water contents will now fail before serialization. This is intentional for WEPP model safety. Rollback is to revert the sanitizer and serializer validation commits, but rollback should only be used if validated scientific workflows require a broader water-content range and a new ADR revises the accepted bounds.

## Implementation Notes

Keep the guard local to SSURGO and WEPP soil utility code. Do not alter the global `isfloat()` helper for this incident. Production batch invalidation must remove `build_soils` and downstream task timestamps only after fixed worker code is deployed.
