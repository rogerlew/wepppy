# Incident Report: p258 + p1319 Hillslope SIGFPE (`watbal_hourly` `log10` domain)

- `incident_id`: `20260425_p258-p1319_hillslope_sigfpe-watbal-log10`
- `status`: `closed`
- `scope`: `hillslope`
- `author`: `Codex`
- `date_utc`: `2026-04-26`
- `host_scope`: `mixed`

## 1) Summary

Two hillslope seeds crash on current release hillslope binary with `SIGFPE` rooted at
`log10f` in `watbal_hourly_`.
Observe-only lane O0 identified the concrete boundary: `fc/ul = 0` at hk
initialization (`hk = -2.655 / alog10(fc/ul)`).
Guard lane G1 (`fc/ul <= 0 -> hk=0`) resolves both incident seeds and passes the
required fuzzy regression gate.
Post-fix rebuild with pinned system compiler (`/usr/bin/gfortran`) preserves
behavior (`C120`,`C121`; `FUZZ_G1_SYS`) and resolves the prior Homebrew
interpreter mismatch.

- failing run/config:
  - `/geodata/wc1/runs/tw/twenty-two-fratricide/wepp/runs/p258.run`
  - `/geodata/wc1/runs/un/unveiled-grinder/wepp/runs/p1319.run`
- failure signature: `SIGFPE` (`log10f`, `watbal_hourly_`)
- first observed time: 2026-04-25 (reproduced 2026-04-26 UTC in this package)
- current impact: release hillslope binary hard-fails on both incident seeds

## 2) Impact and Blast Radius

- affected hosts: production-origin inputs on `wepp1`, replayed on `forest`
- affected runids/configs: `twenty-two-fratricide:p258`, `unveiled-grinder:p1319`
- user-facing effect: hillslope simulation aborts without completion marker
- severity: high for affected configurations (hard failure)

## 3) Baseline Reproduction

- source error files:
  - `artifacts/logs/C100.source_p258.err.txt`
  - `artifacts/logs/C101.source_p1319.err.txt`
- baseline commands:
  - `timeout 180 /home/workdir/wepp-forest/release/wepp_260421b_hill < p258.run`
  - `timeout 180 /home/workdir/wepp-forest/release/wepp_260421b_hill < p1319.run`
  - `timeout 180 /home/workdir/wepp-forest/src/wepp_hill < p258.run`
  - `timeout 180 /home/workdir/wepp-forest/src/wepp_hill < p1319.run`
- baseline result (`PASS|FAIL|ERROR`): `FAIL` on all four baseline replays
- baseline signature (signal/backtrace/success-marker status):
  - signal: `SIGFPE`
  - frame family: `log10f` with `watbal_hourly_` address resolution
  - success marker: absent

## 4) Ablation Findings

- first known failing cases in this cycle: `C100`,`C101`
- observe-only attribution lane: `C104`,`C105`
  - last marker before trap shows `fc=0`, `ul>0`, `ratio=0.0`
- guard closure lane: `C110`,`C111`
  - both complete with success marker and no SIGFPE
- guard closure confirmation on pinned-system rebuild: `C120`,`C121`
  - both complete with success marker and no SIGFPE
- upstream mutation lanes (`U*`): not executed (eligibility not met after guard closure)
- confidence level (`low|medium|high`): `high`

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

## 6) Root Cause Hypothesis / Scientific Rationale

Leading technical hypothesis (supported by O0 evidence):
- In hourly water-balance initialization, at least one layer can have `fc=0` while
  `ul>0`; this drives `fc/ul` to `0.0` and evaluates `alog10(0.0)`, which traps
  under current floating-point settings.

Competing hypotheses deprioritized:
- `perc.for` horizon-transition arithmetic was considered, but O0 markers localize
  the first failing boundary earlier at hk initialization in `watbal_hourly`.

Scientific rationale for kept guard:
- When `fc/ul <= 0`, no physically meaningful positive ratio exists for the
  calibration expression; setting hk adjustment to `0` is a bounded hardening
  fallback that avoids undefined arithmetic and permits full simulation.

## 7) Remediation Decision

- selected fix:
  - `G1`: guard non-positive `fc/ul` domain in `src/watbal_hourly.for` hk
    initialization (`hk=0` when `fc/ul <= 0`), otherwise preserve original formula
- why this fix:
  - directly targets observed fault boundary with one mechanism
  - resolves both incident seeds
  - passes required fuzzy regression gate on incident + watchlist case set
- rollback plan:
  - if non-target regressions appear in future watchlist expansions, revert G1 and
    reopen guarded U-lane campaign
- required validations:
  1. incident seeds pass (`C110`,`C111`,`C120`,`C121`) ✅
  2. fuzzy gate no-regression rule ✅
  3. binary gates executed ✅
     - smoke gates: pass
     - reconciled-condenser replay gate: pass
     - readelf interpreter gate: pass (`/lib64/ld-linux-x86-64.so.2` for `wepp` + `wepp_hill`)
     - pytest: canonical full pass in `artifacts/logs/gates/pytest.stdout.txt` (`43 passed`)
- non-regression gate status: `pass`
- fuzzy-regression gate status: `pass`

## 8) Production Safety Notes

- No in-place mutation of original `/geodata/wc1/runs/...` files.
- All incident runs executed on staged copies under `artifacts/repro/*` and
  `artifacts/logs/replays/*`.
- Source path correction documented: requested p258 disturbed9002 path was not
  present; active source path was `/geodata/wc1/runs/tw/twenty-two-fratricide/wepp/runs/p258.err`.

## 9) Follow-Up Work

1. Preserve G1 as minimal patch candidate and keep O0 markers available for future attribution.
2. Keep release docs aligned with pinned compiler + readelf gate workflow to prevent Homebrew-linked binaries from entering vendoring.
3. If promotion is approved, vendor only the system-linked artifacts with hashes recorded in `artifacts/logs/gates/sha256_sys.txt`.

## 10) Closeout Decision

- campaign closeout: `complete`
- recommendation: `promote`
- release target: `wepp_260425` and `wepp_260425_hill` built with pinned `/usr/bin/gfortran`
