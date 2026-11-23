# Incident Report: operational-berry `pw0` SIGFPE (`locate_ -> frostn_ -> winter_ -> wshdrv_`)

- `incident_id`: `20260419_operational-berry_pw0_sigfpe-locate-frostn`
- `status`: `resolved`
- `scope`: `watershed`
- `author`: `Codex`
- `date_utc`: `2026-04-19`
- `host_scope`: `dev`

## 1) Summary

- failing run/config: `/wc1/runs/op/operational-berry/wepp/runs/pw0.run` (staged copies only for ablation)
- failure signature: `SIGFPE` at `SIMULATION YEAR = 24`, top frame `locate_`
- first observed time: baseline reproduced at `2026-04-19T19:09:10Z` (`C000`)
- current impact: patched binary (`/home/workdir/wepp-forest/src/wepp`) completes full 45-year staged run (`C070`, `C071`)

## 2) Impact and Blast Radius

- affected hosts: reproducible on `forest` using local rq-worker binary parity (`/workdir/wepppy/wepp_runner/bin/wepp_260419`)
- affected runids/configs: confirmed for `operational-berry/pw0`; trigger depends on full watershed complexity (full hillslope pass set)
- user-facing effect: watershed run aborts with floating-point trap
- severity: high for impacted run(s) because results are not produced

## 3) Baseline Reproduction

- source error file: `/wc1/runs/op/operational-berry/wepp/runs/pw0.err`
- baseline command: `/workdir/wepppy/wepp_runner/bin/wepp_260419 < .../artifacts/repro/C000/runs/pw0.run`
- baseline result (`PASS|FAIL|ERROR`): `FAIL`
- baseline signature (signal/backtrace/success-marker status): `SIGFPE`, backtrace resolves to `locate_ -> frostn_ -> winter_ -> wshdrv_`, no success completion

## 4) Ablation Findings

- first known failing case: `C000` (baseline), `C013/14/15` (year sweep at/after 24), `C059` (full pass set)
- nearest passing case: `C058` (`first_n_hillslopes=230`), `C031` (impoundment `No`), `C020-023` (single output toggles `No`)
- minimal failing delta:
  - input-space boundary: `C058 -> C059` (`230 -> 231` hillslopes) flips `PASS -> FAIL`
  - fix-space boundary: `C061 -> C070` (same staged inputs; binary changes from unguarded to guarded `locate`) flips `FAIL -> PASS`
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

## 6) Root Cause Hypothesis

Leading hypothesis: in frost/winter processing, `locate` is called with a depth that maps to `layern=5` while `nsl(iplane)=4` for at least one hillslope context (`C061` observe log: `LOC_BAD_LYR ... v1=5 v2=4` at `y=2003 d=69 e=8`).

Without a bounds guard, `locate` proceeds to denominator operations using out-of-range layer state (`nfine(layern)` / `fthick`) and trips `SIGFPE` under `-ffpe-trap`.

Competing hypotheses (pure denominator-zero with valid layer, random runtime nondeterminism) were deprioritized because the sparse observe lane captured deterministic out-of-range layer index immediately before trap, and a targeted `locate` guard eliminated the failure with unchanged inputs.

## 7) Remediation Decision

- selected fix: data-triggered numeric/index guard in `src/locate.for` with no runfile contract changes:
  - guard invalid `nsl`
  - clamp/bound `layern` to valid profile limits (with bottom-layer return on `layern > nsl`)
  - guard non-positive `nfine(layern)` denominator
  - guard near-zero `fthick`
  - bound `flyern` and endpoint decrement behavior
- why this fix: minimal containment at the crashing operation boundary (`locate`), preserving existing contracts while preventing floating-point trap conditions
- rollback plan: revert `src/locate.for` guard block and `src/wepp_observe.for` frost-scope tag filter additions
- required validations: completed (`C070/C071`, host smokes, targeted instability pytest)

## 8) Production Safety Notes

- This incident was executed in `dev` scope only.
- Original `/wc1/runs/op/operational-berry/*` inputs were not mutated in place.
- All ablation mutations were applied only under incident staging paths (`artifacts/repro/C*`).

## 9) Follow-Up Work

1. Add upstream depth-contract clamp(s) in frost/winter callers before invoking `locate` so `layern > nsl` requests are reduced at source.
2. Add regression fixture covering a `layern > nsl` trigger path to prevent reintroduction of this fault class.
3. Evaluate whether selected watershed output toggles/impoundment settings are surfacing latent frost-depth state inflation, and document expected bounds in model notes.
