# EROD interval-support ablation

Status: source observation complete; behavioral ablation declared, not accepted.
Continue the active Roads program. DEPEND G1 remains an isolated, unpromoted
candidate, with 1142 native tests, 28 watchlist cases, 99 Disturbed tests and
840+348 prior physical audits passing. Its expanded particle audit fails on
pre-existing discrepancies; no gate is waived.

## Confirmed source behavior

The six full-period observer replays (three ENRICH/SLOSS and three extended
EROD/RUNGE) have exact ordinary-output parity. In the ordinary development seed
site/1718465/inveg/paved/high on 2005 day309, terminal-OFE EROD receives
[0,0.00941210799], next grid0.00999999978, initial load0.000691379304 and
interrill theta0.00120668847. It returns without a RUNGE call or load update.
The following interval starts at0.00941210799 with the same load. The omitted
interrill contribution alone is0.00001135748219. ENRICH later sees a negative
rill residual and clamps it, producing fraction sum1.00601828. The preceding
2005day308 event does not omit an interval and stays normalized.

The buffer-cap secondary seed on 2012day302 similarly omits [0,0.00999037083],
with theta0.0189505089: minimum omitted load0.0001893226113. Its original-buffer
control has no omitted interval. Exact traces and hashes are in
`particle-erod-observation.json` and the three observation receipts. These
observations identify a missing bulk integration interval; do not repair only
ENRICH normalization or SLOSS output.

## Frozen single-mechanism candidate

Promote source-based EROD fixtures before repair. Add an empty-grid interval
path that advances the bulk solution from XB to XE, preserves actual wet-domain
limits, and locates a deposition transition if one occurs inside the interval.
Retain the existing grid-containing path and governing RUNGE/deposition equations.
No thresholds, coefficients, soil inputs or particle renormalization changes.
An interval containing no publication grid point is still physical support.
Any case outside the scientifically established wet interval must retain the
existing explicit terminal/non-root behavior, not be silently extrapolated.

## Required tests and execution

Independent constant-source reference: with zero rill detachment and positive
transport capacity above the load, L(XE)=L(XB)+theta*(XE-XB). Test the observed
widths, float32 neighbors around0.01, internal intervals between adjacent grid
points, intervals after the final grid index, zero-width intervals and wet/dry
terminal handling. For a constant capacity C crossed by interrill addition,
reference transition is XB+(C-L(XB))/theta. Test correct root location and
in-domain trials. General nonzero-rill cases need independent ODE references.

Execute matched full-period ordinary and downstream seed/controls, then repeat
all840+348 inventories and expanded particle normalization/class-mass audits.
Retain any unresolved mismatch, including small-source thresholds, as a failed
physical gate. Run native regression/watchlist, Disturbed and fresh matched Cedar
hillslope/watershed semantic/particle/source checks before promotion. Independent
scientific and implementation review required. Keep failed/incomplete runs in
denominators. Create the parameterization ADR before merge. Retain portability,
withheld materials, unchanged production defaults and the UI human gate.

## U1 rejection and predeclared U2/U3 lanes

U1 closes all class-versus-bulk discrepancies across 135765 EVENT rows in
840 Roads and348 downstream runs, but two strict fraction-sum flags remain.
Water/soil outputs match G1 for all1188 cases. The original1160 native tests,
99 Disturbed cases and full24-year Cedar execution pass; these do not override
independent counterexamples. U1 is rejected for promotion. Four new scalar
tests fail: two stiff constant-coefficient roots and two initial-equality
followed-by-later-crossing roots. The stiff defect also reproduces in the
existing grid-containing path (see erod-grid-failure-class.json).

U2 changes transition selection only: use strict initial load excess, preserve
the actual upstream coordinate and load for every trial, and bisect the same
residual in both grid-containing and grid-free paths. Freeze RUNGE unchanged.
Target: both equality cases and constant-source grid/partial-interval roots
pass; retain stiff failures as expected, not waived.

U3 is a separate proposed integration lane, contingent on scientific review:
use an exponentially fitted midpoint solution of the same linear load ODE for
stiff steps, refining the whole interval until endpoint loads converge. Keep
ordinary RUNGE arithmetic for nonstiff steps. This is numerical integration,
not a transport-capacity or erodibility change. Dispatcher and error criterion
require explicit rationale and independent variable-coefficient references.

Both lanes have boundary_disposition=requires_scientific_review. Existing
physical/magnitude criteria remain frozen. Stop promotion on any unresolved
scalar, physical, or non-target gate. Retain rejected candidates and results.

