# ADR-0054: Staley dNBR backend normalization

## Status and provenance

Accepted for backend implementation, 2026-09-09. Venue: user/Codex repository
session. User requested the dNBR contract and WEPPpy implementation; Codex
implements the bounded backend-first increment after stating that assumption.
Scientific direction from prior user decisions: SBS format family, differing
scales/extents, exact project alignment, and resilience to partial coverage.
Browser/NoDb/RQ publication is deferred, not implicitly approved here.

## Decision and rationale

Follow the [backend contract](../../wepppy/nodb/mods/postfire_debris_flow/docs/dnbr_upload.md).
Accept real integer and float dNBR with explicit positive scale and finite
offset. Normalize before compiled GDAL nearest sampling to Float32/NaN.
Default metadata does not infer encoding; nondefault conflicting metadata
fails. Negative/zero values survive. Nonfinite values are invalid support.
Report rather than clip ideal-range departures. Source public fixtures are
Float32 x1000, illustrating why dtype-based automatic scaling is unsound.

Nearest sampling preserves observations and source holes; bilinear/cubic
interpolation can mix values or bridge holes. Report target-cell support, not
exact source-polygon support. Partial means use observed equal-area target
cells, and normalized mean supplies M1 F directly. No double /1000, implicit
zero fill, minimum coverage cutoff, or effect on M3.

## Alternatives and limits

SBS categorical class restrictions do not apply to continuous dNBR. A 30 m
source does not become genuinely 10 m information by project-grid alignment.
Unknown dates are allowed, but supplied date order is validated. Restrict VRT
to explicit local identity wrappers and HFA/GTiff to self-contained inputs;
full VRT execution/sidecar transport requires a later boundary contract.
New completed artifact directories preserve prior results on failure without
pretending to implement concurrent NoDb publication or invalidation.

## Evidence, risk and rollback

See the active `20260908_staley_dnbr` package for fixtures, kernel comparison,
tests and independent review evidence. No predictive calibration claim.
Nearest target support can miss tiny overlaps, which fail explicitly. Callers
must validate WBT/locale readiness and own output publication. Removing this
additive backend does not require a production-state migration.
