# EROD U6 prototype scientific review

Disposition: hold application/promotion until the two confirmed capacity-evaluation inconsistencies below are closed. The event-piece design itself is scientifically justified for valid incoming detachment states L<=C. This review does not approve the unresolved initial-excess ROUTE/DEPOS boundary contract or release promotion.

Reviewed isolated prototype: `/workdir/wepppy/out/roads-parameterization-program-20261031/erod-event-u6/probe`.

Source SHA-256:
- `src/erod.for`: `04a7f0338d41342008010385212c3d1adc06e8a9ee9d50a066ff0c29f09104fc`
- `src/runge.for`: `93d59601bb8ae662f4e64c5f47626cd49e1242748607705812bdbbddf1739cb9`
- `tests/test_erod_interval_support.py`: `767470fde6364884f504a8b163ba3cb1721d534223b4b3461bbc7ad2e6011769`

## Findings

1. **High: EROCROSS still evaluates a different capacity polynomial from the event detector/stable ODE.** `src/erod.for:444,471` evaluate the polynomial in single precision. EROSTEP uses double Horner evaluation through RUNCOEF, followed by one REAL conversion. With XB=.499, XE=.509, initial L=1e-7, theta=D=0, C=x*x-x+float32(.2500001), ilast=50, the initial state is valid and the first crossing is analytically `.4998970775340097`. U6 returns REAL `.49991366267204285`, 556.5 coordinate ULP late. Capacity at the returned point using the retained REAL coefficients is `9.686110136186699e-8`, versus L=`1.0000000116860974e-7`: a 3.13889977% excess, inconsistent with the promised supported-side return. This matters at the DEPOS handoff, which reconstructs capacity when DU=0. The exact amount of subsequent bulk-output impact requires a caller-level test; the scalar discrepancy is confirmed.

2. **High: EROD can reverse EROSTEP's correct no-transition decision.** `src/erod.for:153` and the corresponding grid/partial checks at 240 and390 retain the single-polynomial capacity. Concrete no-grid case: XB=.499, XE=.49992, initial L=`9.260612188199957e-8`, theta=D=0, C=x*x-x+float32(.2500001), ilast50. C decreases but remains above L throughout; endpoint double capacity is `9.58052766009132e-8`. EROSTEP detects no crossing. The subsequent single endpoint capacity is `8.940696716308594e-8`, creating false NDEP=1 at `.499913663`. Thus changing the root search alone is insufficient: all transition decisions must share the same capacity evaluation, or defer to EROSTEP's authoritative result.

A coherent minimal policy is shared double-Horner capacity evaluation with one explicit conversion to REAL wherever compared against a returned REAL load. Do not compare rounded REAL L directly with unrounded double C: exact equality L=C=.1*x can acquire a small positive residual solely from the final load rounding. Preserve the all-through-equality control. EROZERO at492 also needs consistent evaluation; the present confirmed evidence does not justify an arbitrary tolerance.

## Mathematical assessment

For positive capacity, y=L-C satisfies y'=-(D/C)y+theta-C'. Multiplication by the positive integrating factor makes the derivative have the sign of theta-C'. Splitting at C=0 and C'=theta therefore gives at most one crossing per positive-capacity piece. Equality throughout is not a positive crossing. This is a justified first-event treatment, not a new physical law.

Classifying an internal capacity root as a mandatory closing boundary when capacity is positive on its left is correct. It also covers a positive-zero-positive tangent; restricting the rule to positive-to-negative sign changes would not. An opening root should remain an integration partition rather than be called deposition merely because single evaluation rounded its capacity to zero. Actual positive upstream load or interrill supply in a zero-capacity prefix can still create a legitimate earlier transition and must remain covered.

The evidence supports diagnostic work on valid incoming detachment states. It does not settle the separately retained strict-initial-excess and DU handoff contract. The whole-interval exponential midpoint stopping test is a convergence estimator, not a universal error bound; prior supported-domain and broad physical gates remain required.

## Independent validation

- Existing source suite independently rerun: **63 passed in1.13s**.
-41 capacity-hump variants across neighboring float32 intercepts all retained a physical interior transition rather than the opening root.
- New analytic constant-load positive-capacity dip probes exposed the two findings above; they are independent of the exponential solver and do not rely on fitted tolerances.

Evidence:
- `/tmp/erod-u6-science-probes.json` (hashes, all41 hump variants, compiler observer path).
- `/tmp/erod-u6-cancellation-probes.json` (analytic root comparisons).
- `/tmp/erod-u6-postcheck-probes.json` (false no-grid transitions).
- `/tmp/review_u6_probe.py` (reproducer/compiler harness).

No repository code was edited. Full U5 matrix results are not evidence for the corrected U6 candidate; the final U6 binary needs its own exact-hash broad checks after these scalar failures close.
