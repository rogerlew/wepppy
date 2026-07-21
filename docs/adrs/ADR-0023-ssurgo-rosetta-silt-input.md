# ADR-0023: SSURGO Rosetta Silt Input

Status: Accepted
Date: 2026-07-21
Review Date: 2026-08-21

## Context

The `plastic-bundling` production run generated 85 SSURGO Rosetta FC/WP
fallback failures. SSURGO's `sandvf_r` (very-fine sand) was being passed to
Rosetta as silt, so texture fractions did not sum to 100 and Rosetta returned
the invalid `fc=-9.9`, `wp=nan` sentinel pair. The FC/WP sanitizer correctly
rejected that pair. Soil construction continued with valid map units, as
intended.

## Decision

For SSURGO and shared horizon Rosetta predictions, derive silt as
`100 - total_sand - clay`. Validate that sand, silt, and clay are finite,
non-negative percentages summing to 100 before calling Rosetta. Continue to
use `sandvf_r` only for WEPP erodibility calculations, where very-fine sand
is the required input.

## Decision Provenance

Decision Venue: Codex operator session, 2026-07-21, America/Los_Angeles
Participants Present: Roger Lew, Codex
Decision Owner(s): Roger Lew / WEPPcloud maintainer
Implementer(s): Codex

## Change Summary

Old behavior passed `(total sand, very-fine sand, clay)` to Rosetta. New
behavior passes `(total sand, derived silt, clay)` and rejects malformed
texture triples before prediction. Bulk-density estimation when SSURGO bulk
density is absent uses the same derived silt value.

## Rationale

Rosetta requires mutually exclusive sand, silt, and clay fractions. Very-fine
sand is a subset of total sand, not the silt fraction. Derivation from the
two SSURGO total texture fields provides the physically complete triple and
recovers valid Rosetta predictions for the observed production data.

## Alternatives Considered

1. Pass `sandvf_r` as silt — rejected because it double-counts sand and can
   leave the texture fractions short of 100.
2. Bypass FC/WP validation — rejected because it permits invalid Rosetta
   sentinel values into WEPP inputs.
3. Stop a whole soil build on an invalid map unit — rejected; retaining valid
   map units and reporting individual invalid soils is the intended behavior.

## Consequences

Missing SSURGO texture fields continue to use the existing defaults, but
Rosetta now receives their derived silt remainder. Existing generated soils
must be rebuilt after deployment because Rosetta-derived hydraulic values may
change.

## Evidence

- Production run: `/wc1/runs/pl/plastic-bundling/soils.log`, 2026-07-21.
- Regression tests: `tests/soils/test_ssurgo_fc_wp_sanitization.py` and
  `tests/wepp/soils/test_horizon_mixin.py`.
- Related guardrail: [ADR-0012](ADR-0012-ssurgo-fc-wp-sanitization.md).

## Risk and Rollback Notes

The change affects only Rosetta calls and bulk-density estimation that uses
Rosetta's texture preparation. Invalid texture data remains an explicit
per-soil failure. Roll back by reverting this ADR and its implementation only
if validation against representative SSURGO data shows the derived silt
contract is incorrect.
