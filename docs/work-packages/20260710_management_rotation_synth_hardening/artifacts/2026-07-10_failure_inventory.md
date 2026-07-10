# Failure Inventory - `sacral-self-discipline`

## Incident Identity

- Run ID: `sacral-self-discipline`
- Run root: `/wc1/runs/sa/sacral-self-discipline/`
- Queue: `rq:agfields_run_wepp`
- Job ID: `5ced742c-5b8c-45ea-8d5e-054987448d24`
- Failed: 2026-07-10 18:46:35 UTC
- Duration before failure: 35.76 seconds
- Representative sub-field: 3733
- Representative field: 1479
- Representative parent WEPP ID: 621
- Representative Topaz ID: 2613

## Scan Scope and Result

The directory
`/wc1/runs/sa/sacral-self-discipline/wepp/ag_fields/runs/` contains 119 files of
each attempted input type: `.man`, `.run`, `.slp`, and `.err`. All 119 error files
contain the same WEPP failure family:

    *** ncrop read as N. Must be between 1 and 20 ***

No attempted hillslope completed successfully. The job canceled outstanding
futures after the first surfaced failure, so these 119 attempts are a subset of
the project's 6,626 sub-fields.

Observed `ncrop` histogram:

- 34: 52 runs
- 35: 26 runs
- 36: 10 runs
- 37: 5 runs
- 38: 4 runs
- 39: 5 runs
- 40: 1 run
- 41: 3 runs
- 42: 4 runs
- 44: 1 run
- 45: 2 runs
- 46: 1 run
- 47: 1 run
- 48: 2 runs
- 49: 1 run
- 50: 1 run

## Representative Reproduction

`p3733.man` reports 17 source segments: one canola management followed by the
same oat management sixteen times. The source management counts are:

- `canola,spr,MT,_cm8-wepp.man`: 2 plant definitions.
- `oats,spr,_CONV,_cm8-wepp.man`: 3 plant definitions.

The pre-repair synthesizer copies all definitions after prefixing their names:

    2 + (16 * 3) = 50 plant definitions

It correctly retains 17 simulation years, demonstrating that the overflow is
definition duplication rather than a crop-calendar expansion.

Source hashes:

- Canola: `819e32163aa4572113c5cd6d3d0002d1d885989a3bc885454cba5787650b3582`
- Oats: `b3860d9d88cad9527c11c7d1e9dca52749022bf2a7c9c520f214b72c1affc4f2`

## Failure Interpretation

The binary returned zero but did not print its successful-completion marker.
`wepp_runner.run_hillslope` correctly treats that as failure. Changing runner
success detection would hide an invalid management input and is outside scope.
