# Omni MOFE versus manual landuse parameterization audit

Status: Active 2026-09-18

This read-only work-package audits the completed Omni children in the production run `ventilated-gag` against the manual Modify Landuse workflow and its MOFE implementation. It does not rebuild, rerun, or mutate the production run. The audit records persisted scenario definitions, MOFE landuse assignments, generated landuse/soil artifacts, and watershed metrics, then separates expected workflow differences from potential parameterization defects.

## Scope and acceptance

The production source is `wepp1:/geodata/wc1/runs/ve/ventilated-gag` at the time of collection. The Omni parent configuration is `canada-wbt-mofe.cfg`. The observed children are `uniform_low`, `uniform_moderate`, `uniform_high`, `prescribed_fire`, `thinning_40_75`, and `thinning_65_85`; the parent also contains an `undisturbed` result row. Manual comparison means the behavior of `Landuse.modify()` and the Modify Landuse route, not an invented production mutation.

The user tolerance is interpreted as a diagnostic expectation, not byte equality: severity/treatment metrics should be within 20% where the two workflows represent the same intervention, and scenario rank order should remain consistent. A comparison is not considered paired when the manual workflow would require a different spatial selection or a different thinning option.

## Deliverables

- `prompts/active/omni_mofe_manual_parameterization_audit_execplan.md`: living execution plan.
- `artifacts/raw/`: read-only copies of the production Omni manifest, persisted NoDb state, generated parquet summaries, and representative audit inputs.
- `artifacts/omni_manual_comparison.csv`: machine-readable metric and parameterization comparison.
- `audit.md`: findings, discrepancy dispositions, and recommended follow-up.
- `scripts/audit_compare.py`: repeatable local analysis of the captured evidence.

## Initial disposition summary

The Omni child definitions are internally explicit: low/moderate/high use distinct management keys and soil descriptions, prescribed fire and thinning are restricted to the forest classes, and MOFE assignments cover 455 hillslopes and 1,065 OFE segments. Omni rebuilds that complete structure, but treatment application is selective: ineligible OFE segments retain their prior management. The manual workflow is assignment-based: it validates a management key, rewrites every selected hillslope and every OFE segment for that hillslope, rebuilds MOFE inputs, and preserves the selected management parameters.

The production outputs show a high-risk discrepancy requiring follow-up: `uniform_low` and `uniform_moderate` have identical watershed sediment discharge (237.3 tonne/yr), water discharge (20,046,158 m3/yr), hillslope soil loss (121.6 tonne/yr), channel soil loss (234.4 tonne/yr), and sediment-delivery ratio (0.667), despite distinct persisted classes (`406` versus `418`) and distinct soil descriptions. This fails the requested severity rank-order signal and is not explained by byte-level tolerance. It is dispositioned as **investigate / do not silently waive**; no production fix is authorized by this audit.

The thinning options are not a parity defect: Omni exposes only the configured `40% canopy/75% ground` and `65% canopy/85% ground` choices in this run, while the manual catalog supports additional combinations. They are different parameter selections, so only direction/rank checks are valid until a like-for-like manual run exists.
