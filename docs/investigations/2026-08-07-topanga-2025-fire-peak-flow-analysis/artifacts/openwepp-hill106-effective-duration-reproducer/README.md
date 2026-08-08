# Hill 106 Effective-Duration Reproducer

These two input decks preserve the February 15, 1986 Hill 106 peak-flow
discontinuity for OpenWEPP development. They are identical except for two
management values in `p106.man`:

| Case | Maximum LAI | Initial canopy cover |
| --- | ---: | ---: |
| `baseline` | 5.0 | 0.70 |
| `dense-canopy` | 6.0 | 0.90 |

Both cases use the undisturbed no-restrictive-layer soil, first-horizon Ksat
of `35 mm/h`, PMET `Kcb = 1.20`, and `rawp = 0.8`. The climate, slope, soil,
run control, and hydrologic sidecars are byte-identical between cases.

## Reference Executable

The preserved result was generated with:

```text
/workdir/wepppy/wepp_runner/bin/wepp_260803
SHA-256: 4a5158e224c175ac06c760f1006cc19f7691a9bd28911d94788af2622ba178a5
```

From either case directory:

```bash
mkdir -p output
cd runs
/workdir/wepppy/wepp_runner/bin/wepp_260803 < p106.run
```

The run file requests `../output/H106.hbp` because the reference executable
uses the HBP hillslope-pass contract.

## Reproduced Event

The infiltration zone is nearly saturated before the February 15, 1986 event,
following `149.1 mm` precipitation during the preceding five days. The event
receives another `64.7 mm`.

| February 15, 1986 result | Baseline | Dense canopy |
| --- | ---: | ---: |
| Surface-zone saturation fraction before event | 0.99 | 0.98 |
| Total-profile water before event | 211.10 mm | 206.02 mm |
| Runoff | 43.47 mm | 44.05 mm |
| Effective rainfall intensity | 39.12 mm/h | 39.12 mm/h |
| `PeakRO` | 3.56 mm/h | 294.42 mm/h |
| Reported `EffDur` | 12.20 h | 0.150 h |

`EffDur` in the element output is not the rainfall-excess duration passed to
the peak solver. WEPP derives it after peak calculation as
`runtmp / peakro`, capped at one day. The duration collapse is therefore a
consequence of the peak jump, not an independently calculated shortening of
the storm.

The management mutation changes the event-date hydraulic state as follows:

| State | Baseline | Dense canopy |
| --- | ---: | ---: |
| LAI | 2.506 | 4.241 |
| Canopy height | 0.455 m | 0.779 m |
| Live biomass | 0.086 kg/m² | 0.164 kg/m² |
| Dead biomass | 0.461 kg/m² | 0.384 kg/m² |
| Rill width | 0.305 m | 0.336 m |

The immediate cause is a change in the kinematic peak calculation under a
near-saturated surface state. The exact regime transition remains to be
instrumented. An OpenWEPP diagnostic replay should record `drlast`, `remax`,
`ealpha`, composite friction, `apr`, the selected `hdrive`/`appmth` path,
`tstar`, `vstar`, and runoff before and after recession infiltration. This is
necessary to distinguish a physically meaningful saturation threshold from a
discontinuity in the approximate peak formulation.

## Integrity

The management-file checksums are:

```text
dcc6d714f6093f5d57574c0d9170b894ce97843696897274053c71b233e17251  baseline/runs/p106.man
8f82c4cfc3f733e1fdd42f12e209680c763849c570af949194408e535586f86b  dense-canopy/runs/p106.man
```
