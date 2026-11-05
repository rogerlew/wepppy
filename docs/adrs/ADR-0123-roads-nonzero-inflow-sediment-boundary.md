# ADR-0123: Preserve actual sediment load at nonzero inflow

Date: 2026-10-31

Status: Accepted for `wepp_261029` artifact revision 4 (2026-10-31); application delivery tracked separately.

## Context

Actual ROUTE/EROD/DEPOS execution confirms that the abs(qostar)<.0011
no-inflow approximation can discard incoming sediment at small, nonzero
flow. For qostar=.001, incoming load.01, constant capacity.001, phi2 and
zero local sediment source, first-grid load is.001 instead of the independent
.0010743802 reference. The ordinary qostar1 control preserves incoming mass.
This is shared routing logic; applicability extends beyond Roads.

## Decision

Use the no-inflow limiting boundary only for exactly zero normalized inflow.
For nonzero supported flow, compute the initial deposition rate from the
actual incoming load and flow: DU=phi*(C-L)/qostar. Evaluate the arithmetic
in double before converting to the existing native argument type. Preserve
output formats and the separate exactly-zero formula. No erodibility, soil,
transport law or particle renormalization change is proposed.

## Rationale and alternatives

Zero flow and small flow carrying sediment have different boundary conditions.
An arbitrary near-zero band cannot justify replacing the incoming sediment
state. Returning initial excess from EROD while ROUTE still supplies DU0
would retain the same loss. Altering reported concentrations would conceal it.
The existing source comment already distinguishes zero from nonzero inflow.

## Evidence and acceptance

The active [EROD ablation plan](../work-packages/20261029_roads_parameterization_program/artifacts/erod-subgrid-ablation-plan.md)
retains exact actual-source fixture traces and hashes. Freeze valid positive
and negative flow, zero-flow, former-threshold-neighbor and ordinary controls
before execution. Require actual ROUTE→DEPOS load continuity and independent
solutions, not only a scalar rate calculation. Full physical/magnitude, native,
Disturbed, fresh Cedar and independent review gates remain required.

## Risks and rollback

The removed approximation may affect any configuration with small nonzero
inflow. Extreme rates must remain explicitly diagnosed rather than silently
clamped. A scientifically valid rate not representable by the current native
type requires separate evidence and review. Retain isolated pre-change pairs
and unchanged shipped261029 revision3 for exact comparison. No default or
release has been accepted; withheld soils and the UI human gate remain intact.

## Decision provenance

User/Codex repository session,2026-10-31,America/Los_Angeles. The user
authorized autonomous native defect investigation/remediation and scientific
review. Codex implements the ablation; independent agents review the actual
source and outputs. This proposed decision has no external endorsement and
is not an accepted release authorization.

## Transition handoff amendment (U9)

The same actual-load boundary condition applies where EROD returns a native
coordinate adjacent to a deposition root. Unconditionally passing DU0 resets
load to capacity at that coordinate; an actual-chain fixture confirms a30ppm
jump after the larger polynomial-cancellation error is repaired. For finite
wet XDBEG+qostar, compute DU=phi*(C(XDBEG)-L)/(XDBEG+qostar). Preserve
small positive rates from the supported side of the coordinate bracket;
clipping them to zero would recreate the jump. At an exactly zero denominator,
equality retains DU0 and the existing regular limit. Unequal load there is
explicitly unrepresentable and must fail diagnostically, never lose mass
silently. Reached real dry-terminal cases remain release blockers until
explained or repaired. Fifteen actual-chain controls pass this candidate.

## Wet-coordinate contract amendment (U11)

A confirmed legacy DEPEQS guard moves coordinates by a fixed1e-6 when
abs(X+qostar)<1e-7, which can leave the physical interval and corrupt incoming
load. The candidate removes that mutation. DEPOS owns exact negative-flow
terminal load/rate zero; strict wet points retain their actual coordinate.
Direct DEPEQS exact negative-terminal rate requests fail explicitly because
the rate can diverge while the load has a finite dry limit. The regular
zero-inflow origin is evaluated explicitly; DEPEND's separate root-search
terminal contract remains. Tests include supported Case4 flow near terminal,
negative settling-parameter limits and geometry readback, not only dry export.

## Revision-4 acceptance

The exact combined pair is scientifically accepted and installed under the existing
release name. Source `b01a739957bef5aacf35b4a89bc13eddc9d94804` matches all
489 retained build inputs. See the [scientific acceptance](../work-packages/20261029_roads_parameterization_program/artifacts/param-u12-scientific-acceptance.json)
and [revision-4 delivery](../work-packages/20261029_roads_parameterization_program/artifacts/revision4-vendoring.json).
The shared native repair applies beyond Roads; it does not accept Roads parameter
defaults or claim universal numerical accuracy. Historical experimental outcomes
below/above retain their original scope.
