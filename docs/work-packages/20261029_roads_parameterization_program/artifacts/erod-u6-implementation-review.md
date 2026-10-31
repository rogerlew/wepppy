# Independent EROD / RUNGE U6 implementation review

Reviewed isolated prototype at
`/workdir/wepppy/out/roads-parameterization-program-20261031/erod-event-u6/probe`.

- EROD SHA-256: `04a7f0338d41342008010385212c3d1adc06e8a9ee9d50a066ff0c29f09104fc`
- RUNGE SHA-256: `93d59601bb8ae662f4e64c5f47626cd49e1242748607705812bdbbddf1739cb9`

No new blocking implementation finding in the stated valid incoming detachment
domain, L<=C. This is conditional source-review acceptance, not release approval.

## Earlier first-transition finding

EROSTEP now partitions at capacity roots and C'=theta, propagates the actual
load across pieces and returns on the first transition. For y=L-C, the forcing
on a positive-capacity piece is theta-C', whose sign is constant between those
partition points. This addresses the earlier endpoint-recovery counterexample.
Closing roots are distinguished from opening roots using positive capacity on
the preceding piece; the maximum inventory is five points (two polynomial
roots, one forcing turn, and two endpoints). Sorting carries boundary metadata,
and coincident/rounded points do not produce negative-length integrations.

RUNGE's new stage guards restart from the original anchor, not a provisional
stage state. Zero detachment omits an unnecessary load/capacity quotient.
The returned endpoint cache is still restored on the stable integration path.
EROCROSS returns an adjacent supported coordinate and its actual load; it does
not invent a load at a singular endpoint.

## Independent checks

- Source suite: **63 passed in 1.11 seconds**.
- Eighty equality-throughout controls varying initial capacity/load, theta and
  D produced no false deposition flags. Reproducer:
  `/tmp/erod-u6-review-probe.py`.
- Fifteen positive-capacity dip cases with D=.001,.01,.1,1,10 and theta=0,.01,.1
  all selected the first transition against an independent RK4 reference stopped
  before singularities. Reference step halving was checked. Reproducer and
  results: `/tmp/erod-u6-dip-probe.py`, `/tmp/erod-u6-dip-results.jsonl`.
- Largest observed coordinate error was 7.47e-9 (about 4.1e-6 relative), for
  D=.01 on the retained legacy RK4 path below the stiff switch. This is not a
  missed event; do not generalize the adjacent-coordinate search termination
  into an all-path one-ULP physical-root accuracy claim.

## Open boundaries before promotion

Initial L>C remains outside this review's accepted incoming-state domain and
its known caller DU=0 issue is not closed. The existing ROUTE shear-critical
partition assumption remains necessary for the supply checks; no arbitrary
unsplit shear profile is newly authorized. Broad native, Roads, particle/source,
Disturbed and matched Cedar gates, plus runtime measurements, remain required.
Always-on capacity/forcing partition work changes per-step cost, while stable
integration still has a large finite worst-case refinement budget; no production
performance acceptance is inferred from the small scalar suite.
