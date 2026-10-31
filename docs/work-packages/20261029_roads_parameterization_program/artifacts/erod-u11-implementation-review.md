# Independent U10/U11 implementation review

Reviewed native working tree:

- ROUTE `83a9ddd665aab6404e09e9ff2398b194fb24694a1f87d1a4955306f8f8d57f68`
- DEPOS `7bac841e26c99c3f3b785e07f543469ddfa2e9bc01fd9d89f776a4f304e8f6f0`
- DEPEQS `87d9cfab09f759c17e37d0044fe3654191810a4154fa39d76db245e7d53ded30`

## Reviewed boundary repairs

No new blocking implementation finding in U11's coordinate/domain mechanism.
Both prior U9 reproductions are closed:

- Initial ROUTE capacity and nonzero-inflow DU now share the clamped boundary
  value. The constant negative-polynomial test returns the independently
  expected .0082644628 at x=.01 and 8.2644628e-5 at x=1.
- Small finite negative-flow wet coordinates remain unchanged. For q=-1e-7 and
  -1e-8 the first wet load is .00325, the terminal coordinates remain physical,
  and dry export is zero. The prior huge intermediate loads no longer occur.

DEPOS excludes exact dry-terminal coordinates from rate evaluation in grid and
non-grid paths, including q=-1. DEPEQS explicitly rejects negative-flow terminal
or dry inputs and handles the regular zero-inflow origin without mutation.
Production DEPVAL consumers are DEPEND and DEPEQS only: DEPEND retains its
root-trial conventions; DEPEQS supplies the strict-wet production wrapper.
The root-search helper's trial API is not incorrectly treated as a physical
terminal-rate API.

Independent verification:

    PATH=/usr/bin:/bin:$PATH pytest -q
      tests/test_deposition_stable_solution.py
      tests/test_erod_interval_support.py
      tests/test_route_inflow_boundary.py

**209 passed in 5.53 seconds.** `git diff --check` passed. Re-ran both prior
standalone reproducers; explicitly unrepresentable positive-flow initial rates
still fail with the intended diagnostic.

## Remaining capacity-law question (not introduced by U11)

The earlier U9 review explicitly did not establish consistency over an entire
negative-polynomial interval. A further actual-chain probe now demonstrates the
open boundary: raw C=-.001+.1*x, initial load=.01, q=.1, theta=0 and no rill
source returns load(.01)=.007352616. If C=max(0,raw C) is the intended capacity
throughout that interval, the independent zero-capacity solution before x=.01
is .01*(.1/.11)^2=.008264463.

DEPVAL retains the raw polynomial's forcing while DEPOS reconstructs load with
clamped DEPCAP. This is a confirmed inconsistency under the piecewise-clipped
ODE interpretation, not proof of production incidence or a new U11 regression.
It needs an explicit scientific contract/disposition before claiming complete
validation of clipped-capacity deposition intervals. Reproducer:
`/tmp/route-u11-clipped-polynomial-probe.py` (uses the retained U9 driver helper).
Do not infer that correcting the initial boundary alone settles this interval
question.

## Acceptance boundary

Conditional acceptance of the U10/U11 boundary implementation only. Full native,
Roads, particle/source, Disturbed, Cedar and performance gates remain required
for the combined candidate. The capacity-law question above and existing
initial-excess/caller-domain scope must remain visible in the scientific ledger.
