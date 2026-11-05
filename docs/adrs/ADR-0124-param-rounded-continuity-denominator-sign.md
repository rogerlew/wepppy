# ADR-0124: Preserve the physical sign of rounded PARAM continuity denominators

Date: 2026-10-31

Status: Accepted for `wepp_261029` artifact revision 4 (2026-10-31); application delivery tracked separately.

## Decision provenance

Decision venue: Roads program agent session, 2026-10-31, America/Los_Angeles.
Participants: user and Codex; independent scientific/implementation reviewers.
Decision owner: user authorized autonomous native investigation and repair;
exact U12 scientific acceptance is complete. Implementer: Codex.

## Context and evidence

PARAM generates shear/transport polynomials across overland-flow elements.
Positive continuity quantity t is transformed as r=1/(t-1). Tiny positive t
can round away, storing r=-1 and denominator1+r=0. The existing guard chooses
+.001, producing materially negative capacity on real wet intervals.
Five exact-output-parity observations retain positive operands and34 zero
transport guard records; no zero shear occurrence was observed in those runs.
See [U12 experiment](../work-packages/20261029_roads_parameterization_program/artifacts/erod-subgrid-ablation-plan.md)
and [operand receipt](../work-packages/20261029_roads_parameterization_program/artifacts/param-continuity-u11-observation.json).

## Decision and rationale

Change only the exact-zero denominator branch, in both identical shear and
transport guards, for nonnegative first-segment slope: select-.001. Preserve
+.001 for negative first slope and preserve every nonzero denominator branch.
For t approaching zero from above, t/(t-1) approaches zero from below. A true
zero slope uses this one-sided convention. Keep the existing .001 magnitude;
this repairs the regularized sign and does not restore exact continuity.

## Alternatives considered

Reject a blanket zero-sign flip without the nonnegative-slope precondition.
Defer a larger ratio reformulation or clipped-capacity deposition solver:
first repair the demonstrated producer error and measure remaining exposure.
Do not mask the defect by renormalizing particle fractions or widening audits.

## Validation, risks and rollback

Shared PARAM affects non-Roads simulations. Require source-executed scalar
fixtures, separate shear/transport/combined seed ablations, exact-parity
observation, particle/water/soil checks,840 Roads,348 downstream,99 Disturbed,
fresh Cedar semantics and all native release gates on the final matched pair.
All evidence is experimental until those gates and independent review pass.
Rollback is to the frozen U11 research pair; shipped261029 revision3 remains
unchanged. Remaining varying-negative capacity exposure blocks acceptance.

## Revision-4 acceptance

The exact combined pair is scientifically accepted and installed under the existing
release name. Source `b01a739957bef5aacf35b4a89bc13eddc9d94804` matches all
489 retained build inputs. See the [scientific acceptance](../work-packages/20261029_roads_parameterization_program/artifacts/param-u12-scientific-acceptance.json)
and [revision-4 delivery](../work-packages/20261029_roads_parameterization_program/artifacts/revision4-vendoring.json).
The shared native repair applies beyond Roads; it does not accept Roads parameter
defaults or claim universal numerical accuracy. Historical experimental outcomes
below/above retain their original scope.