### U3 numerical contract

Scientific design review supports a narrow dispatcher, not a universal error
guarantee. Evaluate sampled stiffness dx*D/C in double before provisional RK
arithmetic, checking C<=0 before division. For stiffness above0.1, restart
from the full original anchor and use exponential midpoint sweeps. The0.1
switch bounds only constant-coefficient homogeneous RK4 amplification error
(exp(.1)*.1^5/120 below single epsilon); it does not bound load/root/global
error. Refine whole-interval endpoint loads against single epsilon times
max(abs(initial),abs(final),abs(theta*dx)); explicit failure after2^24 steps.
Restore native endpoint detachment cache before returning. Retain the native
single-real0.666667 shear exponent. No interrill floor in the stable path:
the analytic ODE determines the load used for transition bracketing.

Initial34 scalar references pass U3, including all six stiff roots. Expanded
43 references pass, adding linear-capacity origin families, variable-shear
analytic load AND returned-detachment checks, and dispatcher neighbors.
Synthetic tiny-capacity arithmetic remains under review; z alone is not an
all-overflow guard. Broad execution is not yet evidence for U3.

## U3 rejection and U4 capacity-support split

Independent implementation review reproduces false convergence when
C=max(0,x-.008),D=1,theta=0,L0=0 on[0,.009]: both initial midpoint
sweeps miss the active tail and return0, versus analytic.0005. The same
family fails on grid-containing intervals. U3 is rejected for promotion;
its complete broad characterization remains separate evidence.

Predeclare U4: split the stable integration interval at the transport-capacity
polynomial's analytic real zeros before endpoint refinement. Retain the same
ODE and full upstream load, propagate load across all pieces, and keep all
endpoints in double precision inside integration. Include shifted-origin
linear tails and quadratic capacity references. ROUTE already splits EROD
calls at critical-shear crossings (MSHEAR branches); preserve that caller
contract rather than silently inventing a new shear model. Review any
unsupported or violated caller precondition explicitly. No minimum number
of blind refinement steps is accepted as a fix for missing physical support.

## U4 boundary rejection and U5 declared transition guard

U4 closes shifted-origin tails (48 scalar passes) but fails closing capacity:
C=.009-x,D1,theta0,L0=0 has a deposition crossing at
.009*(1-exp(-1)); eager continuation to C=0 exhausts refinement. A quadratic
zero-positive-zero capacity hump reproduces the same failure. U4 is not
promotable. Relative convergence to an unphysical zero endpoint is the wrong
acceptance problem; an arbitrary absolute tolerance is rejected.

U5 establishes a transition bracket before eager integration to zero capacity
when positive load/source is proved on the upstream prefix. Reuse analytic
capacity-root pieces; positive D and C at a piece midpoint prove positive
supply on a nonempty part of that prefix. Positive initial load or interrill
source also suffice. EROCROSS uses the same predicate on each trial prefix,
never source downstream of the trial. No fictitious endpoint load is returned
or published. Required controls include closing capacity, zero initial D
followed by positive D, a capacity hump, an initially inactive plateau and
all-zero source/load. Keep other RUNGE and physical criteria unchanged.

## U5 rejection and U6 first-transition contract

Review reproduces C=max(0,(x-.002)*(x-.008)),D1,theta0,L0=0 on[0,.009]:
U5 continues through closing/reopening capacity and returns NDEP0, hiding
the first crossing near.00007290561. U5 remains rejected despite55 scalar
passes and successful full-period seeds.

Predeclare U6 for valid incoming detachment L<=C. For C>0, residual y=L-C
satisfies y'=-(D/C)*y+theta-C'. Partition at capacity zeros and C'=theta,
so the residual forcing has one sign within each piece and a crossing cannot
be hidden by later recovery. Integrate pieces in order, carry actual load,
and stop at the first crossing; retain the supported zero-boundary treatment.
No model coefficient changes. Zero-D stages evaluate theta without a
meaningless load/capacity ratio. Unsafe actual stage quotients dispatch the
stable solver from the original anchor; ordinary finite arithmetic remains.

Initial-excess L>C is a separate unresolved caller contract: ROUTE sets DU0
before DEPOS, assuming an equality transition. A new early-excess return
could lose incoming mass. U6 must not introduce it. Preserve those synthetic
failures as unsupported/unresolved, and require a separate U7 EROD→ROUTE→DEPOS
continuity experiment before promotion. Independent scientific review approves
U6 only as a diagnostic lane in its declared incoming domain.

