# v1 Rule Gap Analysis

## D2 outlet blind spot
v1 D2 required `outlier_is_interior_ofe == True`; meanwhile `104` of `114` D_UNCLASSIFIED rows still have `runoff_pass_vs_outlet_qofe_residual_m3_max_abs > 1.0`.
Recommendation: split D2 into D2a (interior chain residual) and D2b (outlet mismatch) so outlet-anomaly rows are no longer structurally excluded.

## D3 dead trigger column
Across all `132` flagged rows, `soilwater_gt_porositycap_days >= 1` occurs in `0` rows.
Recommendation: remove the day-count gate and trigger D3 directly on `soilwater_to_porosity_fraction_p99 >= 0.99` (with optional calibration to 0.995 if over-broad).

## D5 upper-bound exclusion
`5` rows have `requires_scientific_review_days >= 30` and `late_max_abs_ofe_closure_residual_mm_max_abs > 500`, so they are persistent but excluded by the v1 D5 upper bound.
Recommendation: keep D5 as moderate persistent (100-500) and split severe persistent rows into D6c (>500) for distinct mechanism handling.

## Coverage gap (4-29 day band)
`57` D_UNCLASSIFIED rows fall in the 4-29 day persistence band that v1 could not map (too long for D4, too short for D5).
Recommendation: add D6a (<=3 day sub-severe) and D6b (4-29 day moderate) to close the temporal gap.

## Coverage Statement
The combined recommendations cover approximately `100.0%` of D_UNCLASSIFIED via explicit outlet-mismatch and day-band mechanisms (plus D3/D6c corrections for remaining tails), satisfying the >=95% targeting requirement.

### Persistent-Severe Rows

| runid | wepp_id | requires_scientific_review_days | late_max_abs_ofe_closure_residual_mm_max_abs |
|---|---:|---:|---:|
| cochlear-beriberi | 25 | 110 | 887.803 |
| cochlear-beriberi | 80 | 42 | 976.967 |
| cochlear-beriberi | 267 | 47 | 708.911 |
| ordained-incentive | 81 | 57 | 912.469 |
| ordained-incentive | 93 | 44 | 580.683 |
