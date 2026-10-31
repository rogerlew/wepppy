# U6b consistency review and actual-ROUTE U7/U8 fixture

## U6b disposition

The two U6a transition-capacity blockers are closed in the isolated U6b prototype. Shared DEPCAP64 evaluates the retained REAL coefficients in double Horner arithmetic; DEPCAP makes one deliberate REAL conversion for comparisons against REAL loads. EROSTEP, EROCROSS, EROZERO and EROD postchecks now use this policy. The all-through-equality control remains intact. Independent source suite: **65 passed in1.04s**.

Reviewed prototype `/workdir/wepppy/out/roads-parameterization-program-20261031/erod-event-u6/probe` SHA-256:
- `src/erod.for`: `422d30692ac31327ee01a9ef8ea83b9543c46f9c1f985434fbd9037720847814`
- `src/runge.for`: `9d450d55beca548c714925d309774e9a4d0d8a40e08b248a413f187b31dc31bb`
- `src/depeqs.for`: `0b8229de965954d88e085c80644ac52c2bbab8c072877a4d0acdc28237a55d62`
- source tests: `eefd2652c25e2b26b17040c551a54fc5f14d95ff8c81ab54df4c7085f59933a7`

This supports diagnostic integration, not release promotion. Ordinary nonstiff RUNGE arithmetic remains deliberately unchanged. The broader exact-candidate gates, particle closure and separately confirmed caller consumers remain required.

## Actual ROUTE fixture, no physics mocks

The temporary fixture links real ROUTE, EROD, RUNGE, DEPOS, DEPEQS, DEPEND, ENRICH, XCRIT, ROOT, SHEAR, UNDFLO and CROSS. Observation-only WRITE statements in temporary ROUTE/DEPOS copies expose NDEP and DEPOS entry/exit states. The fixture initializes a single particle class with consistent water/settling parameters and uses actual native publication coordinates. No repository sources were edited.

Pattern to retain in repository: the existing compiler fixture in `tests/test_deposition_stable_solution.py`, extended to link the complete actual caller chain; preserve the source-hash receipt style of `tests/test_depend_full_fixture.py`. Do not replace ROUTE or ENRICH with stubs for this continuity test. Use a new bounded source test such as `tests/test_route_deposition_boundary.py` plus small JSON input/analytic-reference fixture. Keep observer instrumentation separate from the ordinary source build and assert observed/ordinary outputs agree.

### Confirmed U7 boundary loss

`src/route.for:167` uses the no-inflow approximation for abs(qostar)<.0011, although its comment says qostar=0. A finite nonzero wet inflow instead has the exact boundary condition DU=phi*(C-L)/qostar.

Positive-flow case: qostar=.001, qin=.001, qout=1.001, slplen1, phi2, initial L=.01, constant C=.001, theta=D=0, segment[0,1]. Actual trace:
- EROD returns NDEP at0 carrying L=.009999999776482582.
- ROUTE passes DU0 and that load to DEPOS.
- DEPOS reconstructs capacity and publishes first-grid L=.0010000000474974513.
- Independent exact first-grid solution is `.0010743802199930873`, from L(x)=C+(L0-C)*(q/(q+x))^phi using retained REAL inputs.

Negative-flow companion: qostar=-.001, qin=.001, qout0, phi=-2, with segments[0,.0005] and[.0005,1]. Flow ends at x=.001. The first actual DEPOS return at x=.0005 is `.00100000005` under DU0, versus the exact wet-domain `.00325` (subject to input rounding). Dry export remains zero. This confirms the same loss with the physically correct phi/flow signs.

Controls already executed:
- Ordinary q1 excessive incoming load enters DEPOS directly with DU approximately-.018 and matches the analytic solution.
- Ordinary interior transition with L0=.0007,C=.001,theta=.1,D0,q1 crosses at approximately.003 and gives first-grid L=.00169515959, matching independent `.0016951596917`.
- No-transition theta=D0 case preserves L=.0007.
- Exact q0 with C=x,L0=0,theta=.1,D0 preserves the no-inflow limit and produces L approximately.1 at the outlet.

Recommended U7 lane: exact qostar==0 selects the retained no-inflow formula; nonzero q uses the actual incoming load boundary condition. Perform the quotient/product in double before one REAL result conversion. Do not clamp an unrepresentable result into a plausible physical rate. Retain explicit zero, neighboring float32 values around both signs of the old .0011 cutoff, ordinary q1, and the negative wet-domain control. This lane is separately justified and should not silently alter the no-inflow formula or initialize deposition from an invented load.

### Confirmed U8 downstream capacity inconsistency

U6b's actual ROUTE path now establishes a valid normal transition, but DEPOS still evaluates its capacity polynomial in single precision. Two-segment fixture:
- q1,phi2,D=theta0,L0=1e-7.
- First segment[0,.49992], C=x*x-x+float32(.2500001).
- Second segment[.49992,1] has constant capacity equal to the double-evaluated first-segment endpoint (one REAL conversion).

Trace: U6b finds x=.499897063 with L approximately1e-7. DEPOS returns `9.36046618e-8` at x=.499920011, an approximately6.4% artificial reduction caused by endpoint polynomial cancellation. The native deposition rate is only `-5.59722535e-9`; shared capacity implies a load near1e-7 at that endpoint. On the next constant-capacity segment the load increases again to `9.81662254e-8` despite D=theta0. This is an actual shared-consumer accounting failure, not only a scalar EROD concern. Retain as a separate U8 lane replacing DEPOS capacity evaluation consistently, with endpoint and grid branches covered.

## Evidence

- `/tmp/review_route_fixture.py`: complete original source fixture builder, four initial controls.
- `/tmp/review_route_fixture_extra.py`: negative, exact-zero and U8 companions.
- `/tmp/erod-u7-route-fixture-review.json`: original inputs, full traces, source hashes, independent first-grid references.
- `/tmp/erod-u7-u8-route-extra-review.json`: additional full traces and hashes.

Each JSON receipt names the temporary observer directory containing actual driver and source copies. Retain baseline outputs before applying U7/U8, then rerun unchanged inputs against each lane independently and the combined candidate. Broader acceptance remains frozen.
