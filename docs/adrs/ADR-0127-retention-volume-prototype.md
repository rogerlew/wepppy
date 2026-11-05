# ADR-0127: Experimental whole-soil retention inverse

Date: 2026-11-01

## Status and provenance

Accepted for bounded experiment only; production promotion is not approved.
Decision venue: user/Codex workspace conversation,2026-11-01,America/Los_Angeles.
Participants: user and Codex; independent science and implementation AI reviewers.
Decision owner: user authorizes proceeding with the stated next experiment.
Implementer: Codex. No meeting attendees or institutional endorsement are implied.

## Context and decision

The [capacity contract](../schemas/whole-soil-water-capacity-contract.md) identifies
that SSURGO's capped mass-complement reversal differs from native volume
correction. Test an isolated preparation prototype; do not modify production
Horizon or native capacity formulas.

For complete positive original source FC/WP, direct-source preparation, original
positive density rho<2.65 and mass fraction0<=w<=.85, compute
c=2.65*(1-w)/(rho*w+2.65*(1-w)). Replace only experimental prepared FC/WP with
source fractions divided by c when0<WP/c<FC/c<1-rho/2.65. The final inequality
is a nonporous additive-volume assumption screen, not a validated retention law.
Current behavior instead divides source fractions by1-min(w,.5).

Missing, zero, fallback, invalid, above-cap and assumption-conflicted records keep
current files/status and explicit reasons. No clipping, synthetic density or
fallback change. Existing projects and uploaded soils are untouched. A future
production decision requires its own evidence-backed revision and compatibility
policy; this ADR does not authorize one.

## Rationale and alternatives

Compare actual emitted and consumed values before changing a production law.
Reject a global porosity multiplier: retention ordering does not protect drainage
denominators. Reject universal conversion of fallback/zero inputs because their
source and native semantics differ. Keep above-cap cases explicit because native
volume correction cannot be called the inverse of uncapped source conversion.

## Evidence, risks and rollback

[Prototype work package](../work-packages/20261101_retention_volume_prototype/package.md)
retains the exact panel, actual writer output, paired native histories and reviews.
Native density recomputation, air corrections and guards may prevent recovery of
source retention; initialization success cannot establish dynamic closure.
No production rollback is necessary: experimental outputs reside in a fresh
private root and cannot replace active project files. Preserve failed evidence
and reject promotion if source assumptions or consumer domains are unsupported.

## Experimental disposition

The completed bounded comparison produced42eligible prototype cases and twelve
complete histories in six pairs. Actual native retention responds, but initial absolute
water is unchanged within roundoff. The runtime skips frost processing under its
preserved configuration. Production promotion remains unapproved; native support,
density/remapping and executed dynamic-domain evidence must remain explicit.
