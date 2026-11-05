# ADR-0122: Integrate EROD intervals without an output-grid point

Date: 2026-10-31

Status: Accepted for `wepp_261029` artifact revision 4 (2026-10-31); application delivery tracked separately.

## Accepted implementation (U12 combined source)

Earlier lane descriptions below are retained as rationale, not alternative
accepted implementations. Current EROSTEP covers both grid and grid-free paths,
partitioning at capacity zeros and C'=theta. With Y=L-C on positive capacity,
Y'=-(D/C)Y+theta-C'; each partition has one forcing sign and can contain at
most one transition. Stop at the first crossing before integrating through a
closing-capacity singularity. Preserve the actual upstream coordinate/load and
return the supported native coordinate adjacent to the crossing.

RUNGE retains ordinary RK4 arithmetic, with stage/quotient checks before the
separately reviewed exponential-midpoint continuation. Stable integration splits
at capacity roots, refines the entire supported interval, restores the endpoint
detachment cache and fails explicitly on nonconvergence. Shared DEPCAP64 and
DEPCAP distinguish double integration from once-rounded native load comparison.
The exact source and scalar references define the implementation; all historical
counterexamples remain regressions. This is not a new sediment production law.

The two residual strict fraction flags are now explained by source-observed
binary32 operations and rigorous operation-derived bounds; their failed audit
predicates remain unchanged. See the [scientific certificate](../work-packages/20261029_roads_parameterization_program/artifacts/fraction-arithmetic-scientific-disposition.md).
No ENRICH renormalization or new tolerance is part of this proposal.

## Context

Exact-parity source observations establish that EROD returns without advancing
sediment load for a nonempty physical interval ending before its next output-grid
point. The next interval starts downstream with the unchanged load. Later ENRICH
mixing counts the full interrill contribution, clips a negative rill residual and
can produce fractions above one. This occurs in the ordinary generated Roads
baseline as well as downstream conductivity experiments; it predates DEPEND G1.

## Decision and exact delta

The candidate integrates a nonempty grid-free interval from its actual XB and
upstream load using the existing RUNGE equation. Preserve the explicit terminal
flow convention. If the endpoint remains below transport capacity, return the
integrated load and existing detachment-rate definition. If it crosses capacity,
locate the transition within the interval by bisection to adjacent float32
coordinates, evaluating the same RUNGE solution from the fixed upstream state.
An already depositing upstream state returns that endpoint. The ordinary
interval containing output-grid points retains its existing code path.

The normalized physical domain ends at1. An ilast101 state can have only a
zero-width remainder in this domain; this decision does not add extrapolation
beyond the final grid. No soil parameter, transport equation, interrill/rill
coefficient, particle normalization or output format changes.

## Rationale and alternatives

Output-grid placement must not delete physical integration support. Normalizing
ENRICH fractions or altering SLOSS concentrations would conceal the omitted
bulk contribution. Blindly adding a missing interrill amount would still omit
rill detachment and any transport-capacity transition. Replacing all EROD grid
integration would broaden numerical changes beyond the confirmed failure.

## Evidence and gates

See [the declared interval-support ablation](../work-packages/20261029_roads_parameterization_program/artifacts/erod-subgrid-ablation-plan.md)
and [exact source observations](../work-packages/20261029_roads_parameterization_program/artifacts/particle-erod-observation.json).
Six source-based tests fail before repair. Eighteen initial regression cases
pass afterward, including independent constant-source and constant-coefficient
ODE references, transition roots, float32 grid neighbors and wet-domain controls.
Full seed, particle closure, native, Roads/downstream, Disturbed, fresh Cedar,
and independent reviews are required before acceptance. Existing gate failures
remain visible and block promotion.

## Risks and rollback

Previously omitted support can increase sediment and alter where deposition
begins. This is shared hillslope/watershed logic, not Roads-only behavior.
Retain the isolated DEPEND G1 pair and unchanged shipped revision3 pair so each
mechanism can be compared independently. Revert the EROD candidate if its
scientific gates fail; do not loosen physical or magnitude criteria. Withheld
materials and human UI specification/layout approval remain protected.

## Decision provenance

Venue: ongoing user/Codex repository session,2026-10-31,America/Los_Angeles.
Participants: user,Codex,and independent review agents. Decision owner: user
provided broad authority for native defect investigation/remediation; candidate
acceptance remains conditional on recorded scientific gates. Implementer: Codex.
No separate meeting, field calibration or institutional endorsement is inferred.

## Review amendment — U1 rejected, U2/U3 experimental

The original restriction to the grid-free path is superseded by reproduced
shared-path failures. U1 passes broad execution but fails independent roots.
U2 uses one fixed upstream coordinate/load in the grid and grid-free transition
search, returns the upstream endpoint only for strict load excess, and leaves
RUNGE unchanged. It closes nine expanded scalar failures; six stiff roots remain.
U3 stable integration is separately proposed and requires scientific review.
No candidate or parameter default is accepted. Two strict fraction-sum flags
also remain open. See the active ablation plan for exact evidence and gates.

## Numerical continuation — U3 through U5

U3 switches stiff RUNGE steps to exponential midpoint integration of the same
linear ODE. Sample dx*D/C in double at RK stage locations; above0.1 restart
from the original upstream state. The threshold bounds constant-coefficient
homogeneous RK4 amplification error only, not general load/root error. Keep
ordinary arithmetic otherwise. Restore the endpoint detachment cache.
Whole-interval endpoint convergence uses single epsilon and the actual
load/source scale, with explicit bounded failure; no arbitrary absolute floor.

Independent review rejected U3 because coarse midpoints can both miss a
positive-capacity tail. U4 splits at analytic transport-polynomial zeros.
Independent review then rejected eager continuation to a closing zero-capacity
endpoint: a valid deposition crossing can precede that singular endpoint.

U5 proves positive supply on each trial's upstream prefix before requesting
zero-endpoint integration, using the same capacity-root partition. It locates
the earlier transition without publishing a fabricated endpoint load. When
the transition bracket is only one native coordinate apart and the high
coordinate has zero capacity, return the supported low coordinate and its
actual load. ROUTE retains its critical-shear interval partition.

The current55 scalar references pass, including both rejected failure families;
full-period seeds, broad gates, synthetic initial-excess arithmetic and two
strict fraction-sum discrepancies remain under review. This is an experimental
shared numerical change, not an accepted Roads calibration. All lanes retain
separate sources and evidence; production revision3 remains the comparator.

## Shared capacity evaluation amendment

Independent valid-domain fixtures confirm that mixing single polynomial
evaluation with double integration shifts roots, invents transitions, and
loses sediment at DEPOS reconstruction. The proposed shared evaluator uses
double Horner arithmetic followed by one deliberate REAL rounding for
comparisons/reported native loads. Stable integration uses the unrounded
double value. Apply it to EROD transition decisions and every confirmed
DEPOS capacity reconstruction; test equality-throughout and actual caller
continuity. This changes numerical evaluation, not the capacity polynomial.

## Revision-4 acceptance

The exact combined pair is scientifically accepted and installed under the existing
release name. Source `b01a739957bef5aacf35b4a89bc13eddc9d94804` matches all
489 retained build inputs. See the [scientific acceptance](../work-packages/20261029_roads_parameterization_program/artifacts/param-u12-scientific-acceptance.json)
and [revision-4 delivery](../work-packages/20261029_roads_parameterization_program/artifacts/revision4-vendoring.json).
The shared native repair applies beyond Roads; it does not accept Roads parameter
defaults or claim universal numerical accuracy. Historical experimental outcomes
below/above retain their original scope.