## U6 precision consistency correction (U6b)

The first-transition prototype passes63 tests and four full-period seeds,
but source review confirms two capacity-evaluation inconsistencies. With
C=x*x-x+float32(.2500001), evaluating the polynomial in single precision
shifts a valid constant-load root556 coordinate ULP and can invent a
transition after the step helper correctly accepts. Preserve these failures.

U6b evaluates the polynomial in double precision and deliberately rounds once
to REAL for comparisons with REAL load, consistently in EROD, EROCROSS,
EROZERO and EROSTEP. The stable ODE uses the same double evaluator before
rounding. Comparing REAL load to an unrounded double capacity is rejected
because it can create false equality crossings. Both regressions and all
65 scalar tests pass the isolated prototype. Native source remains U5; no
release acceptance. The remaining DEPOS/caller continuity contract is under
independent review using actual ROUTE, not an unsupported EROD-only entry.

## U7 supported caller-boundary reproduction

An actual ROUTE/EROD/DEPOS/DEPEND/XCRIT/ENRICH fixture (no physics mocks)
confirms incoming excess is not purely an unsupported EROD call. For wet
qostar=.001,L0=.01,C=.001,theta=D=0,phi2, ROUTE's abs(qostar)<.0011
approximation sets the initial rate0, then enters EROD and sends DU0 to
DEPOS. First-grid load is.001, versus the independent supported inflow
solution C+(L0-C)*(q/(q+.01))^phi≈.0010743802. The q1 excess control
correctly enters deposition directly. Exact traces/source hashes and fixture
are retained in review_route_fixture.py and erod-u7-route-fixture-review.json.

Proposed separate U7 change: reserve the no-inflow limiting boundary for
qostar exactly0; evaluate nonzero-flow boundary rate from actual incoming
load and flow, in double before native conversion. This matches the existing
source comment and governing deposition relation. Freeze positive/negative
valid-flow, zero-inflow, former-threshold-neighbor and ordinary controls before
execution. Scientific review is required; no candidate promotion follows from
this hypothesis alone. Do not implement a new early-excess DU0 branch in EROD.

## U7 result and U8 shared deposition capacity

U7 actual-chain tests improve from4 failures/9 passes to13 passes, covering
positive/negative wet boundaries, both sides of the former threshold, exact
zero inflow and observer parity. The incoming-load formula is unchanged for
ordinary nonzero flow; the unsupported approximation band is removed.

Actual ROUTE also confirms a distinct DEPOS consumer defect: after U6b
locates the correct crossing for C=x*x-x+float32(.2500001), its single
polynomial evaluation returns9.36046618e-8 instead of the independent
60-digit integration reference9.9999934353e-8 at x≈.49992, then increases
load in the next source-free segment. Fourteen controls pass; this case fails.
Predeclare U8: use the same double polynomial and one native REAL rounding
for all DEPOS capacity reconstructions. Preserve the governing deposition
equation, wet/dry cutoff, load cap and other model behavior. Validate actual
ROUTE→DEPOS continuity and all prior scalar controls, then matched broad gates.

## U8 reconstruction result and U9 finite-coordinate handoff

U8 removes the6.4% cancellation loss, but the same actual-chain fixture
returns1.00002971e-7 versus9.9999934353e-8. EROCROSS correctly returns the
supported native coordinate adjacent to the mathematical root; capacity
there is slightly greater than actual load. ROUTE's unconditional DU0 resets
the boundary load to that capacity, producing a roughly30ppm jump. Preserve
the failed continuity assertion rather than enlarging its tolerance.

Predeclare U9: pass the rate implied by actual incoming load at XDBEG,
DU=phi*(C(XDBEG)-L)/(XDBEG+qostar), evaluated in double then converted to
REAL. An exactly zero denominator with equality retains DU0; unequal load
at that singular boundary must fail explicitly pending scientific disposition.
Keep source/particle/geometry behavior unchanged. Validate the actual-chain
continuity reference, zero/no-inflow, negative wet flow, observer parity and
all prior scalar controls before broad execution.

## U10 remaining entry-capacity consumer

Independent actual-chain review finds that ROUTE's initial capacity and
nonzero-inflow rate still use unclamped ktrato*cinftc while DEPOS uses max(0,C).
For constant raw capacity-.001,q.1,L0.01,theta0, the resulting loads are10%
above the consistent zero-capacity solution. Predeclare U10: use the shared
capacity evaluator for the initial capacity and nonzero-inflow boundary rate.
Preserve the separate exact-zero limiting formula; add positive/negative wet
actual-chain controls before changing that supported consumer.

