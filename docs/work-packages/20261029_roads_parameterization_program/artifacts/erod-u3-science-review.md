# Independent EROD U3 scientific review

Disposition: **U3 remains rejected/unpromoted**. The shared stable integration
closes the retained stiff examples and correctly handles an interior-first
stiffness trigger, but confirmed capacity-boundary failures require U4/U5
validation. This review concerns RUNGE SHA
`0d39a1b545f5f8fe3f60ba54d0e8592c1d799504bcf8772cfc5d56b18e06f658`
and EROD SHA
`1d4f3351013472eecffd0d5800bb47da5a814566221d4617a51159c1679c1ea3`.
Later working-tree edits are not implicitly accepted by this review.

## Positive findings

The source evaluates all three RK stage locations before provisional-load
arithmetic, restarts fallback from the original full anchor, handles zero
capacity before the stiffness division, retains the native exponent, and
restores the endpoint detachment cache before returning. These implement the
requested common-state and anchoring contracts.

Independent observed-source probes span linear-capacity origin D values
0.001,0.01,0.1,1,10,100. All match their analytic regular solution at the expected
single-real accuracy. Accepted final refinement counts range4–16,384; wall time
including process startup is about1.7–5.5ms in this probe environment. This is
bounded scalar evidence, not a full-model performance result.

An interior-first stiffness case uses shear x,capacity1,theta0,eata1000,
XB0.00001,XE0.009,L00.0007. Sampled z values are0.00417,0.24522,0.38897:
the initial stage is below the switch and the midpoint triggers it. Native load
0.208908394 agrees with analytic0.208908371682; native dl34.2284966 agrees with
analytic34.2284945931. It required4,096 final midpoint steps. This independently
checks full-anchor restart and restored endpoint state.

Stiff grid-containing D1/D10 transitions now agree with the independent ODE
reference within the tests' stated floating-load/root tolerances. Root-coordinate
accuracy is limited by single-real load rounding; bounded bisection alone is
not a claim of exact coordinate ULP accuracy.

Probes, source hashes, native results, expected values and work counts are in
`/tmp/erod-u3-science-probes.json`; executable probe is
`/tmp/review_u3_probes.py`.

## Confirmed blockers

1. Implementation review established false convergence for
   C=max(0,x−0.008),D1,theta0,L00,XE0.009: early midpoint refinements can miss the
   positive-capacity tail entirely. Analytical transport-root partitioning is
   required before relying on endpoint convergence. ROUTE's critical-shear
   partitions do not partition the separate capacity polynomial.

2. Independent closing-capacity probe C=0.009−x,D1,theta0,L00,XB0,XE0.009
   fails with `RUNEXP failed endpoint convergence` after3.83s. Its exact regular
   solution is L=(0.009−x)*log(0.009/(0.009−x)); deposition begins at
   0.009*(1−exp(−1))=0.005689085029457018. Seeking convergence of the continued
   detachment solution at the singular zero-capacity endpoint is unnecessary
   after a guaranteed earlier crossing. Evidence is retained in
   `/tmp/erod-u3-closing-capacity.json`.

3. The synthetic tiny-capacity state C1e-42,L00.0007,theta0.1,D0 orD1e-42
   still SIGFPEs. A stiffness-only criterion cannot catch every unsafe load/capacity
   ratio. The smallest supported handling is strict initial-excess classification
   before eager integration, together with explicit unsafe-ratio dispatch for
   provisional stages if those remain in supported scope. This is a synthetic
   arithmetic edge, not production-frequency evidence.

## U4/U5 review conditions

Splitting stable integration at at most two transport polynomial roots, while
retaining the same whole-interval refinement loop and final convergence criterion,
is a narrow response to the missed-tail case. It needs no new length-weighted
per-piece tolerance; tiny active pieces otherwise receive unnecessarily severe
budgets. Include tangent/zero-root and tail controls.

At a zero-capacity trial endpoint, establishing a guaranteed deposition bracket
without integrating a singular post-transition continuation is sound when positive
load/supply is proved on the preceding prefix. Positive incoming load or theta
suffices. With both zero, a nonempty positive-C piece with positive detachment
before that endpoint also suffices; ROUTE already supplies a critical-shear-sign-
consistent interval. Upstream D alone is insufficient because it can be exactly
zero at a critical-shear boundary and positive immediately afterward. Positive
supply after the trial coordinate cannot justify an earlier bracket.

Check the final adjacent-coordinate branch too: it must not re-enter RUNGE at a
zero-capacity high endpoint after all such trial evaluations were intentionally
avoided. Retain valid load provenance and explicitly test a transition rounding
to that endpoint. No fictitious endpoint loads should be published.

Mandatory controls include the closing case above; closing C with D initially0
then positive; a C0-positive-0 hump; a zero-capacity plateau before a positive tail;
all-zero source/load; and finite strictly positive initial excess. Fresh scalar
and broad gates remain necessary. The0.1 dispatcher rationale remains limited to
constant-coefficient homogeneous-factor error; it is not a universal load,
root-coordinate, or global error bound.

## U5 follow-up and U6 design boundary

Independent rerun of the U5 source suite:55passed. Reviewed hashes at that
checkpoint were EROD122f56d173977dbe7acf983b59ca7e93ad90ce0017bb82135be85c43a8350036
and RUNGE35496c2dd96cdd598df25e126ef87dce6609a797bcf0120cfba27b6bfe18f8a0.
The capacity-tail and closing-endpoint controls pass. Subsequent review identified
an internal closing/reopening interval that needs first-transition detection;
passing these55 tests is not whole-candidate acceptance.

The proposed U6 event-piece helper has a direct equation rationale. With
`y=L-C`, `y'=-(D/C)y+theta-C'` on positive-C support. After splitting at capacity
zeros and C'=theta, an integrating factor makes its residual monotone on each
piece. There is at most one crossing per piece (identically-zero forcing/residual
is equality throughout, not a positive crossing). Carry actual upstream load
between pieces and stop at the first positive residual. Existing critical-shear
partitioning remains supplied by ROUTE. This is a bounded extension for the
confirmed first-transition failure, not a new sediment law.

U6 also needs actual-stage arithmetic protection. The tiny-C SIGFPE was reproduced
with VALID initial detachment states L00 andL05e-43, both belowC1e-42,theta0.1,D0.
The stage2 provisional load overflows `(C-L)/C`; the exact pre-transition law is
L=L0+theta*x. Early initial-excess classification cannot fix this class. When D0,
use the exact derivative theta without evaluating the meaningless ratio; for
nonzero D, dispatch unsafe actual stage quotients before division, retaining the
original full-step anchor. Ordinary safe arithmetic can remain unchanged.

Strict initial-excess classification requires a separate caller-boundary ablation.
ROUTE currently overwrites DU with0 before DEPOS, assuming the reported transition
is an equality point. Returning XB with Lbeg>Cbeg while leaving this behavior
would initialize deposition at capacity rather than actual incoming load. DEPOS
uses `L=C-DU*(x+qostar)/phi`; preserving the excess would require the matching
nonzero upper deposition rate under a valid wet-domain contract. Do not bundle
that change implicitly or claim mass preservation from returning LD alone.

Proceed diagnostically with U6 for valid incoming detachment L<=C. Keep the
initial-excess fixtures explicitly unresolved and promotion blocked pending a
separate EROD→ROUTE→DEPOS continuity decision/test. ROUTE has no same-segment
backward jump from the NDEP path to DEPEND: it calls DEPOS to segment end and
advances the finite segment loop. That rules out the specifically suggested
same-coordinate-loop mechanism in current source, but does not prove correct
load transfer. Full model output validation remains required.
