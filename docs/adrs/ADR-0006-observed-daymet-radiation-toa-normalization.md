# ADR: Observed-Daymet Radiation TOA Normalization

Status: Accepted
Date: 2026-06-06
Review Date: 2027-06-06

## Context

Observed-Daymet climate production for
`/wc1/runs/in/indispensable-presenter` generated daily solar radiation values
that downstream openWEPP rejected before WBVAL03 could reach its
snowmelt/water-balance validation surface. The observed failure was:
`CLIM-RUNTIME-E-017`, `radly=486`, with the accepted domain
`0 <= radly <= baseline sunmap horizontal daily potential (rpoth/r3)`.

WEPPpy's observed-Daymet single-location producer converts Daymet daylight
average `srad(W/m^2)` to `srad(l/day)` using `srad * dayl / 41840`, then writes
that value into the WEPP CLI `rad` field. Static evidence showed the generated
CLI values match Daymet-derived `srad(l/day)` after integer publication
rounding. For `indispensable-presenter`, 53 of 2191 rows exceeded the baseline
`sunmap.r3` daily potential at the CLI latitude.

## Decision

For observed-Daymet climate publication, WEPPpy will normalize only genuine
over-TOA daily radiation rows before writing generated WEPP CLI radiation:

- compute the baseline `sunmap.r3` horizontal daily potential in Langleys/day
  from day-of-year and CLI latitude using the legacy `sunmap` formula and solar
  constant `1.94 Ly min^-1`;
- when Daymet-derived `srad(l/day)` exceeds that bound, publish the bound
  instead of the over-bound source value;
- leave all non-over-bound rows unchanged;
- preserve original source values in the exported Daymet parquet with explicit
  provenance columns;
- write a `daymet_radiation_toa_normalization_<label>.csv` artifact listing
  affected dates, original values, computed bounds, normalized values, excess,
  latitude, and reason.

This rule applies to the observed-Daymet single-location and interpolated
producer helpers that write Daymet radiation into generated CLI `rad`.

## Decision Provenance (Required for Parameterization Changes)

Decision Venue: Codex user request thread, 2026-06-06 20:55 UTC
Participants Present: User, Codex
Decision Owner(s): User / WEPPcloud operator request
Implementer(s): Codex

## Change Summary

Old behavior:

- observed-Daymet `srad(l/day)` was copied into CLI `rad` without checking
  against the baseline daily radiation potential;
- over-TOA Daymet rows reached downstream openWEPP and failed there with
  `CLIM-RUNTIME-E-017`.

New behavior:

- observed-Daymet `srad(l/day)` is compared to baseline `sunmap.r3` using the
  CLI latitude and day-of-year;
- rows above `sunmap.r3` are bounded to `sunmap.r3`;
- provenance columns and CSV artifact preserve the original source value and
  the exact bound used.

## Rationale

Daily radiation above top-of-atmosphere horizontal potential is physically
invalid for the WEPP CLI boundary. Normalizing at the WEPPpy producer boundary
keeps openWEPP fail-closed guards intact while preventing known invalid
source rows from blocking downstream validation and operation.

Using baseline `sunmap.r3` avoids an arbitrary clamp. It matches the downstream
contract that rejected the values, keeps the unit in Langleys/day, and preserves
auditability through explicit artifacts.

## Alternatives Considered

1. Relax openWEPP's radiation guard - Rejected. The guard encodes the
   downstream physical invariant and should remain fail-closed.
2. Treat genuine over-TOA Daymet values as an external-source HOLD - Rejected.
   The source defect is normalizable to a physical upper bound at the WEPPpy
   producer boundary with clear provenance.
3. Fail closed before CLI publication - Rejected for this source class because
   bounded normalization preserves operational observed-Daymet workflows while
   retaining evidence.
4. Clamp to a fixed numeric threshold - Rejected. The physically valid maximum
   depends on day-of-year and latitude.

## Consequences

- Positive:
  - Observed-Daymet CLI publication no longer emits radiation above the
    downstream TOA bound.
  - Affected values remain auditable through parquet provenance columns and CSV
    artifacts.
  - openWEPP source-bound guards can remain strict.
- Risks:
  - Normalized rows alter source climate forcing for affected dates.
  - The bound uses CLI metadata latitude, matching downstream consumption, even
    though Daymet retrieval may use watershed centroid latitude.
  - Reviewers must distinguish this bounded normalization from silent clipping.

## Evidence

- Work package:
  `docs/work-packages/20260606_indispensable_presenter_daymet_radiation_bounds/package.md`
- Initial evidence:
  `docs/work-packages/20260606_indispensable_presenter_daymet_radiation_bounds/artifacts/initial_radiation_evidence.md`
- Execution evidence:
  `docs/work-packages/20260606_indispensable_presenter_daymet_radiation_bounds/artifacts/execution_evidence.md`
- openWEPP downstream contract evidence:
  `/workdir/openWEPP/docs/specifications/science-contracts/contracts/SC-CLIMATE-001.md#inv-climate-013`

## Risk and Rollback Notes

Monitor observed-Daymet climate builds for unexpected numbers of normalized
rows. If normalization proves too broad or the bound is later revised, rollback
is to remove the normalization helper and return to source-value publication,
which will again let downstream guards fail closed on over-bound rows.

## Implementation Notes

- Production implementation:
  `wepppy/nodb/core/climate_build_helpers.py`
- Regression coverage:
  `tests/nodb/test_climate_build_helpers.py`
- Normalization artifact naming:
  `daymet_radiation_toa_normalization_<label>.csv`
- Parquet provenance columns:
  - `srad_source(l/day)`
  - `srad_toa_bound(l/day)`
  - `srad_toa_normalized`
  - `srad_toa_normalization_reason`
  - `srad_toa_bound_latitude(deg)`
