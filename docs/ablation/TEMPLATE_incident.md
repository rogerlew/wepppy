# Incident Report: <title>

- `incident_id`: `<YYYYMMDD_runid_scope_signature>`
- `status`: `draft|active|resolved|resolved-and-hardened|closed|mitigated-dev`
- `scope`: `hillslope|watershed|mixed`
- `author`: `<name>`
- `date_utc`: `<YYYY-MM-DD>`
- `host_scope`: `dev|prod|mixed`
- `contract_refs`: `<SC-...#INV-...|none|model_gap|requires_scientific_review>`

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
- fuzzy case results: `./artifacts/logs/fuzzy_case_results.csv`
- fuzzy failure ledger: `./artifacts/logs/fuzzy_failures.md`
- contract observations (required for policy-era `U*` lanes):
  `./artifacts/logs/contract_observations.csv`

## 6) Root Cause Hypothesis / Scientific Rationale

State the leading technical hypothesis and why competing hypotheses were rejected.
If this incident includes upstream mutation lanes, also capture:

- contract references for the root-cause hypothesis:
  `<SC-...#INV-...|model_gap|requires_scientific_review>`
- boundary disposition:
  `<invalid_input|inactive_process|valid_extreme|neutral_branch|bounded_transition|model_gap|requires_scientific_review>`
- process-level scientific rationale for each kept mutation,
- key assumptions,
- invariant checks used and results.

## 7) Remediation Decision

- selected fix:
- why this fix:
- rollback plan:
- required validations:
- non-regression gate status (if mutation lane):
- fuzzy-regression gate status:
- contract disposition match (if mutation lane):

## 8) Science Contract References

Use this section for upstream mutation lanes and unresolved model gaps.

Root-cause hypothesis references:
- `contract_refs`:
- boundary disposition:
- evidence:

Remediation decision references:
- `contract_refs`:
- boundary disposition:
- evidence:

Upstream mutation lanes:

| Lane ID | Contract refs | Boundary disposition | Observation evidence | Decision |
| --- | --- | --- | --- | --- |
| `U1` | `<SC-...#INV-...|none>` | `<disposition>` | `<path>` | `<keep|rollback|blocked>` |

Observation evidence path guidance:
- for policy-era `U*` lanes, point to concrete rows in
  `artifacts/logs/contract_observations.csv`.
- each observation row should use:
  `case_id,contract_id,invariant_id,contract_ref,status,observed_value,disposition,evidence_path,notes`.

Unresolved model gaps:

| Gap | Disposition | Evidence | Follow-up owner |
| --- | --- | --- | --- |
| `<gap>` | `model_gap|requires_scientific_review` | `<path>` | `<owner>` |

## 9) Production Safety Notes

If `host_scope` includes production:

- confirmation no in-place mutation of original `/wc1/runs/...` inputs
- containment steps used
- any operator approvals

## 10) Follow-Up Work

1. Add or update permanent hillslope seed coverage in `docs/ablation/hillslope_watchlist.csv` when status is `resolved`, `resolved-and-hardened`, or `closed`.
2. `<item>`
3. `<item>`