## U11 legacy wet-coordinate mutation — investigation

DEPEQS changes X whenever abs(qostar+X)<1e-7, moving X to -qostar-1e-6.
Actual ROUTE q=-1e-7,phi-2,XE5e-8 is moved to -9e-7 and returns wet load
.9009999 instead of.00325; final dry export0 hides the error. Smaller q=-1e-8
is worse. This predates the current candidate. Freeze these actual-chain
fixtures and investigate nonzero wet support plus exact-terminal/no-inflow
contracts before repair. No fixed absolute inward shift is acceptable for a
shorter physical interval. Scientific review remains required.

### U11 frozen wet-domain contract

Do not mutate X or upstream/grid coordinates. For any nonzero X+qostar,
DEPEQS evaluates that actual coordinate. DEPOS treats an exact negative-flow
terminal as dry (zero load and rate) in grid and no-grid paths, including
qostar=-1 at the domain endpoint. DEPEQS's direct exact negative-terminal
rate API is unsupported and fails explicitly: rates can diverge even when
terminal load is zero. DEPEND's separate rootsearch terminal limit is unchanged.
The qostar=X=XU=0 regular-origin rate is evaluated explicitly.

XINFLO floors Case4 |qostar| at1e-5; tiny-q analytic controls remain useful
but are not claimed production-prevalence evidence. Add a supported q=-.001
endpoint5e-8 before its terminal, phi=-2 and-.5, neighbors of the old trigger,
exact terminal/dry-side controls, and unchanged coordinate assertions.
Retire the old test that required coordinate mutation, with this documented
replacement contract; do not silently preserve a knowingly corrupting guard.

## U12 PARAM rounded continuity-denominator sign

Predeclared before source change. Five full-period observer replays preserve
all ordinary output hashes. Retained PARAM operands show110 positive shear
and transport continuity quantities;34 transport segment guards receive an
exact-zero denominator after the positive quantity is lost in REAL rounding.
No exact-zero shear guard or inherited-QOSTAR fallback was observed. See
`param-continuity-u11-observation.json` and the independent scientific review.

For t>0, r=1/(t-1) gives 1+r=t/(t-1); near t=0 this approaches zero from
below. The current zero guard picks+.001, reversing the capacity polynomial.
U12 changes only exact-zero guard selection for nonnegative first-segment
slope b(2,iplane): choose-.001 in both shear and transport. Preserve the
positive branch for negative first slope and all nonzero-denominator branches.
A true zero slope uses the limit from nonnegative slopes; this repairs the
existing regularized sign, not exact continuity. Keep the .001 bound unchanged.

First freeze source-executed behavioral fixtures: actual retained positive
operands, synthetic shear exposure, REAL ratio neighbors, zero/negative first
slope and ordinary controls. Execute transport-only, shear-only and combined
seed lanes against immutable U11. Re-observe combined capacity production;
every remaining varying-negative wet interval requires disposition. Advance
only the combined candidate to all broad gates after scalar/seed review.
U11's1238 native,99 Disturbed and840+348 prior-physical passes are comparison
evidence, not certification of U12. Cedar is still completing. No production
binary/default change or UI implementation is authorized by this experiment.

### U12 executed checkpoint

All15 source controls and three separate four-seed lanes pass. Shear-only
matches U11; combined matches transport-only. Broad combined validation now
passes1253 native,28 watchlist,99 Disturbed,840 Roads and348 downstream prior
physical checks. Final Cedar and full1188 exact-parity capacity inventory remain
pending. The source and matched binary hashes are frozen in
`param-u12-gates-in-progress.json`; no shipped release changed.

The original host replay attempt completed the model but lacked pyarrow for
artifact validation. Preserve those outputs under host-unvalidated-seed-ordinary;
they are not validation passes. The corrected seeds phase uses canonical
`wctl exec -T weppcloud python .../param_sign_ablation.py <lane> seeds`.

The two strict fraction-sum flags retain identical failed predicates. Exact
source replay and operation-derived bounds explain both for the exact U12
pair; see `fraction-arithmetic-scientific-disposition.md` and its applicability
receipt. No audit threshold, particle fraction or ENRICH behavior changed.
Matrix magnitude remains713/766 meaningful plus31/74 small, with no threshold
recoveries or regressions. Native accounting acceptance does not accept Roads
parameter defaults. Source-observed terminal capacity precision is being bounded
across all1188 cases rather than extrapolated from four seeds.
