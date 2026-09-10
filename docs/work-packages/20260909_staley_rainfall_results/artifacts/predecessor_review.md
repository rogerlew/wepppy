# Predecessor and Climate readiness review

Read-only review, 2026-09-10 05:15 UTC at WEPPpy `264b54845`. This assesses
integration readiness; it is not a fresh independent code/security review or a
rerun of the predecessor's tests.

## M1 foundation

The accepted `docs/m1_predictors.md` contract and closed package evidence record
50 focused tests, 8,016 full-suite passes and 72 skips. An external-mask regression
was added after full-suite collection and passed focused/security reruns; do not
claim that exact 50-case set was included in the earlier full run.

The rebuilt Wallow assessment has 12,973 basin cells with full support:
T=0.1894704386032529, F=0.6141950971236625, S=0.43397823632668575.
The 11.6757 km² basin retains the accepted area warning. Earlier July 1 evidence
has unknown T and null probabilities; final June 23 evidence is complete. Keep
these assessment identities separate. Source/evidence paths live in the closed
[M1 validation record](../../20260909_staley_m1_predictors/artifacts/validation.md).

`integration.evaluate_m1_scenarios(bundle, scenarios)` accepts a dict and
(duration, accumulation_mm) pairs, invokes the scalar engine and returns null
probability when any predictor is null. It preserves warnings and source kind.
It does not authenticate a persisted manifest or validate its full schema/
artifact lineage. A new local loader must define that boundary before composing
results; do not reinterpret its existence as an existing file-reading contract.

## Climate precedent and implications

Inspected `wepppy/nodb/core/climate_artifact_export_service.py`:
`export_cli_parquet` exports peak_intensity_15/30/60 in mm/hour, source year,
month/day and sim_day_index. Retain source fields and define event identity
explicitly; dates or simulation indices alone are not presumed unique.

The frequency export filters precipitation >0, counts distinct numeric years
among those rows, uses shared `weibull_series(..., method="pds")`, ranks positive
intensities separately for each duration, clamps indices exceeding sample count,
and rounds CSV numbers to two decimals. Missing duration data produces zeros.
These zeros are not design rainfall. Sparse-duration clamping is a material
edge case for contract review. A zero event intensity and a frequency placeholder
are different contexts and require separate policies.

The shared rank helper assigns indices across the supplied recurrence set;
subset calls can therefore differ from calls using the full supported set.
Verify rank parity using the same recurrence request and year count as Climate
before selecting only 1/2/5/10-year outputs. Do not silently fork the estimator.
If correction/extraction across the Climate owner is needed, scope and approve
it separately before editing that owner.

NOAA output is `atlas14_intensity_pds_mean_metric.csv` under `Climate.cli_dir`.
Its download can be absent even after a successful climate build. Inspect actual
CSV metadata/headers and existing readers before coding. NOAA frequency values
are design scenarios, not dated storm observations. This scaffold performs no
network acquisition or actual NOAA file-validation claim.

## Readiness conclusion

The numerical/predictor foundation supports a bounded local M1 result package.
Remaining gates are adapters, input identity, missing/sample policies and result
schemas. A proposed CLIGEN/NOAA source selector, 12-scenario matrix and UI defaults
are not yet approved production behavior. No new blockers in the completed
predictor contract were identified by this read-focused review.
