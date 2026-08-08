# Hill 106 Ksat Peak-Flow Diagnostic

## Result

The February 14, 1980 Hill 106 response is caused primarily by how WEPP assigns
daily soil-water surplus to a subdaily runoff hydrograph. It is compounded by a
discontinuous switch between the approximate and characteristic peak solvers.

Increasing first-horizon Ksat from `20` to `35 mm/h` produces more infiltration
into an almost full profile. The daily water-balance calculation consequently
returns more water as surface surplus (`surdra`). In `irs.for`, WEPP does not
retain a physical time series for this returned water. It divides the complete
daily surplus by `durre` and adds that constant rate only to intervals where
rainfall excess is already positive:

```fortran
if (surpls.gt.1.0E-6) then
  if (durre.gt.0.0) then
    do ii = 1, nstemp - 1
      if (s(ii).gt.1.e-10) then
        s(ii) = s(ii) + surpls/durre
      endif
    enddo
  endif
endif
```

This representation compresses a larger saturation-excess volume into a
shorter period in the higher-Ksat case.

## Instrumented Operands

The diagnostic used the pinned `/workdir/wepp-forest_260430_baseline` source at
`2f65506d239b449bbb73c6820ff9cb949fa55158` in an isolated worktree. An
unmodified build reproduced the established event exactly before tracing.

| February 14, 1980 operand | Burned Ksat 20 | Burned Ksat 35 |
| --- | ---: | ---: |
| Final surface-runoff volume | 60.122 mm | 58.630 mm |
| Soil-water surface surplus, `surpls` | 36.999 mm | 51.637 mm |
| Rainfall-excess duration, `drlast` | 4536.60 s | 2478.44 s |
| Added surplus rate, `surpls/drlast` | 29.36 mm/h | 75.00 mm/h |
| Recorded pre-surplus `remax` | 34.69 mm/h | 19.35 mm/h |
| Maximum solver lateral-inflow rate after surplus addition | 64.05 mm/h | 94.35 mm/h |
| Ponding-time sentinel, `tp(2)` | 0 s | 5100 s |
| Selected solver | `APPMTH` | `HDRIVE` |
| Published `PeakRO` | 47.710 mm/h | 92.714 mm/h |

The higher-Ksat case has lower final runoff volume and lower recorded maximum
infiltration-excess rate. Its solver forcing is nevertheless much larger
because `51.637 mm` of daily surface surplus is divided by only `2478.44 s` and
added to the positive-excess intervals.

The resulting state is internally inconsistent if interpreted as a rainfall-
excess summary. For Ksat 20, `runoff/drlast` is `47.71 mm/h`, or `1.38` times
the recorded `remax`. For Ksat 35 it is `85.16 mm/h`, or `4.40` times the
recorded `remax`. The added surface-surplus rate is not incorporated into
`remax`, while the complete surplus volume is incorporated into `runoff` and
the solver input array.

## Solver-Branch Counterfactuals

We forced both cases through each existing solver without changing their event
inputs:

| Solver assignment | Ksat 20 peak | Ksat 35 peak | Ksat-35 increase |
| --- | ---: | ---: | ---: |
| Production branch | 47.710 mm/h (`APPMTH`) | 92.714 mm/h (`HDRIVE`) | 45.004 mm/h |
| Force `HDRIVE` | 61.751 mm/h | 92.714 mm/h | 30.963 mm/h |
| Force `APPMTH` | 47.710 mm/h | 85.162 mm/h | 37.452 mm/h |

The `tp(2) > 0` test accounts for part of the discontinuity: the Ksat mutation
changes `tp(2)` from the zero sentinel to `5100 s`, switching from `APPMTH` to
`HDRIVE`. It is not the primary source of the reversal. Even with a common
solver, the Ksat-35 peak remains much larger because the water-balance surplus
has already been concentrated into its shorter positive-excess duration.

## Defect Statement

WEPP combines a daily saturation-excess volume with a subdaily infiltration-
excess hydrograph by assigning the entire daily surplus uniformly over only
the already-positive rainfall-excess intervals. Ksat affects both the surplus
volume and the selected duration. The construction can therefore turn greater
infiltration into a much larger instantaneous lateral-inflow rate even when
total surface runoff decreases. It does not preserve a physically derived
subdaily timing for saturation excess and is not monotone with respect to
surface Ksat.

The independent `tp(2)` solver-selection test adds a second discontinuity.
A change in ponding-time representation switches between two peak algorithms
without a continuity constraint at the selection boundary.

The derived output `EffDur = runoff / PeakRO` occurs after both effects. It is
not causal.

## Implications

- The Hill 106 Ksat mutation is not evidence that increased conductivity
  physically concentrates infiltration-excess runoff.
- Similar daily runoff volumes do not constrain WEPP's peak because the daily
  surface-surplus volume is assigned an assumed subdaily timing.
- The Topanga burned-versus-undisturbed inversion can be influenced by this
  coupling whenever profile saturation produces appreciable `surdra`.
- Annual water balance, ET bias, and antecedent soil water remain separate
  questions. They affect how frequently saturation surplus occurs, but they do
  not validate its imposed within-storm timing.
- A repair requires a conservative, explicitly timed saturation-excess source
  and a continuous or consistently selected peak-routing method. Merely forcing
  one of the existing solvers does not remove the main defect.
