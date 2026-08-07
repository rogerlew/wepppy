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
- [`fixtures/hill-106/windows-reconstruction/burned-man-ballpark/`](fixtures/hill-106/windows-reconstruction/burned-man-ballpark/)
  — factorial management screen and a 40-year LAI `2.25` lane that closely
  reproduces Elliot's burned runoff, ET, lateral flow, and daily lateral-flow
  maximum.

## Next Steps

- Preserve run metadata, inputs, output inventories, and checksums before
  changing or rerunning either working copy.
- Build an event-level burned/undisturbed comparison from raw output using
  same-date comparisons as well as independently ranked return periods.
- Trace the precise variables included in watershed runoff and peak-discharge
  products before attributing differences to lateral flow.
- Reproduce the Hill 106 experiment with documented executable versions and
  byte-level input transformations.
- Identify suitable observed records and verify watershed, units, period of
  record, missing-data treatment, and drainage-area normalization before using
  them for model evaluation.
