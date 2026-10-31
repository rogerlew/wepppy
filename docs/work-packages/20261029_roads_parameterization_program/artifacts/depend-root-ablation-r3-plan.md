# Next native ablation: bounded DEPEND root search

Status: executing; scalar regression reproduced and candidate under validation. Continue the active Roads program and native
ablation protocol. No release change is accepted by this declaration.

## Confirmed failure and scientific reference

The retained full-run fixture reproduces SIGFPE with exact partial-output parity
on released revision 3. The scalar fixture reproduces an unbounded positive-flow
Newton search for a finite interior root. The frozen float32 inputs and 80-digit
closed-form reference are in `depend-scalar-r3-result.json`. The scalar compiler
uses system gfortran and the actual DEPEND/DEPVAL sources; it is not a claim of
bit-identical linkage to the released full binary.

For the observed `a=theta=0`, let `U=xu+qostar`, `V=x+qostar`,
`A=phi*b*ktrato/(1+phi)`. Then
`D(x)=A+(DU-A)*(U/V)^(1+phi)`. The reference root is
`U*((A-DU)/A)^(1/(1+phi))-qostar`. Implement independent high-precision
references for general cases as well; do not use DEPVAL as its own oracle.

## Required lanes and coverage

1. Promote the portable input fixture or its deterministic generator into the
   native test infrastructure, with source hashes and expected failure before
   repair. Add the scalar case and its interior-root assertion.
2. Trace positive-flow and decreasing-flow branch domains, endpoint sign tests,
   zero-flow boundary handling, convergence and existing non-root returns.
   Assess other consumers of the same Newton/domain assumption. Do not redesign
   deposition physics or change model parameter defaults to avoid the input.
3. Declare the smallest safeguarded search: maintain a physical bracket when
   one exists, accept Newton steps only inside it with a safe finite quotient,
   and use bounded interval progress otherwise. Preserve legacy non-root branch
   contracts where scientifically valid. Use an independent reference to justify
   stopping/rounding behavior rather than introducing a fitted tolerance.
4. Run actual source tests at the observed case, float32 neighbors, steep positive
   phi, near-flat derivatives, existing phi=-1/-2 limits, positive/decreasing
   flow, and terminal/absent roots. Require finite in-domain search trials and
   correct selected roots, not merely successful process exit.
5. Re-execute the full failed fixture and paired original/buffer/both controls;
   rehash emitted inputs and verify native water/sediment/particle outputs.
   Retain failure denominators. No blanket guard disabling or stdout-only success.
6. Complete native regression/watchlist, Disturbed, full Roads 840 baseline plus
   the new downstream panel, and Cedar semantic/source checks before any binary
   delivery. Independent scientific and implementation review are required for
   promotion. Review solver effects separately from parameter acceptance.

## Delivery boundary

Keep the current release pair unchanged during ablation. If a repair is accepted,
follow canonical vendoring/release procedures and the user's existing undeployed
same-name `wepp_261029` re-release preference, with an explicit artifact revision,
matched pair, updated provenance and release note. No deployment or Roads default
change is implied. Preserve portability changes, generated-soil normalization,
withheld materials and the human configuration specification/layout gate.
