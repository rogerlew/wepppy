# ADR-0026: Partial-Year Observed Climate Restoration

Status: Accepted
Date: 2026-07-26

## Context

WEPP requires complete calendar-year climate input. Current-year GridMET and
Daymet products can publish different variables through different dates. In a
GridMET multiple-interpolated production build, temperature extended through
2026-07-25 while humidity-derived dewpoint ended on 2026-07-23.

The existing GridMET loader allocated the requested year through December 31
with zeros. Those zeros were interpreted as observed radiation, wind, and
humidity. Dewpoint calculation produced NaN, while other future variables could
silently overwrite CLIGEN-generated values with zero.

CLIGEN already supports `9999` missing observed values and generates the
missing portion while retaining a complete year. The maintainer confirmed that
the generated future portion is the required workflow.

## Decision

Represent unpublished source values as missing, not observed zero. Generate a
complete calendar-year CLI with CLIGEN, then overlay each supplemental observed
variable only across its independently available finite prefix.

A variable may have a trailing missing suffix. A finite value after the first
missing value is an internal data hole and must fail explicitly with variable
and date context. If a variable is entirely unavailable, retain CLIGEN's
generated values for that variable. Do not synthesize dewpoint or other
observations in Python.

## Decision Provenance

Decision Venue: Codex API conversation, 2026-07-26 20:14 PDT
Participants Present: Roger Lew, Codex
Decision Owner(s): Roger Lew, WEPPpy maintainer
Implementer(s): Codex

## Change Summary

Old behavior: Full-year arrays were zero-filled beyond upstream availability;
post-processing attempted to overlay the entire year, either failing on NaN
dewpoint or publishing false observed zeros.

New behavior: Unpublished values remain missing through PRN generation. CLIGEN
fills the missing interval, and post-processing overlays only each variable's
finite observed prefix. The final CLI remains a complete year.

## Rationale

This preserves every published observation without fabricating observations or
discarding valid later data from another variable. CLIGEN remains the canonical
weather generator for missing observed intervals, and WEPP receives its
required complete-year input.

## Alternatives Considered

1. End the CLI on the last common observed date - rejected because WEPP requires
   a complete year.
2. Use one common cutoff for all variables - rejected because variable
   publication dates differ and valid later observations would be discarded.
3. Replace missing dewpoint with minimum temperature or zero - rejected because
   that invents an observation and changes physical assumptions.
4. Weaken the NaN guard - rejected because it would permit malformed CLI output
   and conceal source-data gaps.

## Consequences

Partial-year output after each variable's publication date is generated rather
than observed. This was already the intended CLIGEN missing-input behavior but
is now explicit and independently applied. Internal missing holes become
actionable failures. Complete historical years remain unchanged.

## Evidence

- Production run `mdobre-undimmed-cellulite`
- Jobs `a4b65525-3f23-4cc5-a5da-6690df28ab37` and
  `7e97f4f5-dec8-4fc1-83a9-86c7486e37cd`
- `docs/work-packages/20260726_climate_partial_year_cligen_hardening/`

## Risk and Rollback Notes

The primary risk is incorrectly classifying an internal source gap as future
publication lag. The contiguous-prefix rule and exact regression tests prevent
that. Rollback requires reverting the overlay/missingness changes; no persisted
schema migration is needed.

## Implementation Notes

Regression coverage must prove full-year output length, per-variable overlay,
generated suffix preservation, all-missing behavior, and internal-hole
rejection for the multiple-interpolated climate paths.
