# Palisades four-cell ET attribution results

## Conclusion

`pmetpara.txt` materially changes the modeled `Es`/ET partition, but it is not
carrying the Palisades peak-flow inversion through antecedent drying or reduced
burned hillslope runoff. PMET slightly *reduces* the burned-minus-undisturbed
runoff contrast relative to legacy ET. The primary inversion explanation
therefore remains sub-daily runoff timing and channel aggregation, not PMET
soil evaporation.

## Design

All 278 `upset-reckoning` hillslopes were run in four cells with
`wepp_260803_hill`:

| Land state | PMET (`pmetpara.txt`) | Legacy ET (no `pmetpara.txt`) |
|---|---:|---:|
| Burned SBS mosaic | 278 | 278 |
| Undisturbed | 278 | 278 |

The 1,112 hillslope simulations each produced and passed validation on a
16,802-row, 25-column daily water-balance file. `wepp_ui.txt` and the other
runtime sidecars were retained in every lane. No watershed or channel run was
performed.

The original undisturbed Omni WEPP inputs had been pruned, so its hillslopes
were reconstructed using the canonical undisturbed management for each NLCD
class and the original, unmodified soil file retained beside each disturbed
soil variant. This reconstruction closely reproduces the retained original
Omni PASS runoff signal: daily runoff-volume correlation is 0.9991 and the
record-total scaling ratio differs from the burned control by only 0.15
percentage point (1.0796 versus 1.0812). That common scaling reflects the
different area/output bases, not scenario drift.

## Annual response

Median annual area-weighted results across the 46 climate years are:

| Cell | Ep (mm) | Es (mm) | Er (mm) | ET (mm) | Es/ET | Runoff (mm) | Full-profile soil water (mm) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Burned PMET | 89.08 | 119.76 | 0.00 | 211.56 | 0.566 | 68.72 | 149.78 |
| Burned legacy | 92.39 | 94.00 | 28.07 | 216.89 | 0.425 | 66.79 | 149.17 |
| Undisturbed PMET | 288.16 | 23.02 | 0.00 | 308.55 | 0.074 | 64.49 | 107.21 |
| Undisturbed legacy | 328.93 | 2.59 | 2.10 | 333.48 | 0.008 | 61.00 | 102.97 |

PMET increases median burned `Es` by 25.77 mm/year and undisturbed `Es` by
20.43 mm/year. Thus the burned-specific interaction is only +5.33 mm/year,
even though PMET raises burned `Es`/ET much more strongly (+0.141 versus
+0.067).

The hydrologically consequential responses run against the proposed drying
mechanism:

- PMET lowers total ET by 5.33 mm/year in burned and 24.93 mm/year in
  undisturbed hillslopes.
- PMET raises runoff by 1.93 mm/year in burned and 3.49 mm/year in
  undisturbed hillslopes.
- Consequently the PMET difference-in-differences for runoff is **-1.56
  mm/year**. PMET weakens rather than amplifies the burned-minus-undisturbed
  runoff contrast.
- PMET increases mean full-profile soil water in both states. It does not dry
  the burned profile.

The strong partition change remains a model-structure concern: PMET reports no
`Er` in these cells and moves atmospheric demand between `Ep` and `Es` very
differently from legacy ET. But total ET, storage, and runoff show that this is
not equivalent to excessive net water loss from the burned hillslopes.

## Previously flagged inversion events

For all 22 flagged outlet events, median seven-day antecedent values are:

| Cell | Antecedent Es (mm) | Antecedent Ep (mm) | Antecedent runoff (mm) | Pre-event soil water (mm) |
|---|---:|---:|---:|---:|
| Burned PMET | 6.07 | 2.48 | 37.37 | 242.45 |
| Burned legacy | 3.27 | 2.63 | 36.83 | 241.18 |
| Undisturbed PMET | 0.83 | 9.36 | 35.16 | 235.32 |
| Undisturbed legacy | 0.06 | 11.72 | 33.00 | 233.50 |

PMET does increase seven-day burned `Es` by 2.80 mm, compared with 0.77 mm in
undisturbed. Nevertheless, burned pre-event storage is 1.27 mm *higher* with
PMET, and burned antecedent runoff is 0.54 mm higher. Undisturbed PMET effects
on both storage and runoff are larger. The 30-day windows give the same
direction.

This breaks the proposed causal chain:

1. PMET does increase burned `Es` partitioning.
2. It does not produce lower burned antecedent soil storage.
3. It does not reduce burned hillslope runoff on inversion events.
4. It therefore cannot explain why comparable burned runoff is delivered to
   the outlet in a broader, lower hydrograph.

## Daily magnitude check

Watershed-average burned PMET `Es` peaks at 3.86 mm/day, with a 99th percentile
of 2.42 mm/day. No cell has a watershed-average `Es` day at or above 10 mm.
This is not the Stevens Canyon 10--15 mm/day failure signature.

A subsequent like-for-like replay supersedes that informal Stevens magnitude:
the canonical area-weighted Stevens burned-PMET maximum is 4.96 mm/day versus
3.86 mm/day here. The cross-site ratio is 1.28, not eight, and the corresponding
99th-percentile ratio is only 1.09. See the
[`counterfactual results`](../../../../work-packages/20260803_stevens_palisades_es_counterfactual/artifacts/results.md).

## Interpretation boundary

This experiment diagnoses daily hillslope runoff generation, ET, and storage.
It cannot generate a new outlet peak because watershed routing was deliberately
excluded. The pre-existing five-minute channel results remain decisive for the
peak inversion: flagged burned hydrographs have median outlet width50 of 0.92
hour versus 0.46 hour undisturbed, while the undisturbed/burned peak ratio is
1.34 at a runoff-volume ratio of 0.94.

The combined evidence supports this disposition:

> PMET `Es` is a material partitioning artifact and a poor basis for native
> ET interpretation, but it is not a material causal contributor to the
> Palisades peak-flow inversion. Continue investigating hillslope response
> timing and routed synchronization; do not spend the next inversion study on
> PMET antecedent drying.

## Reproducibility and artifacts

- [Runner](run_four_cell_et.py)
- [Input and binary hash manifest](input-manifest.json)
- [Annual results](four-cell-annual.csv)
- [Four-cell summary](four-cell-summary.csv)
- [Factorial interactions](four-cell-interactions.csv)
- [Flagged-event windows](four-cell-flagged-event-windows.csv)
- `four-cell-daily.csv.gz` contains the compact daily area-weighted series.
- [Annual ET partition figure](../../figures/four-cell-et/four-cell-annual-et-partition.md)
- [Es fraction and runoff figure](../../figures/four-cell-et/four-cell-es-fraction-and-runoff.md)
- [Flagged-event antecedent figure](../../figures/four-cell-et/four-cell-flagged-event-antecedent-state.md)

Runtime lanes were removed after aggregation. The production project and
`/workdir/wepp-forest_260430_baseline` remained unchanged.
