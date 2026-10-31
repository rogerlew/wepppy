# Independent DEPEND implementation review

Reviewed candidate `src/depend.for` SHA-256
`8a3178548b21969a48d159f74eee86e7b2ed4f32cf32020a48f130004ea7d01e`,
source-based deposition tests, portable full-run test, and source specification.

No blocking correctness finding in the reviewed change.

The division check at `src/depend.for:188` computes from finite single-real
operands in double precision, whose range accommodates their quotient. The
positive-flow branch rejects out-of-segment proposals before single-real
arithmetic; the negative-flow overflow branch applies the existing clamps
before conversion. Ordinary convergent arithmetic remains on the old path.
The fallback at `src/depend.for:256` strictly shrinks a representable interval
until its midpoint rounds to an endpoint, so it terminates without a fitted
rate tolerance. ROUTE's DU<0 caller condition and DEPEND's endpoint-rate check
supply the positive-flow bracket. Existing decreasing-flow terminal and no-root
returns are retained and tested.

Independent verification: `PATH=/usr/bin:/bin:$PATH pytest -q
 tests/test_deposition_stable_solution.py tests/test_depend_full_fixture.py`
completed with **114 passed in 5.90 seconds**. `git diff --check` passed for
source and tracked tests. Tests compile actual sources under invalid/zero/
overflow traps, compare general and constant-shear roots with independent
80-digit equations, exercise float32 neighbors and the decreasing-flow quotient
range control, and run the retained 16-year fixture from hash-verified inputs.

Residual risks / coverage limits:

- This review does not establish full-model sediment equivalence or approve
  delivery. Previously unconverged searches can now select different roots;
  the complete Roads/downstream, Disturbed, Cedar and native gates remain
  necessary and must explain changed outputs.
- The full fixture test verifies full-year completion, all OFEs, finite ELEMENT
  values and nonnegative sediment leaving; full water/sediment/particle
  reconciliation is delegated to the retained scientific audit, not duplicated
  in this small native regression.
- The candidate preserves the legacy 0.001 stopping criterion for convergent
  paths, rather than promising one-ULP roots for every call. Documentation states
  this distinction. No claim of production incidence is warranted from the
  synthetic decreasing-flow floating-range test.
