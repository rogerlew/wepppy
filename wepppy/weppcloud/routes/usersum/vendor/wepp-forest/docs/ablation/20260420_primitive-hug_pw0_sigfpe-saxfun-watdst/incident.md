# Incident Report: primitive-hug `pw0` SIGFPE (`saxfun_ -> watdst_ -> frostn_ -> winter_ -> wshdrv_`)

- `incident_id`: `20260420_primitive-hug_pw0_sigfpe-saxfun-watdst`
- `status`: `resolved`
- `scope`: `watershed`
- `author`: `Codex`
- `date_utc`: `2026-04-20`
- `host_scope`: `dev`

## 1) Summary

- failing run/config: `/wc1/runs/pr/primitive-hug/wepp/runs/pw0.run` with watershed path.
- failure signature: authoritative source error shows `SIMULATION YEAR = 13` and `SIGFPE` with top call chain `saxfun_ -> watdst_ -> frostn_ -> winter_ -> wshdrv_`.
- first observed time: source run artifacts dated `2026-04-20`.
- current impact: source baseline hard-stops at year 13; patched `src/wepp` lane (`C021`) completes the full 14-year watershed run.

## 2) Impact and Blast Radius

- affected hosts: `forest` dev execution context.
- affected runids/configs: confirmed on `primitive-hug/pw0`; broader runid screening remains follow-up work.
- user-facing effect: patched binary removes the observed crash for this run profile; baseline binary still exhibits the failure signature.
- severity: `high` at baseline, `mitigated` for patched lane.

## 3) Baseline Reproduction

- source error file: `/wc1/runs/pr/primitive-hug/wepp/runs/pw0.err`
- baseline command: source artifact inspection plus partial direct replay commands captured in `notes.md`.
- baseline result (`PASS|FAIL|ERROR`): `FAIL` for source evidence (`C000-source`), with earlier replay attempts (`C000`, `C010`-`C013`) ending `ERROR` from runtime-budget interruption.
- baseline signature (signal/backtrace/success-marker status): `SIGFPE`, top frame `saxfun_`, success marker absent in source failing artifact.

## 4) Ablation Findings

- first known failing case: `C000-source` (authoritative source log).
- nearest passing case: `C021` (`L05`) using patched `src/wepp`, completed year 14/day 365 with success marker.
- minimal failing delta: arithmetic/domain guards in `src/saxfun.for` (`WFR_G_SLYI`, `WFR_G_SSMN`, `WFR_G_SPOR`, `WFR_G_SDEN`, `WFR_G_SEXP`) with no `ntype/ntype2` change.
- confidence level (`low|medium|high`): `high` for this run-level mitigation, `medium` for exact physics-state trigger at baseline year-13 boundary.

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

Supported hypothesis: failure is in frost/water-distribution arithmetic (`saxfun_`/`watdst_`) reached from watershed winter processing, consistent with the source backtrace and the patched lane clearing the previous year-13 boundary. Compact contract-valid replays (`C010`-`C013`) established prompt fidelity; `C021` then demonstrated full-run completion under the guard patch.

## 7) Remediation Decision

- selected fix: runtime/domain guard patch in `src/saxfun.for` accepted for this incident closeout.
- why this fix: source-level arithmetic paths in `saxfun` include known FPE-risk operations (power/divide) under degenerate inputs; the patch adds bounded guards plus observability without changing `ntype/ntype2` contracts.
- rollback plan: if broader regression screening fails, revert `src/saxfun.for` guard block and rerun baseline plus compact repro suite.
- required validations: completed `C021` unattended long-horizon lane (year 14 success) plus source-level and execution regression tests documented in `notes.md`.

## 8) Production Safety Notes

- this session primarily used copied/staged inputs; some direct run attempts executed from `/wc1/runs/pr/primitive-hug/wepp/runs` to preserve input contract fidelity.
- source-code patch was applied in `src/saxfun.for` only; no `ntype/ntype2` edits were made.
- no operator approval workflow required in this dev-context run.

## 9) Follow-Up Work

1. Run additional non-`pw0` watershed configs to confirm no regressions from `saxfun` guard logic.
2. Keep the resumable harness/heartbeat enhancement as operational debt reduction for future long-horizon incidents.
3. If needed, refine guard telemetry to pinpoint which guard branch first prevents baseline year-13 failure state.
