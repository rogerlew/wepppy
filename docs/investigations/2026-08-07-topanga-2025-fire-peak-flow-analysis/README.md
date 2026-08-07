# Topanga 2025 Fire Peak-Flow Investigation

**Status: OPEN (`2026-08-07`).** This investigation reviews W. Elliot's July
2026 Topanga watershed analysis, reproduces its results, and expands the
analysis of burned-versus-undisturbed runoff and peak-flow behavior following
the January 2025 Palisades Fire.

## Starting Point

The supplied report compares these 43-year GridMET WEPPcloud runs:

- undisturbed original: `perceivable-fishnet`;
- burned original: `beatable-facial`;
- undisturbed working copy: `positional-mink`;
- burned working copy: `hand-to-mouth-drought`.

The report confirms an unexpected result: the undisturbed scenario has larger
2-, 5-, and 10-year peak-discharge estimates, while the burned scenario has
larger 20- and 25-year estimates. It explores antecedent rainfall, soil water,
lateral flow, storm intensity, anisotropy, hillslope-versus-watershed behavior,
and differences between WEPPcloud and WEPP Windows. These findings are the
investigation's starting hypotheses, not yet independently reproduced here.

## Investigation Questions

1. Can every reported return-period value and event date be reproduced from
   the archived WEPPcloud inputs and raw outputs?
2. Are the burned and undisturbed runs equivalent outside their intended
   management and soil parameterization differences?
3. What explains the peak-flow inversion: event ranking, antecedent state,
   lateral flow, spatially varying climate, hillslope timing, channel routing,
   or an interaction among them?
4. Why do the report's WEPPcloud and WEPP Windows hillslope water balances
   differ, and are the compared configurations truly equivalent?
5. How do modeled runoff volumes and peaks compare with appropriate observed
   Topanga-area streamflow records and alternative hydrologic estimates?

## Source Material

- [`artifacts/260806_Elliot_Topanga_Watershed_Peak_Flow_Analyses.pdf`](artifacts/260806_Elliot_Topanga_Watershed_Peak_Flow_Analyses.pdf)
  — W. Elliot, *Topanga Watershed Analyses: Before and After the Palisades
  Fire*, July 2026; supplied `2026-08-06`; 18 pages; SHA-256
  `871f823a8417a2f991db860e90c17f09329a6e0415e8fd485b33366dcbb88aee`.

The PDF is vendored unchanged and is tracked through the repository's global
Git LFS rule for `*.pdf` files.

- [`fixtures/hill-106/`](fixtures/hill-106/) — unchanged Hill 106 WEPPcloud
  inputs, hydrology sidecars, run logs, and generated outputs for both working
  copies, retrieved read-only from `wepp1` on `2026-08-07`.
- [`artifacts/windows-sidecar-ballpark.md`](artifacts/windows-sidecar-ballpark.md)
  — isolated Windows WEPP reconstruction showing that Elliot's unburned
  results match the lane with neither `wepp_ui.txt` nor `pmetpara.txt`; its ET
  interpretation is cross-referenced against the
  [Stevens Canyon legacy-ET ablation](../2026-08-03-stevens-canyon-peak-flow-inversion/artifacts/legacy-et-ablation-results.md).
- [`artifacts/bill-windows-replication-handoff.md`](artifacts/bill-windows-replication-handoff.md)
  — self-contained handoff for Elliot describing the Windows replication and
  the influence of the hourly seepage and Penman-Monteith sidecars.
- [`fixtures/hill-106/windows-reconstruction/burned-man-ballpark/`](fixtures/hill-106/windows-reconstruction/burned-man-ballpark/)
  — factorial management screen and a 40-year LAI `2.25` lane that closely
  reproduces Elliot's burned runoff, ET, lateral flow, and daily lateral-flow
  maximum.
- [`artifacts/kslast-anisotropy-calibration-study.md`](artifacts/kslast-anisotropy-calibration-study.md)
  — calendar-year 2020 soil calibration screens: 60 `kslast` × anisotropy
  cases, 42 horizon-Ksat × anisotropy cases, and 48 fixed-Ksat anisotropy ×
  PMET-Kcb cases. The closest reasonable candidate produces `9.35 mm` total
  runoff, still above the provisional `6.2 mm` target.

## Current Findings

- Elliot's `288 mm` WEPPcloud value is not calendar-year 2020 surface runoff.
  It is the long-term mean unburned Hill 106 surface runoff plus lateral flow:
  `121 + 167 mm/year`. His corresponding `242 mm` Windows value is likewise
  the long-term mean `220 + 22 mm/year`.
- The archived WEPPcloud Hill 106 result for calendar year 2020 is `9.74 mm`
  surface runoff plus `105.92 mm` lateral flow, or `115.66 mm` combined.
- The observed `6.2 mm` value is independently reproduced from the Los Angeles
  County Topanga Creek F54C-R calendar-year 2020 volume of `234 acre-feet`
  divided by its `18.0 square mile` drainage area. It is measured channel
  discharge and therefore is not a surface-runoff-only observation.
- The observed and modeled values remain provisional as a calibration pair:
  Topanga Creek is a nearby but different drainage area, and gauged discharge
  combines every source and loss operating upstream of the gauge.
- The Windows reconstruction closely reproduces Elliot's Hill 106 results
  without `wepp_ui.txt` or `pmetpara.txt`. The hourly seepage sidecar strongly
  increases modeled lateral flow, while PMET changes ET and the remaining
  water partition.
- Raising the restrictive-boundary conductivity from `0.00011` to
  `0.6 mm/h` reduces 2020 combined Hill 106 runoff from `115.66` to
  `12.16 mm` with the original anisotropy and Ksat. This is the dominant
  calibration response.
- Neither horizon Ksat nor reasonable anisotropy and PMET-Kcb tuning closes
  the remaining difference. With original Ksat, the closest screened case is
  `kslast = 0.6 mm/h`, anisotropy `1`, and `Kcb = 1.20`, producing `9.35 mm`
  runoff and `295.23 mm` ET. Most additional ET displaces deep percolation
  rather than runoff.

## Next Steps

- Build an event-level burned/undisturbed comparison from raw output using
  same-date comparisons as well as independently ranked return periods.
- Reconstruct calendar-year 2020 outlet flow for the complete WEPPcloud
  watershed, including routed surface flow, lateral flow, groundwater/baseflow,
  and channel losses, rather than treating one hillslope as the basin outlet.
- Identify a modeled basin that matches the F54C-R drainage area, or locate an
  observed record for the actual modeled watershed, before promoting any
  calibration parameter set.
- Constrain PMET Kcb and seasonal ET against independent vegetation or ET
  evidence before considering `Kcb = 1.20` a candidate value.
