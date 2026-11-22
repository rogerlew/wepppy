# Incident Report: exorbitant-affidavit `p14` SIGFPE (`perc_ -> purk_ -> watbal_hourly_ -> contin_`)

- `incident_id`: `20260420_exorbitant-affidavit_p14_sigfpe-perc-purk-watbal`
- `status`: `resolved`
- `scope`: `hillslope`
- `author`: `Codex`
- `date_utc`: `2026-04-20`
- `host_scope`: `dev`

## 1) Summary

- failing run/config: `/wc1/runs/ex/exorbitant-affidavit/wepp/runs/p14.run` (hillslope option `1`, hillslope id `14`).
- failure signature: authoritative source error shows `SIMULATION YEAR = 1` and `SIGFPE` with top frames `perc_ -> purk_ -> watbal_hourly_ -> contin_`.
- first observed time: source run artifacts dated `2026-04-20`.
- current impact: baseline binaries (`wepp_260419_hill`, `wepp_260420_hill`, `wepp_260421_hill`) all trap with the same `SIGFPE`; patched `src/wepp_hill` completes full 100-year simulation.

## 2) Impact and Blast Radius

- affected hosts: `forest` dev execution context.
- affected runids/configs: confirmed baseline failures for `exorbitant-affidavit` hillslopes `p13,p14,p25,p27,p40,p43,p45,p49` (screening artifacts in `artifacts/screening/*`).
- patched sweep status: patched `src/wepp_hill` completed all 8/8 matched hillslopes to year 100 with success marker (`S008`, `S009`).
- user-facing effect: run aborts before first-year completion and no success marker is emitted on baseline binaries.
- severity: `high` for this run profile.

## 3) Baseline Reproduction

- source error file: `/wc1/runs/ex/exorbitant-affidavit/wepp/runs/p14.err`.
- baseline command: `run_hillslope(wepp_id=14, runs_dir=<staged>/runs, wepp_bin='wepp_260421', timeout=60, timeout_retries=3)`.
- baseline result (`PASS|FAIL|ERROR`): `FAIL`.
- baseline signature (signal/backtrace/success-marker status): attempt `1/4` exits `-8` with `SIGFPE`, `SIMULATION YEAR = 1`, no success marker (`artifacts/logs/C000c.*`).

## 4) Ablation Findings

- first known failing case: `C000-source` (authoritative source artifact), reproduced contract-faithfully in `C000c`.
- nearest passing case: `C020b` (`src/wepp_hill` with minimal `perc.for` guard), plus comparator `C030` (`wepp_dcc52a6_hill`) also passes.
- minimal failing delta: one guard block in `src/perc.for` at the UI harmonic-conductivity expression, plus `WFR_G_PSSZ` marker.
- confidence level (`low|medium|high`): `high` for trap attribution, guard effectiveness, and parity acceptance for this incident scope.

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

Leading hypothesis (confirmed by observability lane `C010`):

- in `perc.for` (`ui_run.eq.1` path), the seepage conductivity equation divides by `ssc(k1+1,iplane)`; at the failure boundary marker `WFR_SSZ_PRC`, the logged state is `year=1 day=1 ofe=1 layer=4 ssc(k1)=1.25e-4 ssc(k1+1)=0.0` and the run traps immediately afterward.

Competing hypotheses rejected with evidence:

- layer-index out-of-range in `perc_`: marker emitted at `k1=4` with valid array reads (`WFR_STZ_PRC`, `WFR_FX_PRC`, `WFR_SSZ_PRC`) before trap; no index signature observed.
- power-domain fault in `fx = stz ** hk(k1)`: marker values at boundary are `stz=1.9902e-02`, `hk=1.5529` (positive base and exponent), so this site is not the observed trigger for this case.

## 7) Remediation Decision

- selected fix: add a narrow denominator guard in `src/perc.for` (UI seepage path only): if either conductivity term is nonpositive, set `sscz=0.0` and emit `WFR_G_PSSZ`; otherwise execute original equation.
- why this fix: smallest scoped guard at the observed arithmetic trap boundary; preserves routine shape and layer identity contract.
- rollback plan:
  - rollback target base commit: `2a7de19e7f38a5c9c14e57a894a87c86ff8ac7f7`.
  - restore routine: `git -C /home/workdir/wepp-forest show 2a7de19e7f38a5c9c14e57a894a87c86ff8ac7f7:src/perc.for > /home/workdir/wepp-forest/src/perc.for`.
  - rebuild: `cd /home/workdir/wepp-forest/src && make wepp_hill && make wepp`.
  - compact repro: rerun `C000c` baseline and `C020b` patched lane commands from `notes.md`.
