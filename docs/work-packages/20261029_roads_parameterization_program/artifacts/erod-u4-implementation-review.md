# Independent EROD / RUNGE U4 implementation review

Reviewed `src/runge.for` SHA-256
`d4e59ee866ab16062748a5995b31d38403ebb46b9c1373e29e8c5fbc795e517a`.

## Previous P1 closed for the tested shifted-origin family

Capacity-root partitioning correctly represents the previously missed short
positive-capacity tails. The stable quadratic-root formula, bounded points(4)
inventory, sorting, duplicate-root zero-length skips and fixed-resolution piece
sweeps are coherent. Refinement retains a whole-original-interval comparison;
there is no length-proportional per-piece tolerance. The 48 source tests pass
independently in 0.78 seconds.

## P1 — Zero-capacity exit exhausts endpoint refinement before locating deposition

RUNEXP's convergence scale still consists only of initial load, final load and
total interrill source. With zero initial load/source and a positive-capacity
region that terminates inside the interval, its exact continuation load tends
to zero. Every finite midpoint resolution leaves a nonzero residual, and its
tolerance shrinks in proportion to that residual. Refinement exhausts the
2^24-cell limit and stops the entire model before EROD can locate the interior
deposition transition.

Simple actual-source reproduction using native_erod in the current tests:

    xb=0, xe=.009, theta=0, load=0,
    capacity=.001, btc=-1, erodibility=1

The candidate exits status 1 with:

    RUNEXP failed endpoint convergence 0.0 8.99999961E-03 0.0
    STOP 1

Elapsed time: approximately 6.05 seconds for this one scalar call. On the
positive-capacity side C=.001-x and D=1, the exact solution is
L=C*ln(.001/C). Its first deposition transition L=C is at
x=.001*(1-exp(-1)) ≈ .0006321205588, strictly inside the interval.
This supplies an independent transition oracle, not merely a desired successful
exit. The candidate should locate the transition before extending the erosion
solution through the zero-capacity boundary. Increasing a tolerance or accepting
a failed solve would not establish that behavior.

A second confirmed reproduction has
C=max(0,-x*x+.01*x-.000016), D=1, zero initial load/source, [0,.009].
It likewise stops after about 8.27 seconds. Multiplying all capacity coefficients
by 100 retains the failure. These illustrate the same endpoint-scale/event
issue; they do not establish production prevalence.

## Acceptance disposition

U4 fixes the prior unsampled-tail finding but is not ready for promotion while
this finite interior-transition case fails. Preserve the known tiny-capacity
initial-excess overflow as unresolved too. Shared EROD anchor handling remains
sound in the inspected paths. Full scientific/native/runtime gates remain
required after the mechanism is corrected; 48 passing tests alone do not close
the new failure family.
