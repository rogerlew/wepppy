# Stochastic CLIGEN dewpoint clipping study

Status: Closed 2026-10-08 (existing-station research baseline).

All 180 paired cases completed and 2,344,980 daily rows passed artifact checks.
Clipping improves pooled seasonal-cycle RMSE and monthly distribution distance
in all 36 site–product comparisons, with modest annual ET effects. Large station
climate mismatch and generator quality diagnostics limit the policy conclusion.
See [results and figures](artifacts/results.md). Native stochastic production
behavior remains unchanged; location-matched evaluation is a separate follow-up.

Run native stochastic CLIGEN and a paired `Td = max(Td, Tmin)` treatment at
the same nine hillslopes used in the GridMET/OpenET study. Preserve the completed
study as immutable history. No production climate policy or UI changes.

## Registered design

Reuse the nine frozen hillslope fixtures, vegetation, soil, slope and common
`wepp_260803_hill` executable. Use the three projects' retained CLIGEN station
parameter files with ten declared seeds, 1001–1010, and their original historical
record lengths. Generate fully stochastic climates; do not feed observed daily
weather to CLIGEN. Copy each generated series and change only its daily dewpoint
to implement the floor. Apply the treatment throughout spinup and assessment.

Assess seven synthetic years per seed after at least 16 years of warmup. Synthetic
year labels 2016–2022 are bookkeeping, not observed-weather realizations. Compare
12-month climatologies and within-month distributions against the archived
2016–2022 OpenET series. Do not pair individual synthetic months with actual
calendar years. Report ten-seed variation and avoid treating hillslopes sharing
a station as independent climate replications.

The primary baseline uses the existing station parameterizations. Report station
versus hillslope precipitation and temperature differences explicitly; agreement
with OpenET can reflect that mismatch. Localizing station parameters would be
a separate, declared treatment rather than an implicit climate adjustment.
The existing-station baseline proceeded after the optional clarification window;
no localization was silently introduced into the experiment.

## Artifacts and compatibility

Additive standalone scientific fixtures only; no project cloning, schema changes,
new dependencies, model rebuilds, deployment or key access. Reuse retained public
OpenET evidence with hashes. Keep scripts, generation provenance, tables and plots
under `artifacts/`; large model outputs and logs reside in a named external study
directory. Preserve failed runs and never overwrite source projects or closed
work packages. Security impact is low: local executable runs and read-only
source fixtures, with no new authenticated network requests.

See the [completed ExecPlan](prompts/completed/study_execplan.md) and [tracker](tracker.md).
