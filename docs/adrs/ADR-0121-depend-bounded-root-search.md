# ADR-0121: Bound failed DEPEND root searches to the physical segment

Status: Accepted for `wepp_261029` artifact revision 4 (2026-10-31); application delivery tracked separately.

## Context

A generated Roads fill-conductivity experiment exposes a native overflow in
DEPEND. Newton trials leave the physical [0.05,1] segment and reach 7.24766e32.
An independently integrated deposition equation has an interior root at
0.050115891779652795. Tuning soil parameters to avoid this state would conceal
the numerical defect. DEPEND is shared by hillslope and watershed ROUTE calls,
so any accepted repair applies beyond Roads.

## Decision and exact change

Retain the existing deposition equation, convergent Newton calculations and
endpoint conventions. For positive flow, a step outside the segment, a zero
usable derivative or exhausted ten-iteration budget invokes a bracketed fallback.
ROUTE supplies DU<0 and DEPEND checks a nonnegative segment-end rate. Bisection
uses the unchanged DEPVAL equation until its endpoints are adjacent representable
single-precision coordinates, then returns the non-depositing side. It introduces
no fitted physical tolerance. Existing convergent searches retain their 0.001
rate tolerance. Check quotients in double precision before single-real division;
apply existing decreasing-flow clamps before overflowing conversion when needed.

## Rationale and alternatives

A finite physical root must not fail because of an unconstrained search step.
Changing deposition physics, weakening floating-point traps or changing soils
would not address the demonstrated defect. Replacing every convergent legacy
search would create broader output changes without evidence that they are needed.
A whole-segment clamp alone prevents escape but can stagnate away from the root;
bisection guarantees representable interval progress for the confirmed bracket.

## Evidence and acceptance

See the [active ablation plan](../work-packages/20261029_roads_parameterization_program/artifacts/depend-root-ablation-r3-plan.md).
Native fixture and source tests live in `wepp-forest` under
`tests/fixtures/roads_native_accounting/depend/` and
`tests/test_deposition_stable_solution.py`. The pre-repair scalar test traps;
113 deposition tests now pass, including independent 80-digit general-equation
roots, float32 neighbors, terminal/absent roots and a synthetic decreasing-flow
overflow control. The full failing run now completes and passes artifact audits.
Broad Roads, native regression, Disturbed, Cedar and independent reviews remain
required; this ADR does not accept a release or Roads parameter set.

## Risks and rollback

Previously unconverged searches can change sediment outputs. Compare complete
outputs and physical accounting, not process completion alone. Current fallback
assumes the physical positive-flow bracket supplied by ROUTE; legacy decreasing-
flow non-root conventions remain distinct. Preserve matched binary pairs and
portability changes. Keep shipped revision 3 unchanged during ablation. Reject
or revise the candidate if broad physical/semantic gates fail; no deployed state
needs rollback. Withheld soil materials and the UI human approval gate are unchanged.

## Decision provenance

Decision venue: ongoing user/Codex repository session, 2026-10-31,
America/Los_Angeles. Participants: user and Codex; independent reviewer assesses
the solver candidate. Decision owner: user authorized autonomous defect ablation
and remediation; final candidate acceptance remains conditional on recorded gates.
Implementer: Codex. No separate meeting or stakeholder approval is inferred.

## Revision-4 acceptance

The exact combined pair is scientifically accepted and installed under the existing
release name. Source `b01a739957bef5aacf35b4a89bc13eddc9d94804` matches all
489 retained build inputs. See the [scientific acceptance](../work-packages/20261029_roads_parameterization_program/artifacts/param-u12-scientific-acceptance.json)
and [revision-4 delivery](../work-packages/20261029_roads_parameterization_program/artifacts/revision4-vendoring.json).
The shared native repair applies beyond Roads; it does not accept Roads parameter
defaults or claim universal numerical accuracy. Historical experimental outcomes
below/above retain their original scope.
