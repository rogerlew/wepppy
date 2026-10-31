# Independent EROD U1 scientific review

Disposition: **scientific promotion blocked**. Source observations establish the
missing integration interval and the four full-period seeds pass the expanded
particle audit, but a finite constant-coefficient counterexample demonstrates
that U1's transition search can return a materially incorrect location.

Reviewed EROD SHA256:
`fff9125e81e3eb1d9e237e7cb492f8ae68ae61fef1456c0ee65f2da2e2944dd8`.

## P1: transition bisection can select a spurious RK4/floor crossing

`src/erod.for`'s new empty-grid interval branch repeatedly integrates from XB to
its trial coordinate with one legacy RUNGE step. Bisection makes the returned
coordinate precise for that step's residual; it does not make the step an accurate
solution of the governing ODE. RUNGE's existing lower bound
`Lnew >= Lold + theta*dx` can conceal a numerically unstable RK4 step and create
a spurious transition in otherwise finite, positive states.

Concrete source probe: XB0,XE0.009,initial load0.0007,capacity0.001,theta0.1,
qostar1,ktrato1,shear1,critical shear0,ilast1,erodibility1. The independent ODE is
L'=D(1-L/C)+theta. Its solution has equilibrium E=C(1+theta/D) and transition
`x=-log((E-C)/(E-L0))*C/D`.

Independent transition:0.0013862943611198904. Native U1:0.00300000119,
116.4% late. With erodibility10, independent transition0.00034339872044851434
versus the same native0.00300000119. These are synthetic analytic controls,
not claims about production prevalence. Their values are finite and the true
solution is nonnegative and increasing up to capacity.

All18 checked-in source tests pass, but their nonzero-rill transition test uses
D0.001/C0.001 and does not exercise this integration regime. Retain the failing
controls and require a narrowly declared integration/step ablation with independent
root/load reference evidence. Do not accept nominal interval bounds or successful
process completion as proof of correct root selection. The RUNGE limitation
predates this candidate; the new transition branch inherits it and currently
claims broader validity than the tests establish.

## Expanded audit semantics

The initial `audit_particle_closure.py` skipped all checks for EVENT records with
zero summed class concentration. Mass closure must be checked for every EVENT;
only the normalization expectation should depend on positive concentration.
Otherwise a positive bulk load paired with all-zero classes is silently omitted.
This is a coverage defect, not proof that the four seeds contain such a failure.

Independent all-EVENT mass audit of all four16-year seeds:1306 EVENT records,
1036 positive-concentration records, zero flags. This includes the270 zero-class
EVENT records skipped by the initial audit. Retained at
`/tmp/erod-seed-allevent-particles.json`.

## Pending broad evidence

The840 Roads and348 downstream runs are still in progress at initial review.
Do not infer whole-matrix acceptance from the four seeds. Source probe inputs,
results and hashes are in `/tmp/erod-scientific-review.json`; executable independent
probe is `/tmp/erod_scientific_probe.py`. Further output review will supplement
this record without overriding the demonstrated source-level failure.

## P1: initial equality is not necessarily immediate deposition

A separate native probe uses D0,theta0.1,L0=0 and
C(x)=0.2x−20x² over[0,0.009]. The exact load is0.1x; load initially stays below
capacity and first crosses it at0.005. U1 returns0 because its
`ldbeg >= tclast` branch treats the zero-zero upstream equality as deposition.
The positive-equality variant C(x)=0.001+0.2x−20x²,L0=0.001 has the same later
crossing. Use strict initial excess as the immediate-deposition condition;
equality requires the downstream residual search.

## Confirmed wider failure class

The existing grid-containing path has the same stiff transition defect. With
XE0.01 or0.02,D1,C0.001,theta0.1,L00.0007 it returns0.00300510321 instead of
0.0013862943611198904. D10 returns the same0.00300510321 instead of
0.00034339872044851434. Exact six-case comparisons and source hashes are in
`/tmp/erod-grid-failure-class.json`. A no-grid-only repair cannot be called
sufficient for this confirmed shared integration/transition assumption.

## U2 design review

Stable exponential midpoint stepping is a reasonable candidate for the same
linear-in-load ODE, with constant-coefficient solutions exact at any stiffness
and positivity preserved for physical nonnegative D,C,theta. A local error
budget proportional to step length fails at a linear zero-capacity origin:
for C=x,D1,theta0.1,L00, both the local full-versus-half error and tolerance
scale with h, so halving cannot resolve their ratio. Whole-interval refinement
avoids that specific stall; compare successive final-load estimates with a
unit-consistent single-precision-derived load scale, retain work counts, and
fail explicitly on non-convergence. This is an estimated accuracy criterion,
not a rigorous universal error bound.

Mandatory independent controls include C=x with D/C' spanning0.01,0.1,1,10;
the stiff constant-C cases above; zero/positive upstream equality with later
crossing; and variable detachment with constant capacity. The confirmed grid
consumer must receive an explicit remediation/disposition. This design review
supports experimental evaluation; scientific acceptance remains pending.

## Complete downstream U1 expanded audit

Independently audited all348 downstream cases,18,620 EVENT rows and13,100
positive-concentration rows, including mass closure for zero-class EVENT rows.
One normalization flag remains: Denver/1718465/outunrut/gravel/none/buffer_cap,
year8 day228, fraction sum1.000017 versus print bound0.000016. Its class mass
is within the bulk comparison bound. It predates U1;21 other prior downstream
fraction flags and all prior downstream class-mass flags clear. Do not silently
waive the remaining strict flag: source arithmetic evidence must explain it.
Against G1,21 annual exports increase slightly,327 stay equal, and magnitude
classifications do not change. Complete paired hash verification and840 Roads results are recorded below.


## Completed broad U1 review

Independently rehashed all840 Roads and348 downstream emitted input/output
inventories and paired source records. Inputs match the declared source; all1,188
water/soil output pairs match G1 exactly. All1,188 pass the existing finite,
nonnegative and report-reconciliation audit. Output-changing case counts806 Roads
and293 downstream compare against declared R3, while the following annual changes
isolate U1 against G1.

Roads annual sediment increases in157 cases, decreases by one reporting increment
(0.00396 kg/year) in one case, and stays equal in682. Maximum absolute increase
is0.7327888995 kg/year (0.14736%) in Birmingham/53949/outunrut/gravel/none.
Meaningful713/766 and small31/74 magnitude results remain unchanged. Downstream
annual changes and controls remain as described above; no magnitude transitions.

Expanded all-EVENT particle audit covers135,765 events,108,259 with positive class
concentration. No class-versus-bulk mass flags remain. Two strict normalization
flags remain, both byte-identical to G1: the Denver downstream row above, and
Roads site/2711250/outunrut/paved/low,2003 day29, sum1.000005010000286038 versus
bound0.0000050050000000015. The latter exceeds the printing-only bound by about
5e-9. Source arithmetic evidence must distinguish roundoff from missing support;
the printed bound is not silently changed.

The broad results strongly support the omitted-interval mechanism, but do not
supersede the independent analytic counterexamples. **U1 remains rejected and
unpromoted.** U2 must address the confirmed grid-containing consumer as well as
the new no-grid path, retain the exact ODE/source meaning, and rerun source and
broad scientific gates on the actual candidate binaries. G1 Cedar evidence cannot
substitute for a fresh U2 matched hillslope/watershed replay.

Artifacts: `/tmp/erod-paired-output-review.json`,
`/tmp/erod-roads-allevent-particles.json`,
`/tmp/erod-downstream-allevent-particles.json`,
`/tmp/erod-scientific-review.json`, `/tmp/erod-grid-failure-class.json`.
