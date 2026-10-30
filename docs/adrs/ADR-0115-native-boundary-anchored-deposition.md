# ADR-0115: Evaluate deposition from its boundary condition

- Status: Proposed; U6 combined native validation, no release or default change.
- Date: 2026-10-30.
- Decision venue: WEPPcloud Roads development conversation, America/Los_Angeles.
- Participants: project owner and Codex, with independent scientific and implementation reviewers.
- Decision owner: project owner, authorizing defect investigation and remediation.
- Implementer: Codex.

## Context

The equivalent melt/storage repairs in [ADR-0114](ADR-0114-native-equivalent-melt-support-and-storage.md)
exposed three negative-sediment cases in the frozen 840-case Roads panel. All
840 complete, but 837 pass accounting. Observation locates the first negative
load in DEPOS during a real rain event, with PHI=-1.99979949. The expanded
analytic solution stores CDEP=-798041.875 in single precision, losing the small
boundary derivative. DEPEND then incorrectly ends deposition at x=0.0001 and
DEPEQS returns +0.0625 instead of approximately -0.01464114. Negative load is
propagated by EROD; later report clipping hides it in one output product.

## Proposed decision

Carry the boundary derivative DU explicitly through ROUTE, DEPEND, DEPOS and
DEPEQS. Evaluate the existing analytic equation in double precision using
exponential divided differences, with continuous limits at PHI=-1 and -2.
Do not form or store the ill-conditioned expanded constant. DEPC remains as
an unused legacy source unit; its original formula is not used by ROUTE.

With u=xu+q, v=x+q, L=log(u/v), alpha=1+phi, beta=2+phi,
A=2*a*k and B=b*k-theta-A*q, evaluate:

`D(x) = DU*exp(alpha*L) - phi*B*L*exprel(alpha*L) - A*phi*v*L*exprel(beta*L)`.

Here `exprel(z)=(exp(z)-1)/z`, with `exprel(0)=1`. A 12-term series for
abs(z)<0.01 avoids arithmetic cancellation; this is not a fitted physical
threshold. Differentiate the governing equation for root finding. Preserve
existing endpoint adjustment, caller-specific ratio guards and UNDFLO range
convention where the legacy expression is defined. For a confirmed Newton trial at PHI=-2 and v=0, use the finite wet-side
rate 2*B; the endpoint derivative is unused by the existing caller. Root iteration limits,
convergence tolerance, sediment parameters, hydraulic formulas, output formats
and existing output guards are unchanged in the bulk solver.

## Confirmed particle-enrichment consumer (U6)

The failure-class audit also proves the expanded-boundary defect in ENRICH.
Five positive particle classes under positive outflow reproduce native traps
at class PHI=-1 and -2 (committed generator/receipt 458f8e86e). Carry the entering
class load GU into the same class-load ODE, evaluated with divided exponentials
in double precision. Preserve final nonnegative-class handling, normalization
to bulk load, available-class sediment limits, PHI caps and hydraulic inputs.

Retire the numerical approximation that drops only the homogeneous term when
its power is below 1e-8 on valid wet intervals. This approximation is nonuniform:
a tiny power multiplies an arbitrarily large expanded coefficient near the
singular values, and deleting it destroys the removable limit. Evaluate the
complete anchored integral instead, retaining integrated source terms even when
the decaying exponential underflows safely. Preserve the legacy reverse-interval
and positive-amplification arithmetic conventions outside the physical forward
wet domain; these guards are compatibility behavior, not physical validation.

This is an explicit numerical-approximation change, not a sediment calibration
threshold. Require independent raw-class ODE references, continuity around the
retired cutoff, five-class normalized output tests and renewed full-model gates.
Remaining ROUTE/EROD no-inflow expressions are distinct formulas with no proved
failure in this investigation; DEPC has no active caller.

## Rationale and alternatives

This is the same sediment equation evaluated stably, not calibration to FSWEPP2.
Simply promoting arithmetic after reading single-precision CDEP cannot recover
lost DU. Clipping negative loads would hide the producer defect. A parameter
band around PHI=-2 would leave the identical cancellation near PHI=-1 and
introduce an unnecessary switch in model behavior.

The scope includes all native ROUTE consumers, including ordinary hillslopes
and channels. Water calculations are untouched. Sediment differences outside
Roads therefore require explicit scientific assessment.

## Evidence and acceptance

Canonical native package is `docs/work-packages/20261030-roads-native-accounting/`
in `/workdir/wepp-forest-release-20261009`. Full 16-year inputs were committed
before repair (08b6860bb); the independent native cancellation probe and
70-digit reference were committed as fd7ef7d51. The original expression traps
at exact PHI=-1/-2 and produces negative loads near -2; the bounded stable
probe completes all 13 cases with maximum load error 1.36e-8.

Acceptance requires full-period nonnegative sediment, reconciliation across
ELEMENT/EBE/LOSS, water-output parity for this isolated repair, independent
boundary controls, full native tests, 840-case accounting, Disturbed and fresh
matched Cedar assessment. A passing equation probe alone is insufficient.

## Risks and rollback

The stable expression can change erosion/deposition transition positions where
rounding previously changed their sign. Preserve all diagnostic evidence and
reject unexplained regressions. Invalid geometry is not made physically valid
by retaining a legacy arithmetic guard. No installed release or Roads default
is changed; release promotion is separate. The configuration specification and
layout remain human-gated before UI implementation.
