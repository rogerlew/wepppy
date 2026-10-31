# Independent U2/U3 design review

The proposed separation is scientifically defensible for evaluation: U2 repairs
shared transition anchoring/root selection; U3 dispatches numerically unsuitable
RUNGE steps to a stable solution of the same linear-in-load ODE. Neither lane is
accepted for release until independent controls and broad artifact gates pass.

The z=|dx|D/C threshold0.1 has a reproducible constant-coefficient rationale:
exp remainder <=exp(0.1)*0.1^5/120 is below epsilon(single). This bounds the
homogeneous amplification-factor error only. Load error multiplies that factor
by |L0-equilibrium|; root error also depends on the slope at crossing. It does
not establish universal single-precision load/root accuracy, variable-coefficient
accuracy, or accumulated global accuracy. Document the limited rationale and
retain independent varying-coefficient/boundary tests.

## Required implementation contracts

- Evaluate the dispatch quantity in double precision and handle C<=0 before
  division. Do not overflow while deciding whether arithmetic is safe.
- Dispatch detected at stages2/3/4 restarts the full interval from the original
  x,ldold,dx, not the provisional RK stage state.
- Restore RUNGE's endpoint common state xx,shr,dcap,eatax,taucx. EROD uses dcap
  immediately to compute dl; the last exponential midpoint is not that endpoint.
- Whole-interval refinement avoids the demonstrated zero-origin local-budget
  stall. Use a unit-consistent load scale, record refinement/work counts, and
  fail explicitly on non-convergence. The successive-load comparison is an
  estimated accuracy criterion, not a rigorous universal error bound.
- Keep strict initial excess distinct from equality followed by a later crossing.
- Test both sides/float32 neighbors of the dispatcher threshold, first becoming
  stiff at an interior stage, linear capacity origins, variable detachment,
  stiff constant-capacity roots, and unchanged ordinary arithmetic.

## Confirmed arithmetic edge beyond stiffness

Actual U2 source probe: XB0,XE0.009,L00.0007,C1e-42,theta0.1,D0 (also D1e-42),q1
SIGFPEs before EROCROSS sees initial excess. z is0 (or approximately0.009), so a
stiffness-only dispatcher cannot catch `(C-L)/C` overflow. This is a synthetic
initial-deposition state, not production-frequency evidence. Recognizing strict
initial excess before eager integration is the smallest relevant root-domain
handling; provisional stage crossings may also require an explicit unsafe-ratio
dispatch check. Do not claim z alone protects all unsafe arithmetic.

## Independent endpoint-state control

Use shear polynomial x, capacity1,theta0,eata1000,tauc0,XB0.1,XE0.109,L00.0007.
The step dispatches but stays below capacity. With s=float32(0.666667), exact
load is `1-(1-L0)*exp[-1000*(XE^(s+1)-XB^(s+1))/(s+1)]`; endpoint
`dl=D(XE)*(1-Lfinal)`. Check both to catch stale common-state values. Preserve
the existing exponent; substituting exact2/3 silently changes the retained law.

A representative full-interval linear-origin control is C=x,D1,theta0.1,L00,
whose regular solution is L0.55x. Sweep D/C' to avoid validating only one favorable
convergence rate. Fresh matched broad gates remain necessary after U3 changes.