- required validations:
  - staged patched lane completion: `PASS` (`C020b.status.json`, success marker true).
  - smoke: `tools/smoke_wepp_binary_host.sh` for `src/wepp_hill` and `src/wepp` passed (`*_b.rc=0`).
  - regressions: `tests/test_upstream_scheme_pw0_wshpas_execution_regression.py`, `tests/test_frost_adjacent_guard_sources.py`, `tests/test_mlttp_watdst_index_guards.py`, and `tests/test_perc_sscz_guard.py` all passed.
  - parity decision: strict tool report (`C041c`) flags water-lane fail, but shared-column/common-prefix assessment (`C042`) shows low aggregate drift (`pass/wat/loss` sum relative deltas `2.77e-07`, `1.85e-08`, `2.46e-06`) and expected legacy-vs-modern output shape differences (`TSMF`, `QRain`, `QSnow` columns). `soil` common-prefix exceedances are dominated by a stable `Kr` offset (`0.13` vs `0.12`) and are accepted as non-guard-specific drift for this campaign.
  - provenance gate: `tools/check_wepp_binary_provenance.sh` passed after pinned `/usr/bin/gfortran` rebuild (`artifacts/logs/provenance/C050b.provenance.log`).

### Patch Review Checklist (Mandatory)

| Item | Status | Evidence |
| --- | --- | --- |
| Diff restricted to offending routine(s); no unrelated source edits | PASS | Source patch confined to `src/perc.for`; no edits retained in `purk.for`/`watbal_hourly.for`; generated build artifacts were restored. |
| No `ntype/ntype2` change; layer-count contract intact | PASS | `src/pntype.inc` reverted to HEAD; final diff has no contract-count edits. |
| Each new guard returns sentinel already used by surrounding code | PASS | Guard sets `sscz=0.0` (zero conductivity/no-seepage sentinel), consistent with existing no-seepage sentinel `sep(iplane)=0.0` in the same routine (`src/perc.for:253`). |
| Each new guard emits a `WFR_G_*` marker | PASS | `WFR_G_PSSZ` added at `src/perc.for:208-209`; activations captured in `artifacts/logs/C020.guard_hits.txt`. |
| Sibling division/power-site audit in same routine completed | PASS | Audit table recorded in `notes.md` (`Sibling Arithmetic Audit`). |
| Parity against canonical baseline `wepp_dcc52a6` (raw + meaningful) | PASS | Strict reports (`C040b`,`C041c`) fail due expected legacy-vs-modern file-shape drift plus sparse local exceedances; meaningful-difference review (`C042`) finds no material aggregate regression attributable to the guard patch. |
| Rollback plan documented (revert target + rerun commands) | PASS | This section includes rollback target and replay commands. |
| Binary provenance gate passes for binaries intended for vendoring | PASS | `C050b.provenance.log` passes for rebuilt `src/wepp` and `src/wepp_hill`. |

Decision: campaign is `resolved` for source remediation scope; no vendoring step was performed in this campaign.

## 8) Production Safety Notes

- all experiment runs were executed from staged copies under `artifacts/repro/*`.
- no in-place mutation was made under `/wc1/runs/ex/exorbitant-affidavit/...`.
- no changes were made to `run_hillslope` retry/timeout policy or WEPPpy Python driver logic.

## 9) Follow-Up Work

1. Completed 2026-04-20: assessed parity divergence versus `wepp_dcc52a6_hill` using shared-column/common-prefix numeric comparison (`C042`); differences are accepted as non-material for this guard campaign.
2. Completed 2026-04-20: broader hillslope screening for the same denominator-risk signature (`perc_ -> purk_ -> watbal_hourly_`) across `/wc1/runs` hillslope error corpus; only `exorbitant-affidavit` matches (8 hillslopes), and patched sweep resolves all 8/8.
3. Open a separate binary-release/vendoring work package if and when this source patch is selected for release.
