# Rainfall/results decision register

Status: resolved for local implementation, including explicit owner approval of
R02. The table retains initial recommendations and gates; the execution
disposition below records their resolution. Existing scalar numerical policy
remains accepted in ADR-0056.

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

## Execution disposition (2026-09-09 Pacific)

R01, R03–R06 are selected for the authorized local implementation in the
canonical contract's two "Execution contract" sections. Frequency source,
durations, intervals and inverse targets remain explicit caller arguments.
The measured materialized strategy preserves bounded deterministic queries;
reopening additionally checks scalar parity. No browser defaults are selected.
R07 preserves Climate wet-year count and full recurrence context, reports sample
counts and unsupported record lengths, and adds no adequacy cutoff.

**R02 accepted by explicit operator response “YES”.** The owner approved the
recommended unavailable result for a CLI rank beyond positive-sample support.
Return `insufficient_positive_samples`, preserve requested rank/sample count,
and leave rainfall/probability null. This replaces the temporary refusal gate;
flagged clamping was rejected because it could appear to be a supported estimate.
Climate’s own clamped CSV export remains unchanged and is checked as provenance.

Positive infinity makes CLI design unavailable for the affected duration rather
than shifting valid ranks by dropping the sample. NaN/negative/zero exclusions
match the positive-rank precedent. ADR-0062 records parameterization, alternatives,
execution provenance and the explicit approval.
