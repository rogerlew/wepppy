# Independent combined U9 implementation review

Reviewed native working-tree copies matching the isolated U9 prototype:

- EROD `422d30692ac31327ee01a9ef8ea83b9543c46f9c1f985434fbd9037720847814`
- RUNGE `9d450d55beca548c714925d309774e9a4d0d8a40e08b248a413f187b31dc31bb`
- ROUTE `a42733e1d56e072b4b6032d26899184654d47380edb7070f3dfa95ca5e338650`
- DEPOS `7be71b278baeacefe56a4aae0bfb31dcee572636b9724eb62ea71219c847703a`
- DEPEQS `0b8229de965954d88e085c80644ac52c2bbab8c072877a4d0acdc28237a55d62`

## P1 — Small finite negative-flow wet endpoints are moved outside their segment

`src/depeqs.for:54` retains the fixed near-terminal displacement:

    if (abs(qostar+x).lt.10e-8) x = -qostar - 0.000001

The newly corrected nonzero-inflow boundary exposes this legacy displacement
on finite wet prefixes. Actual ROUTE/EROD/DEPOS chain with constant C=.001,
initial load=.01, theta=0, phi=-2 and qostar=-1e-7 intends its first wet endpoint
at x=5e-8. DEPEQS mutates it to -9e-7, upstream of the segment. DEPOS returns
load=.900999904 instead of the independent .00325. For qostar=-1e-8 the endpoint
becomes -9.9e-7 and the first returned load is 90.0009995; the next trace reaches
18000. Final dry export remains zero, so checking only final load masks the
corrupted wet state and coordinate mutation.

Retained reproduction: `/tmp/route-u9-small-flow-probe.py`. The legacy guard is
the underlying source defect; the new boundary branch makes its effects relevant
to the candidate's claimed nonzero-inflow correctness. Add wet-prefix tests at
these scales and preserve the actual physical interval. A dry-export pass is
not sufficient disposition.

## P1 — ROUTE's initial nonzero boundary still uses a different capacity convention

`src/route.for:173–174` forms DU from raw ktrato*cinftc(2). DEPOS reconstructs
loads using the clamped, consistently rounded DEPCAP. For negative polynomial
capacity at x=0 these disagree and do not preserve the incoming boundary load.

Actual-chain driver with constant cinftc=-.001, q=.1, initial load=.01,
theta=0 returns load(.01)=.0090909088 and load(1)=9.0909096e-5. The consistent
C=0 solution gives .0082644628 and 8.2644628e-5, respectively: a 10% discrepancy.
Negative polynomial capacity is explicitly clamped elsewhere in this candidate,
so this is a remaining consumer of the shared-capacity assumption, not evidence
that negative transport is a valid physical capacity.

Retained reproduction: `/tmp/route-u9-negative-capacity-probe.py` changes only
the driver capacity. Use the same boundary capacity contract throughout and
retain a source test for this case. This finding establishes boundary inconsistency;
it does not by itself prove every negative-polynomial deposition interval is
otherwise scientifically valid. No production incidence is inferred.

## Verification and remaining boundaries

Independently ran the EROD and actual ROUTE chain suites: **80 passed in 4.04
seconds**; `git diff --check` passed. Existing positive-flow, ordinary negative
wet/dry, exact-zero and observer-parity tests pass. Source-range checks for
q=1e-42 and 1e-44 correctly produce the explicit `ROUTE boundary rate not
representable` failure rather than silently clipping a rate.

The finite-root handoff now derives DU from actual rounded load/capacity and
explicitly rejects unequal singular/unrepresentable states. No additional
concrete handoff/interface defect was found in the tested ordinary cases.
However, neither 80 source tests nor a successful dry final output closes the
two boundary cases above. Expanded chain tests and broad physical, particle,
native, Disturbed and Cedar evidence remain required before promotion.
