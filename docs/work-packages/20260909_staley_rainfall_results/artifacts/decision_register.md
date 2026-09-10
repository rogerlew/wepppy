# Rainfall/results decision register

Status: proposals, 2026-09-10 05:15 UTC. Existing scalar numerical policy is
accepted in ADR-0056; do not re-decide endpoint, inverse or overflow behavior.

| ID | Recommendation / question | Gate |
| --- | --- | --- |
| R01 | Support requested 1/2/5/10-year × 15/30/60-minute design scenarios; keep source explicit (CLI-derived or NOAA), with no silent substitution. | Ratify the matrix. Backend should require explicit source; browser default can remain deferred. Missing requested combinations retain unavailable rows. |
| R02 | Derive full-precision CLI frequency values from parquet using the existing Climate-owned rank method and selection context; retain rounded CSV as provenance/parity evidence. | Verify full recurrence-set parity, positive-duration sample counts and rank clamping. Recommend unavailable when a requested rank lacks support, rather than silently using the last observation; this deviation needs explicit approval/ADR. Do not repair Climate globally in this package. |
| R03 | Catalog wet CLI rows as event scenarios; retain original row/date/simulation fields and duration-specific validity. | Freeze duplicate/invalid dates, zero/negative/nonfinite intensities, missing duration columns and ordering policy. Recommend identity from snapshot hash plus stable original row ordinal; invalid/missing duration should not discard other valid durations. |
| R04 | Inverse targets supplied explicitly by caller, no backend default. | 50%/75% UI defaults can wait. Use accepted available/unavailable/nonunique scalar statuses; frequency source does not affect inverse thresholds. No automatic recurrence assignment. |
| R05 | Long-form local results and manifest with explicit units/status/reasons; bounded event listing and event-detail query. | Benchmark parquet/materialized versus on-demand design on a representative catalog before final schema. One watershed only; no public endpoint or catchment selector. |
| R06 | Validate version-1 predictor bundle and expected hashes, freeze source lineage and preserve warning/assessment identity. | Define bounded loader, allowed relative artifact paths, stale/mutated input behavior and numeric/predictor availability consistency before code. Do not reopen project paths embedded in provenance. |
| R07 | Report record length, wet-event years, duration sample counts and frequency method. | No unapproved sample-size cutoff or annual debris-flow probability. Decide behavior for unsupported short records explicitly; ten years permitting a 10-year estimate is not a precision guarantee. |

Keep current postfire predictors fixed for all events, including multidecade
synthetic climate catalogs. Do not simulate recovery, combine duration
probabilities, reconstruct a hyetograph, or label NOAA estimates as observations.
