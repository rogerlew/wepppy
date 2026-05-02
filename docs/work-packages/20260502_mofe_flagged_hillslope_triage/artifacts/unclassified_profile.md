# D_UNCLASSIFIED Profile

- population: 114 rows (from 132 flagged hillslopes)
- run/config breakdown:
  - cochlear-beriberi / disturbed9002-mofe: 79
  - ordained-incentive / disturbed9002-wbt-mofe: 35

## Distribution Table

| feature | min | p25 | p50 | p75 | max |
|---|---:|---:|---:|---:|---:|
| late_max_abs_ofe_closure_residual_mm_max_abs | 103.045700 | 167.381500 | 284.847000 | 499.587150 | 976.967000 |
| late_max_surface_pulse_proxy_mm_max_abs | 100.755700 | 165.395925 | 279.665750 | 497.948975 | 974.547000 |
| closure_residual_pct_of_rm_total | -8.930587 | -0.687052 | -0.279459 | 0.030940 | 3.180747 |
| closure_residual_total_mm | -5970.616884 | -422.151503 | -138.317781 | 20.711329 | 942.775778 |
| requires_scientific_review_days | 1.000000 | 2.000000 | 4.500000 | 10.000000 | 110.000000 |
| flagged_day_fraction | 0.000100 | 0.000100 | 0.000300 | 0.000700 | 0.007300 |
| late_outlier_ofe_id | 5.000000 | 7.000000 | 8.000000 | 10.000000 | 18.000000 |
| chain_surface_transfer_residual_m3_p99 | 0.000000 | 0.000000 | 0.000000 | 0.000001 | 0.000121 |
| chain_subsurface_transfer_residual_m3_p99 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.081720 |
| runoff_pass_vs_outlet_qofe_residual_m3_max_abs | 0.049547 | 9.804489 | 19.932818 | 35.730389 | 245.957940 |
| soilwater_to_porosity_fraction_p99 | 0.747692 | 0.958994 | 0.988100 | 0.996424 | 0.999883 |
| soilwater_gt_porositycap_days | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |

## Topology Counts

- outlet outlier rows: 113
- interior outlier rows: 1
- first-OFE outlier rows: 0
- null outlier rows: 0

## Day-Band Counts

- <= 3 days: 52
- 4-29 days: 57
- >= 30 days: 5

## Summary

D_UNCLASSIFIED is heavily outlet-dominated, indicating the v1 gap is primarily magnitude/persistence separation rather than outlet-vs-interior topology. The day-band shape is bimodal-with-tail: many rows are <=3 days, many fall in 4-29 days, and a smaller persistent tail extends >=30 days, which v1 could not map cleanly. The v1 D3 trigger column is effectively dead here: `soilwater_gt_porositycap_days` stays at zero, so storage-pressure detection must pivot to `soilwater_to_porosity_fraction_p99` directly.
