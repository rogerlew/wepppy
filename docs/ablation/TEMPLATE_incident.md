# Incident Report: <title>

- `incident_id`: `<YYYYMMDD_runid_scope_signature>`
- `status`: `draft|active|resolved`
- `author`: `<name>`
- `date_utc`: `<YYYY-MM-DD>`
- `host_scope`: `dev|prod|mixed`

## 1) Summary

Describe the failure in 2-5 lines:

- failing run/config:
- failure signature:
- first observed time:
- current impact:

## 2) Impact and Blast Radius

- affected hosts:
- affected runids/configs:
- user-facing effect:
- severity:

## 3) Baseline Reproduction

- source error file:
- baseline command:
- baseline result (`PASS|FAIL|ERROR`):
- baseline signature (signal/backtrace/success-marker status):

## 4) Ablation Findings

Link matrix rows or case ids that matter:

- first known failing case:
- nearest passing case:
- minimal failing delta:
- confidence level (`low|medium|high`):

## 5) Evidence Index

- `matrix.csv`: `./matrix.csv`
- `notes.md`: `./notes.md`
- logs root: `./artifacts/logs/`
- diffs root: `./artifacts/diffs/`
- repro root: `./artifacts/repro/`
- environment capture: `./artifacts/env/`
- artifact manifest: `./artifacts/manifest.csv`
- checksums: `./artifacts/checksums.sha256`

## 6) Root Cause Hypothesis

State the leading technical hypothesis and why competing hypotheses were rejected.

## 7) Remediation Decision

- selected fix:
- why this fix:
- rollback plan:
- required validations:

## 8) Production Safety Notes

If `host_scope` includes production:

- confirmation no in-place mutation of original `/wc1/runs/...` inputs
- containment steps used
- any operator approvals

## 9) Follow-Up Work

1. `<item>`
2. `<item>`
3. `<item>`

