# Stevens–Palisades peak soil-evaporation decomposition

## Result

The like-for-like replay does **not** reproduce an eightfold cross-site peak
contrast. Burned-PMET area-weighted `Es` peaks at 4.96 mm/day in Stevens Canyon
and 3.86 mm/day in Palisades, a ratio of 1.28. Their 99th percentiles are 2.64
and 2.42 mm/day, a ratio of 1.09. The previously discussed 10–15 mm/day Stevens
signature is not present in the canonical area-weighted daily fixture.

## Counterfactual decomposition

| Quantity | Stevens Canyon | Palisades |
|---|---:|---:|
| Observed area-weighted peak `Es` (mm/day) | 4.959 | 3.863 |
| Perfect-synchronization upper bound (mm/day) | 5.181 | 3.958 |
| Observed/bound synchronization efficiency | 0.957 | 0.976 |
| Peak-day `Ep + Es` (mm/day) | 10.740 | 5.049 |
| Peak-day upper-layer soil water (mm) | 293.56 | 170.27 |
| Peak-day rain plus snowmelt (mm) | 13.50 | 0.00 |
| Prior-seven-day rain plus snowmelt (mm) | 31.00 | 48.87 |

Perfect synchronization raises the Stevens peak by only 0.222 mm/day and the
Palisades peak by 0.094 mm/day. It slightly widens the cross-site difference
from 1.096 to 1.224 mm/day. Spatial synchronization therefore cannot explain
the contrast; Palisades is already marginally more synchronized by this metric.

The strongest discriminator is total evaporative throughput on high-`Es`
days, not a larger soil share. Across each site's top 100 `Es` days, Stevens
has median `Ep + Es` of 7.79 mm/day and median `Es/(Ep+Es)` of 0.455;
Palisades has only 3.62 mm/day of `Ep + Es` but a larger soil fraction of
0.770. Stevens therefore produces more absolute `Es` despite allocating a
smaller fraction of ET to soil. More aggressive PMET soil partitioning at
Stevens is not the primary cross-site explanation.

Water availability lets the larger throughput be realized. Stevens' top 100
days occupy a wetter modeled upper-layer state and usually coincide with daily
rain or snowmelt (median 10.7 mm/day). Palisades' top `Es` days usually occur
after recharge (median daily `RM` is zero). Absolute soil-water values are not
portable across sites because profiles and capacities differ, so this is
evidence of water coincidence, not an interchangeable storage experiment.

## Interpretation

The supported ordering is:

1. Stevens' high-`Es` tail occurs under roughly twice the realized daily
   evaporative throughput of Palisades.
2. Its surface remains wet enough, often through same-day rain or snowmelt,
   for PMET to realize part of that throughput as soil evaporation.
3. Low-LAI and low-residue management permits a substantial soil share, but
   Stevens does not have the larger soil share of the two sites.
4. Hillslope synchronization contributes less than 0.13 mm/day to the
   cross-site gap and operates in the wrong direction as a primary cause.

WEPP reports realized `Ep` and `Es`, not the intermediate PMET terms. Fully
separating meteorological reference ET from water and vegetation constraints
would require an instrumented diagnostic binary. That narrower experiment is
not warranted by an alleged eightfold contrast, because that contrast failed
reproduction.

## Reproducibility

- [`run_counterfactual.py`](run_counterfactual.py) replays all 278 Palisades
  burned-PMET hillslopes and parses all 13 Stevens hillslopes.
- [`site-summary.csv`](site-summary.csv) contains site peaks and bounds.
- [`hillslope-maxima.csv`](hillslope-maxima.csv) contains the individual maxima
  used for the synchronization counterfactual.
- [`top-es-days.csv`](top-es-days.csv) contains the top-100 samples.
- [`peak-es-counterfactual.md`](peak-es-counterfactual.md) is the figure
  sidecar.

Every Palisades replay used `wepp_260803_hill`, `pmetpara.txt`, and the source
`wepp_ui.txt`; the runner verifies the PMET marker and byte-identical UI
sidecar. Temporary lanes were removed. No WEPP source or production tree was
modified.
