# H2637 Ablation Evaluation Summary

- Generated: 2026-04-30
- Incident package: `/workdir/wepp-forest/docs/ablation/20260430_uncapped-spectacular_h2637_hillslope_closure-spike`
- Source run: `wepp1:/geodata/wc1/runs/un/uncapped-spectacular`
- Target hillslope: `H2637` (`p2637.run`)

## Lane Matrix Executed

1. `C000` Linux replay with production binary `wepp_260429_hill` (copied from wepp1).
2. `C010` Linux comparator replay with historical binary `wepp_dcc52a6_hill`.
3. `C020` Windows comparator replay on `blarhg` with `C:\src\wepppy-win-bootstrap\bin\wepppy-win-bootstrap.exe`.

All three lanes completed successfully through simulation year 34 (success markers present).

## Key Closure Findings

Primary evidence: `incident_snapshot/lane_day44_legacy_closure.csv` and `incident_snapshot/lane_closure_summary.csv`.

- Source + C000 reproduce the day-44 anomaly:
  - `day44_hillslope_error_mm_legacy = -180.31779`
  - dominant OFE residual on day 44: `OFE 19 = -180.4590 mm`
  - OFE 14-18 remain small (`~0.008` to `0.019 mm`)
- C010 (`wepp_dcc52a6_hill`) does not reproduce the day-44 anomaly:
  - `day44_hillslope_error_mm_legacy = +0.12130`
- C020 (`wepppy-win-bootstrap.exe`) does not reproduce the day-44 anomaly:
  - `day44_hillslope_error_mm_legacy = +0.13619`

## Erin Claim Check

Evidence supports two parts and contradicts one part:

- Supported: there is a large day-44 anomaly in the production/source lineage.
- Supported: day 45 is near-zero in all tested lanes (source `-0.0482 mm`, comparators near zero).
- Not supported by lane evidence: the day-44 spike does **not** begin at OFE 14 in this replay; the dominant error term is OFE 19.

## Output Provenance

- Incident docs snapshot:
  - `incident_snapshot/incident.md`
  - `incident_snapshot/notes.md`
  - `incident_snapshot/matrix.csv`
- Key machine artifacts:
  - `incident_snapshot/lane_closure_summary.csv`
  - `incident_snapshot/lane_day44_legacy_closure.csv`
  - `incident_snapshot/day44_ofe_errors_legacy_by_lane.csv`
  - `incident_snapshot/lane_output_hashes.csv`
  - `incident_snapshot/C020_blarhg_winbootstrap_env.txt`

## Residual Risks

1. This package attributes behavior to binary lineage/platform lanes but does not isolate routine-level causality inside `wepp_260429_hill`.
2. Scope is one hillslope (`H2637`); prevalence across additional hillslopes in `uncapped-spectacular` is not yet quantified.
3. No patch candidate was promoted, so fuzzy-regression gates were intentionally deferred.
