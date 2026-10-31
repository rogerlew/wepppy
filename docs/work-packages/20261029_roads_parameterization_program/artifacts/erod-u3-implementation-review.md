# Independent EROD U2 / RUNGE U3 implementation review

Reviewed source hashes:

- EROD: `1d4f3351013472eecffd0d5800bb47da5a814566221d4617a51159c1679c1ea3`
- RUNGE: `0d39a1b545f5f8fe3f60ba54d0e8592c1d799504bcf8772cfc5d56b18e06f658`

## P1 — RUNEXP accepts false convergence across an unsampled capacity onset

`src/runge.for:290–305` compares the first two exponential-midpoint sweeps and
returns when their endpoint loads agree. Both sweeps can miss a supported
positive-capacity region near an interval endpoint, so equality does not even
establish that both sweeps sampled the active equation.

Actual native EROD reproduction (defaults from the committed source test driver):

    xb=0, xe=.009, theta=0, load=0, capacity=-.008,
    btc=1, erodibility=1

The candidate returns `load=0, DL=1, NDEP=0`. The model coefficient is
C(x)=max(0,x-.008), D=1. Before .008, zero load remains zero; afterward the
regular governing solution is L=(x-.008)/2. Expected endpoint load is about
.0005 and DL=.5. The single-cell midpoint .0045 and two-cell midpoints .00225,
.00675 all see C=0; the method incorrectly accepts their identical zero result.
Capacity=-.007 likewise returns zero instead of about .001. Nearby -.006 and
-.004 cases work, demonstrating a sampling-dependent discontinuity.

The same defect affects existing grid-containing paths: xe=.01 with
capacity=-.009, and xe=.02 with capacity=-.019, both return zero instead of
about .0005. This is not confined to the newly introduced subgrid support path.

Retained reproducer: `/tmp/erod-u3-review-probe.py`. Add these as regression
cases and ensure known coefficient zero/cutoff boundaries are represented in
the integration domain (or supply an independently validated equivalent
convergence criterion). Merely increasing a fixed minimum refinement count
would move, rather than remove, the unsampled-tail case. U3 is not suitable for
promotion while this reproduction remains.

## Other implementation assessment

No additional concrete U2 state/anchor defect found. Grid and partial endpoint
integration capture upstream state before mutation; EROCROSS reuses a fixed
anchor and shrinks its interval until midpoint rounding prevents progress.
Strict upstream excess correctly distinguishes initial equality followed by
later crossing. U3 restores the endpoint DETCOM cache used by EROD's DL, and
existing tests check that state as well as load.

Independently ran `PATH=/usr/bin:/bin:$PATH pytest -q
 tests/test_erod_interval_support.py`: **43 passed in 0.67 seconds**.
`git diff --check` passed. The passing suite does not cover the shifted
capacity-onset cases above.

## Remaining evidence limits

The parent has separately recorded a tiny-capacity initial-excess overflow;
this review does not close or reclassify that finding. Full native/scientific
runs remain necessary. RUNEXP permits up to 2^24 cells in its final sweep
(33,554,431 coefficient evaluations across all sweeps), and EROCROSS may invoke
it repeatedly. That bound terminates, but broad runtime measurements are needed
before accepting its cost; no production slowdown is asserted by this review.
