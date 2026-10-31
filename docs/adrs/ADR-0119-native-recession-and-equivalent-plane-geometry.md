# ADR-0119: Native recession continuity and equivalent-plane geometry

Status: Accepted

Date: 2026-10-31

## Context

Roads open-boundary diagnostics found an unsupported local surface-water exchange
after removing QINF's discontinuity at `tstar=1`. EPLANE's length argument was
one-based while IRS supplied a zero-based array. Lengths were paired with the
wrong OFE hydraulic coefficients. Homogeneous probes concealed this error.

## Decision

Adopt artifact revision 3 of `wepp_261029`, correcting EPLANE's dummy bound to `SLPLEN(0:mxplan)` and
removing QINF's additional unity cutoff. Retain its documented FTEST branches,
coefficients and nonpositive-infiltration handling. Native and independent scientific validation passed on the final dated pair;
application and publication checks remain required release-delivery gates.

## Decision Provenance

Decision Venue: ongoing user/Codex workspace conversation, 2026-10-31,
America/Los_Angeles; exact conversation time not retained.

Participants Present: requesting user and Codex.

Decision Owner(s): requesting user/operator, explicitly authorizing the undeployed
261029 same-name re-release on 2026-10-31; scientific acceptance recorded in `D2-final-scientific-acceptance.json`.

Implementer(s): Codex, under authorization to investigate and remediate native defects.

## Change Summary

Previously EPLANE dummy index 1 read the caller's index 0, shifting lengths
relative to ALPHA. The repair preserves the caller's zero origin while keeping
ALPHA one-based and the existing equivalent-storage integral unchanged.
Previously QINF disabled recession loss for `tstar < 1`; the repair uses the
existing continuous FTEST solution for positive infiltration on both sides of unity.
No soil horizons, soil properties, erosion parameters or output formats change.

## Rationale

The array mismatch is directly reproducible: released source passes two of eight
integral probes; corrected source passes all eight. A separate finite-volume
reference supports the scalar recession formula across unity. Both origin-only
(U2) and combined (U3) candidates complete all twelve retained 16-year fixtures
with no negative linked total FIN or unfunded request in the observed stages.

## Alternatives Considered

1. Continuity alone: rejected for adoption because one local exchange lacks a
   demonstrated surface-water source despite sufficient soil storage.
2. Origin alone: passes the local panel but retains the independently demonstrated
   unity discontinuity; retained as a scientific control.
3. New conservative cascade solver: deferred until the smaller confirmed defect
   is repaired and revalidated.
4. Clipping or sediment tuning: does not repair the demonstrated causal defect.

## Consequences

The routines serve connected hillslopes beyond Roads. QINF also has CONRUN
(contour runoff) and WSHIRS (channel-surface runoff) callers. Runoff, peaks and sediment
may change for heterogeneous OFEs, so local success is insufficient for adoption.
Scalar-domain validation does not prove all heterogeneous or unsteady routing.

## Evidence

- [Roads program](../work-packages/20261029_roads_parameterization_program/package.md).
- Native repository: `docs/work-packages/20261031-roads-open-boundary-funding/artifacts/`,
  specifically `D2-eplane-probe.json`, `U2-analysis.json`, `U3-analysis.json` and
  `U2-U3-science-contract.md`.
- Native durable contract: `docs/contracts/hillslope-recession-geometry-contract.md`.
- Native regression: 1,095 tests, 28 permanent watchlist cases, 99 Disturbed
  tests and 840 Roads physical cases pass with the final dated pair. All 6,057
  fresh Cedar outputs exactly match the independently reviewed candidate.
- Scientific acceptance: native `D2-final-scientific-acceptance.json`, SHA-256
  `c57c39d392680fda2a2f5a72ae76b40b616a6bb5ee216ffb686c6b0a26bf8247`.

## Risk and Rollback Notes

Retain revision-2 binary backups and issued reports. Reject adoption on physical,
source-accounting or semantic regressions. Preserve U2/U3 outputs and failed
controls rather than adjusting thresholds. Revert candidate source edits if the
physical justification fails; do not mix pass files across candidate/released builds.

## Implementation Notes

Clean-build parity, native suite/watchlist, Disturbed matrix and Cedar Creek
scientific checks pass. Roads magnitude passes 744/840 cases, versus 749/840
for revision 2: this native correction does not establish parameterization success.
Cedar sediment changes by -0.02803% relative to revision 2. Dedicated full-event
CONRUN validation remains outside the retained empirical panel. Withheld
materials remain unused. Roads UI specification/layout remains human-gated.
