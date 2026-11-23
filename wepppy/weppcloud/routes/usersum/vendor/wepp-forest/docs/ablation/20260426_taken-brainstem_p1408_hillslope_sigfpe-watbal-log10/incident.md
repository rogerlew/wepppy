# Incident Report: taken-brainstem p1408 Hillslope SIGFPE (`watbal` `log10` domain)

- `incident_id`: `20260426_taken-brainstem_p1408_hillslope_sigfpe-watbal-log10`
- `status`: `closed`
- `scope`: `hillslope`
- `author`: `Codex`
- `date_utc`: `2026-04-26`
- `host_scope`: `mixed`

## 1) Summary

A production-origin hillslope seed (`taken-brainstem:p1408`) fails with `SIGFPE`
in `wepp_260425_hill`. Reproduction on `forest` confirms the same signature on both
release and source binaries. Observe-only lane localized the boundary to
`watbal` hk initialization (`hk = -2.655 / alog10(fc/ul)`) with `fc=0` and
`ul>0` (`ratio=0.0`). A minimal guard lane in `watbal.for` resolves the seed and
passes focused fuzzy regression.

This package was reopened for a semantic-parity phase against
`wepp_dcc52a6_hill` comparator outputs. New parity lanes (`C300`,`C310`) both
complete successfully and produce structurally valid non-empty outputs; key
summary metrics are effectively aligned (for example annual runoff equal and
annual precipitation delta `-0.01 mm`).

- failing run/config:
  - `/geodata/wc1/runs/ta/taken-brainstem/wepp/runs/p1408.run`
- failure signature:
  - `SIGFPE` (`log10f`); `addr2line` frame resolves to `watbal_`
- first observed time:
  - 2026-04-26 (from wepp1 failure report)
- current impact:
  - resolved for hillslope replay scope (`p1408` now completes to 100 years with
    success marker on guarded candidate/release build path)

## 2) Impact and Blast Radius

- affected hosts:
  - source failure on `wepp1`; replay and ablation on `forest`
- affected runids/configs:
  - `taken-brainstem:p1408` (hillslope)
- user-facing effect:
  - hillslope execution aborts without completion marker
- severity:
  - high for this run configuration (hard failure)

## 3) Baseline Reproduction

- source error file:
  - `artifacts/logs/C100.source_p1408.err.txt`
- baseline command:
  - `timeout 180 /workdir/wepppy/wepp_runner/bin/wepp_260425_hill < p1408.run`
- baseline result (`PASS|FAIL|ERROR`):
  - `FAIL` (`C100`)
- baseline signature (signal/backtrace/success-marker status):
  - signal: `SIGFPE`
  - frame family: `watbal_` (via `addr2line` from backtrace address)
  - success marker: absent

## 4) Ablation Findings

- first known failing case:
  - `C100` (release baseline), `C101` (source baseline)
- nearest passing case:
  - `C110`/`C111` (guard lane), `C300` (comparator), `C310` (candidate parity lane)
- minimal failing delta:
  - non-positive `fc/ul` at hk initialization (`ratio=0.0`) in observe lane `C104`
- confidence level (`low|medium|high`):
  - `high` for crash root cause and guard closure
  - `medium-high` for semantic parity against comparator (`C300` vs `C310`)

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
- semantic parity artifacts:
  - `./artifacts/logs/C300.output_stats.txt`
  - `./artifacts/logs/C310.output_stats.txt`
  - `./artifacts/logs/C300.pass_event_counts.txt`
  - `./artifacts/logs/C310.pass_event_counts.txt`
  - `./artifacts/logs/C300_C310.loss_metric_deltas.txt`
  - `./artifacts/logs/C300_C310.sha256.txt`

## 6) Root Cause Hypothesis / Scientific Rationale

Leading hypothesis supported by O0 evidence:
- In `watbal` (non-hourly path), hk initialization uses `alog10(fc/ul)`.
  For this seed, at least one layer has `fc=0` while `ul>0`, producing
  `fc/ul = 0.0` and invalid `alog10(0.0)` under trap-enabled builds.

Competing hypothesis deprioritized:
- `watbal_hourly` regression from prior incidents. This incident’s backtrace and
  symbol mapping localize to `watbal_`, not `watbal_hourly_`.

Scientific rationale for kept guard:
- When `fc/ul <= 0`, no physically meaningful positive log-domain ratio exists
  for the hk expression. Setting `hk=0` is a bounded hardening fallback that
  avoids undefined arithmetic while preserving original behavior for valid ratios.

## 7) Remediation Decision

- selected fix:
  - guard in `src/watbal.for` hk initialization:
    - `if ui_hk_ratio > 0 then hk = -2.655 / alog10(ui_hk_ratio)`
    - `else hk = 0.0`
- reopened semantic-parity phase:
  - compare guarded candidate (`/workdir/wepp-forest/src/wepp_hill`) against
    `wepp_dcc52a6_hill` on the same staged `p1408` seed
- why this fix:
  - one-mechanism, directly tied to observed boundary (`fc=0`, `ul>0`, `ratio=0`)
  - closes incident seed deterministically (`C110`,`C111`)
  - passes focused fuzzy regression gate with no comparator-pass regressions
  - candidate outputs remain semantically aligned with comparator in reopened
    parity lanes (`C300`,`C310`)
- rollback plan:
  - revert guard if future non-target regressions are observed and reopen campaign
    with additional observe-first lanes
- required validations:
  1. baseline reproduced (`C100`,`C101`) ✅
  2. observe-only localization (`C104`) ✅
  3. guard closure (`C110`,`C111`) ✅
  4. fuzzy gate (11 seeds, paired lanes) ✅
  5. candidate hillslope smoke gate (`tools/smoke_wepp_binary_host.sh`) ✅
  6. semantic parity replay vs comparator (`C300`,`C310`) ✅
- non-regression gate status (if mutation lane):
  - `pass` (watchlist unchanged)
- fuzzy-regression gate status:
  - `pass`

## 8) Production Safety Notes

- No in-place mutation of `/geodata/wc1/runs/...` originals.
- All replays used staged seed copies under `artifacts/repro/seeds/p1408` and
  `artifacts/logs/replays/*`.
- Production host use was read-only path validation and seed copy.

## 9) Follow-Up Work

1. Keep `p1408` in the permanent hillslope watchlist for every pre-vendor
   regression gate.
2. Preserve observe markers for future numerical-boundary triage in `watbal`.
3. Track downstream watershed EOF fallout separately under incident
   `20260426_taken-brainstem_pw0_watershed_eof-wshpas-h1408`.
