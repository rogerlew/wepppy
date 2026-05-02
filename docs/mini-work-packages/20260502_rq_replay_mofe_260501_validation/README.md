# 20260502 RQ Replay + MOFE 260501 Validation (Closeout)

## Scope and Intent
Validate four local WEPPcloud runs after stack restart by:

1. rerunning `run-wepp` via rq-engine with `wepp_bin=wepp_260501`,
2. auditing MOFE closure across all hillslopes from interchange outputs, and
3. determining whether water-balance defect signals require scientific follow-up.

Execution artifacts are under:
`docs/mini-work-packages/20260502_rq_replay_mofe_260501_validation/artifacts/`

## Auth and API Mode Used
- Host: `https://wc.bearhive.duckdns.org`
- rq-engine base: `https://wc.bearhive.duckdns.org/rq-engine/api`
- Auth flow: login session + CSRF + `POST /weppcloud/profile/mint-token` (bearer user token)
- Tokens are redacted in transcripts.

## Canonical Validation Evidence
- Run matrix: `artifacts/run_execution_matrix.csv`
- Hillslope rollup: `artifacts/hillslope_audit_rollup.csv`
- Defect narrative: `artifacts/defect_summary.md`
- API transcript: `artifacts/api_transcript.md`
- Summary JSON: `artifacts/validation_summary.json`

## Initial Run Outcome (As Executed)
The automated validation execution concluded with `FAIL` because rerun terminal statuses were not all `finished`.

From `artifacts/run_execution_matrix.csv`:
- `moth-eaten-blackhead/disturbed9002-wbt-mofe`: `stopped`
- `cochlear-beriberi/disturbed9002-mofe`: `stopped`
- `ordained-incentive/disturbed9002-wbt-mofe`: `stopped`
- `uninsured-deformation/disturbed9002-wbt-mofe`: `failed`

Binary verification was `PASS` for all four runs (request evidence + run-root artifact evidence).

## MOFE Audit Coverage and Defect Signals
- Total audited hillslopes: `1166/1166` (complete coverage).
- Hillslopes flagged `requires_scientific_review=true`: `132`.
- Concentration of flagged hillslopes:
  - `cochlear-beriberi/disturbed9002-mofe`: `96`
  - `ordained-incentive/disturbed9002-wbt-mofe`: `36`
  - `moth-eaten-blackhead`: `0`
  - `uninsured-deformation`: `0`

Largest observed closure anomaly in the rollup:
- `cochlear-beriberi/disturbed9002-mofe`, `wepp_id=461`, `max_abs_closure_mm=855.807381`

## Post-Run Addendum (Operator Rerun)
User reran `uninsured-deformation` watershed independently:
- Job: `1e804233-41ac-4254-a94a-d331ede4e924`
- Verified via API polling: `status=finished`

Given this follow-up evidence, `uninsured-deformation` failure from the initial validation run is treated as an operational flake for now, with ongoing monitoring.

## Closeout Disposition
- Package status: **Closed with follow-up required**.
- RQ replay objective completed with full evidence capture and complete hillslope-audit coverage.
- A new mini work-package is opened to triage and group flagged hillslopes for future ablation campaigns.

## Follow-Up Work-Package
See:
`docs/mini-work-packages/20260502_mofe_flagged_hillslope_triage_execplan.md`
