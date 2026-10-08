# Dewpoint clipping sensitivity and OpenET comparison

Status: Closed 2026-10-08 (research execution).

All 18 paired runs and 36 OpenET series are complete. Existing clipping gives
lower monthly MAE/RMSE in all 36 site–product comparisons, including the
secondary low-snow assessment. Retain current behavior and defer a general
disable option; see [results and figures](artifacts/results.md). This bounded
GridMET study does not validate PRISM-specific humidity or change production.

Determine whether evidence supports retaining the existing climate preparation
rule, `Td = max(raw Td, source Tmin)`, or offering an advanced option to disable
it. Anurag specified the existing rule; this study does not change production
defaults, climate clients, or UI. Preserve original humidity and dewpoint data.

## Study contract

Run paired standalone WEPP hillslope experiments at multiple locations. Change
only daily dewpoint; preserve precipitation, storm timing, temperatures, radiation,
wind, soil, management, slope, executable, and initial conditions. Recover raw
dewpoint from retained source humidity using the existing climate formula and
verify that reclipping reproduces archived climate forcing before interpreting
the comparison. Retain original spatial temperature adjustments: the existing
GridMET multi-location workflow clips before those adjustments.

Select three hillslopes per watershed across three CONUS watersheds, spanning
elevation and aspect without selecting on response. Compare monthly 2016–2022
ET after the available historical spinup. Use the same histories in both arms.
Document vegetation, fire/management representativeness, spatial support, and
missing data before assigning observational meaning to OpenET agreement.

Use the official OpenET API with the user-provided `~/openet.key`. Retain public
request bodies and responses, never credentials or request headers. Prefer
hillslope polygon mean depths in mm, with ensemble and component-model series.
Missing ET is missing, not zero. Assess seasonal bias, monthly MAE/RMSE,
water-balance plausibility, and component spread. Hillslopes in one watershed
are correlated; they are not nine independent climate replications.

Report paired changes in ET, runoff, deep drainage, soil water and snow where
supported by output. Do not choose clipping solely by closeness to OpenET:
satellite ET uncertainty, prescribed vegetation and water storage can dominate.
No parameter tuning is part of the primary comparison. A user-facing control
requires a separate reviewed production change and parameterization ADR.

## Artifacts, compatibility and security

Additive offline research only; no production data/schema mutations. Extract
standalone model input fixtures with hashes and provenance; these are not cloned
WEPPcloud projects and make no application workflow validation claim. If actual
project cloning becomes necessary, use the supported fork/archive workflow.
Keep compact source fixtures, API evidence, execution manifests, summaries and
figures under this package. Preserve full execution evidence in a named study
directory and identify it in the manifest. Never modify source projects.

Reuse the existing scientific matrix-runner pattern from the Topanga investigation
and installed scientific libraries; no new dependency or service. Security impact
is limited to credential-bearing requests to `https://openet-api.org`, read-only
source projects, and bounded local executable runs. Disable cross-host redirects
for authenticated requests. Do not serialize credentials in exceptions or logs.

## Execution

See [the completed ExecPlan](prompts/completed/study_execplan.md) and
[tracker](tracker.md). Prior source evidence is in
[the dewpoint audit](../../investigations/20261008_prism_800m_bulk/dewpoint-source-audit.md).
