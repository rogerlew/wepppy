# Roads EROD interval and transition accounting

- `incident_id`: `20261031_roads_erod_interval_support`
- `status`: `active`
- `scope`: `mixed`
- `author`: Codex
- `date_utc`: `2026-10-31`
- `host_scope`: `dev`
- `contract_refs`: `requires_scientific_review`


## Final U12 scientific acceptance (release promotion pending)

Independent scientific review accepts the exact combined pair after1253 native,
28 watchlist,99 Disturbed,840 Roads and348 downstream physical gates, plus
fresh864-hillslope/24-year Cedar. All5201 Cedar inputs and864 water plus864
soil outputs are byte-identical across U12/U11/revision3. Cedar outlet sediment
is517671.83kg, +1.20kg versus revision3; reported water metrics are unchanged.
Full1188 exact-parity source observations classify all40006 negative-capacity
calls as bounded dry-terminal precision. Two strict fraction flags remain
reported, with exact source-replay/machine-derived certificates. No thresholds
were relaxed; no particle renormalization was added.

Acceptance receipt: artifacts/logs/param-u12-scientific-acceptance.json.
Watershed SHA2a3f9f2b9efd202365c6ef27222bc9f4836918bd16e865c1e3cd54b14c297b48;
hill SHA9ef6b62677407a66255a2b95becc9f350c87ef8e4cf67ab4e543ddb89ed4a010.
All489 source/include/math files match the frozen build. Native source promotion
is separate from release-note publication, WEPPpy delivery and deployment.
Roads magnitude remains713/766 meaningful plus31/74 small: no parameter default
or UI implementation is accepted. Legacy-context instrumenters remain private
under artifacts/private-tools; the public research set uses explicit entrypoints.

## Confirmed failure and scope

Shared hillslope/watershed EROD omits a nonempty interval if its endpoint is
before the next output-grid coordinate. Full-period source observations have
exact ordinary-output parity. The ordinary Roads site/1718465/inveg/paved/high
event2005day309 omits [0,.00941210799], then ENRICH counts the full interrill
source and clips a negative rill residual. A downstream buffer-cap case has
the same defect. Baseline G1 and released revision3 share the discrepancy.
This is not Roads-specific logic. Production prevalence is not quantified.

## Evidence and experiments

Portable scalar reproductions are committed in tests/test_erod_interval_support.py
(commit3c226ce55); source observations and raw inputs are retained by the
WEPPpy Roads program. Evidence root is
/workdir/wepppy/out/roads-parameterization-program-20261031.
U1 under erod-support-u1 adds missing integration support but fails independent
transition roots. Its840 Roads+348 downstream runs close class-versus-bulk
mass discrepancies across135765 EVENT rows; two strict fraction-sum flags
remain. Initial1160 native tests,28 watchlist,99 Disturbed and fresh full
Cedar864 hillslopes/24 years complete. Cedar water is unchanged; outlet
sediment increases1.18kg over24 years. These do not override failed scalars.

U2 under erod-root-u2 fixes transition bracketing using the actual upstream
load/coordinate and strict initial excess. Nine of15 expanded scalar failures
close; six stiff roots remain. Legacy RUNGE is unchanged. Four full16-year
seeds pass prior physical checks and all1306 EVENT particle checks.

U3 under erod-stable-u3 adds separately reviewed stiff integration. All43
scalar cases pass, including analytic variable-detachment load and endpoint
detachment state. Four full-period seeds and1306 EVENT particle checks pass.
Broad validation and independent source reviews remain in progress.

## Scientific rationale and promotion gate

Retain the same detachment/transport equation and inputs. Grid publication
spacing must not remove physical support. A load exactly equal to capacity
can initially enter detachment before a later deposition transition. Legacy
RK4 plus its interrill floor can produce wrong stiff roots in both existing
grid and newly supported paths. U3 integrates the same linear ODE with
exponential midpoint refinement; it is experimental, not a new physical law.
Boundary disposition is requires_scientific_review; no proposed science
contract is represented as active authorization.

No candidate is promoted. Preserve both small fraction-sum flags, synthetic
arithmetic counterexamples, and all failed runs. Required gates are independent
analytic references, complete native/watchlist, Disturbed,840+348 Roads,
expanded particle accounting, and fresh matched Cedar semantic/source checks.
Magnitude criteria and withheld materials remain frozen. Shipped261029
revision3 is unchanged. Human approval still gates UI implementation.

## Recovery and next action

All source snapshots and isolated matched pairs remain under the evidence root.
Revert experimental source to the accepted release for production builds.
Continue scalar review and broad U3 characterization; do not infer release
acceptance from process completion. Resolve tiny-capacity arithmetic scope
and both strict normalization flags before promotion.

## Subsequent bounded lanes and current disposition

U4 partitions stable integration at capacity zeros but fails a closing-capacity
transition. U5 locates a transition before continuation to a closing endpoint;
1197 native tests pass, but a closing/reopening interval exposes a missed first
transition. U6 partitions at both capacity zeros and C'=theta. U6b uses the
same double-evaluated, once-REAL-rounded capacity across transition consumers.
U7 reserves ROUTE's no-inflow approximation for exactly zero flow; U8 shares
capacity reconstruction with DEPOS; U9 preserves actual load at finite-coordinate
handoff. U10 uses the shared clamped capacity at initial entry. U11 removes
DEPEQS's fixed inward coordinate mutation and defines exact-terminal dry load
without evaluating a singular rate. Portable actual-chain fixtures use actual
ROUTE, EROD, DEPOS, DEPEND, XCRIT and ENRICH implementations.

Frozen U11 passes209 targeted,1238 full native,28 watchlist,99 Disturbed and
840+348 prior physical checks. All135765 EVENT rows close class/bulk mass;
two strict printed-fraction flags remain under investigation. Fresh Cedar
864-hillslope/24-year native execution completes; semantic conversion pending.
These gates do not approve release: exact-parity PARAM observation confirms
material negative capacity from a rounded continuity denominator's wrong sign.

U12 is predeclared in the WEPPpy active ablation plan and proposed ADR-0124.
Five full-period U11 producer observations preserve every ordinary output hash:
110 positive shear/transport quantities,34 exact-zero transport guard records,
no observed zero shear guards or inherited-QOSTAR fallbacks. For t>0,
r=1/(t-1) gives 1+r=t/(t-1), approaching zero from below as t approaches0.
At rounded r=-1 the old guard selects+.001 and reverses capacity sign.
U12 selects-.001 only at an exactly zero denominator and nonnegative first
slope, in both shear and transport guards. Negative slope and every nonzero
branch remain unchanged. The existing .001 bound is preserved; exact
unregularized continuity is not claimed.

Separate transport, shear and combined lanes are retained under
param-sign-u12-{transport,shear,combined}. All four full-period seeds pass
prior physical checks. Shear-only outputs equal U11; combined equals
transport-only. Water/soil outputs are unchanged. Combined has zero particle
flags in1306 EVENT rows (1044 positive). Source-executed producer/guard tests
reproduce four U11 failures; all15 controls pass the combined prototype.
An exact-parity combined observer removes the material negative capacities;
remaining small terminal negatives require a bounded scientific disposition.
U12 broad gates are not yet executed. No source candidate is released.
