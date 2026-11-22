# Incident Report: suppurative-skunk `pw0` SIGFPE (`wshdrv_`)

- `incident_id`: `20260418_suppurative-skunk_pw0_sigfpe-wshdrv`
- `status`: `mitigated-dev`
- `scope`: `watershed`
- `author`: `Codex`
- `date_utc`: `2026-04-19`
- `host_scope`: `dev`

## 1) Summary

- failing run/config: `/wc1/runs/su/suppurative-skunk/wepp/runs/pw0.run`
- failure signature: `SIGFPE` at simulation year `13`, top frame `wshdrv_`
- first observed time: `2026-04-19T04:37:36Z` (source run logs)
- current impact:
  - baseline worker binary `wepp_260418` aborts before success marker (`C000`, `C004`).
  - guarded candidate binary `/home/workdir/wepp-forest/src/wepp` completes (`C028`, `C030`, `C031`).

## 2) Impact and Blast Radius

- affected hosts: `forest` (local dev host in this incident)
- affected runids/configs: confirmed for `suppurative-skunk/pw0` with `wepp_260418`; mitigated with guarded candidate build
- user-facing effect: hard-stop failure on baseline binary; containment verified with guarded binary replay
- severity: `high` on baseline binary; `mitigated in dev` with guarded build

## 3) Baseline Reproduction

- source error file: `/wc1/runs/su/suppurative-skunk/wepp/runs/pw0.err`
- baseline command:
  - `cd /workdir/wepp-forest/docs/ablation/20260418_suppurative-skunk_pw0_sigfpe-wshdrv/artifacts/repro/C000/wepp/runs && /home/workdir/wepppy/wepp_runner/bin/wepp_260418 < pw0.run > .../C000.stdout.txt 2> .../C000.stderr.txt`
- baseline result (`PASS|FAIL|ERROR`): `FAIL` (`matrix.csv` row `C000`)
- baseline signature (signal/backtrace/success-marker status): `SIGFPE`, `wshdrv_`, success marker absent

## 4) Ablation Findings

- first known failing case: `C004` (`sim_years=13`) on baseline binary `wepp_260418`
- nearest passing case: `C030` (`sim_years=13`) on guarded binary `/home/workdir/wepp-forest/src/wepp`
- minimal failing vs passing delta:
  - **Primary FAIL->PASS flip**: binary-only delta (same staged inputs, no `pw0.run`/`pw0.str` changes): `C004 FAIL` -> `C030 PASS`
  - **Data trigger boundary (baseline binary)**: `sim_years 12 -> 13` flips `PASS -> FAIL` (`C003 -> C004`)
  - **Containment replay**: full-run case `C028` reaches year `300` and emits `WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY`
  - **Subset lane blocker**: direct first-`N` runfile mutation with `N < 264` fails structure contract before watershed simulation (`C013`-`C017`, `C019`-`C027`), so minimal `H*.pass.dat` isolation remains blocked in runfile-only mode.
- confidence level (`low|medium|high`): `high` for binary containment efficacy and baseline year-13 boundary; `high` that subset isolation is blocked by runfile/structure mismatch

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

Leading hypothesis:
- The watershed routing path encounters data-triggered denominator/celerity degeneracy (tiny/invalid values), causing arithmetic traps under `-ffpe-trap`:
  - `wshdrv.for:1019` (`runvol/rvolon`)
  - `wshchr.for` Muskingum-Cunge coefficient path (`ckref`-driven overflow chain) and channel ratio divisions
  - `case34.for` channel sediment-routing ratio divisions

Why alternatives were rejected:
- Watershed output toggles (`chnwb`, `soil_pw0`, `plot_pw0`, `ebe_pw0`) do not change failure outcome (`C007`-`C010` all fail with same signature).
- Impoundment `Yes` still fails with same signature (`C011`).
- Impoundment `No` did not produce a clean A/B because prompt-sequence contract diverged and failed earlier (`C012`).
- Pass-subset direct first-`N` edits do not reach watershed years unless `N=264` due `pw0.str` consistency requirement; therefore they cannot yet support causal single-pass isolation in this mutation mode.

## 7) Remediation Decision

- selected fix: `data-triggered numeric guard in watershed routing code path`
- why this fix:
  - immediate containment for crashing runs required binary-side guards, while keeping `pw0.run`/`pw0.str` untouched
  - verified `FAIL -> PASS` flip on identical staged inputs (`C004` vs `C030`)
  - verified full-run completion to success marker (`C028`)
- rollback plan:
  - keep binary guard change isolated and feature-flagged at build/release level
  - revert to previous vetted binary tag if regression appears in parity/smoke checks
- required validations:
  - replay this incident package baseline and sim-year boundary (`12/13/15`) with guarded binary
  - compare watershed outputs for non-failing control runs (parity smoke)
  - add a pre-run validator for runfile/`pw0.str` hillslope-count consistency to fail fast with explicit contract error

## 8) Production Safety Notes

- `host_scope` is `dev` only in this incident.
- originals under `/wc1/runs/...` were not mutated in place; all ablation mutations were in `docs/ablation/.../artifacts/repro/*`.

## 9) Follow-Up Work

1. Add a structure-consistent first-`N` subset generator (mutate `pw0.run` + `pw0.str` + dependent channel references together) and rerun subset binary search for single-`H*.pass.dat` isolation.
2. Run full `wepp-forest` quality/vendoring gates for this candidate build (`smoke_wepp_binary_host`, `pytest`, reconciled-condenser manual replay, ELF interpreter check).
3. Vendor guarded binary into `wepppy/wepp_runner/bin` under a new dated filename after gate pass and update release provenance (`change-log.md` + wepppy binary provenance docs).
4. Add automated regression coverage for this incident signature (baseline fail on `wepp_260418`, pass on guarded binary).
