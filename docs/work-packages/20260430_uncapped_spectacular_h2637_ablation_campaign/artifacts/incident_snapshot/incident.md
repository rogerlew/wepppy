# Incident Report: uncapped-spectacular H2637 day-44 closure spike

- `incident_id`: `20260430_uncapped-spectacular_h2637_hillslope_closure-spike`
- `status`: `active`
- `scope`: `hillslope`
- `author`: `codex`
- `date_utc`: `2026-04-30`
- `host_scope`: `mixed`
- `contract_refs`: `none`

## 1) Summary

- failing run/config: `runid=uncapped-spectacular`, hillslope `H2637` (`p2637.run`).
- failure signature: large one-day closure spike on `year=1987`, `julian=44` in the legacy daily OFE closure diagnostic.
- first observed time: production outputs generated on `2026-04-30` from `wepp_260429_hill` (`sha256=0a7a5ced...`).
- current impact: closure-audit consumers can see a severe day-44 anomaly on current production binary lineage.

## 2) Impact and Blast Radius

- affected hosts: source anomaly reproduced from `wepp1` artifact set; Linux replay on `forest` with copied production binary reproduced same signature.
- affected runids/configs: confirmed on `uncapped-spectacular/H2637`; not yet generalized to other hillslopes.
- user-facing effect: audit residuals can be interpreted as a model/data error event for this hillslope day.
- severity: `medium` (analysis quality and confidence risk, not a hard runtime crash).

## 3) Baseline Reproduction

- source error file: `/geodata/wc1/runs/un/uncapped-spectacular/wepp/runs/p2637.err`.
- baseline command: `cd artifacts/repro/staged/runs && ../../source_wepp1/bin/wepp_260429_hill < p2637.run`.
- baseline result (`PASS|FAIL|ERROR`): `PASS` (simulation completes).
- baseline signature: day-44 legacy closure spike reproduced (`day44_hillslope_error_mm_legacy=-180.31779`; dominant OFE error at OFE 19 `-180.4590`).

## 4) Ablation Findings

- first known failing case: `C000` (Linux replay with production binary and full shared context).
- nearest passing case: `C010` and `C020` (same staged inputs with alternate comparator binaries) where day-44 spike is absent.
- minimal failing delta: binary lineage (`wepp_260429_hill`) is the strongest isolated differentiator from comparator lanes.
- confidence level (`low|medium|high`): `medium` (strong lane signal; root-cause routine not yet isolated).

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

Leading hypothesis: this is a binary-lineage numerical behavior difference, not a cross-platform-only effect.

Supporting evidence:
- `C000` (`wepp_260429_hill`, Linux) reproduces the day-44 spike from source outputs.
- `C020` (`wepppy-win-bootstrap.exe` on `blarhg`) does not reproduce the day-44 spike.
- `C010` (`wepp_dcc52a6_hill`) does not reproduce the day-44 spike.

Competing hypotheses considered and currently weaker:
- missing shared run context files: rejected (shared context was staged and used for all replay lanes).
- platform-only drift: weakened by `C020` absence of spike and `C000` Linux reproduction.

## 7) Remediation Decision

- selected fix: no source patch selected in this incident package.
- why this fix: this package was scoped to attribution via ablation, not code modification.
- rollback plan: N/A (no source mutation lanes were promoted).
- required validations: baseline/comparator lane execution + closure diagnostics complete.
- non-regression gate status (if mutation lane): N/A.
- fuzzy-regression gate status: not run (no candidate patch promotion).
- contract disposition match (if mutation lane): N/A.

## 8) Science Contract References

Root-cause hypothesis references:
- `contract_refs`: `none`
- boundary disposition: `na`
- evidence: `artifacts/logs/lane_closure_summary.csv`, `artifacts/logs/lane_day44_legacy_closure.csv`

Remediation decision references:
- `contract_refs`: `none`
- boundary disposition: `na`
- evidence: `artifacts/logs/lane_closure_summary.csv`

Upstream mutation lanes:

| Lane ID | Contract refs | Boundary disposition | Observation evidence | Decision |
| --- | --- | --- | --- | --- |
| `none` | `none` | `na` | `artifacts/logs/lane_closure_summary.csv` | `blocked` |

Unresolved model gaps:

| Gap | Disposition | Evidence | Follow-up owner |
| --- | --- | --- | --- |
| Precise routine/state origin of day-44 OFE19 spike under `wepp_260429_hill` | `requires_scientific_review` | `artifacts/logs/lane_day44_legacy_closure.csv` | WEPP numerical maintainers |

## 9) Production Safety Notes

- no in-place mutation was performed under `/geodata/wc1/runs/...`.
- containment steps: source artifacts copied into incident-local repro directories before replay.
- operator approvals: not required; no production binary replacement or queue mutation performed.

## 10) Follow-Up Work

1. Launch a focused source-level ablation package in `wepp-forest` to isolate the routine-level cause of the OFE19 day-44 spike under `wepp_260429_hill`.
2. Replay additional hillslopes from `uncapped-spectacular` with the same binary trio to determine whether this signature is isolated to `H2637`.
3. If a candidate patch is identified, run fuzzy-regression gates and update `docs/ablation/hillslope_watchlist.csv` when promoting to `resolved`/`closed`.
